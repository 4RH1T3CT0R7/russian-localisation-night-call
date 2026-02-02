#!/usr/bin/env python3
"""
fix_phase2_dedup.py - Remove remaining adjacent duplicate lines.

Pattern: old translation (ASCII quotes, ...) followed by polished version (guillemets, …).
Only removes TRULY adjacent duplicates with >80% similarity in content lines.
Keeps the better-formatted version (guillemets preferred).
"""

import os
import sys
import re
import shutil
from difflib import SequenceMatcher

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
GAME_DIR = r"F:\SteamLibrary\steamapps\common\Night Call\Russian_Texts"

SIMILARITY_THRESHOLD = 0.80
MIN_LENGTH = 15  # minimum characters to compare


def is_content_line(line):
    """Check if line is dialogue/narration content."""
    s = line.strip()
    if not s:
        return False
    if s.startswith('=== '):
        return False
    if s.startswith('$$') or s.endswith('$$'):
        return False
    if s.startswith('*'):
        return False
    if s.startswith('{') or s.startswith('}'):
        return False
    if s.startswith(':') and '(' in s:  # echo line :silence: (text)
        return False
    if '?' in s and ';;' in s:  # conditional routing
        return False
    if s.startswith('->'):  # routing line
        return False
    if s.startswith('//'):
        return False
    if re.match(r'^[\w\-]+=', s):  # variable assignment
        return False
    if re.match(r'^[\w\.\-]+=\d', s):  # counter
        return False
    return True


def get_speaker(line):
    """Extract speaker name from dialogue line, or None for narration."""
    m = re.match(r'^([А-ЯЁA-Z\s]+?)\s*:\s*[«"\']', line.strip())
    return m.group(1).strip() if m else None


def has_guillemets(line):
    """Check if line uses guillemets (« ») — indicates polished version."""
    return '«' in line or '»' in line


def has_em_dash(line):
    """Check if line uses em-dash (—) — indicates polished version."""
    return '—' in line


def has_yo(line):
    """Check if line uses ё — indicates polished version."""
    return 'ё' in line or 'Ё' in line


def quality_score(line):
    """Higher score = better formatted line (keep this one)."""
    score = 0
    if has_guillemets(line):
        score += 3
    if has_em_dash(line):
        score += 1
    if has_yo(line):
        score += 1
    if '…' in line:  # proper ellipsis
        score += 1
    return score


def normalize_for_comparison(text):
    """Normalize text for similarity comparison (strip quotes, punctuation variants)."""
    s = text.strip()
    # Remove speaker prefix
    m = re.match(r'^[А-ЯЁA-Z\s]+?\s*:\s*', s)
    if m:
        s = s[m.end():]
    # Normalize quotes
    s = s.replace('«', '"').replace('»', '"').replace('\u201c', '"').replace('\u201d', '"')
    s = s.replace('\u2018', "'").replace('\u2019', "'")
    # Normalize dashes
    s = s.replace('—', '-').replace('–', '-')
    # Normalize ellipsis
    s = s.replace('…', '...')
    # Normalize ё → е for comparison
    s = s.replace('ё', 'е').replace('Ё', 'Е')
    return s


def process_file(filepath):
    """Remove adjacent duplicate content lines, keeping the better version."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    removed = 0
    i = 0
    result = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this and the next line are both content and similar
        if (i + 1 < len(lines) and
            is_content_line(stripped) and
            len(stripped) >= MIN_LENGTH and
            is_content_line(lines[i + 1].strip()) and
            len(lines[i + 1].strip()) >= MIN_LENGTH):

            next_line = lines[i + 1]
            next_stripped = next_line.strip()

            # Check speakers match (both narration or same speaker)
            speaker1 = get_speaker(stripped)
            speaker2 = get_speaker(next_stripped)

            if speaker1 == speaker2:  # both None (narration) or same speaker
                norm1 = normalize_for_comparison(stripped)
                norm2 = normalize_for_comparison(next_stripped)

                sim = SequenceMatcher(None, norm1, norm2).ratio()

                if sim >= SIMILARITY_THRESHOLD:
                    # Keep the better-formatted version
                    q1 = quality_score(stripped)
                    q2 = quality_score(next_stripped)

                    if q1 >= q2:
                        result.append(line)
                        # Skip next line (duplicate)
                    else:
                        result.append(next_line)
                        # Skip next line (we're keeping it, skipping current)
                        # Actually: skip current (worse), keep next (better)
                        # But we already appended... let me fix the logic

                    # Redo: decide which to keep
                    result_line = line if q1 >= q2 else next_line
                    result[-1] = result_line  # replace last append

                    removed += 1
                    i += 2
                    continue

        result.append(line)
        i += 1

    if removed > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(result)

    return removed


def main():
    total_removed = 0
    files_modified = 0

    for filename in sorted(os.listdir(TEXTS_DIR)):
        if not filename.endswith('_rus.txt'):
            continue

        filepath = os.path.join(TEXTS_DIR, filename)
        removed = process_file(filepath)

        if removed > 0:
            files_modified += 1
            print(f"  {filename}: {removed} duplicates removed")
            total_removed += removed

    print(f"\nTotal: {total_removed} duplicates removed from {files_modified} files")

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
