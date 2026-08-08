# Roadmap

## Goal
A commercial line of free, offline, on-device products from **Pink Elephant Limited**
(Hong Kong): no cloud, no API fees, private. Flagship: **Pink Elephant Talk**, an
on-device chat assistant.

## Phase 1 — Data (DONE in code)
- [x] `build_english.py`: synthetic daily-life images (labels, prices, signs, menus,
      receipts, medicine instructions) + QA in Qwen2.5-VL format
- [x] `translate.py`: NLLB-200 offline translation to 12 languages
- [ ] Generate full-scale English + multilingual dataset
- [ ] Push dataset to Hugging Face

## Phase 2 — Train (DONE)
- [x] `train/train_vlm.py`: QLoRA fine-tune of Qwen2.5-VL-3B-Instruct, eval-loss
      tracking, HF push
- [x] Adapter + model card on HF (pinkelephantlimited/pink-elephant-talk-vlm-3b)
- [x] GGUF conversion + quantization (Q4_K_M + f16 mmproj)

## Phase 3 — On-device inference (DONE, superseded)
- [x] GGUF verified on llama.cpp (receipt → "The total is 31.17.")
- [x] **v4.0 pivoted to text-only chat:** Qwen2.5-3B-Instruct (Q4_K_M) runs offline
      via llama.rn/llama.cpp. Dropped vision/voice (camera/mic permissions removed).
      Model cached on device — no re-download on relaunch. Web-grounding fallback for
      live facts (fixed: search turn now built as a proper chat-templated message).

## Phase 4 — Mobile apps (SHIPPED)
- [x] Pink Elephant Talk v4.0 — text chat, rose UI, arm64-v8a, signed release APK,
      installed + verified on a vivo V2157A (Snapdragon 865, CPU-only)
- [x] **Pink Elephant Talk v5.0 — Qwen3-1.7B + thinking mode:** switched to
      Qwen3-1.7B-Instruct Q4_K_M (lm-kit GGUF, 1,282,439,360 B, Apache-2.0) with
      on-device streaming and visible reasoning. Thinking delimiters are `<think>` /
      `</think>` (CONTROL tokens 151667/151668) — the app forces thinking by
      appending `<think>` to the assistant generation prompt and splits the reply
      on `</think>` so reasoning renders separately (italic) and no markers leak
      into the answer. **Fixed the `/think` leak:** root cause was a vocab mismatch
      (app injected `<|thinking_start|>`, which is absent from this GGUF's vocab)
      plus a parse that looked for `<think>` in the output, which a forced-thinking
      prompt never emits. Verified on vivo V2157A: "Who wrote Hamlet?" → separate
      reasoning bubble + "William Shakespeare wrote *Hamlet*."; multi-turn works;
      cached relaunch boots straight to ready.
- [x] **Pink Elephant Talk v6.0 — reliable web search + branding:** fixed the v5.0
      live-data failure (the model answered "I can't provide real-time data" instead
      of searching). Added a **client-side topic detector** in `src/model.ts` that
      runs a web fetch for weather/news/prices/sports even when the model never emits
      `[search:]`; weather now comes from **Open-Meteo** (geocoding + current weather,
      no API key, CC BY 4.0), headlines from Google News RSS, summaries from
      Wikipedia; today's date/time is injected into the system prompt. Full branding:
      model identity set to "created by Pink Elephant Limited" in the system prompt,
      company byline in the UI, and a custom pink-elephant launcher icon (all
      densities, ROSE palette). versionCode 7 / versionName 6.0.
- [x] **Pink Elephant Talk v6.1 — document upload + real logo + internet fix:** the
      model can now read attached documents (📎 button → Android document picker →
      on-device text extraction: plain text, PDF via pdfbox-android, DOCX via its
      XML; no extra npm deps). Extracted text is injected as context so the model can
      answer questions about the document. Replaced the generated icon with the user's
      thumbnail logo (white margin cut, corners transparent, all 5 densities + round).
      Fixed the "no internet access" claim: the system prompt now states the app CAN
      fetch live web info and must never deny internet access (HK news still searches).
      versionCode 8 / versionName 6.1, signed series keystore.
- [x] **Pink Elephant Talk v6.2 — internet-right prompt:** the system prompt now
      explicitly grants the model the RIGHT to access the internet ("you can and do
      retrieve fresh, up-to-date information from the web", "if asked whether you can
      search the internet or access live data, answer YES", "never say you cannot
      access the internet or that current information is unavailable"); removed the
      contradictory "running fully offline" wording. versionCode 9 / versionName 6.2,
      signed series keystore, installed as an update (model cache preserved, verified
      via logcat "Context initialized"). APK PinkElephantTalk-v6.2.apk SHA-256
      2f1e677331915579ec72179b5c3e6b58996d698e155c11df959c891839d3f81a.
- [x] **Pink Elephant Talk v7.0 — photo vision on-device:** switched the core to the
      phone-class vision model **Qwen3-VL-2B-Thinking** (Apache-2.0) so the app can
      SEE images. Language GGUF Q4_K_M (1,107,409,888 B) + mmproj Q8_0
      (445,053,216 B), ~1.5 GB total. New native `PhotoModule.kt` (ACTION_OPEN_DOCUMENT
      image/*, on-device downscale to max 1280 px / JPEG 90) + 🖼️ photo button +
      removable photo chip in the UI. Kept thinking mode, reliable web search,
      document upload and branding from v6.2. FIXED the v7.0 chat crash
      ("Value is undefined, expected an Object"): the completion params always
      carried `media_paths: undefined` when no photo was attached and the native JSI
      rejected the existing-but-undefined key — now the key is added only when an
      image path exists. Added download-stage labels so the progress reset between
      the language model and the vision encoder is no longer confusing. Verified on
      device: photo of the pink-elephant logo → the model streams a description of it.
      versionCode 10 / versionName 7.0, signed series keystore, update-installed
      (model + mmproj cache preserved). APK PinkElephantTalk-v7.0.apk SHA-256
      b0e22e63c574bbfbc5c99d0d81551290bef57ee3b70691e2b55b329c4b5808a1.
      NOTE: on the CPU-only vivo, image processing is slow (encode ~80 s); on
      GPU-capable phones this is much faster.
- [x] Sleep / Compass / Pulse / Notes / Flashlight / Converter / Timer v1.0 —
      all installed + verified
- [ ] Play Store / direct APK distribution
- [ ] Optional: non-i8mm OpenCL llama.rn variant for GPU speed on Snapdragon 865
      (documented follow-up — vivo blocks the i8mm path)

## Principles
- Apache-2.0 weights + data; proprietary app source/binary © Pink Elephant Limited
- No telemetry, no network required at runtime (except optional live-fact lookup)
- Short, warm, helpful answers; free of charge
