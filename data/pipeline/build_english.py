"""Build the English daily-helper VLM dataset.

Generates synthetic "daily life" images (labels, prices, signs, menus,
receipts, medicine instructions) with rendered text, plus natural-language
QA pairs in Qwen2.5-VL chat format. Fully offline, deterministic, free.

Usage:
    python build_english.py --out ../en --n 2000 --seed 42

Output: one JSONL line per sample:
    {"id": "en-0001", "image": "<abs path>", "messages": [
        {"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": "What is the expiry date?"}]},
        {"role": "assistant", "content": [
            {"type": "text", "text": "It expires on 2027-03-14."}]},
    ]}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIRS = [
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
]

# --------------------------------------------------------------------------
# Image rendering helpers
# --------------------------------------------------------------------------


def _candidates():
    for d in FONT_DIRS:
        if d.exists():
            for p in d.rglob("*"):
                if p.suffix.lower() in (".ttf", ".otf") and "Emoji" not in p.name:
                    yield p


FONTS = list(_candidates())
TEXTURES = ["#f5f0e6", "#fdfaf0", "#ffffff", "#eef1f5", "#fff4f0", "#f2f7ee", "#faf3e3"]


def _font(size: int) -> ImageFont.FreeTypeFont:
    path = random.choice(FONTS) if FONTS else None
    try:
        return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def render_text_image(text: str, *, w: int = 640, h: int = 240) -> Image.Image:
    """Render text onto a realistic-looking label/photo surface."""
    bg = Image.new("RGB", (w, h), random.choice(TEXTURES))
    draw = ImageDraw.Draw(bg)

    # subtle background noise
    for _ in range(60):
        x, y = random.randint(0, w), random.randint(0, h)
        c = random.randint(180, 240)
        draw.ellipse([x, y, x + random.randint(2, 8), y + random.randint(2, 8)],
                     fill=(c, c, c))

    font = _font(random.randint(36, 72))
    angle = random.uniform(-4, 4)
    x = random.randint(20, 60)
    y = random.randint(20, 80)
    draw.text((x, y), text, font=font, fill=(20, 20, 20))

    img = bg.rotate(angle, expand=False, fillcolor=(255, 255, 255))
    if random.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.9)))
    if random.random() < 0.3:
        img = img.filter(ImageFilter.EDGE_ENHANCE)
    return img


def _render_and_save(text: str, out_dir: Path, sample_id: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = render_text_image(text)
    path = out_dir / f"{sample_id}.jpg"
    img.save(path, quality=88)
    return str(path)


# --------------------------------------------------------------------------
# Task generators
# --------------------------------------------------------------------------


@dataclass
class Task:
    image_text: str | None
    image_path: str | None
    messages: list[dict]


def _msg(user: str, assistant: str, has_image: bool = True) -> list[dict]:
    user_content = [{"type": "image"}] if has_image else []
    user_content.append({"type": "text", "text": user})
    return [
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": [{"type": "text", "text": assistant}]},
    ]


def _expiry_date(rng: random.Random, out_dir: Path, sid: str) -> Task:
    d = date.today() + timedelta(days=rng.randint(30, 1500))
    fmt = rng.choice([
        d.strftime("%Y-%m-%d"),
        d.strftime("%d/%m/%Y"),
        d.strftime("%m/%Y"),
        "EXP " + d.strftime("%Y-%m-%d"),
        "Expiry: " + d.strftime("%B %Y"),
    ])
    if rng.random() < 0.5:
        fmt = "EXPIRY DATE " + fmt
    path = _render_and_save(fmt, out_dir, sid)
    questions = [
        "What is the expiry date?",
        "When does this expire?",
        "What date should I throw this out?",
        "Is this still good?",
    ]
    q = rng.choice(questions)
    if fmt.startswith(("EXPIRY", "EXP ")) or "Expiry" in fmt:
        date_str = re.sub(r"^(EXPIRY DATE|EXP|Expiry:\s*)\s*", "", fmt)
    else:
        date_str = fmt
    answers = [
        f"It expires on {date_str}.",
        f"The expiry date is {date_str}.",
        f"You should use it before {date_str}.",
    ]
    return Task(fmt, path, _msg(q, rng.choice(answers)))


def _price(rng: random.Random, out_dir: Path, sid: str) -> Task:
    price = rng.choice([0.5, 0.99, 1.5, 2.49, 3.99, 5.0, 7.5, 9.99, 12.5, 19.99, 25.0])
    fmt = rng.choice([
        f"${price:.2f}", f"{price:.2f}", f"€{price:.2f}",
        f"PRICE ${price:.2f}", f"${price:.2f} / kg", f"{price:.0f} CHF",
    ])
    path = _render_and_save(fmt, out_dir, sid)
    q = rng.choice([
        "How much does this cost?", "What is the price?",
        "How much is this item?", "What does the price tag say?",
    ])
    a = rng.choice([
        f"It costs {fmt}.", f"The price is {fmt}.", f"That is {fmt}.",
    ])
    return Task(fmt, path, _msg(q, a))


def _sign(rng: random.Random, out_dir: Path, sid: str) -> Task:
    texts = [
        "NO PARKING", "STAFF ONLY", "OPEN 24 HOURS", "EXIT", "WET FLOOR",
        "MIND THE STEP", "DO NOT ENTER", "FREE WIFI", "MENU INSIDE",
        "WASH HANDS", "TRASH", "RECYCLING", "PHARMACY", "EMERGENCY EXIT",
        "OUT OF ORDER", "USE OTHER DOOR", "PLEASE KNOCK", "RING BELL",
    ]
    text = rng.choice(texts)
    path = _render_and_save(text, out_dir, sid)
    q = rng.choice([
        "What does this sign say?", "Can you read this sign for me?",
        "What is written here?", "What should I do according to this sign?",
    ])
    a = f"It says: “{text}”."
    return Task(text, path, _msg(q, a))


def _instruction(rng: random.Random, out_dir: Path, sid: str) -> Task:
    pairs = [
        ("Take one tablet twice a day.", "How should I take this medicine?"),
        ("Apply a thin layer to the affected area.", "How do I use this cream?"),
        ("Take 5 ml three times a day after meals.", "What is the dosage for this?"),
        ("Shake well before use.", "What should I do with this bottle first?"),
        ("Store below 25°C in a dry place.", "How should I store this?"),
        ("Do not exceed 4 tablets in 24 hours.", "What is the maximum dose?"),
    ]
    text, q = rng.choice(pairs)
    path = _render_and_save(text, out_dir, sid)
    a = rng.choice([
        f"The instruction says: {text}",
        f"You should {text[0].lower()}{text[1:]}",
    ])
    return Task(text, path, _msg(q, a))


def _menu(rng: random.Random, out_dir: Path, sid: str) -> Task:
    items = [
        ("Burger", "8.50"), ("Pasta", "9.00"), ("Salad", "6.50"),
        ("Pizza", "12.00"), ("Soup", "4.50"), ("Rice", "5.00"),
        ("Chicken", "10.00"), ("Tea", "2.00"), ("Coffee", "3.00"),
    ]
    name, price = rng.choice(items)
    text = f"{name} ... {price}"
    path = _render_and_save(text, out_dir, sid)
    q = rng.choice([
        f"How much is the {name.lower()}?", "What does the menu say for this item?",
        "How much does this dish cost?",
    ])
    a = rng.choice([
        f"The {name.lower()} costs {price}.", f"It is {price}.",
    ])
    return Task(text, path, _msg(q, a))


def _receipt(rng: random.Random, out_dir: Path, sid: str) -> Task:
    total = round(rng.uniform(2.0, 60.0), 2)
    lines = [
        "MILK 3.50", "BREAD 2.00", "EGGS 4.25", "FRUIT 6.00", "COFFEE 4.00",
        "CHEESE 5.50", "JUICE 3.25", "SNACK 2.75",
    ]
    pick = rng.sample(lines, rng.randint(2, 4))
    text = "\n".join(pick + [f"TOTAL {total:.2f}"])
    path = _render_and_save(text, out_dir, sid)
    q = rng.choice([
        "What is the total on this receipt?", "How much was the total?",
        "What did I pay in total?",
    ])
    a = f"The total is {total:.2f}."
    return Task(text, path, _msg(q, a))


def _short_answer(rng: random.Random, out_dir: Path, sid: str) -> Task:
    """Text-only daily-helper chat (no image)."""
    pairs = [
        ("What should I do if I get lost?", "Stay calm, look for a safe spot, and ask someone nearby for help."),
        ("How much water should I drink a day?", "About 8 glasses, or more if it is hot or you exercise."),
        ("What is the emergency number in most of Europe?", "112."),
        ("I forgot my password. What should I do?", "Try the recovery option, then update it to something you remember."),
        ("How can I tell if food is still safe?", "Check the expiry date and smell or look for signs of spoilage."),
        ("What should I carry when going out?", "Your phone, keys, some money, water, and an ID."),
        ("How do I use a phone to call for help?", "Unlock it, open the dialer, type 112 or 911, and press call."),
        ("I feel dizzy. What should I do?", "Sit down, drink water, rest, and get help if it does not pass."),
    ]
    q, a = rng.choice(pairs)
    return Task(None, None, _msg(q, a, has_image=False))


GENERATORS = {
    "read_expiry_date": _expiry_date,
    "read_price": _price,
    "read_sign": _sign,
    "read_instruction": _instruction,
    "read_menu": _menu,
    "read_receipt": _receipt,
    "short_answer": _short_answer,
}


# --------------------------------------------------------------------------


def _sample_id(sid_counter: int, text: str, lang: str = "en") -> str:
    h = hashlib.sha1(f"{sid_counter}:{text}".encode()).hexdigest()[:8]
    return f"{lang}-{sid_counter:05d}-{h}"


def build_english(n: int = 2000, seed: int = 42,
                  out_dir: str | Path = "../en",
                  images_dir: str | Path = "../images") -> Path:
    """Generate the English daily-helper dataset. Returns the JSONL path."""
    rng = random.Random(seed)
    out_dir = Path(out_dir).resolve()
    img_dir = Path(images_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    keys = list(GENERATORS)
    samples = []
    for i in range(n):
        key = keys[i % len(keys)]
        sid = _sample_id(i, key)
        task = GENERATORS[key](rng, img_dir, sid)
        img_path = task.image_path
        if img_path is not None:
            # store relative to repo so the path survives on any machine
            rel = str(Path(img_path).relative_to(Path(__file__).resolve().parents[2]))
        else:
            rel = None
        samples.append({
            "id": sid,
            "language": "en",
            "image": rel,
            "image_text": task.image_text,
            "task": key,
            "messages": task.messages,
        })

    out_file = out_dir / "train.jsonl"
    with open(out_file, "w") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"Wrote {len(samples)} samples to {out_file}")
    print(f"Images in {img_dir}")
    return out_file


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../en")
    ap.add_argument("--n", type=int, default=2000, help="total samples")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--images", default="../images")
    args = ap.parse_args()
    build_english(n=args.n, seed=args.seed, out_dir=args.out, images_dir=args.images)


if __name__ == "__main__":
    main()
