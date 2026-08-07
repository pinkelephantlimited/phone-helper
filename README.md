---
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
tags:
  - android
  - on-device
  - offline
  - llm
  - vlm
  - vision
  - llama.cpp
  - react-native
  - pink-elephant
  - commercial
  - web-search
  - document-reader
  - photo-vision
---

# Pink Elephant Talk — v7.2

**Pink Elephant Talk** is the flagship mobile product of
**[Pink Elephant Limited](https://huggingface.co/pinkelephantlimited)**
(Hong Kong) — a commercial AI technology development company.

It is a **fully offline, on-device chat assistant with photo vision**. The
vision-language model runs entirely on your phone: no cloud, no account, no API
fees, no telemetry. Your conversations, photos and documents never leave the device.

## 📥 Download the APK

**Latest release — Pink Elephant Talk v7.2 (stable voice output):**

- [**Download `PinkElephantTalk-v7.2.apk`**](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v7.2.apk)
  (159.6 MB · SHA-256 `e076fff4086cf8f9f5d896b104ad07b363b02486b9f4f15f9f54ef06d01431`)

All versions are listed in the [Files and versions](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/tree/main)
tab of this repository, and in the table below.

## v7.2 Highlights

- **Stable voice output (text-to-speech)** — fixed a crash in the bundled
  espeak-ng voice layer (a synchronous teardown race that aborted the app on
  long text). Voice now runs on the phone's native speech engine and no longer
  crashes. The header 🌐 / 🗣️ control cycles **Auto / 粵語 / 普通话 / English**
  and remembers your choice.
- **Photo vision** — attach a photo with the 🖼️ button; the on-device model sees
  and describes it.
- **Core model: Qwen3-VL-2B-Thinking** (Apache-2.0) — a phone-class
  vision-language model, ~1.5 GB one-time download, cached on device.
- **Visible thinking, web search, document upload** — unchanged from v7.0/v7.1.

## v7.0 Highlights

- **Photo vision** — attach a photo with the 🖼️ button; the on-device model sees
  and describes it (verified on hardware with the pink-elephant logo).
- **Core model: Qwen3-VL-2B-Thinking** (Apache-2.0) — a phone-class
  vision-language model, ~1.5 GB one-time download (language model + vision encoder),
  cached on device.
- **Visible thinking mode** — the model shows its reasoning, then gives a clear
  final answer.
- **Reliable web search** — a client-side topic detector fetches fresh data for
  weather, news, prices and sports even when the model answers from memory.
  Weather comes from **Open-Meteo** (no API key, CC BY 4.0), headlines from
  **Google News RSS**, summaries from **Wikipedia**; sources are cited.
- **The model has the right to the internet** — it never claims it "cannot access
  the internet"; live questions (e.g. HK news, weather) always search.
- **Document upload** — attach a `.txt`, `.pdf` or `.docx`; text is extracted
  on-device (PDF via pdfbox-android) and the model can answer about it.
- **Branded identity** — answers "I was created by Pink Elephant Limited."
- **On-device, offline** — works with zero connectivity after first setup.
  Your chats, photos and documents stay on the phone.

## Releases

| APK (click to download) | Model | Notes |
| --- | --- | --- |
| [`PinkElephantTalk-v7.2.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v7.2.apk) | Qwen3-VL-2B-Thinking (Q4_K_M + mmproj) | Stable voice output (native TTS, no crash), photo vision, thinking mode, web search, document upload (current) |
| [`PinkElephantTalk-v7.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v7.0.apk) | Qwen3-VL-2B-Thinking (Q4_K_M + mmproj) | Photo vision, thinking mode, web search, document upload |
| [`PinkElephantTalk-v6.2.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v6.2.apk) | Qwen3-1.7B-Instruct (Q4_K_M) | Internet-right prompt + duplicate-answer fix |
| [`PinkElephantTalk-v6.1.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v6.1.apk) | Qwen3-1.7B-Instruct (Q4_K_M) | Added document upload + thumbnail logo |
| [`PinkElephantTalk-v6.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v6.0.apk) | Qwen3-1.7B-Instruct (Q4_K_M) | Reliable web search + branding |
| [`PinkElephantTalk-v5.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v5.0.apk) | Qwen3-1.7B-Instruct (Q4_K_M) | Thinking mode (visible reasoning) |
| [`PinkElephantTalk-v4.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v4.0.apk) | Qwen2.5-3B-Instruct (Q4_K_M) | Text chat, offline, rose UI |
| [`PinkElephantTalk-v3.0.1.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v3.0.1.apk) | Qwen2-VL-2B-Instruct (Q4_0) | Vision+voice assistant (legacy) |
| [`PinkElephantTalk-v3.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v3.0.apk) | Qwen2-VL-2B-Instruct (Q4_0) | Vision+voice assistant (legacy) |
| [`PinkElephantTalk-v2.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v2.0.apk) | Qwen2.5-VL-3B-Instruct | Vision (legacy) |
| [`PinkElephantTalk-v1.0.apk`](https://huggingface.co/pinkelephantlimited/pink-elephant-talk/resolve/main/PinkElephantTalk-v1.0.apk) | Qwen2.5-VL-3B-Instruct | Initial release (legacy) |

## Install

1. Download `PinkElephantTalk-v7.0.apk`.
2. Allow installs from unknown sources (Settings → Security).
3. Open the app. On first launch it downloads the model (~1.5 GB, one-time,
   with per-file progress labels), then runs entirely offline.

> On some phones (e.g. vivo) a security check appears on first install; tap
> the checkbox and continue — the app requests no sensitive permissions.

## Model

- **Qwen3-VL-2B-Thinking**, © Alibaba Group, **Apache License 2.0**.
- GGUF: `Qwen/Qwen3-VL-2B-Thinking-GGUF` —
  `Qwen3VL-2B-Thinking-Q4_K_M.gguf` (1,107,409,888 bytes) + vision projector
  `mmproj-Qwen3VL-2B-Thinking-Q8_0.gguf` (445,053,216 bytes).
- Vision config: 1024 image tokens (minimum/maximum).
- Inference engine: **llama.cpp** via **llama.rn** (both MIT).

## Commercial documents

The complete commercial package is included in this repository under
`docs/commercial/`:

| Document | File |
|---|---|
| Company profile | `docs/commercial/company-profile.md` |
| Product line brochure | `docs/commercial/product-line-brochure.md` |
| Data sheet (v7.0) | `docs/commercial/data-sheet.md` |
| Pricing & monetization plan | `docs/commercial/pricing-plan.md` |
| Privacy policy | `docs/commercial/privacy-policy.md` |
| Terms of service | `docs/commercial/terms-of-service.md` |
| Release notes (v1.0 → v7.0) | `docs/commercial/release-notes.md` |
| Partnership & distribution prospectus | `docs/commercial/partnership-prospectus.md` |

## Compliance & Licensing

- **App source & binaries:** © Pink Elephant Limited (Hong Kong). Proprietary.
- **Base model:** redistributed under Apache-2.0 by preserving the Qwen
  copyright/license notice — see `THIRD-PARTY-NOTICES` in the source repo.
  "Qwen" is a trademark of Alibaba Group.
- **Web data:** Open-Meteo (CC BY 4.0), Google News RSS, Wikipedia (CC BY-SA).
  PDF text extraction via **pdfbox-android** (Apache-2.0).
- **No third-party cloud inference:** Pink Elephant Talk performs inference
  on-device; it does not call OpenAI, Google, or any hosted LLM API.

## About Pink Elephant Limited

An official commercial AI technology development company registered in
Hong Kong, building a family of private, on-device mobile products.
