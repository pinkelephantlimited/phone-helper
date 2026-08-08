---
base_model: Qwen/Qwen2.5-VL-3B-Instruct
tags:
  - vision
  - multimodal
  - multilingual
  - on-device
  - daily-helper
license: apache-2.0
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
pipeline_tag: image-text-to-text
datasets:
  - pinkelephantlimited/pink-elephant-talk-vlm-dataset
---

# Pink Elephant Talk VLM 3B

A fine-tuned, multilingual "daily helper" vision-language model that reads
everyday photos (labels, expiry dates, prices, signs, menus, receipts,
medicine instructions) and answers in short, spoken-style phrases. Runs
**entirely on a smartphone** — no cloud, no API, private by design.

## What it does
- Reads text from photos: expiry dates, prices, signs, receipts, menus
- Answers simple daily-life questions in 12 languages
- Short, natural, spoken-style answers (ideal for voice output)

## Languages
`en es fr ar hi zh pt ru id sw bn de` (English, Spanish, French, Arabic,
Hindi, Mandarin, Portuguese, Russian, Indonesian, Swahili, Bengali, German)

## Base model
[Qwen2.5-VL-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)
(Apache-2.0)

## Fine-tuning
QLoRA (r=32, α=64) on language + vision layers, 4-bit NF4, bf16.
See `train/train_vlm.py` in the repo for the exact recipe.

## Data
Generated offline by `data/pipeline/` — synthetic daily-life images with
rendered text (per-script fonts) + QA pairs, translated with NLLB-200.

## On-device
Converted to GGUF Q4_K_M with `llama.cpp`, bundled inside a mobile app
(React Native + llama.rn). See `train/to_gguf.py`.
