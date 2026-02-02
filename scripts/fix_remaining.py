#!/usr/bin/env python3
"""
fix_remaining.py - Fix remaining choice errors and broken intro passages.

1. Fix wrong choice texts in jim (221) and ada (200) files
2. Rewrite broken intro passages in chantal (205) and roksana (214) files
3. Re-deploy all files to game directory
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
    """Replace specific choice lines in a file. fixes: list of (old_text, new_text)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    count = 0
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            count += 1
        else:
            print(f"  WARNING: Could not find: {old[:60]}...")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return count


def rewrite_passage(filepath, passage_name, new_content_lines):
    """Replace an entire passage (from === header to next === header) with new content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the passage
    start_idx = None
    end_idx = None
    header = f"=== {passage_name}\n"

    for i, line in enumerate(lines):
        if line.strip() == f"=== {passage_name}":
            start_idx = i
        elif start_idx is not None and line.strip().startswith("=== ") and i > start_idx:
            end_idx = i
            break

    if start_idx is None:
        print(f"  WARNING: Passage '{passage_name}' not found in {filepath}")
        return False

    if end_idx is None:
        end_idx = len(lines)

    # Build new passage block
    new_block = [header]
    for cl in new_content_lines:
        new_block.append(cl + '\n')
    new_block.append('\n')
    new_block.append('\n')

    lines[start_idx:end_idx] = new_block

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return True


def main():
    total = 0

    # ═══════════════════════════════════════════════════════════════
    # Fix 1: Ada wrong choice (200_ada_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 200_ada_rus.txt...")
    ada_path = os.path.join(TEXTS_DIR, "200_ada_rus.txt")
    n = fix_choices(ada_path, [
        (
            '*Мимо проносится автомобиль. Ваша пассажирка следит за ним глазами. -> ada-01-reveal-help',
            '*«Разве вы не должны помогать людям?» -> ada-01-reveal-help',
        ),
    ])
    print(f"  Fixed {n} choices")
    total += n

    # ═══════════════════════════════════════════════════════════════
    # Fix 2: Jim wrong choices (221_jim_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 221_jim_rus.txt...")
    jim_path = os.path.join(TEXTS_DIR, "221_jim_rus.txt")
    n = fix_choices(jim_path, [
        # jim-start: JIM's dialogue as choice → correct player choice
        (
            '*"Кладбище Пер-Лашез, пожалуйста. Северный вход в 20-м округе". -> jim-start-what',
            '*«Вы идёте на кладбище?» -> jim-start-what',
        ),
        # jim-start: narration as choice → correct player choice
        (
            '*Когда он говорит, вы почти слышите глубокие акценты второго голоса... -> jim-drive',
            '*«Конечно.» -> jim-drive',
        ),
        # jim-drive-hungry: narration as choice
        (
            '*Похоже, они вращаются в одних и тех же кругах. Странный мир... -> jim-drive-hungry-nope',
            '*«Нет… Я только с перерыва.» -> jim-drive-hungry-nope',
        ),
        # jim-drive-hungry-silence: narration as choice
        (
            '*Внезапно он не может больше сдерживаться. Он издает рык. -> jim-hungry-alone',
            '*«Может, подвезти вас куда-нибудь?» -> jim-hungry-alone',
        ),
        # jim-camille & jim-heat-taxi02: narration as choice (appears twice, replace both)
        (
            '*Вы отрицательно качаете головой. Воспоминания об этом пассажире до сих пор раздражают вас. -> jim-heat-taxi-just',
            '*«Я всего лишь таксист.» -> jim-heat-taxi-just',
        ),
        # jim-heat-club-want: JIM's dialogue as choice
        (
            '*"А... Чет Бейкер... Он был очень хорошим человеком..." -> jim-hungry-pieddecochon',
            '*«Я знаю одно место…» -> jim-hungry-pieddecochon',
        ),
        # jim-heat-club-want: narration as choice
        (
            '*Его голос прерывается, как будто всплывает старое воспоминание... -> jim-drive-hungry-nope',
            '*«Понятия не имею.» -> jim-drive-hungry-nope',
        ),
    ])
    print(f"  Fixed {n} choices")
    total += n

    # ═══════════════════════════════════════════════════════════════
    # Fix 3: Chantal intro rewrite (205_chantal_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 205_chantal_rus.txt intro...")
    chantal_path = os.path.join(TEXTS_DIR, "205_chantal_rus.txt")
    ok = rewrite_passage(chantal_path, "intro", [
        "",
        "$$ anim: IDLE_TIRED $$",
        "$$ movie: lamparo_on, display_passenger $$",
        "$$ sfx: sfx_gameplay_car_openclose_from_ext $$",
        "$$ music-control: 0 $$",
        "$$ reveal: 205_00 $$",
        "Увидев следующую пассажирку, ваш первый инстинкт — приготовиться к драке.",
        "Это почти автоматическая реакция. Что-то в её осанке, невероятно широких плечах, огромных руках, открывающих дверь…",
        "Должно быть, эта женщина — чемпионка по тяжёлой атлетике или вроде того.",
        "$$ music-control: 20 $$",
        'ШАНТАЛЬ : «Добрый вечер, месье…»',
        "Низкий голос вас не особенно удивляет. Но в её взгляде на вас есть что-то невероятно мягкое.",
        "$$ anim: IDLE_WINDOW $$",
        "$$ anim: turning_head $$",
        "$$ anim: IDLE_DRIVER $$",
        'ШАНТАЛЬ : «Не могли бы вы… проехать по внешнему кольцу?»',
        "$$ music-control: 40 $$",
        '*«Серьёзно?» -> intro-seriously',
        '*:smile: «Конечно.» -> intro-sure',
        '*«В каком направлении?» -> intro-whichway',
        '*:taxi: (Завести такси.) -> intro-drive',
    ])
    if ok:
        print("  Intro passage rewritten successfully")
        total += 1
    else:
        print("  FAILED to rewrite intro")

    # ═══════════════════════════════════════════════════════════════
    # Fix 4: Roksana intro rewrite (214_roksana_rus.txt)
    # ═══════════════════════════════════════════════════════════════
    print("Fixing 214_roksana_rus.txt intro...")
    roksana_path = os.path.join(TEXTS_DIR, "214_roksana_rus.txt")
    ok = rewrite_passage(roksana_path, "intro", [
        "",
        "$$ anim: IDLE_DRIVER $$",
        "$$ reveal: 214_00 $$",
        "$$ sfx: sfx_gameplay_car_openclose_from_ext $$",
        "$$ movie: lamparo_on, display_passenger $$",
        "$$ music-control: 0 $$",
        "$$ fare: 0 $$",
        "Дверь захлопывается, и вас обдаёт порывом ледяного воздуха.",
        "Вы на мгновение задерживаете взгляд на своей пассажирке в зеркале заднего вида. На ней довольно необычный наряд.",
        "Вы улыбаетесь.",
        "«Добрый вечер.»",
        "Она кивает, после чего подробно осматривает такси с пустым выражением лица.",
        "$$ music-control: 20 $$",
        '*:silence: (Ничего не говорить.) -> intro-silence',
        '*«Всё в порядке?» -> intro-interrupt',
        '*«Куда едем?» -> intro-interrupt',
    ])
    if ok:
        print("  Intro passage rewritten successfully")
        total += 1
    else:
        print("  FAILED to rewrite intro")

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
