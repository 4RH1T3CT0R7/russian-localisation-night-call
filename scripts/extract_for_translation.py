#!/usr/bin/env python3
"""
Extract missing English lines from the Night Call localization report
into a simple pipe-delimited text file for batch translation.

Reads:
    _dev/output/missing_lines.json

Writes:
    _dev/output/lines_to_translate.txt

Output format (one line per missing entry):
    FILE|PASSAGE|POSITION|CATEGORY|ENGLISH_TEXT

Lines with category MISSING_COMMAND are included as-is (they don't need
human translation -- they are engine directives like $$ anim: X $$).

Usage:
    python scripts/extract_for_translation.py
    python scripts/extract_for_translation.py --text-only
    python scripts/extract_for_translation.py --stats
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Ensure Windows console can emit UTF-8
# ---------------------------------------------------------------------------
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, "_dev", "output", "missing_lines.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "_dev", "output", "lines_to_translate.txt")


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class ExtractionLine:
    """One line extracted from the missing-lines report."""

    file: str
    passage: str
    position: int
    category: str
    english_text: str


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def load_missing_lines(input_path: str) -> list[ExtractionLine]:
    """Load missing_lines.json and flatten into a list of ExtractionLine."""
    with open(input_path, "r", encoding="utf-8-sig") as fh:
        data: list[dict] = json.load(fh)

    lines: list[ExtractionLine] = []
    for entry in data:
        file_name: str = entry["file"]
        passage: str = entry["passage"]
        for missing in entry["missing"]:
            lines.append(
                ExtractionLine(
                    file=file_name,
                    passage=passage,
                    position=missing["position"],
                    category=missing["category"],
                    english_text=missing["english_text"],
                )
            )
    return lines


def write_extraction_file(
    lines: list[ExtractionLine],
    output_path: str,
    *,
    text_only: bool = False,
) -> int:
    """Write the pipe-delimited extraction file.

    Args:
        lines: All extracted lines.
        output_path: Destination file path.
        text_only: If True, skip MISSING_COMMAND entries (they can be
            inserted verbatim and do not need translation).

    Returns:
        Number of lines written.
    """
    written = 0
    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        # Header comment so the translator knows the format
        fh.write(
            "## FORMAT: FILE|PASSAGE|POSITION|CATEGORY|TEXT\n"
            "## Replace the TEXT portion (after the 4th pipe) with Russian.\n"
            "## Do NOT modify FILE, PASSAGE, POSITION, or CATEGORY columns.\n"
            "## Lines starting with ## are comments and will be ignored.\n"
            "## MISSING_COMMAND lines should be kept verbatim (no translation).\n"
            "\n"
        )
        for line in lines:
            if text_only and line.category != "MISSING_TEXT":
                continue
            # Escape any pipe characters inside the English text itself
            # (extremely unlikely in this dataset but defensive)
            safe_text = line.english_text.replace("\n", " ").strip()
            fh.write(
                f"{line.file}|{line.passage}|{line.position}"
                f"|{line.category}|{safe_text}\n"
            )
            written += 1
    return written


def print_stats(lines: list[ExtractionLine]) -> None:
    """Print summary statistics about the extraction."""
    categories: dict[str, int] = {}
    files: set[str] = set()
    passages: set[str] = set()

    for line in lines:
        categories[line.category] = categories.get(line.category, 0) + 1
        files.add(line.file)
        passages.add(f"{line.file}::{line.passage}")

    total = len(lines)
    print(f"Total lines to translate: {total}")
    print(f"  Files affected:         {len(files)}")
    print(f"  Passages affected:      {len(passages)}")
    print()
    for cat in sorted(categories):
        print(f"  {cat:20s}: {categories[cat]:>5}")
    print()

    # Show breakdown: how many lines need actual human translation
    text_count = categories.get("MISSING_TEXT", 0)
    cmd_count = categories.get("MISSING_COMMAND", 0)
    logic_count = categories.get("MISSING_LOGIC", 0)
    print(f"Lines needing human translation (MISSING_TEXT):  {text_count}")
    print(f"Lines insertable verbatim (MISSING_COMMAND):     {cmd_count}")
    if logic_count:
        print(f"Lines insertable verbatim (MISSING_LOGIC):      {logic_count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract missing lines for batch translation."
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Only extract MISSING_TEXT lines (skip commands).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics and exit without writing a file.",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help=f"Output file path (default: {OUTPUT_PATH}).",
    )
    args = parser.parse_args()

    # Load data
    if not os.path.isfile(INPUT_PATH):
        print(f"ERROR: Input file not found: {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    lines = load_missing_lines(INPUT_PATH)

    if args.stats:
        print_stats(lines)
        sys.exit(0)

    # Write extraction file
    written = write_extraction_file(
        lines,
        args.output,
        text_only=args.text_only,
    )

    print(f"Extracted {written} lines to: {args.output}")
    print()
    print_stats(lines)
    print()
    print("Next steps:")
    print(f"  1. Open {args.output}")
    print("  2. For each line, replace the English text (after the 4th pipe)")
    print("     with the Russian translation.")
    print("  3. MISSING_COMMAND lines can be left as-is (no translation needed).")
    print("  4. Run: python scripts/apply_translations.py --dry-run")
    print("  5. If dry-run looks correct: python scripts/apply_translations.py")


if __name__ == "__main__":
    main()
