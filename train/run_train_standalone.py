"""Run the VLM fine-tune in a clean subprocess (no stale marimo kernel state).

Usage:
    HF_TOKEN=... python run_train_standalone.py \
        --model pinkelephantlimited/qwen2.5-vl-3b-instruct-nested \
        --out pinkelephantlimited/pink-elephant-talk-vlm-3b \
        --data ../data/multilingual

Runs detached so a client disconnect cannot kill training.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("/marimo")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="pinkelephantlimited/qwen2.5-vl-3b-instruct-nested")
    ap.add_argument("--out", default="pinkelephantlimited/pink-elephant-talk-vlm-3b")
    ap.add_argument("--data", default=str(REPO / "data" / "multilingual"))
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1536)
    ap.add_argument("--lora-r", type=int, default=32)
    ap.add_argument("--log", default=str(ROOT / "train.log"))
    ap.add_argument("--sync", action="store_true", help="run in foreground (blocking)")
    args = ap.parse_args()

    python = "/tmp/uv-venv/bin/python"
    sys_path = ":".join(["/usr/local/lib/python3.13/site-packages"] + sys.path)
    env = dict(os.environ)
    env["PYTHONPATH"] = sys_path
    env["HF_TOKEN"] = os.environ.get("HF_TOKEN", "")

    cmd = [
        python, "-m", "train.train_vlm",
        "--dataset", args.data,
        "--model", args.model,
        "--out", args.out,
        "--lr", str(args.lr),
        "--epochs", str(args.epochs),
        "--max-steps", str(args.max_steps),
        "--batch", str(args.batch),
        "--grad-accum", str(args.grad_accum),
        "--max-len", str(args.max_len),
        "--lora-r", str(args.lora_r),
    ]

    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        f.write("=== launch %s ===\n" % " ".join(cmd))

    if args.sync:
        subprocess.run(cmd, env=env, cwd=REPO, check=True)
    else:
        with open(log, "a") as f:
            proc = subprocess.Popen(
                cmd, env=env, cwd=REPO,
                stdout=f, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(proc.pid)


if __name__ == "__main__":
    main()
