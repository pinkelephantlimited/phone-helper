# Contributing to Pink Elephant Talk

Thanks for your interest in Pink Elephant Talk, the flagship on-device AI
product of [Pink Elephant Limited](https://huggingface.co/pinkelephantlimited)
(Hong Kong).

## Ways to contribute

- **Report bugs** — open an issue with device model, Android version, steps to
  reproduce, and any logs shown on screen.
- **Suggest features** — open an issue describing the use case and expected
  behavior.
- **Improve the model** — contributions to the training pipeline (`train/`,
  `data/pipeline/`, `molab/`) are welcome.
- **Review and PR** — small, focused pull requests are appreciated.

## Development setup

- The app is React Native (TypeScript) with llama.rn for GGUF inference.
  See `docs/ROADMAP.md` and `app/README.md` for the structure.
- The VLM training pipeline is in `train/` and `data/pipeline/`.

## Pull requests

1. Work from a feature branch off `main`.
2. Keep changes focused; include a clear description of what and why.
3. Run any relevant tests and mention how they were run.
4. Open the PR against `main` and wait for review.

## Licensing

This project is released under the Apache-2.0 license. By contributing you
agree that your contributions are licensed under the same terms. Base model
attribution (Qwen, Alibaba) is preserved per the Apache-2.0 license.