import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Pink Elephant Talk — Full molab Pipeline

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
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 0. Setup

    Enter your Hugging Face token. It is used to download the base model and to
    push the dataset + fine-tuned model.
    """)
    return


@app.cell
def _(mo):
    HF_TOKEN = mo.ui.text(label="Hugging Face token (hf_...)", value="hf_xxx")
    mo.hstack([HF_TOKEN]).callout()
    return (HF_TOKEN,)


@app.cell
def _(HF_TOKEN):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    os.environ["HF_TOKEN"] = HF_TOKEN.value or os.environ.get("HF_TOKEN", "")

    missing = []
    for pkg in ("peft", "bitsandbytes", "accelerate"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-input", *missing],
            check=True,
        )

    GITHUB_REPO = "pinkelephantlimited/pink-elephant-talk"
    REPO = Path.cwd() / "pink-elephant-talk"
    if not (REPO / "data").exists():
        subprocess.run(
            ["git", "clone", f"https://github.com/{GITHUB_REPO}.git", str(REPO)],
            check=True,
        )
    sys.path.insert(0, str(REPO / "data" / "pipeline"))
    sys.path.insert(0, str(REPO / "train"))
    os.chdir(REPO)
    print(f"repo at {REPO}")
    return REPO, json, os


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Check compute

    Confirm the GPU is attached and usable.
    """)
    return


@app.cell
def _(mo):
    import torch
    print("torch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        print("VRAM (GB):", round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1))
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    mo.md(f"**Device:** `{DEVICE}`")
    return (DEVICE,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Dataset size

    How many samples per language? 2000 is a good v1; each language gets its own
    JSONL + rendered images.
    """)
    return


@app.cell
def _(mo):
    N_SAMPLES = mo.ui.number(500, 20000, 2000, step=500, label="samples per language")
    mo.hstack([N_SAMPLES]).callout()
    return (N_SAMPLES,)


@app.cell
def _():
    from build_english import build_english
    from translate import translate_all
    from config import PRIORITY_LANGUAGES

    return PRIORITY_LANGUAGES, build_english, translate_all


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Generate English source

    Renders synthetic "daily life" images (expiry dates, prices, signs, menus,
    receipts, medicine instructions) + QA pairs in Qwen2.5-VL chat format.
    """)
    return


@app.cell
def _(N_SAMPLES, REPO, build_english):
    build_english(n=int(N_SAMPLES.value), seed=42,
                  out_dir=REPO / "data" / "en",
                  images_dir=REPO / "data" / "images")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Translate to 12 priority languages

    NLLB-200 offline translation. On the attached Blackwell GPU this is fast
    (CUDA, batched). Images are re-rendered with per-script fonts (Arabic RTL,
    Devanagari, Bengali, CJK, Cyrillic). Results cached on disk.
    """)
    return


@app.cell
def _(DEVICE, PRIORITY_LANGUAGES, REPO, translate_all):
    translate_all(src=REPO / "data" / "en" / "train.jsonl",
                  out=REPO / "data" / "multilingual",
                  images=REPO / "data" / "images",
                  langs=PRIORITY_LANGUAGES,
                  device=DEVICE)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Verify the dataset
    """)
    return


@app.cell
def _(PRIORITY_LANGUAGES, REPO):
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
    return


@app.cell
def _(REPO, json, mo):
    import random
    sample = json.loads(random.choice(list((REPO / "data" / "multilingual" / "es" / "train.jsonl").open())))
    mo.md(f"**Sample (es):** {sample['messages']}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Push dataset to Hugging Face

    Streams JSONL + images to `pinkelephantlimited/pink-elephant-talk-vlm-dataset`.
    """)
    return


@app.cell
def _(REPO, os):
    from push_dataset import push_files

    push_files(src=REPO / "data" / "multilingual",
               images=REPO / "data" / "images",
               repo="pinkelephantlimited/pink-elephant-talk-vlm-dataset",
               token=os.environ.get("HF_TOKEN", ""))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Training config

    QLoRA fine-tune of Qwen2.5-VL-3B-Instruct, tuned for the 96GB Blackwell.
    `max_steps=0` means "full epochs".
    """)
    return


@app.cell
def _(mo):
    MODEL_ID = "pinkelephantlimited/qwen2.5-vl-3b-instruct-nested"
    HUB_REPO = "pinkelephantlimited/pink-elephant-talk-vlm-3b"
    LR = mo.ui.number(1e-5, 1e-3, 2e-4, step=5e-5, label="learning rate")
    EPOCHS = mo.ui.number(1, 5, 1, step=0.5, label="epochs")
    BATCH = mo.ui.number(1, 8, 2, step=1, label="per-device batch size")
    GRAD_ACCUM = mo.ui.number(1, 16, 8, step=1, label="gradient accumulation")
    LORA_R = mo.ui.number(8, 64, 32, step=8, label="LoRA rank")
    mo.vstack([LR, EPOCHS, BATCH, GRAD_ACCUM, LORA_R]).callout()
    return BATCH, EPOCHS, GRAD_ACCUM, HUB_REPO, LORA_R, LR, MODEL_ID


@app.cell
def _(HF_TOKEN, REPO, os):
    import subprocess

    os.environ["HF_TOKEN"] = HF_TOKEN.value or os.environ.get("HF_TOKEN", "")
    if not (REPO / "data" / "multilingual").exists():
        subprocess.run(
            ["git", "clone",
             "https://huggingface.co/datasets/pinkelephantlimited/"
             "pink-elephant-talk-vlm-dataset",
             str(REPO / "data" / "multilingual")],
            check=True,
            env=dict(os.environ),
        )
    from train_vlm import train, load_dataset

    base = REPO / "data" / "multilingual"
    paths = sorted((base / "data").glob("*/train.jsonl")) if (base / "data").exists() \
        else sorted(base.glob("*/train.jsonl"))
    paths = [p for p in paths if p.exists()]
    ds = load_dataset(paths)
    print(f"dataset rows: {len(ds)}")
    return ds, train


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 8. Train

    **This is the long step.** QLoRA on the Blackwell 6000. The adapter is saved
    locally and pushed to Hugging Face with a model card. Watch eval loss — you
    want it to go down.
    """)
    return


@app.cell
def _(
    BATCH,
    EPOCHS,
    GRAD_ACCUM,
    HUB_REPO,
    LORA_R,
    LR,
    MODEL_ID,
    REPO,
    ds,
    os,
    train,
):
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
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 9. Verify the trained model

    Run a quick inference on a held-out multilingual image to confirm it reads
    the text.
    """)
    return


@app.cell
def _(HUB_REPO, REPO, mo):
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
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 10. Done

    - Dataset: `pinkelephantlimited/pink-elephant-talk-vlm-dataset`
    - Model: `pinkelephantlimited/pink-elephant-talk-vlm-3b`

    Next (outside molab): convert to GGUF and bundle in the mobile app.
    """)
    return


if __name__ == "__main__":
    app.run()
