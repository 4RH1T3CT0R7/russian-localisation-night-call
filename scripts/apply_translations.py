#!/usr/bin/env python3
"""
Apply translated lines to Russian localization files for Night Call.

Reads a pipe-delimited translation file (produced by extract_for_translation.py
and then manually translated) and inserts each translated line at the correct
position inside the Russian text file.

Input format (lines_to_translate.txt after translation):
    FILE|PASSAGE|POSITION|CATEGORY|RUSSIAN_TEXT

The script:
  1. Groups insertions by file, then by passage.
  2. For each passage, locates the passage header (=== passage-name) in the
     Russian file and identifies the content lines that belong to it.
  3. Uses the English passage dump and the original missing_lines.json to
     determine exactly where each line should be inserted, by matching
     existing Russian lines against the English line list and finding gaps.
  4. Inserts the translated text at the correct position.

Usage:
    python scripts/apply_translations.py --dry-run
    python scripts/apply_translations.py
    python scripts/apply_translations.py --input path/to/translated.txt
    python scripts/apply_translations.py --dry-run --file 001_patricia

Safety:
    - Always run with --dry-run first to review planned changes.
    - Backup files are created automatically (*.bak) unless --no-backup.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Ensure Windows console can emit UTF-8
# ---------------------------------------------------------------------------
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
MISSING_JSON_PATH = os.path.join(BASE_DIR, "_dev", "output", "missing_lines.json")
DEFAULT_INPUT_PATH = os.path.join(
    BASE_DIR, "_dev", "output", "lines_to_translate.txt"
)
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class TranslationEntry:
    """One translated line to insert."""

    file: str
    passage: str
    position: int  # 0-based index in the English passage line list
    category: str  # MISSING_TEXT or MISSING_COMMAND
    translated_text: str


@dataclass
class MissingInfo:
    """Original context from missing_lines.json for one missing line."""

    category: str
    english_text: str
    position: int
    context_before: str
    context_after: str


@dataclass
class PassageMissing:
    """All missing info for one passage in one file."""

    file: str
    passage: str
    eng_total: int
    rus_total: int
    missing: list[MissingInfo] = field(default_factory=list)


@dataclass
class EnglishPassage:
    """English passage lines from the passage dump."""

    name: str
    lines: list[str] = field(default_factory=list)


@dataclass
class InsertionPlan:
    """A concrete plan: insert text at a specific line number in a file."""

    file_path: str
    file_name: str
    passage: str
    line_number: int  # 1-based line number in the file (insert BEFORE this)
    translated_text: str
    english_text: str
    position: int  # original English position for reference
    category: str


# ---------------------------------------------------------------------------
# Line classification (mirrors find_missing_lines.py)
# ---------------------------------------------------------------------------
def is_engine_command(text: str) -> bool:
    """Return True if the line is a $$ engine command $$."""
    s = text.strip()
    return s.startswith("$$") and s.endswith("$$")


def is_game_logic(text: str) -> bool:
    """Return True for game-variable or conditional routing lines."""
    s = text.strip()
    if re.match(r"^\{.*=.*\}$", s):
        return True
    if re.match(r"^[_a-zA-Z][\w.-]*\s*=\s*\d+$", s):
        return True
    if re.match(r"^[\w.-]+\s*[+-]=\s*\d+$", s):
        return True
    if "?" in s and ";;" in s and not s.startswith("*"):
        return True
    if s.startswith("??"):
        return True
    if re.match(r"^->\s", s):
        return True
    return False


def is_choice_line(text: str) -> bool:
    """Return True if the line is a choice line (*text -> target)."""
    return text.strip().startswith("*")


def normalize_for_match(text: str) -> str:
    """Normalize a line for fuzzy matching between English and Russian."""
    s = text.strip()
    if is_engine_command(s):
        return s.lower()
    if is_game_logic(s):
        return s
    # Strip speaker tag
    s = re.sub(r"^[A-Z\u0400-\u04FF][A-Z\u0400-\u04FF .'-]+\s*:\s*", "", s)
    # Remove quote marks
    for ch in ['"', "'", "\u00ab", "\u00bb", "\u201c", "\u201d", "\u201e"]:
        s = s.replace(ch, "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_translation_file(input_path: str) -> list[TranslationEntry]:
    """Parse the pipe-delimited translation file."""
    entries: list[TranslationEntry] = []
    with open(input_path, "r", encoding="utf-8-sig") as fh:
        for line_num, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n").rstrip("\r")
            # Skip comments and blank lines
            if not line or line.startswith("##"):
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                print(
                    f"WARNING: Skipping malformed line {line_num}: {line[:80]}",
                    file=sys.stderr,
                )
                continue
            file_name, passage, pos_str, category, text = parts
            try:
                position = int(pos_str)
            except ValueError:
                print(
                    f"WARNING: Invalid position on line {line_num}: {pos_str}",
                    file=sys.stderr,
                )
                continue
            entries.append(
                TranslationEntry(
                    file=file_name.strip(),
                    passage=passage.strip(),
                    position=position,
                    category=category.strip(),
                    translated_text=text.strip(),
                )
            )
    return entries


def load_missing_json(json_path: str) -> dict[str, dict[str, PassageMissing]]:
    """Load missing_lines.json into {file: {passage: PassageMissing}}."""
    with open(json_path, "r", encoding="utf-8-sig") as fh:
        data: list[dict] = json.load(fh)

    result: dict[str, dict[str, PassageMissing]] = {}
    for entry in data:
        file_name = entry["file"]
        passage = entry["passage"]
        pm = PassageMissing(
            file=file_name,
            passage=passage,
            eng_total=entry["eng_total"],
            rus_total=entry["rus_total"],
        )
        for m in entry["missing"]:
            pm.missing.append(
                MissingInfo(
                    category=m["category"],
                    english_text=m["english_text"],
                    position=m["position"],
                    context_before=m.get("context_before", ""),
                    context_after=m.get("context_after", ""),
                )
            )
        result.setdefault(file_name, {})[passage] = pm
    return result


def load_english_dump(dump_path: str) -> dict[str, EnglishPassage]:
    """Parse passage_dump.txt into {passage_name: EnglishPassage}.

    Note: passage names may repeat across OBJs. We keep the last one seen
    (they should be identical for passages that share the same name).
    """
    passages: dict[str, EnglishPassage] = {}
    current: Optional[EnglishPassage] = None

    with open(dump_path, "r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")
            if line.startswith("P "):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    current = EnglishPassage(name=name)
                    passages[name] = current
            elif line.startswith("L ") and current is not None:
                current.lines.append(line[2:])
            elif line.startswith("OBJ ") or line.startswith("C "):
                # Don't reset current on choice lines, but OBJ resets context
                if line.startswith("OBJ "):
                    current = None

    return passages


# ---------------------------------------------------------------------------
# Russian file parser (passage-aware, preserving raw lines)
# ---------------------------------------------------------------------------
@dataclass
class RusParsedPassage:
    """A passage as found in a Russian file, with precise line positions."""

    name: str
    header_line_num: int  # 1-based line number of "=== passage-name"
    # content_lines: list of (line_number, stripped_text) for non-blank,
    # non-choice content within this passage
    content_lines: list[tuple[int, str]] = field(default_factory=list)
    # First line number after the passage header where content could go
    first_content_line: int = 0
    # Line number of the next passage header (or end-of-file + 1)
    end_line_num: int = 0


def parse_russian_file_full(filepath: str) -> tuple[list[str], dict[str, RusParsedPassage]]:
    """Parse a Russian file, returning raw lines and passage map.

    Returns:
        (raw_lines, passages_dict)
        raw_lines is 0-indexed; passage line numbers are 1-based.
    """
    with open(filepath, "r", encoding="utf-8-sig") as fh:
        raw_lines = fh.readlines()

    passages: dict[str, RusParsedPassage] = {}
    ordered_passages: list[RusParsedPassage] = []

    for i, raw in enumerate(raw_lines):
        line = raw.rstrip("\n").rstrip("\r")
        line_num = i + 1  # 1-based

        if line.startswith("=== "):
            name = line[4:].strip()
            p = RusParsedPassage(name=name, header_line_num=line_num)
            passages[name] = p
            ordered_passages.append(p)

    # Set end boundaries and parse content
    for idx, p in enumerate(ordered_passages):
        if idx + 1 < len(ordered_passages):
            p.end_line_num = ordered_passages[idx + 1].header_line_num
        else:
            p.end_line_num = len(raw_lines) + 1

        # First content line is right after the header
        # (typically there's one blank line after "=== name")
        p.first_content_line = p.header_line_num + 1

        # Collect content lines (non-blank, non-choice) within the passage
        for li in range(p.header_line_num, p.end_line_num - 1):
            idx0 = li  # 0-based index into raw_lines
            if idx0 >= len(raw_lines):
                break
            text = raw_lines[idx0].rstrip("\n").rstrip("\r")
            stripped = text.strip()
            if not stripped:
                continue
            if stripped.startswith("=== "):
                break
            if stripped.startswith("%%") or stripped.startswith("//"):
                continue
            if stripped.startswith("VAR ") or stripped.startswith("+++"):
                continue
            if stripped.startswith("*"):
                # Choice line -- skip
                continue
            line_num = li + 1  # 1-based
            p.content_lines.append((line_num, stripped))

    return raw_lines, passages


# ---------------------------------------------------------------------------
# Alignment engine: determine where to insert each missing line
# ---------------------------------------------------------------------------
def compute_insertion_plans(
    entries_for_passage: list[TranslationEntry],
    rus_lines: list[str],
    rus_passage: RusParsedPassage,
    eng_passage: EnglishPassage,
    passage_missing: PassageMissing,
    file_path: str,
) -> list[InsertionPlan]:
    """Determine the exact line numbers for insertions in one passage.

    Strategy:
    We reconstruct the alignment between the English line list and the
    existing Russian content lines, then figure out where each missing
    English position maps to in the Russian file.

    The English passage has N lines (indices 0..N-1).  The Russian passage
    has M content lines (M < N).  The missing positions tell us which
    English indices have no Russian counterpart.

    We align English and Russian using the same greedy forward-matching
    algorithm as find_missing_lines.py.  This gives us a mapping:
        eng_index -> rus_content_index (or None if missing)

    For each missing position, we find the nearest MATCHED English line
    that comes AFTER it and insert before the Russian line that matches
    that English line.  If no matched line follows, we insert at the end
    of the passage (before the next passage header or choices).
    """
    eng_lines = eng_passage.lines
    rus_content = rus_passage.content_lines  # list of (line_num, text)

    if not eng_lines:
        return []

    # Build alignment: eng_index -> index in rus_content (or -1)
    eng_to_rus: list[int] = [-1] * len(eng_lines)
    eng_norm = [normalize_for_match(l) for l in eng_lines]
    rus_norm = [normalize_for_match(t) for _, t in rus_content]

    rus_ptr = 0
    for ei in range(len(eng_lines)):
        if rus_ptr >= len(rus_content):
            break
        # Direct normalized match
        if eng_norm[ei] == rus_norm[rus_ptr]:
            eng_to_rus[ei] = rus_ptr
            rus_ptr += 1
            continue
        # Both engine commands
        if is_engine_command(eng_lines[ei]) and is_engine_command(
            rus_content[rus_ptr][1]
        ):
            eng_to_rus[ei] = rus_ptr
            rus_ptr += 1
            continue
        # Both game logic
        if is_game_logic(eng_lines[ei]) and is_game_logic(
            rus_content[rus_ptr][1]
        ):
            eng_to_rus[ei] = rus_ptr
            rus_ptr += 1
            continue
        # Look-ahead in Russian
        found_ahead = False
        for look in range(1, min(4, len(rus_content) - rus_ptr)):
            if eng_norm[ei] == rus_norm[rus_ptr + look]:
                rus_ptr += look
                eng_to_rus[ei] = rus_ptr
                rus_ptr += 1
                found_ahead = True
                break
        if found_ahead:
            continue
        # Both are text -- assume match
        eng_is_text = not is_engine_command(eng_lines[ei]) and not is_game_logic(
            eng_lines[ei]
        )
        rus_is_text = not is_engine_command(
            rus_content[rus_ptr][1]
        ) and not is_game_logic(rus_content[rus_ptr][1])
        if eng_is_text and rus_is_text:
            eng_to_rus[ei] = rus_ptr
            rus_ptr += 1
            continue

    # Build position lookup for the translation entries
    entry_by_pos: dict[int, TranslationEntry] = {
        e.position: e for e in entries_for_passage
    }

    # Build the original missing info lookup
    missing_by_pos: dict[int, MissingInfo] = {
        m.position: m for m in passage_missing.missing
    }

    plans: list[InsertionPlan] = []

    # Sort missing positions so we process them in order
    missing_positions = sorted(entry_by_pos.keys())

    for pos in missing_positions:
        entry = entry_by_pos[pos]
        mi = missing_by_pos.get(pos)
        english_text = mi.english_text if mi else entry.translated_text

        # Find the insertion point:
        # Look for the first English index > pos that IS matched to a Russian line
        insert_before_line: Optional[int] = None
        for later_ei in range(pos + 1, len(eng_lines)):
            if eng_to_rus[later_ei] >= 0:
                # Insert before this matched Russian line
                rus_idx = eng_to_rus[later_ei]
                insert_before_line = rus_content[rus_idx][0]
                break

        if insert_before_line is None:
            # No matched English line follows this position.
            # Insert at the end of the passage content.
            # Find the right spot: after the last content line, but before
            # any choice lines or the next passage header.
            if rus_content:
                last_content_line_num = rus_content[-1][0]
                insert_before_line = last_content_line_num + 1
            else:
                # Passage has no content at all; insert right after header + blank
                insert_before_line = rus_passage.header_line_num + 2

        plans.append(
            InsertionPlan(
                file_path=file_path,
                file_name=entry.file,
                passage=entry.passage,
                line_number=insert_before_line,
                translated_text=entry.translated_text,
                english_text=english_text,
                position=pos,
                category=entry.category,
            )
        )

    return plans


# ---------------------------------------------------------------------------
# Insertion executor
# ---------------------------------------------------------------------------
def apply_insertions_to_file(
    file_path: str,
    plans: list[InsertionPlan],
    *,
    dry_run: bool = False,
    create_backup: bool = True,
) -> int:
    """Apply all insertion plans for a single file.

    Plans must be sorted by passage and position.  We process them in
    reverse line-number order so that earlier insertions don't shift the
    line numbers of later ones.

    Returns:
        Number of lines inserted.
    """
    with open(file_path, "r", encoding="utf-8-sig") as fh:
        lines = fh.readlines()

    # Sort plans by line_number descending so insertions don't shift indices
    sorted_plans = sorted(plans, key=lambda p: p.line_number, reverse=True)

    inserted = 0
    for plan in sorted_plans:
        # Convert 1-based line_number to 0-based index
        idx = plan.line_number - 1
        # Clamp to valid range
        idx = max(0, min(idx, len(lines)))

        new_line = plan.translated_text + "\n"

        if dry_run:
            # Show what would happen
            ctx_before = ""
            ctx_after = ""
            if idx > 0 and idx - 1 < len(lines):
                ctx_before = lines[idx - 1].rstrip("\n").rstrip("\r")
            if idx < len(lines):
                ctx_after = lines[idx].rstrip("\n").rstrip("\r")

            print(f"  INSERT at line {plan.line_number} in {plan.passage}:")
            print(f"    EN (pos {plan.position}): {plan.english_text[:90]}")
            print(f"    RU: {plan.translated_text[:90]}")
            if ctx_before:
                print(f"    after:  {ctx_before[:80]}")
            if ctx_after:
                print(f"    before: {ctx_after[:80]}")
            print()
        else:
            lines.insert(idx, new_line)
            inserted += 1

    if not dry_run and inserted > 0:
        if create_backup:
            backup_path = file_path + ".bak"
            if not os.path.exists(backup_path):
                shutil.copy2(file_path, backup_path)

        with open(file_path, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(lines)

    return inserted


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def run(
    input_path: str,
    *,
    dry_run: bool = False,
    create_backup: bool = True,
    file_filter: Optional[str] = None,
) -> dict[str, int]:
    """Execute the full translation application pipeline.

    Returns:
        Dict of {filename: lines_inserted}.
    """
    # Load all data sources
    print("Loading translation file...")
    entries = load_translation_file(input_path)
    if not entries:
        print("ERROR: No translation entries found.", file=sys.stderr)
        return {}

    print(f"  Loaded {len(entries)} translation entries.")

    print("Loading missing_lines.json for context...")
    missing_data = load_missing_json(MISSING_JSON_PATH)

    print("Loading English passage dump for alignment...")
    eng_passages = load_english_dump(DUMP_PATH)
    print(f"  Loaded {len(eng_passages)} English passages.")

    # Group entries by file
    by_file: dict[str, list[TranslationEntry]] = {}
    for entry in entries:
        by_file.setdefault(entry.file, []).append(entry)

    results: dict[str, int] = {}

    for file_name in sorted(by_file):
        # Apply file filter
        if file_filter and file_filter not in file_name:
            continue

        file_path = os.path.join(TEXTS_DIR, file_name)
        if not os.path.isfile(file_path):
            print(
                f"WARNING: Russian file not found: {file_path}",
                file=sys.stderr,
            )
            continue

        file_entries = by_file[file_name]
        file_missing = missing_data.get(file_name, {})

        if dry_run:
            print("=" * 70)
            print(f"FILE: {file_name}")
            print("=" * 70)
            print()

        # Parse the Russian file
        rus_lines, rus_passages = parse_russian_file_full(file_path)

        # Group this file's entries by passage
        by_passage: dict[str, list[TranslationEntry]] = {}
        for entry in file_entries:
            by_passage.setdefault(entry.passage, []).append(entry)

        all_plans: list[InsertionPlan] = []

        for passage_name in sorted(by_passage):
            passage_entries = by_passage[passage_name]

            # Get Russian passage
            if passage_name not in rus_passages:
                print(
                    f"WARNING: Passage '{passage_name}' not found in "
                    f"{file_name}. Skipping {len(passage_entries)} entries.",
                    file=sys.stderr,
                )
                continue

            rus_p = rus_passages[passage_name]

            # Get English passage
            if passage_name not in eng_passages:
                print(
                    f"WARNING: Passage '{passage_name}' not found in "
                    f"English dump. Skipping.",
                    file=sys.stderr,
                )
                continue

            eng_p = eng_passages[passage_name]

            # Get missing context info
            pm = file_missing.get(passage_name)
            if pm is None:
                # Build a minimal PassageMissing from the entries themselves
                pm = PassageMissing(
                    file=file_name,
                    passage=passage_name,
                    eng_total=len(eng_p.lines),
                    rus_total=len(rus_p.content_lines),
                )
                for entry in passage_entries:
                    pm.missing.append(
                        MissingInfo(
                            category=entry.category,
                            english_text=entry.translated_text,
                            position=entry.position,
                            context_before="",
                            context_after="",
                        )
                    )

            plans = compute_insertion_plans(
                passage_entries,
                rus_lines,
                rus_p,
                eng_p,
                pm,
                file_path,
            )
            all_plans.extend(plans)

        if all_plans:
            count = apply_insertions_to_file(
                file_path,
                all_plans,
                dry_run=dry_run,
                create_backup=create_backup,
            )
            results[file_name] = len(all_plans) if dry_run else count
        else:
            results[file_name] = 0

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply translated lines to Russian localization files.",
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help=f"Path to the translated pipe-delimited file "
        f"(default: {DEFAULT_INPUT_PATH}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned insertions without modifying files.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create .bak backup files.",
    )
    parser.add_argument(
        "--file",
        dest="file_filter",
        default=None,
        help="Only process files whose name contains PATTERN.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: Translation file not found: {args.input}", file=sys.stderr)
        print()
        print("Run extract_for_translation.py first to generate the file,")
        print("then translate it and run this script.")
        sys.exit(1)

    if not os.path.isfile(MISSING_JSON_PATH):
        print(
            f"ERROR: missing_lines.json not found: {MISSING_JSON_PATH}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(DUMP_PATH):
        print(
            f"ERROR: passage_dump.txt not found: {DUMP_PATH}",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN MODE === (no files will be modified)")
        print()

    results = run(
        args.input,
        dry_run=args.dry_run,
        create_backup=not args.no_backup,
        file_filter=args.file_filter,
    )

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = 0
    for fname in sorted(results):
        count = results[fname]
        if count > 0:
            status = "would insert" if args.dry_run else "inserted"
            print(f"  {fname:<45} {status} {count} lines")
            total += count

    print()
    if args.dry_run:
        print(f"Total lines that would be inserted: {total}")
        print()
        print("To apply changes, run without --dry-run:")
        print("  python scripts/apply_translations.py")
    else:
        print(f"Total lines inserted: {total}")
        if not args.no_backup:
            print("Backup files (*.bak) created for modified files.")


if __name__ == "__main__":
    main()
