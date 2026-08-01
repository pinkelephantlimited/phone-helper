# Roadmap

## Goal
A free, open, offline daily-helper assistant that runs **entirely on a
smartphone** (no cloud, no API fees, private). Vision + voice + text in
**12 priority languages**.

## Phase 1 — Data (DONE in code, generating)
- [x] `build_english.py`: synthetic daily-life images (labels, prices,
      signs, menus, receipts, medicine instructions) + QA in Qwen2.5-VL format
- [x] `translate.py`: NLLB-200 offline translation to 12 languages with
      script-aware re-rendering of image text
- [ ] Generate full-scale English + multilingual dataset
- [ ] Push dataset to Hugging Face (`pinkelephantlimited/phone-helper-vlm-1b-dataset`)

## Phase 2 — Train (GPU cloud)
- [x] `train/train_vlm.py`: QLoRA fine-tune of Qwen2.5-VL-3B-Instruct,
      eval-loss tracking, HF push
- [ ] Run on GPU box (~20-40 min), verify eval loss drops
- [ ] Push adapter + model card to HF

## Phase 3 — On-device
- [ ] `train/to_gguf.py`: merge LoRA + convert to GGUF Q4_K_M + mmproj
- [ ] Verify on desktop llama.cpp / LM Studio

## Phase 4 — Mobile app (model bundled)
- [ ] React Native + `llama.rn` (llama.cpp engine)
- [ ] Camera -> vision inference (mmproj)
- [ ] Whisper STT + system TTS voice layer
- [ ] 12-language UI
- [ ] Bundle GGUF in the app install
- [ ] Android APK + Play Store; iOS TestFlight + App Store

## Principles
- Apache-2.0 weights + data, reproducible pipeline
- No telemetry, no network required at runtime
- Short, spoken-style answers for every language
