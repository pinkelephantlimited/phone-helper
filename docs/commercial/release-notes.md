# Pink Elephant Talk — Release Notes

## v7.2 (fixed) — 2026-08-08 · Stable voice output

**What's changed**

- **Crash fix** — the previous v7.2 bundled an espeak-ng voice layer whose
  synchronous synthesis raced during teardown (`FORTIFY: pthread_mutex_lock
  called on a destroyed mutex` → `SIGABRT`) and crashed on long text. This build
  routes all voice output through the device's built-in text-to-speech engine
  instead, which is stable and does not crash.
- **Voice-language selector** — the header 🌐 / 🗣️ control cycles through
  **Auto / 粵語 / 普通话 / English**. Replies are read aloud in the chosen
  language and the preference is remembered between sessions.
- **Robust build** — boots cleanly, stays in the foreground, no JS/native
  errors during voice playback.

**Verified on device**

- App launches and stays in the foreground.
- English and Mandarin (普通话) voice output works reliably and no crash.
- Cantonese (粵語) requires the phone's TTS voice data; some devices report the
  locale but ship no Cantonese audio — on those, switch to English/Mandarin.

**Notes**

- APK: `PinkElephantTalk-v7.2.apk` — SHA-256 `e076fff4086cf8f9f5d896b104ad07bfb363b02486b9f4f15f9f54ef06d01431`.
- Package: `com.pinkelephant.talk`.
- Version **7.2**, versionCode **12** (rebuilt), signed with the Pink Elephant Limited series keystore.

## v7.1 — 2026-08-05 · Voice output (text-to-speech)

**What's new**

- **Voice output** — a 🔊 button in the app header reads every assistant reply
  aloud automatically (hands-free). A per-message 🔊 button under any assistant
  bubble speaks / ⏹ stops that specific message.
- **On-device** — fully local voice synthesis, no network.
- **Graceful** — voice output is never required; if TTS is unavailable the app
  simply hides the buttons and chat continues normally.

**Kept from v7.0**

- Photo vision, thinking mode, reliable web search, document upload,
  branded identity.

**Verified on device**

- The TTS engine connects and initialises without error; the 🔊 control appears
  in the header.

**Note**

- APK: `PinkElephantTalk-v7.1.apk` — SHA-256 `a863092cae1f76648d09e31ef35261309eec353d3e19859ac316da20f7a4d0c54`.

---

## v7.0 — 2026-08-05 · Photo vision on-device

**What's new**

- **Photo vision** — new 🖼️ button attaches a photo; the model sees and describes it.
- **New phone-class vision model** — switched to **Qwen3-VL-2B-Thinking**
  (Apache-2.0): language GGUF (~1.06 GB) + vision projector (~0.44 GB), ~1.5 GB total.
- **Download-stage labels** — the loading screen now shows whether it is downloading
  the language model or the vision encoder.
- **Bug fix** — chat no longer fails with "Value is undefined, expected an Object"
  (completion params no longer carry an empty `media_paths` key).

**Verified on device**

- Text chat streams answers with visible thinking.
- Attached photo of the pink-elephant logo is described by the model.

**Notes**

- Vision on CPU-only phones is slow (image encode ~80 s); GPU-capable phones are far faster.
- APK: `PinkElephantTalk-v7.0.apk` — SHA-256 `b0e22e63c574bbfbc5c99d0d81551290bef57ee3b70691e2b55b329c4b5808a1`.

---

## v6.2 — 2026-08-05 · Internet-right prompt + duplicate-answer fix

- The system prompt explicitly grants the model the **right to access the internet**
  and to answer YES when asked whether it can search; removed the contradictory
  "fully offline" wording.
- Fixed a bug where the same answer could appear twice: web questions now generate the
  direct pass silently, show a "Searching the web…" note, and stream only the final
  answer.

## v6.1 — 2026-08-05 · Document upload + real logo

- New 📎 document upload — `.txt`, `.pdf` and `.docx` are extracted on-device and the
  model answers about them.
- Replaced the generated icon with the official pink-elephant logo thumbnail.
- Fixed the "no internet access" claim.

## v6.0 — 2026-08-05 · Reliable web search + branding

- Client-side topic detector fetches live data for weather/news/prices/sports
  (Open-Meteo, Google News RSS, Wikipedia) even when the model answers from memory.
- Full Pink Elephant branding — model identity, UI byline, custom launcher icon.

## v5.0 — 2026-08-05 · Qwen3-1.7B + thinking mode

- Switched to Qwen3-1.7B-Instruct (Q4_K_M) with **visible thinking**: reasoning shown
  separately from the answer; no marker leaks.
- Streaming output.

## v4.0 — 2026-08-05 · Text-only rewrite

- Qwen2.5-3B-Instruct (Q4_K_M), on-device text chat, warm rose UI, cached model.

## v3.0 — 2026-08-02 · Faster on-device model

- Qwen2-VL-2B-Instruct (Q4_0) vision+voice assistant (legacy, superseded).

## v2.0 / v1.0 — legacy

- Initial Qwen2.5-VL-3B vision prototypes (legacy, superseded).

---

*Full archive of every APK version is available in the
[Pink Elephant Talk Hugging Face repository](https://huggingface.co/pinkelephantlimited/pink-elephant-talk).*