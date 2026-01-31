#!/usr/bin/env python3
"""
Validation script for Night Call Russian localization text files.
Checks for common formatting errors in _rus.txt passage files.

Run: python scripts/validate_texts.py [--strict]

Exit codes:
  0 = all checks pass
  1 = errors found (blocks CI)
"""
import os
import sys
import re
import glob

TEXTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Russian_Texts")

# Valid English emote tags used in choice lines
VALID_EMOTES = {
    "anger", "angry", "irony", "love", "money", "negative", "positive",
    "puzzled", "radio", "sad", "silence", "smile", "smoking", "taxi", "violence",
}

errors = []
warnings = []

STRICT = "--strict" in sys.argv


def error(filepath, lineno, msg):
    rel = os.path.basename(filepath)
    errors.append("  ERROR  {}:{}: {}".format(rel, lineno, msg))


def warn(filepath, lineno, msg):
    rel = os.path.basename(filepath)
    warnings.append("  WARN   {}:{}: {}".format(rel, lineno, msg))


def check_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        error(filepath, 0, "File is not valid UTF-8")
        return

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n").rstrip("\r")

        # --- ERROR: Null bytes (file corruption) ---
        if "\x00" in line:
            error(filepath, i, "Line contains null bytes (file corruption)")

        # --- ERROR: Em-dash in choice lines ---
        if re.match(r"^\*\s*[\u2014\u2013]", line):
            error(filepath, i, "Em-dash in choice (use *\"text\" format): {}".format(line[:80]))

        # --- ERROR: Translated emote tags ---
        m = re.match(r"^\*:([^:]+):", line)
        if m:
            tag = m.group(1)
            if re.search(r"[\u0400-\u04FF]", tag):
                error(filepath, i, "Translated emote :{}: (must be English: :silence:, :smile: etc.)".format(tag))
            elif tag.lower() not in VALID_EMOTES and STRICT:
                warn(filepath, i, "Unknown emote tag :{}:".format(tag))

        # --- ERROR: Cyrillic in passage headers ---
        if line.startswith("=== "):
            passage_name = line[4:].strip()
            if re.search(r"[\u0400-\u04FF]", passage_name):
                error(filepath, i, "Cyrillic in passage header: {}".format(line[:80]))

        # --- WARN: Speaker line without quotes (only in strict mode) ---
        if STRICT:
            speaker_match = re.match(
                r'^([\u0410-\u042F\u0401][\u0410-\u042F\u0401\- ]{1,25})\s*:\s+(.+)$', line
            )
            if speaker_match:
                text_after = speaker_match.group(2).strip()
                if text_after and not text_after.startswith('"') \
                   and not text_after.startswith('\u00ab') \
                   and not text_after.startswith('\u201c') \
                   and not text_after.startswith("'") \
                   and not text_after.startswith('$$'):
                    name = speaker_match.group(1)
                    warn(filepath, i, "Speaker without quotes ({}): {}".format(name, line[:80]))


def main():
    if not os.path.isdir(TEXTS_DIR):
        print("Texts directory not found: {}".format(TEXTS_DIR))
        sys.exit(1)

    txt_files = sorted(glob.glob(os.path.join(TEXTS_DIR, "*_rus.txt")))
    if not txt_files:
        print("No _rus.txt files found")
        sys.exit(1)

    print("Validating {} text files...{}".format(
        len(txt_files), " (strict mode)" if STRICT else ""))

    for f in txt_files:
        check_file(f)

    if errors:
        print("\n{} ERROR(S):".format(len(errors)))
        for e in errors:
            print(e)

    if warnings:
        print("\n{} WARNING(S):".format(len(warnings)))
        for w in warnings:
            print(w)

    if not errors and not warnings:
        print("All checks passed.")

    if errors:
        print("\nFAILED: {} error(s) found.".format(len(errors)))
        sys.exit(1)
    else:
        print("\nPASSED.{}".format(
            " ({} warnings)".format(len(warnings)) if warnings else ""))
        sys.exit(0)


if __name__ == "__main__":
    main()
