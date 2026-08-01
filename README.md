# Pink Elephant Phone Helper

An open, on-device multimodal assistant that runs entirely on a smartphone:
**no cloud, no API fees, private by design.**

- Base model: `Qwen2.5-VL-3B-Instruct` (Apache-2.0)
- Fine-tuned for daily-helper behavior in **12 priority languages**
- Runs in a bundled mobile app (Android APK + iOS) via llama.cpp
- Voice input (Whisper) + voice output (system TTS) + camera vision

## Repo layout

| Path | Purpose |
|---|---|
| `molab/super_pipeline.py` | **The one notebook.** Runs the whole pipeline on molab (GPU cloud) |
| `data/pipeline/` | Dataset generator + translator (used by the notebook) |
| `train/train_vlm.py` | QLoRA fine-tune of Qwen2.5-VL-3B (used by the notebook) |
| `train/to_gguf.py` | Merge LoRA + convert to GGUF Q4 for on-device |
| `app/` | React Native app with bundled model, camera + voice |
| `docs/` | Roadmap and model card |

## Run everything on molab (recommended)

molab is a free browser-based cloud (marimo notebooks) with an attachable
**NVIDIA RTX Pro 6000 Blackwell (96GB VRAM)**.

1. Open `molab/super_pipeline.py` in molab.
2. Attach a GPU via the notebook header specs button.
3. Set your `HF_TOKEN`, run the cells.

That single notebook:
1. Generates the English daily-helper dataset (synthetic images + QA)
2. Translates it to 12 languages (NLLB-200 on CUDA) with re-rendered images
3. Pushes the dataset to Hugging Face
4. Fine-tunes Qwen2.5-VL-3B-Instruct (QLoRA)
5. Pushes the model + model card to Hugging Face

Outputs:
- Dataset: `pinkelephantlimited/phone-helper-vlm-dataset`
- Model: `pinkelephantlimited/phone-helper-vlm-3b`

## Run locally instead

```bash
# 1. Dataset
cd data/pipeline && pip install -r requirements.txt
python build_english.py --out ../en --images ../images --n 2000
python translate.py --src ../en/train.jsonl --out ../multilingual \
    --images ../images --langs all --device mps   # or cpu

# 2. Train (needs a GPU; CLI form of the notebook)
cd train && pip install -r requirements.txt
export HF_TOKEN=hf_xxx
python train_vlm.py --dataset ../data/multilingual

# 3. On-device GGUF (after training)
python to_gguf.py --adapter train/output --base Qwen/Qwen2.5-VL-3B-Instruct
```

## Languages
`en es fr ar hi zh pt ru id sw bn de`

## License
Apache-2.0 weights and data.
