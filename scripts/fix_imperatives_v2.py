"""
Fix remaining imperative verb forms in choice/UI translations.
Only fixes values that are clearly choice labels (in parentheses) or UI strings,
NOT dialogue speech (which correctly uses imperative).
"""
import json, sys, os, re

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'Russian_UI', 'full_translation_mapping.json')

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Loaded {len(data)} entries")

# Targeted fixes for choice labels and UI elements
# Format: (old_value_exact_or_pattern, new_value, match_type)
# match_type: 'exact' = exact value match, 'startswith' = value starts with

fixes = []
fixed = 0

# --- UI STRINGS (exact value matches) ---
ui_exact = {
    "Выберите другого подозреваемого": "Выбрать другого подозреваемого",
    "Выберите": "Выбрать",
    "Нажмите": "Нажать",
    "Выберите расследование": "Выбрать расследование",
    "Выберите режим сложности": "Выбрать режим сложности",
    # Quoted UI duplicates
    '"Выберите другого подозреваемого"': '"Выбрать другого подозреваемого"',
    '"Выберите"': '"Выбрать"',
    '"Нажмите"': '"Нажать"',
    '"Выберите расследование"': '"Выбрать расследование"',
    '"Выберите режим сложности"': '"Выбрать режим сложности"',
}

# --- CHOICE LABELS (parenthetical actions - infinitive required) ---
choice_fixes = {
    # Radio/station choices
    "(Выберите \"культурную\" станцию).": "(Выбрать \"культурную\" станцию).",
    "(Выберите станцию \"хиты\").": "(Выбрать станцию \"хиты\").",
    "(Выберите рэп-станцию).": "(Выбрать рэп-станцию).",
    # Action choices
    "(Остановитесь.)": "(Остановиться.)",
    "(Остановите такси.)": "(Остановить такси.)",
    "(Остановитесь прямо на обочине.)": "(Остановиться прямо на обочине.)",
    "(Ответьте с сарказмом.)": "(Ответить с сарказмом.)",
    "(Верните ему улыбку.)": "(Вернуть ему улыбку.)",
    "(Скажите что-нибудь о перевозчике).": "(Сказать что-нибудь о перевозчике).",
    "(Скажите ей что-нибудь.)": "(Сказать ей что-нибудь.)",
    "(Скажите что-нибудь.)": "(Сказать что-нибудь.)",
    "(Расскажите о своем первом разе.)": "(Рассказать о своем первом разе.)",
    "(Расскажите ей правду.)": "(Рассказать ей правду.)",
    "(Включите нагрев.)": "(Включить нагрев.)",
    "(Спросите об Александре.)": "(Спросить об Александре.)",
    "(Спросите, откуда она знает, что вы нервничаете).": "(Спросить, откуда она знает, что вы нервничаете).",
    # Emote-prefixed choices (the "Радио:" and "Такси:" are already stripped emotes)
    "Радио: (Выключите радио.)": "(Выключить радио.)",
    "Радио: (Выключите радио).": "(Выключить радио).",
    "Такси: (Остановите такси.)": "(Остановить такси.)",
    # Quoted choice duplicates
    '"(Спросите об Александре.)"': '"(Спросить об Александре.)"',
    '"(Спросите, откуда она знает, что вы нервничаете)."': '"(Спросить, откуда она знает, что вы нервничаете)."',
}

# --- NARRATION/STAGE DIRECTION LINES (not in quotes, not dialogue) ---
narration_fixes = {
    "Вернитесь в такси.": "Вернуться в такси.",
    "Вернитесь в такси. Вернитесь к нормальному дыханию.": "Вернуться в такси. Вернуться к нормальному дыханию.",
    "Остановитесь на обочине, как только сможете.": "Остановиться на обочине, как только сможете.",
    "Скажите это как можно ласковее.": "Сказать это как можно ласковее.",
    "Расскажите об этом полиции.": "Рассказать об этом полиции.",
    "Примите к сведению...": "Принять к сведению...",
    "Подождите, пока две женщины войдут в здание, и заведите машину.": "Подождать, пока две женщины войдут в здание, и завести машину.",
    # Quoted variants
    '"Вернитесь в такси. Вернитесь к нормальному дыханию."': '"Вернуться в такси. Вернуться к нормальному дыханию."',
}

all_fixes = {}
all_fixes.update(ui_exact)
all_fixes.update(choice_fixes)
all_fixes.update(narration_fixes)

for key, val in data.items():
    if val in all_fixes:
        new_val = all_fixes[val]
        print(f"  FIX: \"{val}\" -> \"{new_val}\"")
        print(f"       KEY: {key[:80]}")
        data[key] = new_val
        fixed += 1

print(f"\nFixed: {fixed}")
print(f"Total entries: {len(data)}")

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done. JSON saved.")
