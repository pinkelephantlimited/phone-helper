# Pink Elephant Limited — Company Profile

| | |
|---|---|
| **Legal name** | Pink Elephant Limited |
| **Jurisdiction** | Hong Kong SAR (registered commercial company) |
| **Industry** | Consumer software / on-device artificial intelligence |
| **Positioning** | Hong Kong AI pioneer — private, on-device AI products |
| **Product line** | 9 free Android applications (flagship: Pink Elephant Talk) |
| **Web** | [Hugging Face](https://huggingface.co/pinkelephantlimited) |

## Who we are

Pink Elephant Limited is a commercial AI technology development company
registered in Hong Kong. We build a family of **private, on-device mobile
products**: every model runs on the phone's own hardware, no user data leaves the
device, there are no cloud AI dependencies, and all of our apps are free.

Our founding belief is that artificial intelligence should be a **private utility**
— as personal and as dependable as a flashlight. You should not have to trade your
conversations, your documents or your photos to get helpful answers.

## What we do

- **On-device intelligence** — we ship real language and vision models inside
  Android APKs. Inference happens locally on the phone's CPU/GPU via llama.cpp,
  never in a third-party cloud.
- **Privacy by architecture** — no account, no telemetry, no camera/microphone
  permissions, no server-side storage. The model is downloaded once and your data
  stays on the device.
- **Free for everyone** — our full product line is free of charge. We monetize
  through enterprise partnerships, white-label licensing and optional premium
  services (see `pricing-plan.md`), never by selling user data.

## Hong Kong positioning

Hong Kong has no homegrown foundation-model company. We position Pink Elephant
Limited as a **Hong Kong AI pioneer** — building sovereign, privacy-first
intelligence locally and distributing it globally, while staying fully compliant
with Apache-2.0 open-source licensing.

## Product line

| # | Product | Purpose | Status |
|---|---|---|---|
| 1 | **Pink Elephant Talk** | On-device AI chat + photo + document + voice assistant (flagship) | v7.2 |
| 2 | **Pink Elephant Cleaner** | Storage cleanup via SAF | v1.0 |
| 3 | **Pink Elephant Sleep** | Sleep sounds + timer | v1.0 |
| 4 | **Pink Elephant Compass** | Compass + spirit level | v1.0 |
| 5 | **Pink Elephant Pulse** | Battery / RAM / CPU / storage monitor | v1.0 |
| 6 | **Pink Elephant Notes** | Offline text notes | v1.0 |
| 7 | **Pink Elephant Flashlight** | Torch / flash | v1.0 |
| 8 | **Pink Elephant Converter** | Offline unit converter | v1.0 |
| 9 | **Pink Elephant Timer** | Countdown / stopwatch | v1.0 |

All products share one design principle: **offline, permission-free, dependency-free**
(except Talk, which needs internet once to download its model and optionally for
live-fact lookup).

## Flagship — Pink Elephant Talk v7.2

An on-device **vision-language chat assistant**: ask anything in text, attach a
photo and it describes it, attach a document and it answers about it, and choose
a voice — **粵語 Cantonese, 普通话, English or Auto** — to have answers read
aloud in the sound of our own in-house Cantonese voice. Runs fully on the phone.

- **Native Cantonese voice (粵語)** — an in-house, bundled on-device Cantonese
  TTS engine; authentic spoken Cantonese, fully offline
- **Voice-language selector** — 🌐 / 🗣️ controls cycle Auto / 粵語 / 普通话 /
  English; choice is remembered
- **Reliable live answers** — weather/news/prices/sports via Open-Meteo, Google
  News RSS and Wikipedia
- **Photo vision** — attach an image; the app sees it (on-device processing)
- **Document reader** — .txt / .pdf / .docx extracted on-device
- **Private** — no account, no cloud inference, no telemetry

See `product-line-brochure.md` and `data-sheet.md` for details.

## Compliance & licensing

- Base model weights are open-source under **Apache-2.0**, redistributed with
  attribution preserved (`THIRD-PARTY-NOTICES`).
- Web data: Open-Meteo (CC BY 4.0), Google News RSS, Wikipedia (CC BY-SA 4.0).
- App source and binaries: **proprietary © Pink Elephant Limited**.
- No third-party cloud inference is ever called.
