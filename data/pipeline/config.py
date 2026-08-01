PRIORITY_LANGUAGES = [
    "en", "es", "fr", "ar", "hi", "zh",
    "pt", "ru", "id", "sw", "bn", "de",
]

# BCP-47 codes used by NLLB-200 for translation
LANG_TO_NLLB = {
    "en": "eng_Latn", "es": "spa_Latn", "fr": "fra_Latn", "ar": "arb_Arab",
    "hi": "hin_Deva", "zh": "zho_Hans", "pt": "por_Latn", "ru": "rus_Cyrl",
    "id": "ind_Latn", "sw": "swh_Latn", "bn": "ben_Beng", "de": "deu_Latn",
}

# Language display names (for dataset metadata)
LANG_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "ar": "Arabic",
    "hi": "Hindi", "zh": "Chinese (Mandarin)", "pt": "Portuguese",
    "ru": "Russian", "id": "Indonesian", "sw": "Swahili", "bn": "Bengali",
    "de": "German",
}

# Task categories covered by the daily-helper dataset
TASK_TYPES = [
    "read_expiry_date",
    "read_price",
    "read_sign",
    "read_instruction",
    "read_menu",
    "read_receipt",
    "object_color",
    "object_identity",
    "short_answer",
]
