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


def _push_model_card(hub_repo: str, dataset: Dataset, token: str) -> None:
    from huggingface_hub import HfApi, upload_file
    card = f"""---
base_model: Qwen/Qwen2.5-VL-3B-Instruct
license: apache-2.0
tags: [vision, multimodal, multilingual, on-device, daily-helper]
language: [en, es, fr, ar, hi, zh, pt, ru, id, sw, bn, de]
datasets:
  - pinkelephantlimited/phone-helper-vlm-dataset
---

# Phone Helper VLM 3B

Multilingual daily-helper VLM fine-tuned from Qwen2.5-VL-3B-Instruct with
QLoRA. Reads everyday photos (expiry dates, prices, signs, menus, receipts,
medicine instructions) and answers in short spoken-style phrases in 12
languages. Runs entirely on-device (no cloud).
"""
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=card.encode(), repo_id=hub_repo,
        path_in_repo="README.md", commit_message="model card",
    )


def train(dataset, model_id: str = "Qwen/Qwen2.5-VL-3B-Instruct",
          hub_repo: str = "pinkelephantlimited/phone-helper-vlm-3b",
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
        max_steps=max_steps,
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
    ap.add_argument("--model", default="pinkelephantlimited/qwen2.5-vl-3b-instruct-nested")
    ap.add_argument("--out", default="pinkelephantlimited/phone-helper-vlm-3b")
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
