#!/usr/bin/env python3
"""
Compare English and Russian choice lines per passage.
Finds untranslated or mismatched choices.
"""

import os
import re
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
ENG_DIR = os.path.join(BASE, "ExtractForTranslation", "Dialogues")
RUS_DIR = os.path.join(BASE, "Russian_Texts")


def parse_choices(filepath):
    """Parse a Prompter-format file, return dict: passage_title -> list of (text, link)."""
    passages = defaultdict(list)
    current_passage = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")
            stripped = line.strip()
            # Passage header
            m = re.match(r"^===\s+(.+)$", stripped)
            if m:
                current_passage = m.group(1).strip()
                continue
            # Choice line
            if stripped.startswith("*") and current_passage:
                # Extract link: -> target
                link_m = re.search(r"->\s*(\S+)", stripped)
                link = link_m.group(1) if link_m else ""
                # Extract text: everything between * and ->
                text_part = stripped[1:]  # remove leading *
                if link_m:
                    text_part = text_part[:link_m.start() - 1]
                text_part = text_part.strip()
                # Remove emotes like :silence:
                text_part = re.sub(r"^:\w+:\s*", "", text_part)
                # Remove surrounding quotes
                for q in ['"', '\u00ab', '\u00bb', '\u201c', '\u201d', "'", "\u2018", "\u2019"]:
                    text_part = text_part.strip(q)
                text_part = text_part.strip()
                passages[current_passage].append((text_part, link))
    return dict(passages)


def find_matching_files():
    """Find English-Russian file pairs by base name."""
    eng_files = {}
    for fn in os.listdir(ENG_DIR):
        if fn.endswith("_eng.txt"):
            base = fn.replace("_eng.txt", "")
            eng_files[base] = os.path.join(ENG_DIR, fn)

    rus_files = {}
    for fn in os.listdir(RUS_DIR):
        if fn.endswith("_rus.txt"):
            base = fn.replace("_rus.txt", "")
            rus_files[base] = os.path.join(RUS_DIR, fn)

    return eng_files, rus_files


def main():
    eng_files, rus_files = find_matching_files()

    # Files with English but no Russian
    eng_only = set(eng_files.keys()) - set(rus_files.keys())
    rus_only = set(rus_files.keys()) - set(eng_files.keys())
    both = set(eng_files.keys()) & set(rus_files.keys())

    if eng_only:
        print(f"\n=== English files WITHOUT Russian translation ({len(eng_only)}) ===")
        for b in sorted(eng_only):
            eng_choices = parse_choices(eng_files[b])
            total = sum(len(v) for v in eng_choices.values())
            print(f"  {b}: {total} choices in {len(eng_choices)} passages")

    if rus_only:
        print(f"\n=== Russian files WITHOUT English source ({len(rus_only)}) ===")
        for b in sorted(rus_only):
            rus_choices = parse_choices(rus_files[b])
            total = sum(len(v) for v in rus_choices.values())
            if total > 0:
                print(f"  {b}: {total} choices in {len(rus_choices)} passages")

    print(f"\n=== Comparing {len(both)} matched file pairs ===")
    total_eng_choices = 0
    total_rus_choices = 0
    total_missing = 0
    missing_details = []

    for base in sorted(both):
        eng_choices = parse_choices(eng_files[base])
        rus_choices = parse_choices(rus_files[base])

        for passage, eng_list in eng_choices.items():
            total_eng_choices += len(eng_list)
            rus_list = rus_choices.get(passage, [])
            total_rus_choices += len(rus_list)

            # Compare by link
            eng_links = defaultdict(list)
            for text, link in eng_list:
                eng_links[link].append(text)
            rus_links = defaultdict(list)
            for text, link in rus_list:
                rus_links[link].append(text)

            for link, eng_texts in eng_links.items():
                rus_texts = rus_links.get(link, [])
                if len(rus_texts) < len(eng_texts):
                    diff = len(eng_texts) - len(rus_texts)
                    total_missing += diff
                    for et in eng_texts[len(rus_texts):]:
                        missing_details.append((base, passage, link, et))

        # Russian passages not in English
        for passage, rus_list in rus_choices.items():
            if passage not in eng_choices:
                total_rus_choices += len(rus_list)

    print(f"  English choices in matched passages: {total_eng_choices}")
    print(f"  Russian choices in matched passages: {total_rus_choices}")
    print(f"  Missing Russian choices (by link): {total_missing}")

    if missing_details:
        print(f"\n=== Missing choices ({len(missing_details)}) ===")
        for base, passage, link, eng_text in missing_details:
            print(f"  [{base}] passage='{passage}' link='{link}' eng='{eng_text}'")


if __name__ == "__main__":
    main()
