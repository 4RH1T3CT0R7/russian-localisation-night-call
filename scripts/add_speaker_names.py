"""
Add uppercase English speaker names to JSON for TMP_Text translation.
The game's dialogue parser uses English names internally;
the TMP_Text interceptor translates displayed names to Russian.
"""
import json, sys, os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'Russian_UI', 'full_translation_mapping.json')

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Loaded {len(data)} entries")

# Uppercase speaker name mappings (English -> Russian)
# These are used by the game's dialogue engine as speaker identifiers
speaker_names = {
    # Standard passengers
    "PATRICIA": "\u041f\u0410\u0422\u0420\u0418\u0426\u0418\u042f",      # ПАТРИЦИЯ
    "PURVA": "\u041f\u0423\u0420\u0412\u0410",                            # ПУРВА
    "ALARIC": "\u0410\u041b\u0410\u0420\u0418\u041a",                     # АЛАРИК
    "JEAN-NO\u00cbL": "\u0416\u0410\u041d-\u041d\u041e\u042d\u041b\u042c", # ЖАН-НОЭЛЬ
    "JEAN-NOEL": "\u0416\u0410\u041d-\u041d\u041e\u042d\u041b\u042c",     # ЖАН-НОЭЛЬ (no accent)
    "HUGO": "\u0413\u042e\u0413\u041e",                                    # ГЮГО
    "ESMERALDA": "\u042d\u0421\u041c\u0415\u0420\u0410\u041b\u042c\u0414\u0410", # ЭСМЕРАЛЬДА
    "SALIM": "\u0421\u0410\u041b\u0418\u041c",                            # САЛИМ
    "VINCENT": "\u0412\u0415\u041d\u0421\u0410\u041d",                    # ВЕНСАН
    "LUDWIG": "\u041b\u042e\u0414\u0412\u0418\u0413",                     # ЛЮДВИГ
    "CAMILLE": "\u041a\u0410\u041c\u0418\u041b\u041b\u0410",              # КАМИЛЛА
    "ANTOINE": "\u0410\u041d\u0422\u0423\u0410\u041d",                    # АНТУАН
    "ARIANE": "\u0410\u0420\u0418\u0410\u041d\u0410",                     # АРИАНА
    "CHRISTOPHE": "\u041a\u0420\u0418\u0421\u0422\u041e\u0424",           # КРИСТОФ
    "LE\u00cfA": "\u041b\u0415\u042f",                                     # ЛЕЯ
    "LEIA": "\u041b\u0415\u042f",                                          # ЛЕЯ (no accent)
    "FRAGONARD": "\u0424\u0420\u0410\u0413\u041e\u041d\u0410\u0420",      # ФРАГОНАР
    "ALICIA": "\u0410\u041b\u0418\u0421\u0418\u042f",                     # АЛИСИЯ
    "G\u00c9RARD": "\u0416\u0415\u0420\u0410\u0420",                      # ЖЕРАР
    "GERARD": "\u0416\u0415\u0420\u0410\u0420",                           # ЖЕРАР (no accent)
    "GRACE": "\u0413\u0420\u0415\u0419\u0421",                            # ГРЕЙС
    "FRAN\u00c7OIS": "\u0424\u0420\u0410\u041d\u0421\u0423\u0410",        # ФРАНСУА
    "FRANCOIS": "\u0424\u0420\u0410\u041d\u0421\u0423\u0410",             # ФРАНСУА (no accent)
    "HERV\u00c9": "\u042d\u0420\u0412\u0415",                             # ЭРВЕ
    "HERVE": "\u042d\u0420\u0412\u0415",                                   # ЭРВЕ (no accent)
    "JACQUIE": "\u0416\u0410\u041a\u0418",                                # ЖАКИ
    "CARLO": "\u041a\u0410\u0420\u041b\u041e",                            # КАРЛО
    "CLAUDIA": "\u041a\u041b\u041e\u0414\u0418\u042f",                    # КЛОДИЯ
    "APOLLONIE": "\u0410\u041f\u041e\u041b\u041b\u041e\u041d\u0418",      # АПОЛЛОНИ
    "ALICE": "\u0410\u041b\u0418\u0421",                                   # АЛИС
    "HYOGA": "\u0425\u0401\u0413\u0410",                                   # ХЁГА
    "ADE": "\u0410\u0414\u0415",                                           # АДЕ
    "LUCIE": "\u041b\u042e\u0421\u0418",                                   # ЛЮСИ
    "\u00c9MILIE": "\u042d\u041c\u0418\u041b\u0418",                       # ЭМИЛИ
    "EMILIE": "\u042d\u041c\u0418\u041b\u0418",                            # ЭМИЛИ (no accent)
    "CAROLINA": "\u041a\u0410\u0420\u041e\u041b\u0418\u041d\u0410",       # КАРОЛИНА
    "J\u00c9R\u00d4ME": "\u0416\u0415\u0420\u041e\u041c",                 # ЖЕРОМ
    "JEROME": "\u0416\u0415\u0420\u041e\u041c",                           # ЖЕРОМ (no accent)
    "PETER": "\u041f\u0418\u0422\u0415\u0420",                            # ПИТЕР
    "G\u00c9RALDINE": "\u0416\u0415\u0420\u0410\u041b\u042c\u0414\u0418\u041d\u0410", # ЖЕРАЛЬДИНА
    "GERALDINE": "\u0416\u0415\u0420\u0410\u041b\u042c\u0414\u0418\u041d\u0410",      # ЖЕРАЛЬДИНА (no accent)
    "ANITA": "\u0410\u041d\u0418\u0422\u0410",                            # АНИТА
    "CHIARA": "\u041a\u042c\u042f\u0420\u0410",                           # КЬЯРА
    "PHIL": "\u0424\u0418\u041b",                                          # ФИЛ
    "SYLVIE": "\u0421\u0418\u041b\u042c\u0412\u0418",                     # СИЛЬВИ
    "SYLVAIN": "\u0421\u0418\u041b\u042c\u0412\u0415\u041d",              # СИЛЬВЕН
    "SEAN": "\u0428\u041e\u041d",                                          # ШОН
    "SHINJI": "\u0428\u0418\u041d\u0414\u0417\u0418",                     # ШИНДЗИ
    "CROUKY": "\u041a\u0420\u0423\u041a\u0418",                           # КРУКИ
    "FRANCINE": "\u0424\u0420\u0410\u041d\u0421\u0418\u041d\u0410",       # ФРАНСИНА
    "DJENABOU": "\u0414\u0416\u0415\u041d\u0410\u0411\u0423",             # ДЖЕНАБУ
    "JONAS": "\u0419\u041e\u041d\u0410\u0421",                            # ЙОНАС
    "CHRIS": "\u041a\u0420\u0418\u0421\u0422\u041e\u0424",                # КРИСТОФ (044_chris = Christophe Clairouin)
    "KADER": "\u041a\u0410\u0414\u0415\u0420",                            # КАДЕР
    "ANNABELLE": "\u0410\u041d\u041d\u0410\u0411\u0415\u041b\u042c",      # АННАБЕЛЬ
    "AGN\u00c8S": "\u0410\u041d\u042c\u0415\u0421",                       # АНЬЕС
    "AGNES": "\u0410\u041d\u042c\u0415\u0421",                            # АНЬЕС (no accent)
    "PIERROT": "\u041f\u042c\u0415\u0420\u041e",                          # ПЬЕРО
    "MIREILLE": "\u041c\u0418\u0420\u0415\u0419",                         # МИРЕЙ
    "DENIS": "\u0414\u0415\u041d\u0418",                                   # ДЕНИ
    "PAULINE": "\u041f\u041e\u041b\u0418\u041d",                          # ПОЛИН
    "JANET": "\u0416\u0410\u041d\u0415\u0422",                            # ЖАНЕТ
    "NINA": "\u041d\u0418\u041d\u0410",                                    # НИНА
    "PIERRE-HENRI": "\u041f\u042c\u0415\u0420-\u0410\u041d\u0420\u0418",  # ПЬЕР-АНРИ
    "SHA\u00cfNE": "\u0428\u0410\u0418\u041d\u042d",                       # ШАИНЭ
    "SHAINE": "\u0428\u0410\u0418\u041d\u042d",                            # ШАИНЭ (no accent)
    "MATHIEU": "\u041c\u0410\u0422\u042c\u0401",                          # МАТЬЁ
    "SONNY": "\u0421\u041e\u041d\u041d\u0418",                            # СОННИ
    "PIERRETTE": "\u041f\u042c\u0415\u0420\u0415\u0422\u0422",            # ПЬЕРЕТТ
    "MYRIAM": "\u041c\u0418\u0420\u0418\u0410\u041c",                     # МИРИАМ
    "EMILIA": "\u042d\u041c\u0418\u041b\u0418\u042f",                     # ЭМИЛИЯ
    "HENRI": "\u0410\u041d\u0420\u0418",                                   # АНРИ
    "ANG\u00c9LIQUE": "\u0410\u041d\u0416\u0415\u041b\u0418\u041a\u0410", # АНЖЕЛИКА
    "ANGELIQUE": "\u0410\u041d\u0416\u0415\u041b\u0418\u041a\u0410",      # АНЖЕЛИКА (no accent)
    "SANTA": "\u0421\u0410\u041d\u0422\u0410",                            # САНТА
    "HOUSSINE": "\u0423\u0421\u0418\u041d",                               # УСИН
    "GILDA": "\u0413\u0418\u041b\u042c\u0414\u0410",                      # ГИЛЬДА
    "ALEXANDRE": "\u0410\u041b\u0415\u041a\u0421\u0410\u041d\u0414\u0420", # АЛЕКСАНДР
    "DOCTOR": "\u0414\u041e\u041a\u0422\u041e\u0420",                     # ДОКТОР
    "BOSS": "\u0411\u041e\u0421\u0421",                                    # БОСС
    "LIEUTENANT": "\u041b\u0415\u0419\u0422\u0415\u041d\u0410\u041d\u0422", # ЛЕЙТЕНАНТ
    "ADA": "\u0410\u0414\u0410",                                           # АДА
    "MILO": "\u041c\u0418\u041b\u041e",                                    # МИЛО
    "CHANTAL": "\u0428\u0410\u041d\u0422\u0410\u041b\u042c",              # ШАНТАЛЬ
    "AMIRA": "\u0410\u041c\u0418\u0420\u0410",                            # АМИРА
    "LOLA": "\u041b\u041e\u041b\u0410",                                    # ЛОЛА
    "MYRTILLE": "\u041c\u0418\u0420\u0422\u0418\u041b\u042c",             # МИРТИЛЬ
    "XAVIER": "\u041a\u0421\u0410\u0412\u042c\u0415",                     # КСАВЬЕ
    "ROKSANA": "\u0420\u041e\u041a\u0421\u0410\u041d\u0410",              # РОКСАНА
    "ALPH": "\u0410\u041b\u042c\u0424",                                    # АЛЬФ
    "NATHALIE": "\u041d\u0410\u0422\u0410\u041b\u0418",                   # НАТАЛИ
    "JIM": "\u0414\u0416\u0418\u041c",                                     # ДЖИМ
    "MELCHIOR": "\u041c\u0415\u041b\u042c\u0425\u0418\u041e\u0420",       # МЕЛЬХИОР
    "B\u00c9R\u00c9NICE": "\u0411\u0415\u0420\u0415\u041d\u0418\u0421",   # БЕРЕНИС
    "BERENICE": "\u0411\u0415\u0420\u0415\u041d\u0418\u0421",             # БЕРЕНИС (no accent)
    "NADIA": "\u041d\u0410\u0414\u042f",                                   # НАДЯ
    "YVES": "\u0418\u0412",                                                # ИВ
    # Additional speaker names that may appear
    "V\u00c9RONIQUE": "\u0412\u0415\u0420\u041e\u041d\u0418\u041a\u0410", # ВЕРОНИКА
    "VERONIQUE": "\u0412\u0415\u0420\u041e\u041d\u0418\u041a\u0410",      # ВЕРОНИКА (no accent)
    "SHOHREH": "\u0428\u041e\u0425\u0420\u0415",                          # ШОХРЕ
    "AM\u00c9LIE": "\u0410\u041c\u0415\u041b\u0418",                      # АМЕЛИ
    "AMELIE": "\u0410\u041c\u0415\u041b\u0418",                           # АМЕЛИ (no accent)
    "L\u00c9ONIE": "\u041b\u0415\u041e\u041d\u0418",                      # ЛЕОНИ
    "LEONIE": "\u041b\u0415\u041e\u041d\u0418",                           # ЛЕОНИ (no accent)
    "CHILD\u00c9RIC": "\u0428\u0418\u041b\u042c\u0414\u0415\u0420\u0418\u041a", # ШИЛЬДЕРИК
    "CHILDERIC": "\u0428\u0418\u041b\u042c\u0414\u0415\u0420\u0418\u041a",      # ШИЛЬДЕРИК (no accent)
    "LUDIVINE": "\u041b\u042e\u0414\u0418\u0412\u0418\u041d",             # ЛЮДИВИН
    "JULIAN": "\u0416\u042e\u041b\u042c\u042f\u041d",                     # ЖЮЛЬЯН
    "SOPHIE": "\u0421\u041e\u0424\u0418",                                  # СОФИ
    "MARC": "\u041c\u0410\u0420\u041a",                                    # МАРК
    "NINON": "\u041d\u0418\u041d\u041e\u041d",                            # НИНОН
    # Title case versions (game might display "Salim" not "SALIM")
    "Patricia": "\u041f\u0430\u0442\u0440\u0438\u0441\u0438\u044f",       # Патрисия
    "Salim": "\u0421\u0430\u043b\u0438\u043c",                            # Салим
    "Sonny": "\u0421\u043e\u043d\u043d\u0438",                            # Сонни
    "Alph": "\u0410\u043b\u044c\u0444",                                    # Альф
    "Ludwig": "\u041b\u044e\u0434\u0432\u0438\u0433",                     # Людвиг
    "Doctor": "\u0414\u043e\u043a\u0442\u043e\u0440",                     # Доктор
    "Lieutenant": "\u041b\u0435\u0439\u0442\u0435\u043d\u0430\u043d\u0442", # Лейтенант
}

added = 0
for eng, rus in speaker_names.items():
    if eng not in data:
        data[eng] = rus
        added += 1
        print(f"  ADD: {eng} -> {rus}")
    elif data[eng] != rus:
        old = data[eng]
        # Don't overwrite existing translations that are longer/different context
        if len(old) <= len(rus) + 2:
            data[eng] = rus
            added += 1
            print(f"  UPD: {eng}: {old} -> {rus}")

print(f"\nAdded/updated: {added}")
print(f"Total entries: {len(data)}")

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done.")
