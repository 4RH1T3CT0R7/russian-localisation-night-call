#!/usr/bin/env python3
"""
fix_names.py - Normalize speaker names across all Russian localization files.
Fixes inconsistent transliterations of character names.
"""

import os
import sys
import re
import shutil

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
GAME_DIR = r"F:\SteamLibrary\steamapps\common\Night Call\Russian_Texts"

# ─── Name normalization table ─────────────────────────────────
# Maps wrong/variant speaker names to canonical forms.
# Format: (wrong_name, canonical_name, [optional list of specific files])
# If no files specified, applies globally.

NAME_FIXES = [
    # HIGH PRIORITY
    # Mathieu: МАТЬЕ → МАТЬЁ
    ("МАТЬЕ", "МАТЬЁ", ["067_mathieu_rus.txt"]),
    # Christophe: case variants → КРИСТОФ
    ("Кристоф", "КРИСТОФ", ["012_christophe_rus.txt", "990_ending_rus.txt"]),
    ("ХРИСТОФ", "КРИСТОФ", ["012_christophe_rus.txt"]),
    # Milo: МИЛО → МАЙЛО
    ("МИЛО", "МАЙЛО", ["203_milo_rus.txt", "203_milo_00a_rus.txt"]),
    # Alicia: АЛИСИЯ → АЛИЦИЯ
    ("АЛИСИЯ", "АЛИЦИЯ", ["015_alicia_rus.txt"]),
    # Vincent: ВЕНСАН → ВИНСЕНТ (96% of file uses ВИНСЕНТ)
    ("ВЕНСАН", "ВИНСЕНТ", ["008_vincent_rus.txt"]),
    # Ariane: АРИАН → АРИАНА
    ("АРИАН", "АРИАНА", ["011_ariane_rus.txt"]),

    # MEDIUM PRIORITY
    # Pierrette: truncated/case variants → ПЬЕРЕТТА
    ("ПЬЕРЕТТ", "ПЬЕРЕТТА", ["072_pierrette_rus.txt", "990_ending_rus.txt"]),
    ("Пьеретта", "ПЬЕРЕТТА", ["072_pierrette_rus.txt", "990_ending_rus.txt"]),
    ("ПЬЕРЕТ", "ПЬЕРЕТТА", ["072_pierrette_rus.txt"]),
    # Myrtille: МИРТИЛЛ/МИРТИЛЛЬ → МИРТИЛЬ
    ("МИРТИЛЛЬ", "МИРТИЛЬ", ["208_myrtille_rus.txt"]),
    ("МИРТИЛЛ", "МИРТИЛЬ", ["208_myrtille_rus.txt"]),
    # Gilda: ДЖИЛЬДА → ГИЛЬДА
    ("ДЖИЛЬДА", "ГИЛЬДА", ["096_gilda_rus.txt"]),

    # Apollonie: variant spellings → АПОЛЛОНЬЕ
    ("АПОЛЛОНИЯ", "АПОЛЛОНЬЕ", ["023_apollonie_rus.txt"]),
    ("АПОЛЛОНИ", "АПОЛЛОНЬЕ", ["023_apollonie_rus.txt"]),

    # Peter: ПЕТЕР → ПИТЕР (43 ПИТЕР vs 3 ПЕТЕР, standardize to majority)
    ("ПЕТЕР", "ПИТЕР", ["030_peter_rus.txt"]),

    # Skaterz: normalize to translated color names (dominant form)
    ("УЛЬТРА ПИНК", "УЛЬТРА РОЗОВЫЙ", ["026_skaterz_rus.txt"]),
    ("УЛЬТРА ГРИН", "УЛЬТРА ЗЕЛЕНЫЙ", ["026_skaterz_rus.txt"]),
    ("УЛЬТРА РЕД", "УЛЬТРА КРАСНЫЙ", ["026_skaterz_rus.txt"]),
    ("УЛЬТРАЗЕЛЕНЫЕ", "УЛЬТРА ЗЕЛЕНЫЙ", ["026_skaterz_rus.txt"]),
    ("УЛЬТРАЗЕЛЕНЫЙ", "УЛЬТРА ЗЕЛЕНЫЙ", ["026_skaterz_rus.txt"]),
]


def fix_speaker_in_line(line, wrong, canonical):
    """
    Replace speaker name in a dialogue line.
    Matches patterns like:
      WRONG : "text"
      WRONG: "text"
      WRONG : «text»
    Only replaces at the start of the line (speaker position).
    """
    # Special handling for АРИАН → АРИАНА: don't match АРИАНА itself
    if wrong == "АРИАН":
        # Only match АРИАН followed by : or space-: but NOT АРИАНА
        pattern = r'^АРИАН(\s*:)'
        if re.match(pattern, line):
            return re.sub(pattern, f'АРИАНА\\1', line, count=1)
        return line

    # Special handling for ПЬЕРЕТТ → ПЬЕРЕТТА: don't match ПЬЕРЕТТА itself
    if wrong == "ПЬЕРЕТТ":
        pattern = r'^ПЬЕРЕТТ(\s*:)'
        if re.match(pattern, line):
            return re.sub(pattern, f'ПЬЕРЕТТА\\1', line, count=1)
        return line

    # Special handling for ПЬЕРЕТ → ПЬЕРЕТТА: don't match ПЬЕРЕТТ/ПЬЕРЕТТА
    if wrong == "ПЬЕРЕТ":
        pattern = r'^ПЬЕРЕТ(\s*:)'
        if re.match(pattern, line) and not line.startswith("ПЬЕРЕТТ"):
            return re.sub(pattern, f'ПЬЕРЕТТА\\1', line, count=1)
        return line

    # Special handling for МИРТИЛЛ → МИРТИЛЬ: don't match МИРТИЛЛЬ
    if wrong == "МИРТИЛЛ":
        pattern = r'^МИРТИЛЛ(\s*:)'
        if re.match(pattern, line) and not line.startswith("МИРТИЛЛЬ"):
            return re.sub(pattern, f'МИРТИЛЬ\\1', line, count=1)
        return line

    # Special handling for АПОЛЛОНИ → АПОЛЛОНЬЕ: don't match АПОЛЛОНЬЕ/АПОЛЛОНИЯ
    if wrong == "АПОЛЛОНИ":
        pattern = r'^АПОЛЛОНИ(\s*:)'
        if re.match(pattern, line) and not line.startswith("АПОЛЛОНЬЕ") and not line.startswith("АПОЛЛОНИЯ"):
            return re.sub(pattern, f'АПОЛЛОНЬЕ\\1', line, count=1)
        return line

    # Special handling for УЛЬТРАЗЕЛЕНЫЕ/УЛЬТРАЗЕЛЕНЫЙ (no space)
    if wrong == "УЛЬТРАЗЕЛЕНЫЕ":
        pattern = r'^УЛЬТРАЗЕЛЕНЫЕ(\s*:)'
        if re.match(pattern, line):
            return re.sub(pattern, f'УЛЬТРА ЗЕЛЕНЫЙ\\1', line, count=1)
        return line
    if wrong == "УЛЬТРАЗЕЛЕНЫЙ":
        pattern = r'^УЛЬТРАЗЕЛЕНЫЙ(\s*:)'
        if re.match(pattern, line):
            return re.sub(pattern, f'УЛЬТРА ЗЕЛЕНЫЙ\\1', line, count=1)
        return line

    # General case: match wrong name at start of line followed by colon
    if line.startswith(wrong):
        rest = line[len(wrong):]
        if rest.startswith(' :') or rest.startswith(':'):
            return canonical + rest
    return line


def process_file(filepath, filename, fixes_for_file):
    """Process a single file with the given name fixes."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_fixed = 0
    new_lines = []

    for line_raw in lines:
        line = line_raw.rstrip('\n').rstrip('\r')
        original = line

        for wrong, canonical in fixes_for_file:
            line = fix_speaker_in_line(line, wrong, canonical)

        if line != original:
            total_fixed += 1
            new_lines.append(line + '\n')
        else:
            new_lines.append(line_raw)

    if total_fixed > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return total_fixed


def main():
    # Build per-file fix lists
    file_fixes = {}  # filename -> [(wrong, canonical), ...]

    for wrong, canonical, files in NAME_FIXES:
        if wrong == canonical:
            continue
        if files:
            for fn in files:
                if fn not in file_fixes:
                    file_fixes[fn] = []
                file_fixes[fn].append((wrong, canonical))
        else:
            # Apply to all files
            for fn in os.listdir(TEXTS_DIR):
                if fn.endswith('_rus.txt'):
                    if fn not in file_fixes:
                        file_fixes[fn] = []
                    file_fixes[fn].append((wrong, canonical))

    # Sort fixes by wrong name length (longest first) to avoid partial matches
    for fn in file_fixes:
        file_fixes[fn].sort(key=lambda x: -len(x[0]))

    print(f"Processing {len(file_fixes)} files with name fixes...")
    total = 0
    files_modified = 0

    for filename in sorted(file_fixes.keys()):
        filepath = os.path.join(TEXTS_DIR, filename)
        if not os.path.exists(filepath):
            continue

        n = process_file(filepath, filename, file_fixes[filename])
        if n > 0:
            print(f"  {filename}: {n} names fixed")
            total += n
            files_modified += 1

    print(f"\nTotal: {total} names fixed in {files_modified} files")

    # Deploy
    print(f"Deploying to {GAME_DIR}...")
    os.makedirs(GAME_DIR, exist_ok=True)
    deployed = 0
    for fn in os.listdir(TEXTS_DIR):
        if fn.endswith('_rus.txt'):
            shutil.copy2(os.path.join(TEXTS_DIR, fn), os.path.join(GAME_DIR, fn))
            deployed += 1
    print(f"  Deployed {deployed} files")
    print("Done!")


if __name__ == '__main__':
    main()
