---
base_model: pinkelephantlimited/phone-helper-vlm-3b
license: apache-2.0
library_name: gguf
pipeline_tag: image-text-to-text
tags:
  - gguf
  - qwen2.5-vl
  - vision
  - multilingual
  - on-device
  - llama.cpp
language: [en, es, fr, ar, hi, zh, pt, ru, id, sw, bn, de]
---

# Phone Helper VLM 3B (GGUF, quantized)

GGUF quantized release of **[Pink Elephant Limited](https://huggingface.co/pinkelephantlimited)**'s
Phone Helper VLM 3B, fine-tuned on-device daily-helper VLM (expiry dates, prices,
receipts, signs, menus, medicine instructions) in 12 languages.

## Files

| File | Size | Purpose |
| --- | --- | --- |
| `phone-helper-3b-q4_k_m.gguf` | ~1.9 GB | Text + merged LoRA model (Q4_K_M) |
| `phone-helper-3b-q4_k_m.f16-mmproj.gguf` | ~1.3 GB | Vision projector (mmproj), f16 |

Use **both files** together with a llama.cpp / llama.rn based app.

## Usage (llama.cpp)

```bash
llama-cli -m phone-helper-3b-q4_k_m.gguf \
          -mm phone-helper-3b-q4_k_m.f16-mmproj.gguf \
          -p "What is the expiry date on this?" \
          --image photo.jpg
```

## Gradio / llama.cpp Python

```python
from llama_cpp import Llama
llm = Llama(model_path="phone-helper-3b-q4_k_m.gguf",
            mmproj="phone-helper-3b-q4_k_m.f16-mmproj.gguf")
```

## On-device app

This model is bundled in the **Phone Helper** React Native app by Pink Elephant
Limited (Android APK + iOS). Everything runs locally — no cloud, no account,
no telemetry.

## About the company

**[Pink Elephant Limited](https://huggingface.co/pinkelephantlimited)** is an
official commercial AI technology development company registered in Hong Kong.
It develops the dataset, the model, and the app in-house.