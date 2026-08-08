# Pink Elephant Limited — Privacy Policy

**Effective date:** 2026-08-05
**Applies to:** all Pink Elephant Limited Android applications, including
**Pink Elephant Talk**, **Sleep**, **Compass**, **Pulse**, **Notes**,
**Flashlight**, **Converter** and **Timer**.

## The short version

- **We do not collect your data.** Period.
- Our apps run **entirely on your device**. No accounts, no telemetry, no analytics,
  no advertising SDKs, no cloud AI inference.
- Anything you type, any photo or document you attach, and any conversation you have
  with **Pink Elephant Talk** **never leaves your phone**.

## The longer version

### 1. On-device by design

Every Pink Elephant app is built to work **offline**. **Pink Elephant Talk** runs a
real language-and-vision assistant on your phone's own processor. When you
type a question, attach a photo or a document, the content is processed **locally**.
We do not operate servers that receive your prompts, your photos, your documents or
your conversations.

### 2. Permissions

| App | Permissions requested | Why |
|---|---|---|
| Pink Elephant Talk | **Internet** | One-time model download on first launch + optional live-fact lookup |
| Pink Elephant Talk | **None** (picker-based) | Photos and documents are chosen through Android's system picker (Storage Access Framework); the app never reads your media library on its own |
| Sleep / Compass / Pulse / Notes / Flashlight / Converter / Timer | **None** | Pure on-device utilities |

We do **not** request camera, microphone, contacts, location, or call-log
permissions in any product.

### 3. Web lookups (Pink Elephant Talk)

When you ask about live topics (weather, news, prices, sports), the app fetches
public data from:

- **Open-Meteo** (weather, no API key)
- **Google News RSS** (headlines)
- **Wikipedia REST API** (summaries)

These requests are made **only when you ask a question** on those topics. The queries
we send are derived from your question text and are transmitted over standard HTTPS
to those public services under their own terms (see `THIRD-PARTY-NOTICES`). We do not
store them, and we do not attribute them to you.

### 4. Model download (Pink Elephant Talk)

On first launch the app downloads a model (~1.5 GB) from a public model repository
(Hugging Face). This is a static file download; no personal data is sent. The model is
cached on your device and is **not re-downloaded** on relaunch.

### 5. No data we hold

Because there is no account system and no server-side storage, there is nothing for us
(or anyone else) to lose, sell, subpoena or breach. If the app is deleted, all its
data (including the cached model) is removed with it.

### 6. Children

Our products are general-purpose tools and are safe for all ages. We do not knowingly
collect any personal information from anyone, including children.

### 7. Third-party open-source components

Pink Elephant Talk is built on open-source software (the on-device inference engine,
React Native, pdfbox-android) and an open-source base model. These components
may include their own privacy and license terms; they are listed with attribution in
`THIRD-PARTY-NOTICES`. No component transmits your data to us.

### 8. Changes to this policy

If we ever change our data practices (we do not intend to), we will update this
document and clearly mark the change. Any change would never involve selling user data.

### 9. Contact

**Pink Elephant Limited** — Hong Kong SAR.
Questions about privacy: via [our Hugging Face organization](https://huggingface.co/pinkelephantlimited).

*This policy is provided in good faith as general information and is not legal advice.
For production distribution, please have it reviewed by your legal counsel.*
