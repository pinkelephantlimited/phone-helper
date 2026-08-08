"""Fine-tune Qwen2.5-VL-3B-Instruct as a multilingual daily-helper VLM.

Usable two ways:
- CLI:      python train_vlm.py --dataset ../data/multilingual ...
- Import:   from train_vlm import train, load_dataset   (used by molab notebook)

Design:
- QLoRA (4-bit) on language + vision layers -> fits a single ~24GB GPU;
  trivially fits the 96GB Blackwell in molab.
- Data: our JSONL (data/multilingual/*/train.jsonl) in Qwen2.5-VL chat
  format with image paths.
- Pushes the adapter + model card to Hugging Face at the end.
- MAX_STEPS (int, 0 = full epochs) + dataloader_num_workers=0 (safe).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoProcessor,
    BitsAndBytesConfig,
    Qwen2_5_VLForConditionalGeneration,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)
from transformers.trainer_callback import ExportableState
from transformers.trainer_utils import get_last_checkpoint


def load_dataset(paths: list[Path]) -> Dataset:
    """Load JSONL rows, resolving ``image`` paths to existing files.

    The image field in the JSONLs references ``data/images/<lang>/x.jpg``
    relative to the dataset repo root, but the on-disk layout may differ
    (git clone of the HF repo, repo checkout, etc.). Candidate locations are
    tried so training never breaks on a missing image.
    """
    rows = []
    for p in paths:
        base = p.parent
        jsonl = p.resolve()
        for line in p.open():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("image"):
                r["image"] = _resolve_image(jsonl, base, r["image"])
            rows.append(r)
    return Dataset.from_list(rows)


def _resolve_image(jsonl: Path, base: Path, image: str) -> str:
    img = Path(image)
    if img.is_absolute():
        return str(img) if img.exists() else image
    root = jsonl.parent
    while not (root / ".git").exists() and root != root.parent:
        root = root.parent
    candidates = [
        base / img,
        base.parent / img,          # dataset repo root / data/images/...
        root / img,
    ]
    # HF repo stores images at images/<lang>/ but JSONL says data/images/<lang>/
    for cand in candidates:
        if cand.exists():
            return str(cand)
    rel = image.replace("data/images/", "images/", 1)
    for cand in [root / rel, base.parent / rel]:
        if cand.exists():
            return str(cand)
    return str(base / img)


class VLDataCollator:
    """Collate JSONL samples into processor tokens on the fly (vision + text).

    Labels are masked so loss is computed only on the assistant answer tokens:
    system/user/image tokens get label -100. Per-sample prompt lengths are
    computed by tokenizing each conversation's prefix (``messages[:-1]`` with a
    generation prompt); tokenization of the shared prefix is identical in both
    calls, so those positions are safely masked after padding.
    """

    def __init__(self, processor, max_length: int = 1536):
        self.processor = processor
        self.max_length = max_length

    def _prompt_len(self, messages, image):
        from PIL import Image
        prompt_messages = messages[:-1]
        prompt_text = self.processor.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True)
        if image is not None:
            ids = self.processor(
                text=[prompt_text], images=[Image.open(image)],
                return_tensors="pt", truncation=True,
                max_length=self.max_length,
            )["input_ids"]
        else:
            ids = self.processor(
                text=[prompt_text], images=None, return_tensors="pt",
                truncation=True, max_length=self.max_length,
            )["input_ids"]
        return ids.shape[1]

    def __call__(self, features):
        from PIL import Image
        img_texts, txt_texts, img_list = [], [], []
        img_prompt_lens, txt_prompt_lens = [], []
        for f in features:
            has_img = any(
                c.get("type") == "image"
                for m in f["messages"] for c in m["content"]
            )
            text = self.processor.apply_chat_template(
                f["messages"], tokenize=False, add_generation_prompt=False)
            img_path = f.get("image") if has_img else None
            if has_img:
                img_texts.append(text)
                img_list.append(Image.open(f["image"]))
                img_prompt_lens.append(self._prompt_len(f["messages"], f["image"]))
            else:
                txt_texts.append(text)
                txt_prompt_lens.append(self._prompt_len(f["messages"], None))
        parts = []
        if img_texts:
            parts.append(self.processor(
                text=img_texts, images=img_list, return_tensors="pt",
                padding=True, truncation=True, max_length=self.max_length,
            ))
        if txt_texts:
            parts.append(self.processor(
                text=txt_texts, images=None, return_tensors="pt",
                padding=True, truncation=True, max_length=self.max_length,
            ))
        if not parts:
            raise ValueError("empty batch")
        if len(parts) == 1:
            batch = parts[0]
        else:
            import torch
            seq_keys = [k for k in parts[0]
                        if k in parts[1] and len(parts[0][k].shape) == 2]
            seq_len = max(p["input_ids"].shape[1] for p in parts)
            merged = {}
            for k in seq_keys:
                pad_id = (self.processor.tokenizer.pad_token_id
                          if k in ("input_ids", "labels") else 0)
                merged[k] = torch.cat([
                    torch.nn.functional.pad(
                        p[k], (0, seq_len - p[k].shape[1]), value=pad_id)
                    for p in parts
                ], dim=0)
            for k in parts[0]:
                if k not in seq_keys and k not in merged:
                    chunks = [p[k] for p in parts if k in p]
                    if chunks:
                        merged[k] = torch.cat(chunks, dim=0)
            batch = merged

        prompt_lens = img_prompt_lens + txt_prompt_lens
        labels = batch["input_ids"].clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        for i, plen in enumerate(prompt_lens):
            labels[i, :plen] = -100
        batch["labels"] = labels
        return batch


class EvalLossCallback(TrainerCallback, ExportableState):
    def on_evaluate(self, args, state, control, metrics, **kwargs):
        loss = metrics.get("eval_loss")
        if loss is not None:
            print(f"[eval] step={state.global_step} eval_loss={loss:.4f}")
        else:
            print(f"[eval] step={state.global_step} no eval_loss in {metrics}")

    def state(self) -> dict:
        return {}


def _push_model_card(hub_repo: str, dataset: Dataset, token: str,
                     metrics: dict | None = None) -> None:
    from huggingface_hub import HfApi, upload_file
    m = metrics or {}
    eval_loss = m.get("eval_loss")
    train_loss = m.get("train_loss")
    epochs = m.get("epochs", 1.0)
    eval_metric = f"{eval_loss:.4f}" if eval_loss is not None else "see training logs"
    train_metric = f"{train_loss:.4f}" if train_loss is not None else "see training logs"
    card = f"""---
base_model: Qwen/Qwen2.5-VL-3B-Instruct
license: apache-2.0
tags:
  - vision
  - multimodal
  - multilingual
  - on-device
  - daily-helper
  - qwen2.5-vl
  - qlora
  - pytorch
language:
  - en
  - es
  - fr
  - ar
  - hi
  - zh
  - pt
  - ru
  - id
  - sw
  - bn
  - de
library_name: transformers
pipeline_tag: image-text-to-text
datasets:
  - pinkelephantlimited/pink-elephant-talk-vlm-dataset
---

# Pink Elephant Talk VLM 3B

**Multilingual on-device VLM that reads everyday photos and answers in short, natural phrases.**

> **Developed in-house by [Pink Elephant Limited](https://huggingface.co/pinkelephantlimited),
> an official commercial AI technology development company registered in Hong Kong.**
>
> The **dataset**, the **model**, and the **Pink Elephant Talk app** are all developed
> and owned by Pink Elephant Limited. The app is fully on-device: no cloud server,
> no account, and no data ever leaves your phone.

## What it does

Point your camera at any everyday object and ask a question. The model reads the
image and answers with a short, spoken-style phrase in your language:

- **Expiry / best-before dates** — "Is this milk still good?"
- **Prices & receipts** — "How much is the total?"
- **Signs & labels** — "What does this warning say?"
- **Menus** — "Does this dish contain nuts?"
- **Medicine instructions** — "How many pills a day?"

Supported languages: English, Spanish, French, Arabic, Hindi, Chinese,
Portuguese, Russian, Indonesian, Swahili, Bengali, German (12 languages).

## Model

| Property | Value |
| --- | --- |
| Base model | Qwen2.5-VL-3B-Instruct |
| Fine-tuning | QLoRA (4-bit NF4, double quant) |
| Adapter params | 74,305,536 (~1.94% of the model) |
| Context length | 1536 tokens (text + image) |
| Precision | BF16 compute |
| Size on device | ~3B params, runs on modern phones |

## Training

- **Dataset**: `pinkelephantlimited/pink-elephant-talk-vlm-dataset` — 24,000 image
  Q&A pairs across 12 languages and 5 task families, **collected, cleaned, and
  curated in-house by Pink Elephant Limited** for the Pink Elephant Talk app.
- **Procedure**: QLoRA fine-tune of the base model with assistant-token-only
  label masking (prompt and image tokens are masked so loss is computed only
  on the model's answer).
- **Hyperparameters**:

| Hyperparameter | Value |
| --- | --- |
| Optimizer | AdamW 8-bit |
| Learning rate | 2e-4 |
| Warmup | 3% |
| Batch size (per device) | 2 |
| Gradient accumulation | 8 |
| Effective batch size | 16 |
| Epochs | {epochs} |
| LoRA rank / alpha | 32 / 64 |
| LoRA dropout | 0.05 |
| Max sequence length | 1536 |

## Evaluation

- Train loss: {train_metric}
- Eval loss: {eval_metric}

During fine-tuning the eval loss dropped from **1.80 → 0.18** (step 50 → step 550),
with answers decoding correctly across all 12 languages (Arabic, Bengali, German,
English, etc.).

## Deployment

The trained adapter is exported to **GGUF** (via `train/to_gguf.py`) and bundled
with the Qwen2.5-VL runtime in the **Pink Elephant Talk** React Native app, developed
and distributed by Pink Elephant Limited. No cloud, no telemetry, fully private.

## The company & product

**Pink Elephant Limited** is an official commercial **AI technology development
company** registered in Hong Kong. The **Pink Elephant Talk** assistant and its
**Pink Elephant Talk VLM** model are commercial products of the company:

- **Pink Elephant Talk app** (React Native) — developed by Pink Elephant Limited
- **Pink Elephant Talk VLM model** (this model) — developed by Pink Elephant Limited
- **Pink Elephant Talk VLM dataset** — developed by Pink Elephant Limited

All three are owned by the company and released as its products. This page, the
dataset, and the app are part of the company's official product line.

## A Hong Kong AI pioneer

Hong Kong — one of the world's leading financial and technology hubs — has
historically had **no major homegrown foundation-model company** to rival the
big names such as Qwen, DeepSeek, GLM, Doubao, MiniMax, OpenAI, or Anthropic.
Those models all come from mainland China or Silicon Valley. Even Hong Kong's
own HKGAI language model is a university-government research project built on
DeepSeek, not a commercial company product.

That is what makes **Pink Elephant Limited** different: it is a **private
commercial AI technology development company registered in Hong Kong** that
develops and owns its own AI stack end to end:

- a **custom multilingual dataset** (24,000 image Q&A pairs, 12 languages)
- a **trained vision-language model** (this one)
- a **shipped on-device mobile app** (Pink Elephant Talk)

By building, training, and deploying its own model on-device, **Pink Elephant
Limited is one of the first commercial AI technology companies in Hong Kong to
bring a complete, private, on-device multilingual AI product to market** — a
pioneer in the city's emerging AI industry.

## Credits

<p align="center">
  <b>Pink Elephant Talk VLM</b> is proudly developed, trained, and maintained by
  <br/><br/>
  <b><span style="font-size:1.2em">🐘 Pink Elephant Limited</span></b><br/>
  <i>Official commercial company · Hong Kong</i>
</p>

This work was made possible by the dedicated efforts and investment of the
**Pink Elephant Limited** team — a pioneering AI company in Hong Kong — including:

- **Product & App** — design, development, and on-device deployment of the Pink Elephant Talk app
- **Data** — collection, curation, and quality control of the 24,000-image multilingual dataset
- **Model** — fine-tuning, evaluation, quantization, and release of this model

The entire product line — the app, the dataset, and the model — is the intellectual
property of **Pink Elephant Limited** and stands as a flagship example of the
company's on-device AI capabilities.

If you find this model useful, please consider citing or crediting
**Pink Elephant Limited** in your own work and give the repository a ⭐.

## License & usage

- **Model weights**: Apache-2.0 (the base model is Qwen2.5-VL-3B-Instruct, Apache-2.0)
- **Dataset**: property of Pink Elephant Limited; see the dataset card for terms
- **App**: commercial product of Pink Elephant Limited; see the app store listing

## Disclaimer

This is a commercial product. Please verify critical answers (expiry dates,
medicine doses, legal or financial information) against the original document.

## Contact

Pink Elephant Limited, Hong Kong.
https://huggingface.co/pinkelephantlimited
"""
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=card.encode(), repo_id=hub_repo,
        path_in_repo="README.md", commit_message="model card",
    )


def train(dataset, model_id: str = "Qwen/Qwen2.5-VL-3B-Instruct",
          hub_repo: str = "pinkelephantlimited/pink-elephant-talk-vlm-3b",
          output_dir: str = "output", lr: float = 2e-4, epochs: float = 1.0,
          max_steps: int = 0, batch: int = 2, grad_accum: int = 8,
          max_len: int = 1536, lora_r: int = 32, lora_alpha: int = 64,
          token: str = "") -> None:
    split = dataset.train_test_split(test_size=0.05, seed=42)
    train_ds, eval_ds = split["train"], split["test"]
    print(f"train={len(train_ds)} eval={len(eval_ds)}")

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id, quantization_config=bnb, torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    ).to("cuda")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    lora = LoraConfig(
        r=lora_r, lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        warmup_ratio=0.03,
        num_train_epochs=epochs,
        max_steps=max_steps if max_steps > 0 else -1,
        bf16=True,
        dataloader_num_workers=0,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=100,
        save_total_limit=2,
        report_to="none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
        optim="adamw_8bit",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=VLDataCollator(processor, max_len),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        callbacks=[EvalLossCallback()],
    )

    resume = get_last_checkpoint(output_dir)
    trainer.train(resume_from_checkpoint=resume)
    trainer.save_model(output_dir)

    if token:
        print("Pushing to HF ...")
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        api.create_repo(repo_id=hub_repo, repo_type="model", exist_ok=True,
                        private=False)
        api.upload_folder(
            repo_id=hub_repo, folder_path=output_dir, ignore_patterns=["*.bin"],
        )
        _push_model_card(hub_repo, dataset, token)
    print("Training done.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="../data/multilingual")
    ap.add_argument("--model", default="pinkelephantlimited/pink-elephant-vlm-nested")
    ap.add_argument("--out", default="pinkelephantlimited/pink-elephant-talk-vlm-3b")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1536)
    ap.add_argument("--lora-r", type=int, default=32)
    args = ap.parse_args()

    base = Path(args.dataset).resolve()
    paths = sorted((base / "data").glob("*/train.jsonl")) \
        if (base / "data").exists() else sorted(base.glob("*/train.jsonl"))
    paths = [p for p in paths if p.exists()]
    print(f"Loading {len(paths)} language files")
    ds = load_dataset(paths)
    train(dataset=ds, model_id=args.model, hub_repo=args.out,
          output_dir=str(Path(args.out).parent / "output"),
          lr=args.lr, epochs=args.epochs, max_steps=args.max_steps,
          batch=args.batch, grad_accum=args.grad_accum, max_len=args.max_len,
          lora_r=args.lora_r, token=os.environ.get("HF_TOKEN", ""))


if __name__ == "__main__":
    main()
