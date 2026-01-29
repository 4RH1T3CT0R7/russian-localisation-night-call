"""
Add all passenger full names to the translation JSON.
Uses established transliterations from existing dialogue translations.
"""
import json, sys, os

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'Russian_UI', 'full_translation_mapping.json')

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Loaded {len(data)} entries")

# Full name mappings: English -> Russian
# Transliterations follow established patterns from existing dialogue translations
passenger_names = {
    # Full names (as displayed on passenger cards)
    "Patricia Hossein": "Патрисия Хоссейн",
    "Purva Rao": "Пурва Рао",
    "Alaric Petitjean": "Аларик Петижан",
    "Jean-No\u00ebl Ranier": "Жан-Ноэль Ранье",
    "Hugo Delanney": "Гюго Деланне",
    "Esmeralda Pham": "Эсмеральда Фам",
    "Salim Wadyan": "Салим Вадьян",
    "Vincent Bourrelier": "Венсан Буррелье",
    "Ludwig": "Людвиг",
    "Camille Rivi\u00e8re & Antoine Parmentier": "Камилла Ривьер & Антуан Парментье",
    "Ariane Pham": "Ариана Фам",
    "Christophe Lerien": "Кристоф Лерьен",
    "Le\u00efa Graja": "Лея Граже",
    "Paul-Marie Fragonard": "Поль-Мари Фрагонар",
    "Alicia Clefs": "Алисия Клеф",
    "G\u00e9rard Petitcourt": "Жерар Петикур",
    "Grace Ndogo": "Грейс Ндого",
    "Fran\u00e7ois de la N\u00e9r\u00e9e": "Франсуа де ла Нере",
    "Herv\u00e9 Graillou": "Эрве Грайу",
    "Jacquie Elisabeth": "Жаки Элизабет",
    "Carlo Cerruti": "Карло Черрути",
    "Claudia Campos": "Клодия Кампос",
    "Apollonie Girardeau": "Аполлони Жирардо",
    "Alice & Hyoga Ricottier": "Алис & Хёга Рикотье",
    "Ade Bekhti": "Аде Бехти",
    "Ultra Skaterz": "Ультра Скейтерз",
    "Lucie Bataz & \u00c9milie Prince": "Люси Батаз & Эмили Пренс",
    "Carolina Jarreau": "Каролина Жарро",
    "J\u00e9r\u00f4me Praud": "Жером Про",
    "Peter \u201cDJ Watson\u201d Covelo": "Питер \u00abDJ Watson\u00bb Ковело",
    "G\u00e9raldine Zemmour": "Жеральдина Земмур",
    "Anita Ventimiglia": "Анита Вентимилья",
    "Chiara Yamane": "Кьяра Ямане",
    "Phil Bourgeois": "Фил Буржуа",
    "Sylvie & Sylvain Patrux": "Сильви & Сильвен Патрю",
    "Sean Christie": "Шон Кристи",
    "Shinji Kurumada": "Шиндзи Курумада",
    "Crouky": "Круки",
    "Francine Gayard": "Франсина Гайар",
    "Djenabou Henri": "Дженабу Анри",
    "Jonas Piersson": "Йонас Пьерссон",
    "Christophe Clairouin": "Кристоф Клеруэн",
    "V\u00e9ronique Peuchat": "Вероника Пёша",
    "Shohreh Pr\u00e9vert": "Шохре Превер",
    "Am\u00e9lie Franconi": "Амели Франкони",
    "L\u00e9onie Br\u00e9mieux": "Леони Бремьё",
    "Child\u00e9ric de Prahan": "Шильдерик де Праан",
    "Camille Antoine": "Камилла Антуан",
    "Ludivine Grangier": "Людивин Гранжье",
    "Julian Paz": "Жюльян Паз",
    "Kader Bergaoui": "Кадер Бергауи",
    "Annabelle Robert": "Аннабель Робер",
    "Agn\u00e8s Bertrand": "Аньес Бертран",
    "Pierrot Bataz": "Пьеро Батаз",
    "Mireille Popovski": "Мирей Поповски",
    "Denis Petitjean": "Дени Петижан",
    "Pauline Hoareau": "Полин Оаро",
    "Janet Cho": "Жанет Чо",
    "Nina Ishiguro": "Нина Исигуро",
    "Pierre-Henri de Pr\u00e9haut & Sha\u00efne Patel-Marquand": "Пьер-Анри де Прео & Шаинэ Пател-Маркан",
    "Mathieu Vidal": "Матьё Видаль",
    "Sonny Talpa": "Сонни Тальпа",
    "Antoine Mercador": "Антуан Меркадор",
    "Sophie & Marc Veterini": "Софи & Марк Ветерини",
    "Pierrette Manderas": "Пьеретт Мандерас",
    "Myriam Bardot": "Мириам Бардо",
    "Emilia Schoenderfer": "Эмилия Шёндерфер",
    "Henri du Tilleux": "Анри дю Тийё",
    "Ang\u00e9lique de Fondaumi\u00e8re": "Анжелика де Фондомьер",
    "Santa": "Санта",
    "???": "???",
    "Gilda Berger": "Гильда Берже",
    "Alexandre Leclerc": "Александр Леклер",
    "Ada LV426": "Ада LV426",
    "Milo Reacher": "Мило Ричер",
    "Chantal Lemonnier": "Шанталь Лемонье",
    "Amira Feghoul": "Амира Фегуль",
    "Lola Hopkins": "Лола Хопкинс",
    "Myrtille Thevenou": "Миртиль Тевену",
    "Xavier Turcev": "Ксавье Турцев",
    "Roksana Krilova": "Роксана Крилова",
    "Alph": "Альф",
    "Nathalie Pingeot": "Натали Пенжо",
    "Jim M.": "Джим М.",
    "Melchior de Rochas": "Мельхиор де Роша",
    "B\u00e9r\u00e9nice Fabre": "Беренис Фабр",
    "Nadia Boulanger & Yves Kilar": "Надя Буланже & Ив Килар",
    "Boss": "Босс",
    "Lieutenant Ninon Busset": "Лейтенант Нинон Бюссе",
}

# Also add first names that might not be there yet
first_names = {
    "Purva": "Пурва",
    "Djenabou": "Дженабу",
    "Leïa": "Лея",
    "Véronique": "Вероника",
    "Childéric": "Шильдерик",
    "Sophie": "Софи",
    "Marc": "Марк",
    "Sylvie": "Сильви",
    "Sylvain": "Сильвен",
    "Lucie": "Люси",
    "Émilie": "Эмили",
    "Hyoga": "Хёга",
    "Shaïne": "Шаинэ",
    "Pierre-Henri": "Пьер-Анри",
    "Nadia": "Надя",
    "Yves": "Ив",
    "Ninon": "Нинон",
}

# Also add non-accented variants of names with diacritics
# (in case the game sometimes displays without accents)
non_accented_variants = {
    "Jean-Noel Ranier": "Жан-Ноэль Ранье",
    "Leia Graja": "Лея Граже",
    "Gerard Petitcourt": "Жерар Петикур",
    "Francois de la Neree": "Франсуа де ла Нере",
    "Herve Graillou": "Эрве Грайу",
    "Jerome Praud": "Жером Про",
    "Geraldine Zemmour": "Жеральдина Земмур",
    "Veronique Peuchat": "Вероника Пёша",
    "Shohreh Prevert": "Шохре Превер",
    "Amelie Franconi": "Амели Франкони",
    "Leonie Bremieux": "Леони Бремьё",
    "Childeric de Prahan": "Шильдерик де Праан",
    "Agnes Bertrand": "Аньес Бертран",
    "Pierre-Henri de Prehaut & Shaine Patel-Marquand": "Пьер-Анри де Прео & Шаинэ Пател-Маркан",
    "Angelique de Fondaumiere": "Анжелика де Фондомьер",
    "Berenice Fabre": "Беренис Фабр",
    "Camille Riviere & Antoine Parmentier": "Камилла Ривьер & Антуан Парментье",
    "Lucie Bataz & Emilie Prince": "Люси Батаз & Эмили Пренс",
}

added = 0
updated = 0
skipped = 0

# Add all name mappings
for eng, rus in {**passenger_names, **first_names, **non_accented_variants}.items():
    if eng not in data:
        data[eng] = rus
        added += 1
        print(f"  ADD: \"{eng}\" -> \"{rus}\"")
    elif data[eng] != rus:
        # Only update if the current translation looks like a placeholder or first-name-only
        old = data[eng]
        if old == "TRANSLATE" or old == eng or len(old) < len(rus):
            data[eng] = rus
            updated += 1
            print(f"  UPD: \"{eng}\": \"{old}\" -> \"{rus}\"")
        else:
            skipped += 1
    else:
        skipped += 1

print(f"\nAdded: {added}, Updated: {updated}, Skipped (already correct): {skipped}")
print(f"Total entries: {len(data)}")

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done. JSON saved.")
