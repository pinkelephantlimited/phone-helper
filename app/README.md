# Phone Helper mobile app (Phase 4)

React Native app with the trained model **bundled inside the install**.

## Stack
- React Native (0.75+) + TypeScript
- `llama.rn` — llama.cpp engine for iOS + Android (GGUF inference)
- React Native Vision Camera — camera capture for vision prompts
- `react-native-whisper` — on-device speech-to-text (100+ languages)
- System TTS — multilingual voice output (free, on-device)

## Structure (planned)
```
app/
├── android/ ios/          # native shells
├── src/
│   ├── model/             # GGUF bundle loader, llama.rn session
│   ├── vision/            # camera -> image prompt
│   ├── voice/             # whisper STT + TTS
│   ├── i18n/              # 12-language UI strings
│   └── screens/           # chat + camera + settings
└── assets/models/         # bundled pink-elephant-talk-3b-q4.gguf + mmproj
```

## Model delivery
- GGUF Q4_K_M (~2GB) + mmproj bundled in the app package (user chose
  "bundle in the app": everything installed at once).

## Distribution
- Android: APK (direct link) + Play Store
- iOS: TestFlight -> App Store
