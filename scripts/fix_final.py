#!/usr/bin/env python3
"""
fix_final.py - Fix remaining wrong choice texts and missing choices.

1. Fix denis wrong choices (061_denis_rus.txt)
2. Fix mathieu wrong choices (067_mathieu_rus.txt)
3. Fix carolina missing choices (028_carolinaj_rus.txt)
4. Re-deploy
"""

import os
import sys
import shutil

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
GAME_DIR = r"F:\SteamLibrary\steamapps\common\Night Call\Russian_Texts"


def fix_choices(filepath, fixes):
    """Replace specific lines in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    count = 0
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new, 1)
            count += 1
        else:
            print(f"  WARNING: not found: {old[:70]}...")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return count


def fix_carolina(filepath):
    """Fix carolina customer-add-clue-outro: add missing content and choices."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the customer-add-clue-outro passage
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip() == '=== customer-add-clue-outro':
            start = i
        elif start is not None and line.strip().startswith('=== ') and i > start:
            end = i
            break

    if start is None:
        print("  WARNING: customer-add-clue-outro not found")
        return False

    if end is None:
        end = len(lines)

    # Rewrite the passage with correct content and choices
    new_passage = [
        '=== customer-add-clue-outro\n',
        '\n',
        'КАРОЛИНА : «Сегодня на улице довольно холодно, не так ли?»\n',
        'Вы киваете. Есть пассажиры, как эта пожилая женщина, которая сразу располагает к себе.\n',
        '$$ anim-link: SAD_2_BASIC $$\n',
        'КАРОЛИНА : «Я почти чувствую, как холодный воздух проникает в уголки моего рта…»\n',
        'КАРОЛИНА : «Это забавное чувство, но чашка горячего чая может быстро его развеять.»\n',
        'Она тепло улыбается вам.\n',
        'КАРОЛИНА : «Или чашку горячего шоколада, конечно.»\n',
        'КАРОЛИНА : «В такие ночи я больше не могу выходить одна…»\n',
        'КАРОЛИНА : «И всё же мне приходится…»\n',
        '$$ anim-link: BASIC_2_SAD $$\n',
        'Она бросает на вас взгляд.\n',
        '$$ music-control: 20 $$\n',
        '*«Почему вам приходится выходить из дома?» -> carolina-start-out-intro\n',
        '*«Я знаю, каково это…» -> carolina-start-taxi\n',
        '\n',
        '\n',
    ]

    lines[start:end] = new_passage

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return True


def main():
    total = 0

    # ═══════════════════════════════════════════════════════════════
    # Fix 1: Denis wrong choices (061_denis_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 061_denis_rus.txt...")
    denis_path = os.path.join(TEXTS_DIR, "061_denis_rus.txt")
    n = fix_choices(denis_path, [
        # Choice 2: narration → correct player choice
        (
            '*Он не хочет заканчивать фразу. -> denis-01-hell4-plan',
            '*«Каков ваш план?» -> denis-01-hell4-plan',
        ),
        # Choice 3: Denis's dialogue → correct player choice
        (
            '*"Посмейся за мой счет... Вот на что я годен, верно?" -> denis-01-hell4-plan2',
            '*«Это ужасно.» -> denis-01-hell4-plan2',
        ),
        # Choice 4: narration → correct player choice
        (
            '*Его глаза встречаются с вашими, голос дрожит... Он тяжело вздыхает... затем пожимает плечами. -> denis-01-ourtimes',
            '*«Такие уж сейчас времена.» -> denis-01-ourtimes',
        ),
    ])
    print(f"  Fixed {n} choices")
    total += n

    # ═══════════════════════════════════════════════════════════════
    # Fix 2: Mathieu wrong choices (067_mathieu_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 067_mathieu_rus.txt...")
    mathieu_path = os.path.join(TEXTS_DIR, "067_mathieu_rus.txt")
    n = fix_choices(mathieu_path, [
        # Choice 1: wrong character dialogue → correct player choice
        (
            '*МИРТИЙ : "Ну, здравствуйте! Я не была уверена, что вы получили моё сообщение". -> mathieu-01-contact-thatsall',
            '*«И это всё?» -> mathieu-01-contact-thatsall',
        ),
        # Choice 2: narration → correct player choice
        (
            '*Его шаги гулко разносятся по тихой улице, и дверь его дома захлопывается. -> mathieu-01-contact-who',
            '*«Кто первый пошёл на контакт?» -> mathieu-01-contact-who',
        ),
    ])
    print(f"  Fixed {n} choices")
    total += n

    # ═══════════════════════════════════════════════════════════════
    # Fix 3: Carolina missing choices (028_carolinaj_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 028_carolinaj_rus.txt...")
    carolina_path = os.path.join(TEXTS_DIR, "028_carolinaj_rus.txt")
    ok = fix_carolina(carolina_path)
    if ok:
        print("  Passage rewritten with choices")
        total += 1
    else:
        print("  FAILED")

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
