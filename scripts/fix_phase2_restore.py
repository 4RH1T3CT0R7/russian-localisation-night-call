#!/usr/bin/env python3
"""
fix_phase2_restore.py - Restore lines incorrectly removed by dedup.
Fixes 3 passages where the dedup removed intentional content sequences.
"""

import os
import sys
import shutil

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
GAME_DIR = r"F:\SteamLibrary\steamapps\common\Night Call\Russian_Texts"


def insert_after(filepath, anchor, new_line):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if anchor in line.rstrip('\n'):
            lines.insert(i + 1, new_line + '\n')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False


def insert_before(filepath, anchor, new_line):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if anchor in line.rstrip('\n'):
            lines.insert(i, new_line + '\n')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False


def remove_duplicate_line(filepath, target):
    """Remove exact duplicate line from file (keeps first occurrence)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    found_first = False
    result = []
    removed = False
    for line in lines:
        if target in line.strip() and not removed:
            if found_first:
                removed = True
                continue
            found_first = True
        result.append(line)
    if removed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(result)
    return removed


def main():
    total = 0

    # ═══════════════════════════════════════════════════════════════
    # Fix 1: fragonard frag-05-story4 — restore counting sequence
    # English: 4,5,6,7,8,9 → Russian was 4,5,7,9 → need to add 6 and 8
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 014_fragonard_rus.txt frag-05-story4...")
    frag = os.path.join(TEXTS_DIR, "014_fragonard_rus.txt")

    ok = insert_after(frag,
        'ФРАГОНАРД: "Пять раз. "',
        'ФРАГОНАРД : «Шесть раз.»')
    if ok:
        print("  Restored 'Шесть раз.' in counting sequence")
        total += 1

    ok = insert_after(frag,
        'ФРАГОНАРД: "Семь раз. "',
        'ФРАГОНАРД : «Восемь раз.»')
    if ok:
        print("  Restored 'Восемь раз.' in counting sequence")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 2: annabelle annabelle-01-gasstation3 — add opening + remove dup
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 057_annabelle_rus.txt annabelle-01-gasstation3...")
    ann = os.path.join(TEXTS_DIR, "057_annabelle_rus.txt")

    # Add missing opening line
    ok = insert_before(ann,
        'Она бросает на вас последний взгляд, а затем закрывает глаза.',
        'Ветер холодный. Она дрожит.')
    if ok:
        print("  Added opening narration line")
        total += 1

    # Remove the remaining duplicate "Это место действует успокаивающе..."
    ok = remove_duplicate_line(ann,
        'Это место действует успокаивающе и на вас.')
    if ok:
        print("  Removed duplicate 'Это место...' line")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 3: emilia emilia-01-cat-driverkills02-back — restore sequence
    # English: walk back, fingers, lips, eyes → Russian was fingers, eyes
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 074_emilia_rus.txt emilia-01-cat-driverkills02-back...")
    emi = os.path.join(TEXTS_DIR, "074_emilia_rus.txt")

    # Add opening "walk back" line
    ok = insert_before(emi,
        'Ваши пальцы жаждут сигареты.',
        'Вы возвращаетесь к такси.')
    if ok:
        print("  Added opening 'walk back' line")
        total += 1

    # Add "lips" between "fingers" and "eyes"
    ok = insert_after(emi,
        'Ваши пальцы жаждут сигареты.',
        'Ваши губы жаждут сигареты.')
    if ok:
        print("  Restored 'губы' in craving sequence")
        total += 1

    # Deploy
    print(f"\nTotal: {total} fixes")
    print(f"Deploying to {GAME_DIR}...")
    os.makedirs(GAME_DIR, exist_ok=True)
    for filename in os.listdir(TEXTS_DIR):
        if filename.endswith('_rus.txt'):
            shutil.copy2(os.path.join(TEXTS_DIR, filename),
                        os.path.join(GAME_DIR, filename))
    print("Done!")


if __name__ == '__main__':
    main()
