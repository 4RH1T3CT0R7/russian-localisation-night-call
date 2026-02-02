#!/usr/bin/env python3
"""
Find missing dialogue lines in Night Call Russian localization files.

Compares the English passage dump against Russian translation files to
identify specific text lines (dialogue, narration, engine commands, game
logic) that are present in English but absent from Russian.

Each missing line is classified as:
  MISSING_TEXT    -- dialogue or narration the player sees
  MISSING_COMMAND -- $$ engine commands $$ (visual/audio cues)
  MISSING_LOGIC   -- game variables, conditionals, counters

Run:
  python scripts/find_missing_lines.py
  python scripts/find_missing_lines.py --file 054_ludivine
  python scripts/find_missing_lines.py --summary
  python scripts/find_missing_lines.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
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
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class EnglishPassage:
    """One passage as parsed from the English passage dump."""

    name: str
    line_count: int
    choice_count: int
    lines: list[str] = field(default_factory=list)
    choices: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RussianPassage:
    """One passage as parsed from a _rus.txt file."""

    name: str
    start_line: int
    content_lines: list[dict[str, str | int]] = field(default_factory=list)
    choices: list[dict[str, str | int]] = field(default_factory=list)


@dataclass
class MissingLine:
    """A single English line that has no Russian counterpart."""

    category: str            # MISSING_TEXT | MISSING_COMMAND | MISSING_LOGIC
    english_text: str        # The English source line
    eng_position: int        # 0-based index in the English line list
    context_before: str      # The English line immediately before (for orientation)
    context_after: str       # The English line immediately after


@dataclass
class PassageReport:
    """All missing lines for one passage in one file."""

    file: str
    passage: str
    eng_total: int
    rus_total: int
    missing: list[MissingLine] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Line classification helpers
# ---------------------------------------------------------------------------
def is_engine_command(text: str) -> bool:
    """Return True if the line is a $$ engine command $$."""
    s = text.strip()
    return s.startswith("$$") and s.endswith("$$")


def is_game_logic(text: str) -> bool:
    """Return True for game-variable or conditional routing lines.

    Covers patterns such as:
      _Driver.Met.X=1
      interruptions+=1
      _Driver.Is.Sandman=1?passage-a;;passage-b
      { _Driver.Met.Ludwig = 1 }
      ??option1|option2
    """
    s = text.strip()
    # Braced assignment:  { _Driver.Met.X = 1 }
    if re.match(r"^\{.*=.*\}$", s):
        return True
    # Bare assignment:  _Driver.Met.X=1  or  silence=0
    if re.match(r"^[_a-zA-Z][\w.-]*\s*=\s*\d+$", s):
        return True
    # Increment / decrement:  interruptions+=1
    if re.match(r"^[\w.-]+\s*[+-]=\s*\d+$", s):
        return True
    # Conditional routing: contains ? and ;; but is not a choice line
    if "?" in s and ";;" in s and not s.startswith("*"):
        return True
    # Random routing:  ??optionA|optionB
    if s.startswith("??"):
        return True
    # Redirect lines:  -> passage-name  or  -> _Var=1 ? passage
    if re.match(r"^->\s", s):
        return True
    return False


def classify_line(text: str) -> str:
    """Classify an English line into a category string."""
    if is_engine_command(text):
        return "MISSING_COMMAND"
    if is_game_logic(text):
        return "MISSING_LOGIC"
    return "MISSING_TEXT"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def parse_english_dump(dump_path: str) -> dict[str, dict[str, EnglishPassage]]:
    """Parse passage_dump.txt into {obj_id: {passage_name: EnglishPassage}}.

    Format per the dump:
      OBJ <obj_id> <total_passage_count>
      P <passage_name> <line_count> <choice_count>
      L <text>
      C <choice_text>\\t<target_passage>
    """
    objects: dict[str, dict[str, EnglishPassage]] = {}
    current_obj: Optional[str] = None
    current_passage: Optional[EnglishPassage] = None

    with open(dump_path, "r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")

            if line.startswith("OBJ "):
                parts = line.split()
                current_obj = parts[1]
                objects[current_obj] = {}
                current_passage = None

            elif line.startswith("P "):
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    line_count = int(parts[2])
                    choice_count = int(parts[3])
                except ValueError:
                    continue
                passage_name = parts[1]
                current_passage = EnglishPassage(
                    name=passage_name,
                    line_count=line_count,
                    choice_count=choice_count,
                )
                if current_obj is not None:
                    objects[current_obj][passage_name] = current_passage

            elif line.startswith("L ") and current_passage is not None:
                current_passage.lines.append(line[2:])

            elif line.startswith("C ") and current_passage is not None:
                choice_line = line[2:]
                parts = choice_line.split("\t", 1)
                if len(parts) == 2:
                    current_passage.choices.append(
                        {"text": parts[0], "target": parts[1]}
                    )

    return objects


def parse_russian_file(filepath: str) -> dict[str, RussianPassage]:
    """Parse a _rus.txt file into {passage_name: RussianPassage}.

    Format:
      === passage_name
      <content lines -- dialogue, narration, $$ commands $$, game logic>
      *<choice text> -> <target>
    """
    passages: dict[str, RussianPassage] = {}
    current: Optional[RussianPassage] = None

    with open(filepath, "r", encoding="utf-8-sig") as fh:
        lines = fh.readlines()

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")

        if line.startswith("=== "):
            passage_name = line[4:].strip()
            current = RussianPassage(name=passage_name, start_line=i)
            passages[passage_name] = current

        elif current is not None and line.strip():
            stripped = line.strip()
            # Skip pure comments
            if stripped.startswith("%%") or stripped.startswith("//"):
                continue
            # Skip metadata lines (VAR declarations, +++ anim links)
            if stripped.startswith("VAR ") or stripped.startswith("+++"):
                continue

            if stripped.startswith("*"):
                current.choices.append({"text": stripped, "line_number": i})
            else:
                current.content_lines.append({"text": stripped, "line_number": i})

    return passages


# ---------------------------------------------------------------------------
# OBJ-id to file-prefix mapping
# ---------------------------------------------------------------------------
def obj_id_to_prefix(obj_id: str) -> str:
    """Strip the trailing _XX number suffix from an OBJ id.

    Examples:
      054_ludivine_01  -> 054_ludivine
      009_ludwig_00a   -> 009_ludwig_00a   (kept as-is, has letter suffix)
      096_gilda_02     -> 096_gilda
      208_myrtille_00a -> 208_myrtille_00a (kept as-is)
      100_cop_01       -> 100_cop
    """
    # Match trailing _XX where XX is purely digits (01, 02, ... 99)
    m = re.match(r"^(.+?)_(\d{1,2})$", obj_id)
    if m:
        return m.group(1)
    return obj_id


def build_file_map(texts_dir: str) -> dict[str, str]:
    """Build a mapping of file_prefix -> absolute filepath for all *_rus.txt.

    The prefix is the filename with the trailing '_rus.txt' removed.
    e.g. 054_ludivine_rus.txt -> 054_ludivine
    """
    mapping: dict[str, str] = {}
    for fname in os.listdir(texts_dir):
        if fname.endswith("_rus.txt"):
            prefix = fname[: -len("_rus.txt")]
            mapping[prefix] = os.path.join(texts_dir, fname)
    return mapping


# ---------------------------------------------------------------------------
# Positional alignment logic
# ---------------------------------------------------------------------------
def normalize_for_match(text: str) -> str:
    """Produce a simplified key used for fuzzy positional matching.

    Engine commands are compared literally.  For text lines we strip
    speaker tags, quotes, punctuation, and collapse whitespace so that
    minor translation differences don't prevent alignment.
    """
    s = text.strip()
    if is_engine_command(s):
        return s.lower()
    # For game logic, compare literally
    if is_game_logic(s):
        return s
    # Strip speaker tag  (e.g. "ALPH: " / "NAME : ")
    s = re.sub(r"^[A-Z\u0400-\u04FF][A-Z\u0400-\u04FF .'-]+\s*:\s*", "", s)
    # Remove various quote marks
    s = s.replace('"', "").replace("'", "")
    s = s.replace("\u00ab", "").replace("\u00bb", "")  # << >>
    s = s.replace("\u201c", "").replace("\u201d", "")  # smart quotes
    s = s.replace("\u201e", "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def find_missing_lines(
    eng_passage: EnglishPassage,
    rus_passage: RussianPassage,
) -> list[MissingLine]:
    """Align English and Russian content lines by position and identify gaps.

    Strategy:
    1. Build an ordered list of English content lines (L-lines from the dump).
    2. Build an ordered list of Russian content lines (non-choice, non-blank).
    3. Walk both lists with a two-pointer approach.  For each English line,
       try to find a corresponding Russian line nearby (within a small window)
       that looks like it matches (same command, or roughly same position
       relative to shared anchors like $$ commands).
    4. Any English line left unmatched is reported as missing.
    """
    eng_lines = eng_passage.lines
    rus_lines = [cl["text"] for cl in rus_passage.content_lines]

    if not eng_lines:
        return []

    # Normalise both sides for comparison
    eng_norm = [normalize_for_match(l) for l in eng_lines]
    rus_norm = [normalize_for_match(l) for l in rus_lines]

    # Mark which English lines have been matched
    eng_matched: list[bool] = [False] * len(eng_lines)

    # Greedy forward matching -- try to consume Russian lines in order
    rus_ptr = 0
    for ei in range(len(eng_lines)):
        if rus_ptr >= len(rus_lines):
            break
        # Direct match by normalised form (works well for $$ commands)
        if eng_norm[ei] == rus_norm[rus_ptr]:
            eng_matched[ei] = True
            rus_ptr += 1
            continue
        # If both are engine commands but differ, still consume (translated
        # commands may differ slightly)
        if is_engine_command(eng_lines[ei]) and is_engine_command(rus_lines[rus_ptr]):
            eng_matched[ei] = True
            rus_ptr += 1
            continue
        # If both are game logic, consume
        if is_game_logic(eng_lines[ei]) and is_game_logic(rus_lines[rus_ptr]):
            eng_matched[ei] = True
            rus_ptr += 1
            continue
        # Look-ahead in Russian: maybe this English line was skipped in
        # translation but the next Russian line still matches a later English
        # line.  Peek up to 3 Russian lines ahead to find this English line.
        found_ahead = False
        for look in range(1, min(4, len(rus_lines) - rus_ptr)):
            if eng_norm[ei] == rus_norm[rus_ptr + look]:
                # The intervening Russian lines are extras (echo text, etc.)
                rus_ptr += look
                eng_matched[ei] = True
                rus_ptr += 1
                found_ahead = True
                break
        if found_ahead:
            continue
        # If both are text (not command / logic), assume the Russian line is
        # the translation of this English line.
        eng_is_text = classify_line(eng_lines[ei]) == "MISSING_TEXT"
        rus_is_text = (
            not is_engine_command(rus_lines[rus_ptr])
            and not is_game_logic(rus_lines[rus_ptr])
        )
        if eng_is_text and rus_is_text:
            eng_matched[ei] = True
            rus_ptr += 1
            continue
        # Otherwise this English line has no match -- leave it unmatched and
        # do NOT advance rus_ptr (the current Russian line may match a later
        # English line).

    # Collect missing lines
    missing: list[MissingLine] = []
    for ei in range(len(eng_lines)):
        if eng_matched[ei]:
            continue
        ctx_before = eng_lines[ei - 1] if ei > 0 else ""
        ctx_after = eng_lines[ei + 1] if ei < len(eng_lines) - 1 else ""
        missing.append(
            MissingLine(
                category=classify_line(eng_lines[ei]),
                english_text=eng_lines[ei],
                eng_position=ei,
                context_before=ctx_before,
                context_after=ctx_after,
            )
        )
    return missing


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def format_report_text(reports: list[PassageReport]) -> str:
    """Format human-readable report."""
    if not reports:
        return "No missing lines found."

    out: list[str] = []
    current_file = ""

    total_text = 0
    total_cmd = 0
    total_logic = 0

    for rpt in reports:
        if rpt.file != current_file:
            current_file = rpt.file
            out.append("")
            out.append("=" * 72)
            out.append(f"FILE: {current_file}")
            out.append("=" * 72)

        out.append("")
        out.append(
            f"  PASSAGE: {rpt.passage}  "
            f"(EN: {rpt.eng_total} lines, RU: {rpt.rus_total} lines, "
            f"missing: {len(rpt.missing)})"
        )
        out.append("  " + "-" * 60)

        for ml in rpt.missing:
            tag = ml.category
            if tag == "MISSING_TEXT":
                total_text += 1
            elif tag == "MISSING_COMMAND":
                total_cmd += 1
            else:
                total_logic += 1

            out.append(f"    [{tag}] (position {ml.eng_position})")
            if ml.context_before:
                out.append(f"      after : {ml.context_before[:100]}")
            out.append(f"      >>> {ml.english_text[:120]}")
            if ml.context_after:
                out.append(f"      before: {ml.context_after[:100]}")
            out.append("")

    # Grand summary
    total = total_text + total_cmd + total_logic
    out.append("")
    out.append("=" * 72)
    out.append("SUMMARY")
    out.append("=" * 72)
    out.append(f"  Total missing lines  : {total}")
    out.append(f"    MISSING_TEXT        : {total_text}")
    out.append(f"    MISSING_COMMAND     : {total_cmd}")
    out.append(f"    MISSING_LOGIC       : {total_logic}")
    out.append(f"  Passages affected    : {len(reports)}")
    files = sorted({r.file for r in reports})
    out.append(f"  Files affected       : {len(files)}")
    out.append("")

    return "\n".join(out)


def format_summary_text(reports: list[PassageReport]) -> str:
    """Format a compact summary grouped by file."""
    if not reports:
        return "No missing lines found."

    file_stats: dict[str, dict[str, int]] = {}
    for rpt in reports:
        if rpt.file not in file_stats:
            file_stats[rpt.file] = {
                "passages": 0,
                "MISSING_TEXT": 0,
                "MISSING_COMMAND": 0,
                "MISSING_LOGIC": 0,
            }
        stats = file_stats[rpt.file]
        stats["passages"] += 1
        for ml in rpt.missing:
            stats[ml.category] += 1

    out: list[str] = []
    out.append(f"{'FILE':<45} {'PASS':>5} {'TEXT':>5} {'CMD':>5} {'LOGIC':>5}")
    out.append("-" * 72)

    grand_p = grand_t = grand_c = grand_l = 0
    for fname in sorted(file_stats):
        s = file_stats[fname]
        out.append(
            f"{fname:<45} {s['passages']:>5} "
            f"{s['MISSING_TEXT']:>5} {s['MISSING_COMMAND']:>5} "
            f"{s['MISSING_LOGIC']:>5}"
        )
        grand_p += s["passages"]
        grand_t += s["MISSING_TEXT"]
        grand_c += s["MISSING_COMMAND"]
        grand_l += s["MISSING_LOGIC"]

    out.append("-" * 72)
    out.append(
        f"{'TOTAL':<45} {grand_p:>5} {grand_t:>5} {grand_c:>5} {grand_l:>5}"
    )
    return "\n".join(out)


def reports_to_json(reports: list[PassageReport]) -> list[dict]:
    """Convert report list to a JSON-serialisable structure."""
    result = []
    for rpt in reports:
        entry: dict = {
            "file": rpt.file,
            "passage": rpt.passage,
            "eng_total": rpt.eng_total,
            "rus_total": rpt.rus_total,
            "missing": [],
        }
        for ml in rpt.missing:
            entry["missing"].append(
                {
                    "category": ml.category,
                    "english_text": ml.english_text,
                    "position": ml.eng_position,
                    "context_before": ml.context_before,
                    "context_after": ml.context_after,
                }
            )
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def run(
    file_pattern: Optional[str],
    output_json: bool,
    summary_only: bool,
) -> list[PassageReport]:
    """Execute the comparison and return structured reports."""
    # 1. Parse the English reference dump
    eng_objects = parse_english_dump(DUMP_PATH)

    # 2. Build file map for Russian texts
    file_map = build_file_map(TEXTS_DIR)

    # 3. Build obj_prefix -> list of obj_ids lookup
    prefix_to_objs: dict[str, list[str]] = {}
    for obj_id in eng_objects:
        prefix = obj_id_to_prefix(obj_id)
        prefix_to_objs.setdefault(prefix, []).append(obj_id)

    all_reports: list[PassageReport] = []

    # 4. For each Russian file, find the matching English OBJ(s)
    for file_prefix in sorted(file_map):
        filepath = file_map[file_prefix]
        basename = os.path.basename(filepath)

        # Apply file filter
        if file_pattern and file_pattern not in file_prefix:
            continue

        # Determine which OBJ ids map to this file.
        # Direct prefix match first (e.g. "054_ludivine" matches OBJ
        # "054_ludivine_01", "054_ludivine_02", etc.)
        # Also handle sub-files like "009_ludwig_00a" which map directly.
        matching_obj_ids: list[str] = []

        if file_prefix in prefix_to_objs:
            # Direct match (e.g. 054_ludivine -> 054_ludivine_01, _02)
            matching_obj_ids = prefix_to_objs[file_prefix]
        else:
            # The file prefix itself might be a full OBJ id (e.g. 009_ludwig_00a)
            if file_prefix in eng_objects:
                matching_obj_ids = [file_prefix]

        if not matching_obj_ids:
            continue

        # Parse the Russian file
        rus_passages = parse_russian_file(filepath)

        # Compare each English passage from each matching OBJ
        for obj_id in sorted(matching_obj_ids):
            eng_passages = eng_objects[obj_id]

            for pname in sorted(eng_passages):
                eng_p = eng_passages[pname]

                if pname not in rus_passages:
                    # Passage entirely missing -- skip, handled by deep_audit
                    continue

                rus_p = rus_passages[pname]

                # Count content lines (excluding choices) on both sides
                eng_content = eng_p.lines
                rus_content = [cl["text"] for cl in rus_p.content_lines]

                if not eng_content:
                    continue

                # Only analyse passages where English has more content
                # than Russian (potential missing lines).
                eng_text_only = [
                    l for l in eng_content if not is_engine_command(l)
                ]
                rus_text_only = [
                    l
                    for l in rus_content
                    if not is_engine_command(l) and not is_game_logic(l)
                ]

                # Quick skip: if counts match or Russian has more, no gap
                if len(eng_content) <= len(rus_content):
                    continue

                missing = find_missing_lines(eng_p, rus_p)

                if missing:
                    all_reports.append(
                        PassageReport(
                            file=basename,
                            passage=pname,
                            eng_total=len(eng_content),
                            rus_total=len(rus_content),
                            missing=missing,
                        )
                    )

    return all_reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find missing dialogue lines in Russian localization files."
    )
    parser.add_argument(
        "--file",
        dest="file_pattern",
        default=None,
        help="Only process Russian files whose prefix contains PATTERN.",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output results as JSON for automated processing.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only per-file summary counts.",
    )
    args = parser.parse_args()

    reports = run(
        file_pattern=args.file_pattern,
        output_json=args.output_json,
        summary_only=args.summary,
    )

    if args.output_json:
        print(json.dumps(reports_to_json(reports), ensure_ascii=False, indent=2))
    elif args.summary:
        print(format_summary_text(reports))
    else:
        print(format_report_text(reports))

    # Exit with non-zero if there are MISSING_TEXT lines
    text_count = sum(
        1 for r in reports for m in r.missing if m.category == "MISSING_TEXT"
    )
    sys.exit(1 if text_count > 0 else 0)


if __name__ == "__main__":
    main()
