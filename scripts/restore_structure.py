#!/usr/bin/env python3
"""
Restore missing engine commands and fix structural issues across all Russian
localization files for Night Call.

Compares each Russian _rus.txt file against the English passage_dump.txt
reference and reconstructs passages so that:
  - All $$ engine commands $$ from the English reference are present in order
  - Duplicate / leaked content lines are removed
  - Special lines (conditionals, variables, braces) are preserved in place
  - Choice lines are kept as-is from the Russian file
  - File header (before the first === passage) is preserved verbatim

Run:
    python scripts/restore_structure.py [--dry-run] [--file PATTERN] [--verbose]
"""
from __future__ import annotations

import glob
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Encoding safety
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
# CLI flags
# ---------------------------------------------------------------------------
DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv
FILE_FILTER: Optional[str] = None
for _i, _arg in enumerate(sys.argv):
    if _arg == "--file" and _i + 1 < len(sys.argv):
        FILE_FILTER = sys.argv[_i + 1]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class EnglishLine:
    """Single line inside an English passage."""

    text: str
    is_command: bool


@dataclass
class EnglishPassage:
    """Parsed passage from the English dump."""

    name: str
    lines: list[EnglishLine] = field(default_factory=list)
    choices: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Line classification helpers
# ---------------------------------------------------------------------------
_VAR_ASSIGN_RE = re.compile(
    r"^("
    r"\{.*\}"                            # { var = val }
    r"|"
    r"[\w\.\-]+\s*[\+\-]?=\s*\d+"       # var+=1, var=0, var-=1
    r")$"
)
_CONDITIONAL_RE = re.compile(r"^[^\*].*\?.*;;")


def is_engine_command(text: str) -> bool:
    """Return True if *text* is an engine command like ``$$ anim: X $$``."""
    s = text.strip()
    return bool(s.startswith("$$") and s.endswith("$$") and len(s) > 4)


def is_choice_line(text: str) -> bool:
    """Return True if *text* is a choice line ``*... -> target``."""
    s = text.strip()
    return s.startswith("*") and "->" in s


def is_conditional_routing(text: str) -> bool:
    """Return True if *text* is a conditional routing line."""
    s = text.strip()
    return bool(_CONDITIONAL_RE.match(s))


def is_variable_assignment(text: str) -> bool:
    """Return True if *text* is a variable assignment."""
    s = text.strip()
    return bool(_VAR_ASSIGN_RE.match(s))


def is_brace_expression(text: str) -> bool:
    """Return True if *text* is a ``{ ... }`` expression."""
    s = text.strip()
    return s.startswith("{") and s.endswith("}")


def is_special_line(text: str) -> bool:
    """Lines that are NOT in the English dump but must be preserved."""
    s = text.strip()
    if not s:
        return False
    return (
        is_conditional_routing(s)
        or is_variable_assignment(s)
        or is_brace_expression(s)
    )


def classify_rus_line(text: str) -> str:
    """Classify a Russian line into one of the structural categories.

    Returns one of:
        'empty', 'command', 'choice', 'special', 'content'
    """
    s = text.strip()
    if not s:
        return "empty"
    if is_engine_command(s):
        return "command"
    if is_choice_line(s):
        return "choice"
    if is_special_line(s):
        return "special"
    return "content"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_english_dump(dump_path: str) -> dict[str, dict[str, EnglishPassage]]:
    """Parse passage_dump.txt into ``{obj_id: {passage_name: EnglishPassage}}``."""
    objects: dict[str, dict[str, EnglishPassage]] = {}
    current_obj: Optional[str] = None
    current_passage: Optional[EnglishPassage] = None

    with open(dump_path, "r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.rstrip("\n")

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
                    int(parts[2])
                    int(parts[3])
                except ValueError:
                    continue
                passage_name = parts[1]
                current_passage = EnglishPassage(name=passage_name)
                if current_obj is not None:
                    objects[current_obj][passage_name] = current_passage

            elif line.startswith("L ") and current_passage is not None:
                content = line[2:]
                current_passage.lines.append(
                    EnglishLine(
                        text=content,
                        is_command=is_engine_command(content),
                    )
                )

            elif line.startswith("C ") and current_passage is not None:
                current_passage.choices.append(line[2:])

    return objects


@dataclass
class RussianPassage:
    """A passage parsed from a Russian _rus.txt file."""

    name: str
    header_line_idx: int
    body_start_idx: int
    body_end_idx: int
    body_lines: list[str] = field(default_factory=list)


def parse_russian_file(filepath: str) -> tuple[list[str], list[str], list[RussianPassage]]:
    """Parse a Russian file.

    Returns:
        header_lines: lines before the first ``=== ...`` passage
        raw_lines: every line in the file (newlines stripped)
        passages: ordered list of RussianPassage objects
    """
    with open(filepath, "r", encoding="utf-8-sig") as fh:
        raw_lines = [l.rstrip("\n").rstrip("\r") for l in fh.readlines()]

    passages: list[RussianPassage] = []
    header_lines: list[str] = []
    first_passage_found = False

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if line.startswith("=== "):
            first_passage_found = True
            pname = line[4:].strip()

            body_start = i + 1
            if body_start < len(raw_lines) and raw_lines[body_start].strip() == "":
                body_start += 1

            j = body_start
            while j < len(raw_lines):
                if raw_lines[j].startswith("=== "):
                    break
                j += 1

            body_end = j
            while body_end > body_start and raw_lines[body_end - 1].strip() == "":
                body_end -= 1

            body = raw_lines[body_start:body_end]

            passages.append(
                RussianPassage(
                    name=pname,
                    header_line_idx=i,
                    body_start_idx=body_start,
                    body_end_idx=body_end,
                    body_lines=body,
                )
            )
            i = j
        else:
            if not first_passage_found:
                header_lines.append(line)
            i += 1

    return header_lines, raw_lines, passages


# ---------------------------------------------------------------------------
# Reconstruction logic
# ---------------------------------------------------------------------------
@dataclass
class ReconstructionStats:
    """Accumulates statistics for a single file."""

    passages_checked: int = 0
    passages_changed: int = 0
    commands_restored: int = 0
    duplicates_removed: int = 0


def _build_eng_structure(eng: EnglishPassage) -> list[tuple[str, str]]:
    """Build the English line sequence as ``[(type, text), ...]``.

    type is 'command' or 'content'.
    """
    result: list[tuple[str, str]] = []
    for eline in eng.lines:
        kind = "command" if eline.is_command else "content"
        result.append((kind, eline.text.strip() if eline.is_command else eline.text))
    return result


def _extract_russian_parts(
    rus: RussianPassage,
) -> tuple[list[str], list[str], list[str], list[tuple[int, str]]]:
    """Classify Russian body lines into separate buckets.

    Returns:
        commands:  list of normalized command strings in order of appearance
        content:   list of content lines (narration/dialogue) in order
        choices:   list of choice lines in order
        specials:  list of (body_line_index, text) for conditionals/vars/braces
    """
    commands: list[str] = []
    content: list[str] = []
    choices: list[str] = []
    specials: list[tuple[int, str]] = []

    for idx, rline in enumerate(rus.body_lines):
        cat = classify_rus_line(rline)
        if cat == "command":
            commands.append(rline.strip())
        elif cat == "choice":
            choices.append(rline)
        elif cat == "special":
            specials.append((idx, rline))
        elif cat == "content":
            content.append(rline)

    return commands, content, choices, specials


def _compute_special_insertion_points(
    rus: RussianPassage,
    eng_structure: list[tuple[str, str]],
) -> list[tuple[str, int]]:
    """Figure out where special lines (conditionals, variables) should be
    placed in the reconstructed output.

    We walk the Russian body lines and track how many English-structure
    slots we have passed, mapping each special line to a slot index.

    Returns list of (special_line_text, slot_before_which_to_insert).
    """
    result: list[tuple[str, int]] = []

    # We need to figure out how each Russian body line maps to an English
    # structural slot.  We walk the Russian body in order, maintaining
    # a pointer into the English structure.
    eng_idx = 0
    num_eng = len(eng_structure)

    for rline in rus.body_lines:
        cat = classify_rus_line(rline)

        if cat == "special":
            # This special line should be inserted at the current eng_idx position
            result.append((rline, eng_idx))
        elif cat == "command":
            # Try to advance eng_idx to match this command
            cmd = rline.strip()
            # Look ahead in English structure for this command
            found = False
            for k in range(eng_idx, num_eng):
                if eng_structure[k][0] == "command" and eng_structure[k][1] == cmd:
                    eng_idx = k + 1
                    found = True
                    break
            if not found:
                # Command not in English -- might be extra, just advance
                pass
        elif cat == "content":
            # Advance to the next content slot
            for k in range(eng_idx, num_eng):
                if eng_structure[k][0] == "content":
                    eng_idx = k + 1
                    break
        # empty / choice: don't advance

    return result


def reconstruct_passage(
    eng: EnglishPassage,
    rus: RussianPassage,
    stats: ReconstructionStats,
    verbose: bool = False,
) -> Optional[list[str]]:
    """Reconstruct one Russian passage to match the English structure.

    The algorithm walks through the English line sequence in order:
      - For each COMMAND: emit the command.  If the Russian file had it
        (tracked via a count-based pool), use the Russian form; otherwise
        restore it from English.
      - For each CONTENT: emit the next unused Russian content line (up to
        the expected count from English).

    Special lines (conditionals, variables, braces) that only exist in the
    Russian file are re-inserted at their relative structural positions.

    Choice lines are appended at the end, preserved from Russian.

    Returns a new body-line list if changes were made, or None if the
    passage is already correct.
    """
    stats.passages_checked += 1

    eng_structure = _build_eng_structure(eng)
    rus_cmds, rus_content, rus_choices, rus_specials = _extract_russian_parts(rus)

    # Count expected vs actual
    eng_content_count = sum(1 for kind, _ in eng_structure if kind == "content")
    eng_cmd_list = [text for kind, text in eng_structure if kind == "command"]

    # ---- Count-based command pool ----
    # Use a counter so that duplicate commands (e.g. $$ anim: IDLE_DRIVER $$
    # appearing twice) are tracked properly.
    rus_cmd_counter = Counter(rus_cmds)
    eng_cmd_counter = Counter(eng_cmd_list)

    # Determine how many instances of each command are missing
    missing_cmd_count = 0
    for cmd, eng_count in eng_cmd_counter.items():
        rus_count = rus_cmd_counter.get(cmd, 0)
        if rus_count < eng_count:
            missing_cmd_count += eng_count - rus_count

    extra_content = len(rus_content) > eng_content_count

    # ---- Quick check: if nothing is wrong, verify ordering ----
    if missing_cmd_count == 0 and not extra_content:
        if _ordering_matches(eng_structure, rus):
            return None

    # ---- Compute where special lines belong ----
    special_insertions = _compute_special_insertion_points(rus, eng_structure)

    # ---- Build a mutable pool of Russian commands ----
    # For each command text, maintain a count of how many times we can still
    # use it from the Russian file.
    cmd_pool = Counter(rus_cmds)

    # ---- Walk the English structure and build output ----
    output: list[str] = []
    content_idx = 0
    commands_added = 0

    for slot_idx, (kind, eng_text) in enumerate(eng_structure):
        # Insert any special lines that belong before this slot
        for sp_text, sp_slot in special_insertions:
            if sp_slot == slot_idx:
                output.append(sp_text)

        if kind == "command":
            cmd = eng_text
            if cmd_pool.get(cmd, 0) > 0:
                # Russian has this command -- use it
                cmd_pool[cmd] -= 1
                output.append(cmd)
            else:
                # Missing command -- restore from English
                output.append(cmd)
                commands_added += 1

        else:  # content
            if content_idx < len(rus_content) and content_idx < eng_content_count:
                output.append(rus_content[content_idx])
                content_idx += 1
            # If no more Russian content, skip (do not insert English text)

    # Insert any specials that belong after the last English slot
    for sp_text, sp_slot in special_insertions:
        if sp_slot >= len(eng_structure):
            output.append(sp_text)

    # Append choice lines
    for ch in rus_choices:
        output.append(ch)

    # ---- Statistics ----
    duplicates = max(0, len(rus_content) - eng_content_count)

    # ---- Check if anything actually changed ----
    if output == rus.body_lines:
        return None

    stats.passages_changed += 1
    stats.commands_restored += commands_added
    stats.duplicates_removed += duplicates

    if verbose and (commands_added or duplicates):
        parts = []
        if commands_added:
            parts.append(f"+{commands_added} cmds")
        if duplicates:
            parts.append(f"-{duplicates} dup")
        print(f"    {rus.name}: {', '.join(parts)}")

    return output


def _ordering_matches(
    eng_structure: list[tuple[str, str]],
    rus: RussianPassage,
) -> bool:
    """Check if the Russian passage already matches the English structural
    order, accounting for special lines and choices that don't appear in
    English.

    Returns True if the passage is correct as-is.
    """
    # Build the Russian structural sequence (commands + content only)
    rus_seq: list[tuple[str, str]] = []
    for rline in rus.body_lines:
        cat = classify_rus_line(rline)
        if cat == "command":
            rus_seq.append(("command", rline.strip()))
        elif cat == "content":
            rus_seq.append(("content", rline))

    # Walk both sequences in parallel
    ri = 0
    for e_kind, e_text in eng_structure:
        if ri >= len(rus_seq):
            if e_kind == "command":
                return False  # Missing a trailing command
            continue

        r_kind, r_text = rus_seq[ri]

        if e_kind == "command":
            if r_kind != "command" or r_text != e_text:
                return False
            ri += 1
        else:  # content
            if r_kind == "command":
                return False  # Structure mismatch
            ri += 1

    # Check for excess Russian lines after English ends
    remaining_content = sum(1 for k, _ in rus_seq[ri:] if k == "content")
    if remaining_content > 0:
        return False

    return True


# ---------------------------------------------------------------------------
# File-level processing
# ---------------------------------------------------------------------------
def build_obj_mapping(
    dump_objects: dict[str, dict[str, EnglishPassage]],
) -> dict[str, dict[str, EnglishPassage]]:
    """Build a mapping from Russian filename prefix to merged English passages.

    Russian file ``051_leonie_rus.txt`` maps to OBJ ``051_leonie_01``,
    ``051_leonie_02``, etc.
    File ``009_ludwig_00a_rus.txt`` maps directly to OBJ ``009_ludwig_00a``.
    File ``099_boss_01_rus.txt`` maps directly to OBJ ``099_boss_01``.
    """
    prefix_map: dict[str, dict[str, EnglishPassage]] = {}

    for obj_id, passages in dump_objects.items():
        # Always register the exact obj_id
        prefix_map.setdefault(obj_id, {}).update(passages)

        # Also register with the trailing _NN stripped, so that
        # 051_leonie_rus.txt picks up 051_leonie_01, 051_leonie_02, etc.
        base = re.sub(r"_(\d{2})$", "", obj_id)
        if base != obj_id:
            prefix_map.setdefault(base, {}).update(passages)

    return prefix_map


def get_english_passages_for_file(
    basename: str,
    prefix_map: dict[str, dict[str, EnglishPassage]],
) -> dict[str, EnglishPassage]:
    """Given a Russian filename, find all matching English passages."""
    prefix = basename.replace("_rus.txt", "")

    if prefix in prefix_map:
        return prefix_map[prefix]

    return {}


def process_file(
    filepath: str,
    eng_passages: dict[str, EnglishPassage],
) -> ReconstructionStats:
    """Process a single Russian file and rewrite it if needed."""
    stats = ReconstructionStats()

    header_lines, raw_lines, passages = parse_russian_file(filepath)

    if not passages:
        return stats

    reconstructed: dict[str, list[str]] = {}

    for rus_p in passages:
        if rus_p.name not in eng_passages:
            continue
        eng_p = eng_passages[rus_p.name]

        new_body = reconstruct_passage(eng_p, rus_p, stats, verbose=VERBOSE)
        if new_body is not None:
            reconstructed[rus_p.name] = new_body

    if not reconstructed:
        return stats

    if DRY_RUN:
        return stats

    # ----- Rebuild the entire file ----- #
    output_lines: list[str] = []

    # File header (before first passage)
    output_lines.extend(header_lines)

    for p_idx, rus_p in enumerate(passages):
        if p_idx == 0:
            # Ensure at least one blank line before the first === header
            if not output_lines or output_lines[-1].strip() != "":
                output_lines.append("")
        else:
            # Two blank lines between passages
            while output_lines and output_lines[-1].strip() == "":
                output_lines.pop()
            output_lines.append("")
            output_lines.append("")

        # Passage header
        output_lines.append(f"=== {rus_p.name}")
        output_lines.append("")  # blank line after ===

        # Body
        if rus_p.name in reconstructed:
            body = reconstructed[rus_p.name]
        else:
            body = rus_p.body_lines

        output_lines.extend(body)

    # Trailing newline
    while output_lines and output_lines[-1].strip() == "":
        output_lines.pop()
    output_lines.append("")

    with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(output_lines))
        fh.write("\n")

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("  Night Call -- Restore Structure")
    print("  Mode:", "DRY RUN" if DRY_RUN else "LIVE (will modify files)")
    print("=" * 60)
    print()

    print("Parsing English passage dump...")
    dump_objects = parse_english_dump(DUMP_PATH)
    total_eng_passages = sum(len(p) for p in dump_objects.values())
    print(f"  Found {len(dump_objects)} objects, {total_eng_passages} passages")

    prefix_map = build_obj_mapping(dump_objects)

    pattern = os.path.join(TEXTS_DIR, "*_rus.txt")
    txt_files = sorted(glob.glob(pattern))
    if FILE_FILTER:
        txt_files = [f for f in txt_files if FILE_FILTER in os.path.basename(f)]

    print(f"  Processing {len(txt_files)} Russian files")
    print()

    total_stats = ReconstructionStats()
    files_modified = 0
    files_skipped = 0

    for filepath in txt_files:
        basename = os.path.basename(filepath)
        eng_passages = get_english_passages_for_file(basename, prefix_map)

        if not eng_passages:
            files_skipped += 1
            if VERBOSE:
                print(f"  SKIP {basename}: no English passages found")
            continue

        stats = process_file(filepath, eng_passages)

        total_stats.passages_checked += stats.passages_checked
        total_stats.passages_changed += stats.passages_changed
        total_stats.commands_restored += stats.commands_restored
        total_stats.duplicates_removed += stats.duplicates_removed

        if stats.passages_changed > 0:
            files_modified += 1
            action = "would modify" if DRY_RUN else "modified"
            print(
                f"  {action} {basename}: "
                f"{stats.passages_changed} passages "
                f"(+{stats.commands_restored} cmds, "
                f"-{stats.duplicates_removed} dup)"
            )

    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Files processed:      {len(txt_files)}")
    print(f"  Files modified:       {files_modified}")
    print(f"  Files skipped:        {files_skipped} (no English match)")
    print(f"  Passages checked:     {total_stats.passages_checked}")
    print(f"  Passages changed:     {total_stats.passages_changed}")
    print(f"  Commands restored:    {total_stats.commands_restored}")
    print(f"  Duplicates removed:   {total_stats.duplicates_removed}")
    if DRY_RUN:
        print()
        print("  (dry run -- no files were modified)")
    print()


if __name__ == "__main__":
    main()
