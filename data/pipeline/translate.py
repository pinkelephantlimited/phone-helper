"""Translate the English daily-helper dataset into priority languages.

Design: translate only the *unique* strings once (there are only ~60
distinct texts + ~80 Q/A templates), then re-render each image with the
translated text using script-aware fonts. This keeps the cost tiny and the
output consistent (image text matches the answer).

Translator: NLLB-200 (facebook/nllb-200-distilled-600M) via transformers,
fully offline once the model is cached. Set HF_TOKEN for first download.

Usage:
    python translate.py --src ../en --out ../multilingual --langs es,fr,hi

Output: one JSONL per language in --out, e.g. ../multilingual/es/train.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import LANG_TO_NLLB

# --------------------------------------------------------------------------
# Script-aware fonts (macOS system fonts). Add your own paths if on Linux.
# --------------------------------------------------------------------------
FONT_HINTS = {
    "ar": ["/System/Library/Fonts/GeezaPro.ttc", "/System/Library/Fonts/Baghdad.ttc"],
    "hi": ["/System/Library/Fonts/Kohinoor.ttc"],
    "bn": ["/System/Library/Fonts/KohinoorBangla.ttc", "/System/Library/Fonts/Bangla MN.ttc"],
    "zh": ["/System/Library/Fonts/Hiragino Sans GB.ttc"],
    "ru": ["/System/Library/Fonts/Arial Unicode.ttf"],
    "en": ["/System/Library/Fonts/Helvetica.ttc"],
    "de": ["/System/Library/Fonts/Helvetica.ttc"],
    "es": ["/System/Library/Fonts/Helvetica.ttc"],
    "fr": ["/System/Library/Fonts/Helvetica.ttc"],
    "pt": ["/System/Library/Fonts/Helvetica.ttc"],
    "id": ["/System/Library/Fonts/Helvetica.ttc"],
    "sw": ["/System/Library/Fonts/Helvetica.ttc"],
}
FALLBACK_FONT = "/System/Library/Fonts/Arial Unicode.ttf"
_TEXTURES = ["#f5f0e6", "#fdfaf0", "#ffffff", "#eef1f5", "#fff4f0", "#f2f7ee", "#faf3e3"]


def load_font(lang: str, size: int) -> ImageFont.FreeTypeFont:
    for cand in FONT_HINTS.get(lang, []) + [FALLBACK_FONT]:
        if Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_text_image(text: str, lang: str, *, w: int = 640, h: int = 240) -> Image.Image:
    rng = random.Random(hashlib.sha1((lang + text).encode()).hexdigest())
    bg = Image.new("RGB", (w, h), rng.choice(_TEXTURES))
    draw = ImageDraw.Draw(bg)
    for _ in range(60):
        x, y = rng.randint(0, w), rng.randint(0, h)
        c = rng.randint(180, 240)
        draw.ellipse([x, y, x + rng.randint(2, 8), y + rng.randint(2, 8)], fill=(c, c, c))
    font = load_font(lang, rng.randint(36, 60))
    angle = rng.uniform(-4, 4)
    draw.text((rng.randint(20, 60), rng.randint(20, 80)), text, font=font, fill=(20, 20, 20))
    img = bg.rotate(angle, expand=False, fillcolor=(255, 255, 255))
    if rng.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.9)))
    return img


# --------------------------------------------------------------------------
# Translation via NLLB-200
# --------------------------------------------------------------------------
class Translator:
    def __init__(self, device: str = "cpu", batch: int = 16):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        name = "facebook/nllb-200-distilled-600M"
        self.tok = AutoTokenizer.from_pretrained(name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(name).to(device)
        self.device = device
        self.batch = batch

    def _gen(self, texts: list[str], target_lang: str) -> list[str]:
        tgt = LANG_TO_NLLB[target_lang]
        out = []
        for i in range(0, len(texts), self.batch):
            chunk = texts[i:i + self.batch]
            self.tok.src_lang = "eng_Latn"
            enc = self.tok(chunk, return_tensors="pt", padding=True).to(self.device)
            gen = self.model.generate(
                **enc, forced_bos_token_id=self.tok.convert_tokens_to_ids(tgt),
                max_new_tokens=64, max_length=64,
            )
            out += self.tok.batch_decode(gen, skip_special_tokens=True)
        return out

    def __call__(self, texts: list[str], target_lang: str) -> list[str]:
        return self._gen(texts, target_lang)


def _slug(lang: str, text: str, idx: int) -> str:
    h = hashlib.sha1((lang + text).encode()).hexdigest()[:10]
    return f"{lang}-{idx:05d}-{h}"


def translate_all(src: str | Path = "../en/train.jsonl",
                  out: str | Path = "../multilingual",
                  images: str | Path = "../images",
                  langs: str | list[str] = "all",
                  device: str = "cpu") -> None:
    """Translate the English dataset into priority languages + re-render images.

    Results are cached in `<out>/../translation_cache.json` so interrupted
    runs resume without re-translating finished strings.
    """
    src_rows = [json.loads(l) for l in Path(src).open() if l.strip()]

    if langs == "all":
        langs = list(LANG_TO_NLLB)
    elif isinstance(langs, str):
        langs = [x.strip() for x in langs.split(",") if x.strip()]

    tr = Translator(device, batch=int(os.environ.get("BATCH", "16")))

    # 1) collect unique strings to translate (messages + rendered image text)
    texts = set()
    for r in src_rows:
        for m in r["messages"]:
            for c in m["content"]:
                if c.get("type") == "text":
                    texts.add(c["text"])
        if r.get("image_text"):
            texts.add(r["image_text"])
    texts = sorted(texts)
    print(f"Translating {len(texts)} unique strings x {len(langs)} langs", flush=True)

    # persistent cache: survive interrupted runs (translation is the slow part)
    cache_path = Path(out).resolve().parent / "translation_cache.json"
    cache: dict[str, dict[str, str]] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    pending: dict[str, list[str]] = {}
    for t in texts:
        cache.setdefault(t, {})
        for lg in langs:
            if lg in cache[t]:
                continue
            pending.setdefault(lg, []).append(t)

    for lg, todo in pending.items():
        if lg == "en":
            for t in todo:
                cache[t][lg] = t
            continue
        print(f"translating {len(todo)} strings -> {lg}", flush=True)
        results = tr(todo, lg)
        for t, r in zip(todo, results):
            cache[t][lg] = r
        cache_path.write_text(json.dumps(cache, ensure_ascii=False))
    print("translation cache saved", flush=True)

    # 2) write per-language JSONL + re-rendered images
    out_root = Path(out).resolve()
    img_root = Path(images).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]

    for lg in langs:
        lg_dir = out_root / lg
        lg_dir.mkdir(parents=True, exist_ok=True)
        out_path = lg_dir / "train.jsonl"
        print(f"writing {lg} ...", flush=True)
        with open(out_path, "w") as f:
            for i, r in enumerate(src_rows):
                new = dict(r)
                new["id"] = f"{lg}-{i:05d}"
                new["language"] = lg
                new["messages"] = []
                for m in r["messages"]:
                    content = []
                    for c in m["content"]:
                        if c.get("type") == "image":
                            content.append({"type": "image"})
                        else:
                            content.append({"type": "text", "text": cache[c["text"]][lg]})
                    new["messages"].append({"role": m["role"], "content": content})
                # re-render image with translated image text
                src_img_text = r.get("image_text")
                if src_img_text:
                    img = render_text_image(cache[src_img_text][lg], lg)
                elif r.get("image"):
                    src_img_path = repo_root / r["image"]
                    img = Image.open(str(src_img_path))
                else:
                    f.write(json.dumps(new, ensure_ascii=False) + "\n")
                    continue
                sid = _slug(lg, r["id"], i)
                ipath = img_root / lg / f"{sid}.jpg"
                ipath.parent.mkdir(parents=True, exist_ok=True)
                img.save(ipath, quality=88)
                new["image"] = str(ipath.relative_to(repo_root))
                f.write(json.dumps(new, ensure_ascii=False) + "\n")
        print(f"Wrote {lg_dir}/train.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="../en/train.jsonl")
    ap.add_argument("--out", default="../multilingual")
    ap.add_argument("--images", default="../images")
    ap.add_argument("--langs", default="all",
                    help="comma list or 'all' for every priority language")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    translate_all(args.src, args.out, args.images, args.langs, args.device)


if __name__ == "__main__":
    main()
