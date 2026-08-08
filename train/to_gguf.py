"""Convert the fine-tuned LoRA adapter into an on-device GGUF bundle.

Two stages:
1. Merge LoRA into the base model -> full safetensors.
2. Convert to GGUF Q4_K_M + mmproj (vision projector) using llama.cpp,
   so llama.rn (the app) can run it on a phone.

Prereq: llama.cpp built locally (or use official llama-cpp-python tools).
    git clone https://github.com/ggml-org/llama.cpp
    cd llama.cpp && make -j

Usage:
    python to_gguf.py --adapter <lora-dir> --base Qwen/Qwen2.5-VL-3B-Instruct \
        --llamacpp ../llama.cpp --out ../models/pink-elephant-talk-3b-q4.gguf
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from peft import PeftModel
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration


def merge_lora(adapter: Path, base: str, out_dir: Path) -> None:
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        base, torch_dtype="auto", trust_remote_code=True, device_map="cpu",
    )
    model = PeftModel.from_pretrained(model, str(adapter))
    model = model.merge_and_unload()
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    processor = AutoProcessor.from_pretrained(base, trust_remote_code=True)
    processor.save_pretrained(str(out_dir))


def convert_to_gguf(llamacpp: Path, merged: Path, out: Path, quant: str = "q4_k_m") -> None:
    """Convert HF -> GGUF f16 (with mmproj), then quantize.

    Modern llama.cpp's convert_hf_to_gguf.py emits f16/f32/bf16 and requires a
    separate llama-quantize step for K-quants like Q4_K_M.
    """
    conv = llamacpp / "convert_hf_to_gguf.py"
    build = llamacpp / "build"
    quant_bin = build / "bin" / "llama-quantize"
    py = sys.executable
    # temporary f16 file next to the final target
    tmp = out.with_suffix(".f16.gguf")
    subprocess.run(
        [py, str(conv), str(merged), "--outfile", str(tmp),
         "--outtype", "f16", "--model-name", "pink-elephant-talk-vlm-3b"],
        check=True,
    )
    subprocess.run(
        [py, str(conv), str(merged), "--outfile",
         str(tmp.with_name(tmp.stem + "-mmproj.gguf")), "--outtype", "f16",
         "--mmproj"],
        check=True,
    )
    subprocess.run([str(quant_bin), str(tmp), str(out), quant], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="LoRA adapter dir (from train_vlm.py)")
    ap.add_argument("--base", default="Qwen/Qwen2.5-VL-3B-Instruct")
    ap.add_argument("--llamacpp", default="../llama.cpp", help="llama.cpp source dir")
    ap.add_argument("--out-dir", default="../models")
    ap.add_argument("--skip-merge", action="store_true")
    ap.add_argument("--quant", default="q4_k_m")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    merged = out_dir / "merged"
    if not args.skip_merge:
        print("Merging LoRA into base ...")
        merge_lora(Path(args.adapter).resolve(), args.base, merged)

    print("Converting to GGUF ...")
    convert_to_gguf(Path(args.llamacpp).resolve(), merged,
                    out_dir / f"pink-elephant-talk-3b-{args.quant}.gguf", args.quant)
    print(f"Done: {out_dir}")


if __name__ == "__main__":
    main()
