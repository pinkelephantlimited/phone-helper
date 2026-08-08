# Pink Elephant Talk — data

Two-step pipeline generates the training set entirely offline:

```
build_english.py ──► data/en/train.jsonl        (source, English)
translate.py    ──► data/multilingual/<lang>/train.jsonl
```

## 1. Build English source
```bash
cd data/pipeline
python build_english.py --out ../en --images ../images --n 2000
```

Generates synthetic "daily life" images (labels, prices, signs, menus,
receipts, medicine instructions) with rendered text, plus QA pairs in
Qwen2.5-VL chat format. Each line:
```json
{"id": "en-00001", "language": "en", "image": "data/images/en-...jpg",
 "image_text": "EXP 2027-03-14", "task": "read_expiry_date",
 "messages": [
   {"role": "user", "content": [{"type": "image"},
                                {"type": "text", "text": "What is the expiry date?"}]},
   {"role": "assistant", "content": [{"type": "text", "text": "It expires on 2027-03-14."}]}
 ]}
```

## 2. Translate to priority languages
```bash
python translate.py --src ../en/train.jsonl --out ../multilingual \
    --images ../images --langs all
```
- Uses NLLB-200 (`facebook/nllb-200-distilled-600M`) offline.
- Translates only the ~60 **unique** strings once (fast + consistent).
- Re-renders each image with the translated text using script-aware fonts
  (Arabic RTL, Devanagari, Bengali, CJK, Cyrillic).
- Results cached in `translation_cache.json` so interrupted runs resume.

## 3. Push to Hugging Face
```bash
export HF_TOKEN=hf_xxx
python push_dataset.py  # (not yet written)
```

## Languages
`en es fr ar hi zh pt ru id sw bn de` — see `config.py`.
