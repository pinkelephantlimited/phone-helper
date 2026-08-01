"""Stream the multilingual dataset files to Hugging Face.

Avoids building one giant in-memory parquet (which OOMs small machines).
Uploads the JSONL + images as plain files; the training notebook
snapshot-downloads the repo and builds the dataset from paths.

Usage:
    export HF_TOKEN=hf_xxx
    python push_dataset.py --src ../multilingual --repo pinkelephantlimited/phone-helper-vlm-dataset
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi


def push_files(src: str | Path = "../multilingual",
               images: str | Path = "../images",
               repo: str = "pinkelephantlimited/phone-helper-vlm-dataset",
               token: str = "") -> None:
    """Stream JSONL + image files to a HF dataset repo (no giant parquet)."""
    api = HfApi(token=token or None)
    print("Creating repo (private)...")
    api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True, private=True)

    for lang_dir in sorted(Path(src).resolve().glob("*/")):
        train = lang_dir / "train.jsonl"
        if not train.exists():
            continue
        print(f"uploading {lang_dir.name}/train.jsonl")
        api.upload_file(
            path_or_fileobj=str(train), repo_id=repo, repo_type="dataset",
            path_in_repo=f"data/{lang_dir.name}/train.jsonl",
        )

    for lang_dir in sorted(Path(images).resolve().glob("*/")):
        print(f"uploading images/{lang_dir.name} ...")
        api.upload_folder(
            repo_id=repo, repo_type="dataset", folder_path=str(lang_dir),
            path_in_repo=f"images/{lang_dir.name}",
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="../multilingual")
    ap.add_argument("--repo", default="pinkelephantlimited/phone-helper-vlm-dataset")
    ap.add_argument("--also-images", default="../images",
                    help="root dir holding the per-language image subfolders")
    args = ap.parse_args()
    push_files(src=args.src, images=args.also_images, repo=args.repo)


if __name__ == "__main__":
    main()
