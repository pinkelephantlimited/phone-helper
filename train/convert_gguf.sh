#!/bin/bash
set -e
echo '=== [1/3] merge LoRA + base ==='
PYTHONPATH=/usr/local/lib/python3.13/site-packages /tmp/uv-venv/bin/python /marimo/phone-helper/train/to_gguf.py \
  --adapter /marimo/phone-helper/pinkelephantlimited/output \
  --base pinkelephantlimited/qwen2.5-vl-3b-instruct-nested \
  --llamacpp /marimo/llama.cpp --out-dir /marimo/models
echo '=== [2/3] build llama.cpp ==='
cd /marimo/llama.cpp && cmake -B build -DLLAMA_CURL=OFF && cmake --build build -j 20
echo '=== done ==='