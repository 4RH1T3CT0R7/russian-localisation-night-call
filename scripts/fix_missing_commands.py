#!/usr/bin/env python3
"""
Automatically adds missing $$ engine commands $$ to Russian localization files
by comparing against the English passage dump.

For each passage, compares the $$ commands in the English dump with those in the
Russian file, and inserts missing commands at the correct position.

Run: python scripts/fix_missing_commands.py [--dry-run] [--file PATTERN]
"""
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")

DRY_RUN = "--dry-run" in sys.argv
FILE_FILTER = None
for i, arg in enumerate(sys.argv):
    if arg == "--file" and i + 1 < len(sys.argv):
        FILE_FILTER = sys.argv[i + 1]

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def is_engine_command(text):
    s = text.strip()
    return s.startswith("$$") and s.endswith("$$")


def parse_dump(dump_path):
    """Parse passage_dump.txt into {obj_id: {passage: {'commands': [...], 'lines': [...]}}}"""
    objects = {}
    current_obj = None
    current_passage = None

    with open(dump_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("OBJ "):
                parts = line.split()
                current_obj = parts[1]
                objects[current_obj] = {}
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
                current_passage = {"all_lines": [], "commands": []}
                if current_obj:
                    objects[current_obj][passage_name] = current_passage
            elif line.startswith("L ") and current_passage:
                content = line[2:]
                current_passage["all_lines"].append(content)
                if is_engine_command(content):
                    current_passage["commands"].append(content)
    return objects


def parse_rus_file(filepath):
    """Parse Russian file into {passage_name: {'start_line': int, 'end_line': int, 'lines': [...]}}"""
    passages = {}
    current_name = None
    current_start = None

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n").rstrip("\r")
        if line.startswith("=== "):
            if current_name is not None:
                passages[current_name]["end_line"] = i  # exclusive
            current_name = line[4:].strip()
            current_start = i
            passages[current_name] = {
                "start_line": i,
                "end_line": len(lines),
                "lines": [],
            }
        elif current_name is not None:
            passages[current_name]["lines"].append({
                "index": i,
                "text": line,
            })

    if current_name:
        passages[current_name]["end_line"] = len(lines)

    return passages, lines


def find_insert_position(rus_passage_lines, eng_all_lines, missing_cmd):
    """Find the best position to insert a missing command in the Russian passage.

    Strategy: Find the command's position in the English passage,
    look at what text lines are before/after it, and find matching
    text in the Russian passage to place it correctly.
    """
    # Find position of missing_cmd in English lines
    eng_idx = None
    for i, eline in enumerate(eng_all_lines):
        if eline == missing_cmd:
            eng_idx = i
            break

    if eng_idx is None:
        return None

    # Get the first non-empty, non-command content line in Russian
    rus_content = []
    for rl in rus_passage_lines:
        text = rl["text"].strip()
        if text and not text.startswith("==="):
            rus_content.append(rl)

    if not rus_content:
        # Empty passage - insert at start (after header)
        return rus_passage_lines[0]["index"] if rus_passage_lines else None

    # If the command should be at the very start (before any text)
    if eng_idx == 0:
        # Insert before first content line
        for rl in rus_passage_lines:
            if rl["text"].strip():
                return rl["index"]
        return None

    # Find the closest text line BEFORE the command in English
    prev_text = None
    for i in range(eng_idx - 1, -1, -1):
        if not is_engine_command(eng_all_lines[i]):
            prev_text = eng_all_lines[i]
            break

    # Find the closest text line AFTER the command in English
    next_text = None
    for i in range(eng_idx + 1, len(eng_all_lines)):
        if not is_engine_command(eng_all_lines[i]):
            next_text = eng_all_lines[i]
            break

    # Try to find matching position in Russian by looking at existing commands
    # Insert after the last existing command that comes before this one in English order
    last_cmd_pos = None
    for rl in rus_passage_lines:
        if is_engine_command(rl["text"].strip()) and rl["text"].strip() in [e for e in eng_all_lines[:eng_idx] if is_engine_command(e)]:
            last_cmd_pos = rl["index"] + 1

    if last_cmd_pos is not None:
        return last_cmd_pos

    # Default: insert at the start of the passage content (after blank line after header)
    for rl in rus_passage_lines:
        if rl["text"].strip():
            return rl["index"]

    return None


def fix_file(filepath, eng_passages_all):
    """Fix missing commands in a single file."""
    rus_passages, lines = parse_rus_file(filepath)

    insertions = []  # List of (line_index, text_to_insert)

    for pname, eng_p in eng_passages_all.items():
        if pname not in rus_passages:
            continue

        rus_p = rus_passages[pname]
        eng_cmds = set(eng_p["commands"])
        rus_cmds = set()

        for rl in rus_p["lines"]:
            if is_engine_command(rl["text"].strip()):
                rus_cmds.add(rl["text"].strip())

        missing = eng_cmds - rus_cmds

        for cmd in missing:
            # Find where to insert
            pos = find_insert_position(rus_p["lines"], eng_p["all_lines"], cmd)
            if pos is not None:
                insertions.append((pos, cmd))

    if not insertions:
        return 0

    # Sort by position (reverse order to avoid index shifting)
    insertions.sort(key=lambda x: x[0], reverse=True)

    # Remove duplicates at same position
    seen_pos = set()
    unique_insertions = []
    for pos, cmd in insertions:
        key = (pos, cmd)
        if key not in seen_pos:
            seen_pos.add(key)
            unique_insertions.append((pos, cmd))

    if DRY_RUN:
        for pos, cmd in sorted(unique_insertions):
            print(f"  Would insert at line {pos + 1}: {cmd}")
        return len(unique_insertions)

    # Apply insertions (reverse order)
    for pos, cmd in unique_insertions:
        lines.insert(pos, cmd + "\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return len(unique_insertions)


def main():
    print("Parsing passage dump...")
    dump_objects = parse_dump(DUMP_PATH)

    # Build prefix mapping
    obj_by_prefix = {}
    for obj_id in dump_objects:
        prefix = re.sub(r'_\d+$', '', obj_id)
        if prefix not in obj_by_prefix:
            obj_by_prefix[prefix] = []
        obj_by_prefix[prefix].append(obj_id)

    import glob
    txt_files = sorted(glob.glob(os.path.join(TEXTS_DIR, "*_rus.txt")))
    if FILE_FILTER:
        txt_files = [f for f in txt_files if FILE_FILTER in os.path.basename(f)]

    mode = "DRY RUN" if DRY_RUN else "FIXING"
    print(f"{mode}: Processing {len(txt_files)} files...\n")

    total_fixes = 0
    files_fixed = 0

    for filepath in txt_files:
        basename = os.path.basename(filepath)
        prefix = basename.replace("_rus.txt", "")

        matching_objs = obj_by_prefix.get(prefix, [])
        if not matching_objs:
            continue

        eng_passages = {}
        for obj_id in matching_objs:
            eng_passages.update(dump_objects[obj_id])

        if not eng_passages:
            continue

        count = fix_file(filepath, eng_passages)
        if count > 0:
            files_fixed += 1
            total_fixes += count
            print(f"  {basename}: {count} commands {'would be ' if DRY_RUN else ''}added")

    print(f"\n{'='*40}")
    print(f"Total: {total_fixes} commands in {files_fixed} files")
    if DRY_RUN:
        print("(dry run - no changes made)")


if __name__ == "__main__":
    main()
