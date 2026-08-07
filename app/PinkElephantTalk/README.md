# Pink Elephant Talk

An on-device **chat + photo + document + voice** assistant for Android, made by
**Pink Elephant Limited**.

Pink Elephant Talk runs a vision-language assistant entirely on the phone's own
hardware. Type a question, get an answer — your prompts never leave the device.
It answers in the language you write, can see attached photos, read attached
documents, fetch fresh information (news, weather, prices) to ground live answers,
and read its replies aloud in a native on-device voice.

## Key facts

- **Fully on-device** — the assistant runs on the phone's CPU/GPU. No third-party
  cloud inference API, no OpenAI, no Ollama.
- **Native Cantonese voice (粵語)** — a bundled, on-device Cantonese text-to-speech
  engine. Real spoken Cantonese, fully offline, without depending on system voices
  that usually ship Mandarin only.
- **Voice-language selector** — the 🌐 / 🗣️ header control cycles through
  **Auto / 粵語 / 普通话 / English**; your choice is remembered between sessions.
- **Photo vision** — attach an image with the 🖼️ button; the app sees it and can
  describe what's in the picture.
- **Document upload** — attach a .txt, .pdf or .docx; text is extracted on-device
  and used as context.
- **Optional web fetch** for live facts, with cited sources (weather via Open-Meteo,
  headlines via Google News RSS, summaries via Wikipedia). Today's date/time is
  injected so "what's the date" is always right.
- **Multilingual** — answers in the language the user writes.
- **Branded identity** — the assistant identifies itself as Pink Elephant Talk by
  Pink Elephant Limited, and answers "who made you" accordingly.
- **First-launch model download** (~1.5 GB, one-time — language model + vision
  encoder, with progress labels for each file), then works offline.
- **Cached** — downloaded once, not re-downloaded on relaunch.

## Requirements

- Android 12+ device with **at least 4 GB RAM** (light enough to run comfortably
  on a Snapdragon 865 with CPU-only inference).
- ~1.5 GB free storage for the model files.
- Internet once on first launch (to download the model); optional thereafter for web fetch.

## Build

```bash
npm install
cd android
./gradlew assembleRelease \
  -PPINK_ELEPHANT_STORE_FILE=pinkelephant-series-release.keystore \
  -PPINK_ELEPHANT_STORE_PASSWORD=<store-pass> \
  -PPINK_ELEPHANT_KEY_ALIAS=pinkelephant-series \
  -PPINK_ELEPHANT_KEY_PASSWORD=<key-pass>
```

Output: `android/app/build/outputs/apk/release/app-release.apk`
The release APK is signed with the Pink Elephant Limited series keystore and is
**arm64-v8a only**.

## Native voice engine

The bundled Cantonese/Mandarin/English voice engine is an in-house native module
(`jni/cantonese_tts.c`, `CantoneseTtsModule.kt`) that synthesizes 22,050 Hz
16-bit WAV audio on-device. Its runtime language/voice data is shipped inside the
app assets, so 粵語 works with no internet and no system-TTS dependency. See
`THIRD-PARTY-NOTICES` for third-party components.

## Legal / attribution

- App and datasets © Pink Elephant Limited. Release binaries are signed by
  Pink Elephant Limited.
- Base model weights and open-source libraries are licensed by their respective
  owners; see `THIRD-PARTY-NOTICES` for attribution.
- Web data sources: Open-Meteo (CC BY 4.0), Google News RSS, Wikipedia REST API.