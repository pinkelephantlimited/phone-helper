# Pink Elephant Talk — Product Data Sheet

**Product:** Pink Elephant Talk v7.2
**Vendor:** Pink Elephant Limited (Hong Kong)
**Type:** On-device AI chat, photo and document assistant for Android
**Release:** 2026-08-08 · **versionCode** 12 · **versionName** 7.2

## Summary

Pink Elephant Talk is a **fully offline, on-device vision-language chat assistant**.
A vision-language model runs entirely on the phone's own processor. Users can
chat by text, attach a **photo** and have the model describe it, attach a
**document** and have the model answer questions about it, or tap 🔊 to have
answers **read aloud** in your chosen voice. Live topics (weather, news, prices,
sports) are grounded with public web data. No account, no telemetry, no cloud AI
inference.

## Technical specification

| Item | Detail |
|---|---|
| **Assistant model** | In-house on-device vision-language model (Apache-2.0 base) |
| **Language model file** | `Qwen3VL-2B-Instruct-Q4_K_M.gguf` — 1,107,409,952 bytes (~1.06 GB) |
| **Vision projector** | `mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf` — 445,053,216 bytes (~0.44 GB) |
| **Total model download** | ~1.5 GB (one-time; cached on device) |
| **Inference engine** | llama.cpp via llama.rn (both MIT) |
| **Acceleration** | CPU by default; GPU backend used when available (OpenCL/Vulkan) |
| **Image tokens** | 1024 minimum / maximum per image |
| **Photo handling** | on-device downscale to max 1280 px, JPEG quality 90 |
| **Voice language selector** | 🌐 / 🗣️ header control — **Auto / 粵語 / 普通话 / English** |
| **Native Cantonese voice** | In-house bundled on-device Cantonese TTS engine (粵語), fully offline; preference persisted on device |
| **System-voice Auto mode** | default; uses the device's built-in TTS engine |
| **Languages** | multilingual (answers in the user's language; voice selectable) |

### Web data sources

| Source | Used for | License |
|---|---|---|
| Open-Meteo | weather (geocoding + forecast) | CC BY 4.0 |
| Google News RSS | headlines | Google terms |
| Wikipedia REST API | article summaries | CC BY-SA 4.0 |

### Document reader

| Type | Extraction |
|---|---|
| `.txt` | raw text |
| `.pdf` | pdfbox-android (Apache-2.0) |
| `.docx` | internal XML (`word/document.xml`) |

## Platform & build

| Item | Detail |
|---|---|
| Framework | React Native 0.76 (TypeScript, New Architecture) |
| ABI | **arm64-v8a** |
| minSdk / targetSdk | 24 / 34 |
| Minimum device | Android 12+, **≥ 4 GB RAM**, ~1.5 GB free storage |
| Signing | Pink Elephant Limited series keystore (release) |
| APK | `PinkElephantTalk-v7.2.apk` — 159,590,069 bytes |
| SHA-256 | `e076fff4086cf8f9f5d896b104ad07bfb363b02486b9f4f15f9f54ef06d01431` |
| Package | `com.pinkelephant.talk` |

## Permissions

| Permission | Purpose |
|---|---|
| `android.permission.INTERNET` | one-time model download + optional live-fact lookup |
| (none else) | photos/documents chosen via Android system picker; voice synthesis is fully on-device |

No camera, contacts, location, or call-log permissions.

## Privacy & compliance

- **Zero data collection** — no accounts, no telemetry, no ads, no cloud inference.
- Base model redistributed under **Apache-2.0** with attribution retained (see `THIRD-PARTY-NOTICES`).
- App source and binaries: **proprietary © Pink Elephant Limited**.
- See `privacy-policy.md`, `terms-of-service.md` and `THIRD-PARTY-NOTICES`.

## Verified on hardware

- Device: vivo V2157A (Snapdragon 865 SM8250, CPU-only, 8 threads).
- **Boot stability:** app launches and stays in the foreground; no JS/native errors.
- **Native Cantonese voice:** switching the header control to 粵語 produced
  correct spoken Cantonese output — confirmed working on hardware.
- **Voice-language selector:** Auto / 粵語 / 普通话 / English cycles correctly;
  preference persists across sessions.
- **Text chat:** answers stream instantly.
- **Photo vision:** an attached photo of the pink-elephant logo was correctly
  described by the model.
- **Model caching:** relaunch boots straight to ready; no re-download.

> Note: on CPU-only phones, image processing is slow (~80 s encode). GPU-capable
> phones are significantly faster.
