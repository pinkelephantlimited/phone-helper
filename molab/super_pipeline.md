# Phone Helper — Full molab Pipeline

One notebook to build **everything**: dataset generation, multilingual
translation, Hugging Face push, fine-tune Qwen2.5-VL-3B on the Blackwell GPU,
and model push.

## How to run

1. Open this notebook in molab.
2. **Attach a GPU** (RTX Pro 6000 Blackwell, 96GB) via the notebook header
   specs button.
3. Set your `HF_TOKEN` in the Setup cell.
4. Run cells top to bottom. Training is the long step (~20–40 min).

Everything is cached on disk + on Hugging Face, so re-runs are cheap.

```{python}
import marimo as mo
```

## 0. Setup

Enter your Hugging Face token. It is used to download the base model and to
push the dataset + fine-tuned model.

```{python}
HF_TOKEN = mo.ui.text(label="Hugging Face token (hf_...)", value="hf_xxx")
mo.hstack([HF_TOKEN]).callout()
```

```{python}
import json
import os
import sys
from pathlib import Path

os.environ["HF_TOKEN"] = HF_TOKEN.value or os.environ.get("HF_TOKEN", "")

GITHUB_REPO = "pinkelephantlimited/phone-helper"
REPO = Path.cwd() / "phone-helper"
if not (REPO / "data").exists():
    import subprocess
    subprocess.run(
        ["git", "clone", f"https://github.com/{GITHUB_REPO}.git", str(REPO)],
        check=True,
    )
sys.path.insert(0, str(REPO / "data" / "pipeline"))
sys.path.insert(0, str(REPO / "train"))
os.chdir(REPO)
print(f"repo at {REPO}")
```

## 1. Check compute

Confirm the GPU is attached and usable.

```{python}
import torch
print("torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM (GB):", round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
mo.md(f"**Device:** `{DEVICE}`")
```

## 2. Dataset size

How many samples per language? 2000 is a good v1; each language gets its own
JSONL + rendered images.

```{python}
N_SAMPLES = mo.ui.number(500, 20000, 2000, step=500, label="samples per language")
mo.hstack([N_SAMPLES]).callout()
```

```{python}
from build_english import build_english
from translate import translate_all
from config import PRIORITY_LANGUAGES
```

## 3. Generate English source

Renders synthetic "daily life" images (expiry dates, prices, signs, menus,
receipts, medicine instructions) + QA pairs in Qwen2.5-VL chat format.

```{python}
build_english(n=int(N_SAMPLES.value), seed=42,
              out_dir=REPO / "data" / "en",
              images_dir=REPO / "data" / "images")
```

## 4. Translate to 12 priority languages

NLLB-200 offline translation. On the attached Blackwell GPU this is fast
(CUDA, batched). Images are re-rendered with per-script fonts (Arabic RTL,
Devanagari, Bengali, CJK, Cyrillic). Results cached on disk.

```{python}
translate_all(src=REPO / "data" / "en" / "train.jsonl",
              out=REPO / "data" / "multilingual",
              images=REPO / "data" / "images",
              langs=PRIORITY_LANGUAGES,
              device=DEVICE)
```

## 5. Verify the dataset

```{python}
import pandas as pd

def stats(lang: str) -> dict:
    p = REPO / "data" / "multilingual" / lang / "train.jsonl"
    n = img = 0
    if p.exists():
        for line in p.open():
            n += 1
            if '"image"' in line:
                img += 1
    return {"language": lang, "rows": n, "with_image": img}

pd.DataFrame(stats(lg) for lg in PRIORITY_LANGUAGES)
```

```{python}
import random
sample = json.loads(random.choice(list((REPO / "data" / "multilingual" / "es" / "train.jsonl").open())))
mo.md(f"**Sample (es):** {sample['messages']}")
```

## 6. Push dataset to Hugging Face

Streams JSONL + images to `pinkelephantlimited/phone-helper-vlm-dataset`.

```{python}
from push_dataset import push_files

push_files(src=REPO / "data" / "multilingual",
           images=REPO / "data" / "images",
           repo="pinkelephantlimited/phone-helper-vlm-dataset",
           token=os.environ.get("HF_TOKEN", ""))
```

## 7. Training config

QLoRA fine-tune of Qwen2.5-VL-3B-Instruct, tuned for the 96GB Blackwell.
`max_steps=0` means "full epochs".

```{python}
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
HUB_REPO = "pinkelephantlimited/phone-helper-vlm-3b"
LR = mo.ui.number(1e-5, 1e-3, 2e-4, step=5e-5, label="learning rate")
EPOCHS = mo.ui.number(1, 5, 1, step=0.5, label="epochs")
BATCH = mo.ui.number(1, 8, 2, step=1, label="per-device batch size")
GRAD_ACCUM = mo.ui.number(1, 16, 8, step=1, label="gradient accumulation")
LORA_R = mo.ui.number(8, 64, 32, step=8, label="LoRA rank")
mo.vstack([LR, EPOCHS, BATCH, GRAD_ACCUM, LORA_R]).callout()
```

```{python}
from train_vlm import train, load_dataset

paths = sorted((REPO / "data" / "multilingual").glob("*/train.jsonl"))
ds = load_dataset(paths)
print(f"dataset rows: {len(ds)}")
```

## 8. Train

**This is the long step.** QLoRA on the Blackwell 6000. The adapter is saved
locally and pushed to Hugging Face with a model card. Watch eval loss — you
want it to go down.

```{python}
train(
    dataset=ds,
    model_id=MODEL_ID,
    hub_repo=HUB_REPO,
    output_dir=str(REPO / "train" / "output"),
    lr=float(LR.value),
    epochs=float(EPOCHS.value),
    max_steps=0,
    batch=int(BATCH.value),
    grad_accum=int(GRAD_ACCUM.value),
    max_len=1536,
    lora_r=int(LORA_R.value),
    lora_alpha=int(LORA_R.value) * 2,
    token=os.environ.get("HF_TOKEN", ""),
)
```

## 9. Verify the trained model

Run a quick inference on a held-out multilingual image to confirm it reads
the text.

```{python}
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image
import torch as T

proc = AutoProcessor.from_pretrained(HUB_REPO, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(HUB_REPO, trust_remote_code=True,
                                              torch_dtype=T.bfloat16, device_map="auto")
model.eval()

img_path = next((REPO / "data" / "images" / "es").glob("*.jpg"))
msgs = [
    {"role": "user", "content": [
        {"type": "image"}, {"type": "text", "text": "¿Cuál es la fecha de caducidad?"}]},
]
txt = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
inputs = proc(text=txt, images=[Image.open(img_path)], return_tensors="pt").to(model.device)
out = model.generate(**inputs, max_new_tokens=64)
answer = proc.decode(out[0], skip_special_tokens=True)
mo.md(f"**Model says:** {answer}")
```

## 10. Done

- Dataset: `pinkelephantlimited/phone-helper-vlm-dataset`
- Model: `pinkelephantlimited/phone-helper-vlm-3b`

Next (outside molab): convert to GGUF and bundle in the mobile app.
