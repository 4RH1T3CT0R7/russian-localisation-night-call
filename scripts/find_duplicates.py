#!/usr/bin/env python3
"""
find_duplicates.py - Find remaining duplicate content lines within passages.
Checks both adjacent and near-adjacent duplicates using similarity matching.
"""

import os
import sys
from difflib import SequenceMatcher

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TEXTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "Russian_Texts")


def is_content_line(line):
    """Check if line is dialogue/narration content (not a command, choice, or routing)."""
    s = line.strip()
    if not s:
        return False
    if s.startswith('=== '):
        return False
    if s.startswith('$$ ') or s.endswith(' $$'):
        return False
    if s.startswith('*'):
        return False
    if s.startswith('{') or s.startswith(':'):
        return False
    if '?' in s and ';;' in s:  # conditional routing
        return False
    if s.startswith('//'):
        return False
    return True


def find_duplicates_in_file(filepath):
    """Find duplicate content lines within each passage."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    results = []
    current_passage = None
    passage_content = []  # (line_num, text)

    def check_passage():
        if not current_passage or len(passage_content) < 2:
            return
        # Check all pairs within window of 5 lines
        for i in range(len(passage_content)):
            for j in range(i + 1, min(i + 5, len(passage_content))):
                ln_i, text_i = passage_content[i]
                ln_j, text_j = passage_content[j]
                # Skip very short lines
                if len(text_i.strip()) < 15 or len(text_j.strip()) < 15:
                    continue
                sim = SequenceMatcher(None, text_i.strip(), text_j.strip()).ratio()
                if sim > 0.75:
                    results.append({
                        'passage': current_passage,
                        'line1': ln_i,
                        'text1': text_i.strip(),
                        'line2': ln_j,
                        'text2': text_j.strip(),
                        'similarity': sim,
                    })

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('=== '):
            check_passage()
            current_passage = stripped[4:]
            passage_content = []
        elif is_content_line(stripped):
            passage_content.append((idx + 1, line))

    check_passage()
    return results


def main():
    total_dupes = 0
    files_with_dupes = 0

    for filename in sorted(os.listdir(TEXTS_DIR)):
        if not filename.endswith('_rus.txt'):
            continue

        filepath = os.path.join(TEXTS_DIR, filename)
        dupes = find_duplicates_in_file(filepath)

        if dupes:
            files_with_dupes += 1
            print(f"\n{'='*70}")
            print(f"FILE: {filename}  ({len(dupes)} duplicates)")
            print(f"{'='*70}")
            for d in dupes:
                total_dupes += 1
                print(f"\n  Passage: {d['passage']}  (similarity: {d['similarity']:.0%})")
                print(f"  L{d['line1']}: {d['text1'][:120]}")
                print(f"  L{d['line2']}: {d['text2'][:120]}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: {total_dupes} duplicates in {files_with_dupes} files")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
