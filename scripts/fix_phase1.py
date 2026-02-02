#!/usr/bin/env python3
"""
fix_phase1.py - Fix remaining missing lines, commands, and duplicates.

Based on find_missing_lines.py results:
- 2 missing commands (christophe customer-add-clue-outro)
- 5 missing text lines (ade, skaterz, lola x2, christophe)
- 2 duplicate lines (lola intro, fragonard customer-newspaper)
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
    """Insert new_line after the first occurrence of anchor line."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if anchor in line.rstrip('\n'):
            lines.insert(i + 1, new_line + '\n')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False


def remove_line(filepath, target):
    """Remove first occurrence of a line containing target text."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if target in line.rstrip('\n') and line.rstrip('\n').rstrip() == target:
            lines.pop(i)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False


def replace_passage_content(filepath, passage_name, old_lines, new_lines):
    """Replace specific content within a passage."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_text = '\n'.join(old_lines)
    new_text = '\n'.join(new_lines)

    if old_text in content:
        content = content.replace(old_text, new_text, 1)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    total = 0

    # ═══════════════════════════════════════════════════════════════
    # Fix 1: christophe customer-add-clue — add missing narration
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 012_christophe_rus.txt customer-add-clue...")
    path = os.path.join(TEXTS_DIR, "012_christophe_rus.txt")
    ok = insert_after(path,
        'Может пригодиться.',
        'Вы делаете мысленную заметку об услышанном… Кто знает? Возможно, это пригодится…')
    if ok:
        print("  Added missing narration line")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 2: christophe customer-add-clue-outro — add missing commands + text
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 012_christophe_rus.txt customer-add-clue-outro...")
    ok = replace_passage_content(path, 'customer-add-clue-outro',
        [
            'КРИСТОФ : "Забавно..."',
            'КРИСТОФ: "Знаете, я почему-то рад вас видеть."',
            'КРИСТОФ: "Я начинаю понимать, почему моим прихожанам так нравится исповедь."',
        ],
        [
            'КРИСТОФ : «Забавно…»',
            '$$ anim-link: WIN2DRI $$',
            'КРИСТОФ : «Знаете, я почему-то рад вас видеть.»',
            '$$ music-control: 20 $$',
            'КРИСТОФ : «Я начинаю понимать, почему моим прихожанам так нравится исповедь.»',
            'КРИСТОФ : «Это почти затягивает — это желание говорить о себе, быть выслушанным…»',
        ])
    if ok:
        print("  Added 2 commands + 1 dialogue line")
        total += 3
    else:
        print("  WARNING: passage content not found")

    # ═══════════════════════════════════════════════════════════════
    # Fix 3: fragonard customer-newspaper — remove duplicate + add missing
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 014_fragonard_rus.txt customer-newspaper...")
    frag_path = os.path.join(TEXTS_DIR, "014_fragonard_rus.txt")
    ok = replace_passage_content(frag_path, 'customer-newspaper',
        [
            'Вы хватаете его и убираете.',
            'Вы берёте её и убираете.',
            '$$ newspaper: 1 $$',
            'Может пригодиться.',
        ],
        [
            'Вы берёте её и убираете.',
            '$$ newspaper: 1 $$',
            'Может пригодиться.',
            'Вы уезжаете.',
        ])
    if ok:
        print("  Removed duplicate + added 'Вы уезжаете.'")
        total += 2
    else:
        print("  WARNING: passage content not found")

    # ═══════════════════════════════════════════════════════════════
    # Fix 4: ade ade-01-start — add missing ЭЙД dialogue
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 025_ade_rus.txt ade-01-start...")
    ade_path = os.path.join(TEXTS_DIR, "025_ade_rus.txt")
    ok = insert_after(ade_path,
        'Она улыбается и называет вам свой адрес. Вы заводите двигатель.',
        'ЭЙД : «Ничего страшного, просто хорошенько испугали… Недовольный бывший клиент.»')
    if ok:
        print("  Added missing ЭЙД dialogue line")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 5: skaterz ultra-01-drive — add missing УЛЬТРА РОЗОВЫЙ line
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 026_skaterz_rus.txt ultra-01-drive...")
    sk_path = os.path.join(TEXTS_DIR, "026_skaterz_rus.txt")
    ok = insert_after(sk_path,
        'УЛЬТРА РОЗОВЫЙ: "Мы родом из Бордо... а не из Гарагара IV..."',
        'УЛЬТРА РОЗОВЫЙ : «Но… но Красный прав. Ультра Жёлтая может быть в маленьком парке… Что нам… о чёрт, мой живот… куд…»')
    if ok:
        print("  Added missing УЛЬТРА РОЗОВЫЙ dialogue line")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 6: lola intro — remove duplicate + add missing narration
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 207_lola_rus.txt intro...")
    lola_path = os.path.join(TEXTS_DIR, "207_lola_rus.txt")

    # Remove the duplicate narration line
    ok1 = remove_line(lola_path,
        'Вы на мгновение смотрите на своего пассажира в зеркало заднего вида. На ней довольно необычный наряд.')
    if ok1:
        print("  Removed duplicate narration line")
        total += 1

    # Add missing narration after music-control: 0
    ok2 = insert_after(lola_path,
        '$$ music-control: 0 $$',
        'Она устраивается, поправляя пальто вокруг своего огромного живота.')
    if ok2:
        print("  Added missing narration about settling in")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Fix 7: lola outro-understand — add missing ЛОЛА dialogue
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 207_lola_rus.txt outro-understand...")
    ok = insert_after(lola_path,
        'ЛОЛА : "Простите за все это".',
        'ЛОЛА : «Мне не нужно думать об этом каждую чёртову минуту.»')
    if ok:
        print("  Added missing ЛОЛА dialogue line")
        total += 1

    # ═══════════════════════════════════════════════════════════════
    # Deploy
    # ═══════════════════════════════════════════════════════════════
    print(f"\nTotal fixes: {total}")
    print(f"Deploying to {GAME_DIR}...")
    os.makedirs(GAME_DIR, exist_ok=True)
    deployed = 0
    for filename in os.listdir(TEXTS_DIR):
        if filename.endswith('_rus.txt'):
            src = os.path.join(TEXTS_DIR, filename)
            dst = os.path.join(GAME_DIR, filename)
            shutil.copy2(src, dst)
            deployed += 1
    print(f"  Deployed {deployed} files")
    print("Done!")


if __name__ == '__main__':
    main()
