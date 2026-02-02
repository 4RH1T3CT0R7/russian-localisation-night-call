#!/usr/bin/env python3
"""
fix_phase3_quotes.py - Normalize quotation marks to ASCII double quotes.
The translator uses "..." consistently; guillemets «...» are a minority
introduced by fix scripts. Normalize to maintain consistency.
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


def normalize_quotes(filepath):
    """Replace « with " and » with " in dialogue lines only."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    # Replace guillemets with ASCII quotes
    content = content.replace('«', '"').replace('»', '"')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        changes = original.count('«') + original.count('»')
        return changes
    return 0


def main():
    total_changes = 0
    files_modified = 0

    for filename in sorted(os.listdir(TEXTS_DIR)):
        if not filename.endswith('_rus.txt'):
            continue

        filepath = os.path.join(TEXTS_DIR, filename)
        changes = normalize_quotes(filepath)

        if changes > 0:
            files_modified += 1
            total_changes += changes

    print(f"Normalized {total_changes} guillemets to ASCII quotes in {files_modified} files")

    # Deploy
    print(f"Deploying to {GAME_DIR}...")
    os.makedirs(GAME_DIR, exist_ok=True)
    deployed = 0
    for filename in os.listdir(TEXTS_DIR):
        if filename.endswith('_rus.txt'):
            shutil.copy2(os.path.join(TEXTS_DIR, filename),
                        os.path.join(GAME_DIR, filename))
            deployed += 1
    print(f"  Deployed {deployed} files")
    print("Done!")


if __name__ == '__main__':
    main()
