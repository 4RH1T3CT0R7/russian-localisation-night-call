#!/usr/bin/env python3
"""
Scan all _rus.txt files to find driver speech lines missing quotes.
Also finds SPEAKER lines with missing/malformed quotes.

Game engine rules:
- SPEAKER : "text"    -> colored character dialogue
- "text"              -> colored driver dialogue
- :emote: "text"      -> colored driver dialogue with emote
- Plain text          -> gray narration/inner thoughts
"""

import os
import re
import glob
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TEXTS_DIR = r"C:\Users\artem\NightCallRussian\data\Russian_Texts"

# ============================================================
# LINE TYPE DETECTION
# ============================================================

def is_structural(line):
    """Lines that are engine commands, choices, section headers, empty."""
    s = line.strip()
    if not s:
        return True
    if s.startswith("==="):
        return True
    if s.startswith("$$"):
        return True
    if s.startswith("*"):
        return True
    if s.startswith("%%"):
        return True
    if re.match(r'^[a-zA-Z_]+=', s):
        return True
    if re.match(r'^[a-zA-Z_]+\?.*->', s):
        return True
    if '->' in s and '"' not in s:
        return True
    return False

def is_proper_speaker_line(line):
    """Properly formatted: SPEAKER : "text" """
    s = line.strip()
    if re.match(r'^[А-ЯЁ][А-ЯЁ\s\-\.]+\s*:\s*"', s):
        return True
    return False

def is_broken_speaker_line(line):
    """SPEAKER : text  (missing opening quote) or SPEAKER: text" (missing opening quote)."""
    s = line.strip()
    # Pattern: RUSSIAN_UPPERCASE_NAME : text (no opening quote)
    # Must have at least 2 uppercase Cyrillic chars for the name
    m = re.match(r'^([А-ЯЁ][А-ЯЁ\s\-\.]+)\s*:\s*(.+)$', s)
    if m:
        name = m.group(1).strip()
        rest = m.group(2).strip()
        # It has a speaker-like name but the rest doesn't start with "
        if not rest.startswith('"'):
            # Make sure name looks like a real speaker (at least 2 consecutive uppercase)
            if re.match(r'^[А-ЯЁ]{2,}', name):
                return True
    return False

def is_already_quoted(line):
    """Driver dialogue that already has quotes."""
    s = line.strip()
    return s.startswith('"')

def is_emote_line(line):
    """Emote lines like :smile: or :silence:"""
    s = line.strip()
    return bool(re.match(r'^:[a-z]+:', s))

def is_parenthetical(line):
    """(Action descriptions)"""
    s = line.strip()
    return s.startswith('(') and s.endswith(')')

def is_plain_text(line):
    """A line that renders as plain text (potential narration or unquoted speech)."""
    s = line.strip()
    if not s:
        return False
    if is_structural(line):
        return False
    if is_proper_speaker_line(line):
        return False
    if is_broken_speaker_line(line):
        return False  # handled separately
    if is_already_quoted(line):
        return False
    if is_emote_line(line):
        return False
    if is_parenthetical(line):
        return False
    if re.match(r'^(clue_|doc_|poi_|guess_|UI\.|GC\.)', s):
        return False
    return True


# ============================================================
# NARRATION DETECTION
# ============================================================

def is_definitely_narration(text):
    """Is this line definitely narration/description (not spoken)?"""
    t = text.strip()

    # "You" descriptions
    if re.match(r'^Вы\s', t):
        return True
    if re.match(r'^Ваш', t):
        return True

    # He/She/They descriptions
    if re.match(r'^(Он|Она|Они)\s+(делает|делают|смотрит|смотрят|'
                r'говорит|начинает|начинают|продолжает|останавливается|поворачивается|'
                r'замолкает|вздыхает|улыбается|кивает|качает|трясётся|дрожит|'
                r'бормочет|шепчет|кричит|плачет|молчит|ждёт|ждет|'
                r'садится|встаёт|встает|выходит|входит|уходит|отходит|'
                r'протягивает|берёт|берет|достаёт|достает|опускает|поднимает|'
                r'закрывает|открывает|хватает|бросает|кладёт|кладет|'
                r'выглядит|кажется|пытается|старается|колеблется|'
                r'повышает|понижает|меняет|издаёт|издает|испускает|'
                r'на\s|не\s|ещё|еще|снова|уже|тоже|всё|все|так|'
                r'с\s|в\s|по-|при|за|у)', t):
        return True
    if re.match(r'^(Его|Её|Их)\s+(голос|лицо|глаза|руки|пальцы|взгляд|тон|'
                r'дыхание|фигура|силуэт|тело|фраза)', t):
        return True

    # Scene/atmosphere descriptions
    scene_starters = [
        'Наступает', 'Наступила', 'Проходит', 'Прошло', 'Пауза', 'Тишина', 'Молчание',
        'Начинается', 'Начался', 'Минута', 'Секунда', 'Мгновение',
        'Свет', 'Дверь', 'Машина', 'Такси', 'Улица', 'Город', 'Музыка', 'Телефон',
        'Светофор', 'Ночь', 'Вечер', 'Утро', 'Дорога',
        'Следующ', 'Пассажир', 'Клиент', 'Адвокат', 'Священник',
        'Когда ', 'Пока ', 'После ', 'Потом ', 'Затем ',
        'Внезапно', 'Неожиданно', 'Вдруг', 'Наконец',
        'Кажется,', 'Похоже,', 'Очевидно,', 'Видимо,', 'Должно быть',
        'Несколько', 'Может быть', 'Возможно',
        'Где-то', 'Откуда-то', 'Кто-то', 'Что-то', 'Ничего', 'Никто',
        'Звук', 'Голос', 'Взгляд', 'Лицо', 'Руки', 'Пальцы', 'Глаза', 'Дыхание',
        'Сегодня', 'Этим вечером', 'Этой ночью',
        'Адрес', 'Счётчик', 'Счетчик', 'Приборная',
        'Время ', 'Воздух', 'За спиной', 'За окном',
        'На заднем', 'На переднем', 'На тротуаре', 'На улице',
        'В салоне', 'В кабине', 'В машине', 'В такси', 'В зеркале', 'В воздухе',
        'Из телефона', 'Из машины', 'Из динамика',
        'Перед ', 'Позади ', 'Снаружи ', 'Мимо ', 'Сквозь ', 'Через ',
        'В свете', 'Со стороны', 'Рядом',
    ]
    for starter in scene_starters:
        if t.startswith(starter):
            return True

    # Data lines
    if re.match(r'^Рост\s*=', t):
        return True
    # Latin-starting lines (code/tags)
    if re.match(r'^[A-Za-z]', t):
        return True

    return False


# ============================================================
# CONTEXT HELPERS
# ============================================================

def get_nearby_content(lines, idx, direction, max_dist=6):
    """Get the nearest non-structural content line."""
    i = idx + direction
    while 0 <= i < len(lines) and abs(i - idx) <= max_dist:
        s = lines[i].strip()
        if s.startswith("==="):
            return None, -1
        if s and not s.startswith("$$"):
            return s, i
        i += direction
    return None, -1

def is_any_dialogue(text):
    """Check if a line is any form of dialogue (speaker or quoted)."""
    if not text:
        return False
    return is_proper_speaker_line(text) or is_already_quoted(text) or is_broken_speaker_line(text)


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_file(filepath):
    """Analyze a single file."""
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return results

    for idx, raw_line in enumerate(lines):
        text = raw_line.strip()
        if not text:
            continue

        # Find current section
        section = "???"
        for si in range(idx, -1, -1):
            sl = lines[si].strip()
            if sl.startswith("=== "):
                section = sl[4:]
                break

        # Skip data sections (not conversation files)
        if section == "???":
            # Check if this is before any === section - likely data/header
            continue

        # Get context
        prev_text, prev_idx = get_nearby_content(lines, idx, -1)
        next_text, next_idx = get_nearby_content(lines, idx, +1)

        # ================================================================
        # CATEGORY A: SPEAKER lines with missing/malformed quotes
        # These are lines like ЖАКИ: Ты знаешь... (missing opening ")
        # ================================================================
        if is_broken_speaker_line(raw_line):
            m = re.match(r'^([А-ЯЁ][А-ЯЁ\s\-\.]+)\s*:\s*(.+)$', text)
            if m:
                speaker = m.group(1).strip()
                content = m.group(2).strip()

                # Determine sub-type
                if content.endswith('"'):
                    issue = "Missing opening quote (has closing quote)"
                elif '"' in content:
                    issue = "Malformed quotes (quote in middle)"
                else:
                    issue = "Missing both quotes"

                results.append({
                    'category': 'A',
                    'line_num': idx + 1,
                    'text': text,
                    'confidence': 'HIGH',
                    'issue': issue,
                    'section': section,
                    'ctx_before': prev_text or "",
                    'ctx_after': next_text or "",
                })
            continue

        # ================================================================
        # CATEGORY B: Plain text driver speech missing quotes
        # ================================================================
        if not is_plain_text(raw_line):
            continue

        if is_definitely_narration(text):
            continue

        prev_is_dial = is_any_dialogue(prev_text) if prev_text else False
        next_is_dial = is_any_dialogue(next_text) if next_text else False
        next_is_speaker = is_proper_speaker_line(next_text) if next_text else False
        prev_is_speaker = is_proper_speaker_line(prev_text) if prev_text else False

        confidence = None
        reason = ""

        # RULE B1: Question ending with ? followed by SPEAKER response
        if text.endswith('?') and next_is_speaker:
            confidence = 'HIGH'
            reason = "Question followed by SPEAKER response"

        # RULE B2: Question ending with ? after SPEAKER line
        elif text.endswith('?') and prev_is_speaker and len(text) < 80:
            inner_starters = ['Что если', 'А что если', 'Как это возможно',
                              'Может ли', 'Зачем он', 'Зачем она', 'Почему он',
                              'Почему она', 'Что в нём', 'Что в ней',
                              'Интересно,', 'Неужели это', 'Как так',
                              'Что заставляет']
            if not any(text.startswith(s) for s in inner_starters):
                confidence = 'HIGH'
                reason = "Question after SPEAKER line"

        # RULE B3: Short line between dialogue lines (not descriptive)
        elif prev_is_dial and next_is_dial and len(text) < 50:
            desc_words = ['выглядит', 'кажется', 'замолкает', 'вздыхает',
                          'улыбается', 'кивает', 'смотрит', 'молчит',
                          'качает', 'делает паузу', 'говорит', 'переводит',
                          'останавливается', 'закрывает', 'открывает',
                          'дрожит', 'бормочет', 'шепчет', 'повышает',
                          'поворачивается', 'наклоняется', 'отводит',
                          'колеблется', 'пытается', 'старается',
                          'тишина', 'тихо', 'пауза', 'молчание']
            if not any(w in text.lower() for w in desc_words):
                confidence = 'MEDIUM'
                reason = "Short line between two dialogue lines"

        # RULE B4: Short question near dialogue context
        elif text.endswith('?') and len(text) < 40:
            in_conv = False
            for ci in range(max(0, idx-15), min(len(lines), idx+15)):
                if is_proper_speaker_line(lines[ci].strip()) or is_already_quoted(lines[ci].strip()):
                    in_conv = True
                    break
            if in_conv:
                if not any(text.startswith(s) for s in ['Что если', 'А что если', 'Может ли', 'Неужели']):
                    confidence = 'MEDIUM'
                    reason = "Short question in conversation context"

        # RULE B5: Short response after SPEAKER before more dialogue
        elif prev_is_speaker and len(text) < 30 and next_is_dial:
            desc_words = ['выглядит', 'кажется', 'молчит', 'смотрит', 'говорит',
                          'замолкает', 'вздыхает', 'кивает', 'качает']
            if not any(w in text.lower() for w in desc_words):
                confidence = 'MEDIUM'
                reason = "Short line after SPEAKER, before more dialogue"

        if confidence:
            results.append({
                'category': 'B',
                'line_num': idx + 1,
                'text': text,
                'confidence': confidence,
                'issue': reason,
                'section': section,
                'ctx_before': prev_text or "",
                'ctx_after': next_text or "",
            })

    return results


def line_type_label(text):
    if not text:
        return ""
    if is_proper_speaker_line(text):
        return "SPEAKER"
    if is_broken_speaker_line(text):
        return "BROKEN-SPEAKER"
    if is_already_quoted(text):
        return "QUOTED-DRIVER"
    if is_emote_line(text):
        return "EMOTE"
    return "plain"


def main():
    pattern = os.path.join(TEXTS_DIR, "*_rus.txt")
    files = sorted(glob.glob(pattern))

    print(f"Scanning {len(files)} _rus.txt files in {TEXTS_DIR}")
    print("=" * 100)

    all_results = []
    for filepath in files:
        filename = os.path.basename(filepath)
        results = analyze_file(filepath)
        for r in results:
            r['filename'] = filename
        all_results.extend(results)

    # ================================================================
    # SECTION 1: SPEAKER lines with broken/missing quotes (Category A)
    # ================================================================
    cat_a = [r for r in all_results if r['category'] == 'A']
    print(f"\n{'=' * 100}")
    print(f"  CATEGORY A: SPEAKER LINES WITH MISSING/MALFORMED QUOTES ({len(cat_a)} found)")
    print(f"  These are lines like  ЖАКИ: text  that should be  ЖАКИ: \"text\"")
    print(f"{'=' * 100}")

    cur_file = ""
    for r in cat_a:
        if r['filename'] != cur_file:
            cur_file = r['filename']
            print(f"\n  --- {cur_file} ---")

        print(f"\n  Line {r['line_num']}  [{r['section']}]  ({r['issue']})")
        if r['ctx_before']:
            print(f"    prev [{line_type_label(r['ctx_before'])}]: {r['ctx_before'][:95]}")
        print(f"    >>> {r['text']}")
        if r['ctx_after']:
            print(f"    next [{line_type_label(r['ctx_after'])}]: {r['ctx_after'][:95]}")

    # ================================================================
    # SECTION 2: Driver speech HIGH confidence (Category B-HIGH)
    # ================================================================
    cat_b_high = [r for r in all_results if r['category'] == 'B' and r['confidence'] == 'HIGH']
    print(f"\n\n{'=' * 100}")
    print(f"  CATEGORY B-HIGH: DRIVER SPEECH MISSING QUOTES ({len(cat_b_high)} found)")
    print(f"  Plain text lines that are clearly the driver speaking to the passenger")
    print(f"{'=' * 100}")

    cur_file = ""
    for r in cat_b_high:
        if r['filename'] != cur_file:
            cur_file = r['filename']
            print(f"\n  --- {cur_file} ---")

        print(f"\n  Line {r['line_num']}  [{r['section']}]")
        if r['ctx_before']:
            print(f"    prev [{line_type_label(r['ctx_before'])}]: {r['ctx_before'][:95]}")
        print(f"    >>> UNQUOTED: {r['text']}")
        if r['ctx_after']:
            print(f"    next [{line_type_label(r['ctx_after'])}]: {r['ctx_after'][:95]}")
        print(f"    Why: {r['issue']}")

    # ================================================================
    # SECTION 3: Driver speech MEDIUM confidence (Category B-MEDIUM)
    # ================================================================
    cat_b_med = [r for r in all_results if r['category'] == 'B' and r['confidence'] == 'MEDIUM']
    print(f"\n\n{'=' * 100}")
    print(f"  CATEGORY B-MEDIUM: POSSIBLY UNQUOTED DRIVER SPEECH ({len(cat_b_med)} found)")
    print(f"  Review needed - these might be speech or might be narration")
    print(f"{'=' * 100}")

    cur_file = ""
    for r in cat_b_med:
        if r['filename'] != cur_file:
            cur_file = r['filename']
            print(f"\n  --- {cur_file} ---")

        print(f"\n  Line {r['line_num']}  [{r['section']}]")
        if r['ctx_before']:
            print(f"    prev [{line_type_label(r['ctx_before'])}]: {r['ctx_before'][:95]}")
        print(f"    >>> POSSIBLY: {r['text']}")
        if r['ctx_after']:
            print(f"    next [{line_type_label(r['ctx_after'])}]: {r['ctx_after'][:95]}")
        print(f"    Why: {r['issue']}")

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n\n{'=' * 100}")
    print(f"  SUMMARY")
    print(f"{'=' * 100}")
    print(f"  Files scanned: {len(files)}")
    print(f"  Category A (broken SPEAKER quotes): {len(cat_a)}")
    print(f"  Category B-HIGH (unquoted driver speech): {len(cat_b_high)}")
    print(f"  Category B-MEDIUM (possible driver speech): {len(cat_b_med)}")
    print(f"  Total: {len(all_results)}")

    # Per-file breakdown
    print(f"\n  Per-file breakdown (files with findings only):")
    file_data = {}
    for r in all_results:
        fn = r['filename']
        if fn not in file_data:
            file_data[fn] = {'A': 0, 'B-HIGH': 0, 'B-MED': 0}
        if r['category'] == 'A':
            file_data[fn]['A'] += 1
        elif r['confidence'] == 'HIGH':
            file_data[fn]['B-HIGH'] += 1
        else:
            file_data[fn]['B-MED'] += 1

    for fn in sorted(file_data.keys()):
        d = file_data[fn]
        parts = []
        if d['A']:
            parts.append(f"{d['A']} broken-speaker")
        if d['B-HIGH']:
            parts.append(f"{d['B-HIGH']} driver-HIGH")
        if d['B-MED']:
            parts.append(f"{d['B-MED']} driver-MED")
        print(f"    {fn}: {', '.join(parts)}")


if __name__ == '__main__':
    main()
