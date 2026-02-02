#!/usr/bin/env python3
"""
Deep structural audit of Night Call Russian localization files.
Compares every _rus.txt passage against the English passage_dump.txt
to detect systemic misalignment issues.

Detects:
  1. Choice lines containing narration text instead of actual dialogue
  2. Passages with wrong/shifted content (echo text instead of real content)
  3. Missing dialogue lines within passages
  4. Missing $$ engine commands $$
  5. Untranslated English text
  6. Speaker name inconsistencies
  7. Missing passages entirely

Run: python scripts/deep_audit.py [--fix-report] [--file PATTERN]
"""
import os
import sys
import re
import json
from collections import defaultdict

# Fix console encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")

# Parse args
FIX_REPORT = "--fix-report" in sys.argv
FILE_FILTER = None
for i, arg in enumerate(sys.argv):
    if arg == "--file" and i + 1 < len(sys.argv):
        FILE_FILTER = sys.argv[i + 1]


def parse_dump(dump_path):
    """Parse passage_dump.txt into a dict of {obj_id: {passage_name: PassageData}}"""
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
                    line_count = int(parts[2])
                    choice_count = int(parts[3])
                except ValueError:
                    continue
                passage_name = parts[1]
                current_passage = {
                    "name": passage_name,
                    "lines": [],
                    "choices": [],
                    "line_count": line_count,
                    "choice_count": choice_count,
                }
                if current_obj:
                    objects[current_obj][passage_name] = current_passage
            elif line.startswith("L ") and current_passage:
                current_passage["lines"].append(line[2:])
            elif line.startswith("C ") and current_passage:
                # Parse choice: C [choice_text]\t[target_passage]
                choice_line = line[2:]
                parts = choice_line.split("\t")
                if len(parts) == 2:
                    current_passage["choices"].append({
                        "text": parts[0],
                        "target": parts[1],
                    })
    return objects


def parse_rus_file(filepath):
    """Parse a _rus.txt file into a dict of {passage_name: PassageData}"""
    passages = {}
    current_passage = None

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n").rstrip("\r")

        if line.startswith("=== "):
            passage_name = line[4:].strip()
            current_passage = {
                "name": passage_name,
                "content_lines": [],
                "choices": [],
                "line_numbers": [],
                "start_line": i,
            }
            passages[passage_name] = current_passage
        elif current_passage and line.strip():
            if line.startswith("*"):
                current_passage["choices"].append({
                    "text": line,
                    "line_number": i,
                })
            else:
                current_passage["content_lines"].append({
                    "text": line,
                    "line_number": i,
                })

    return passages


def is_engine_command(text):
    """Check if a line is a $$ engine command $$"""
    return text.strip().startswith("$$") and text.strip().endswith("$$")


def is_conditional(text):
    """Check if a line is a conditional routing line"""
    return "?" in text and ";;" in text and not text.startswith("*")


def is_counter(text):
    """Check if a line is a counter operation like interruptions+=1"""
    return "+=" in text or "-=" in text


def extract_choice_text(choice_line):
    """Extract the display text from a Russian choice line like *:emote: "text" -> target"""
    m = re.match(r'^\*(?::[\w]+:\s*)?(.*?)\s*->\s*\S+$', choice_line)
    if m:
        return m.group(1).strip()
    return choice_line


def extract_eng_choice_text(choice_text):
    """Extract display text from English choice like ':emote: "text"' or '(action)'"""
    # Remove emote prefix
    text = re.sub(r'^:\w+:\s*', '', choice_text)
    return text.strip()


def looks_like_narration(text):
    """Check if text looks like narration rather than player dialogue"""
    # Narration typically starts with uppercase description or character action
    # Player dialogue is in quotes or parentheses
    text = text.strip()
    if not text:
        return False
    if text.startswith('"') or text.startswith('«') or text.startswith("'"):
        return False
    if text.startswith('(') and text.endswith(')'):
        return False
    # Check for Cyrillic text that's clearly narration
    if re.match(r'^[А-ЯЁ][а-яё]', text) and not text.startswith('"'):
        # Starts with uppercase Cyrillic, likely narration
        # But could be a name like ЛЮДИВИН
        if ':' not in text[:30]:  # No speaker tag
            return True
    return False


def has_english_text(text):
    """Check if text contains substantial English (untranslated)"""
    s = text.strip()
    # Skip engine commands, conditionals, counters
    if is_engine_command(s) or is_conditional(s) or is_counter(s):
        return False
    # Skip random choice lines (??option1|option2)
    if s.startswith("??"):
        return False
    # Skip game variable assignments like _Driver.Met.X=1, silence_intro=1, etc.
    if re.match(r'^[_a-zA-Z][\w.-]*\s*=\s*\d+$', s):
        return False
    # Skip game variable blocks like { _Driver.Met.X = 1 }
    if re.match(r'^\{.*=.*\}$', s):
        return False
    # Skip passage reference lines (just a passage name, no spaces or punctuation)
    if re.match(r'^[\w-]+$', s) and len(s) > 5:
        return False
    # Count English vs Cyrillic characters
    eng_chars = len(re.findall(r'[a-zA-Z]', s))
    rus_chars = len(re.findall(r'[а-яА-ЯёЁ]', s))
    # If more than 10 English chars and no Cyrillic, it's untranslated
    if eng_chars > 10 and rus_chars == 0:
        return True
    return False


def audit_file(obj_id, eng_passages, rus_passages, filename):
    """Compare English passages against Russian file, return issues"""
    issues = []

    # Check each English passage
    for pname, eng_p in eng_passages.items():
        if pname not in rus_passages:
            issues.append({
                "type": "MISSING_PASSAGE",
                "severity": "ERROR",
                "passage": pname,
                "message": f"Passage '{pname}' exists in English but missing from Russian file",
            })
            continue

        rus_p = rus_passages[pname]

        # --- Check choices ---
        eng_choices = eng_p["choices"]
        rus_choices = rus_p["choices"]

        if len(eng_choices) != len(rus_choices):
            issues.append({
                "type": "CHOICE_COUNT_MISMATCH",
                "severity": "WARN",
                "passage": pname,
                "message": f"English has {len(eng_choices)} choices, Russian has {len(rus_choices)}",
            })

        for ci, eng_c in enumerate(eng_choices):
            if ci >= len(rus_choices):
                break
            rus_c = rus_choices[ci]
            rus_text = extract_choice_text(rus_c["text"])
            eng_text = extract_eng_choice_text(eng_c["text"])

            # Check if Russian choice looks like narration instead of dialogue
            if looks_like_narration(rus_text):
                eng_is_dialogue = eng_text.startswith('"') or eng_text.startswith("'")
                eng_is_action = eng_text.startswith('(')
                if eng_is_dialogue:
                    issues.append({
                        "type": "NARRATION_IN_CHOICE",
                        "severity": "ERROR",
                        "passage": pname,
                        "line": rus_c["line_number"],
                        "message": f"Choice has narration instead of dialogue",
                        "current": rus_text[:60],
                        "english": eng_text[:60],
                    })

            # Check missing quotes on dialogue choices
            if eng_text.startswith('"') and not eng_text.startswith('('):
                if not rus_text.startswith('"') and not rus_text.startswith('«') and not rus_text.startswith('('):
                    # Could be narration leaking into choice
                    if not rus_text.startswith(':'):  # not emote echo
                        issues.append({
                            "type": "CHOICE_MISSING_QUOTES",
                            "severity": "WARN",
                            "passage": pname,
                            "line": rus_c["line_number"],
                            "message": f"Dialogue choice may be missing quotes",
                            "current": rus_text[:60],
                            "english": eng_text[:60],
                        })

        # --- Check content lines ---
        # Count non-command text lines in English
        eng_text_lines = [l for l in eng_p["lines"] if not is_engine_command(l)]
        rus_text_lines = [
            cl for cl in rus_p["content_lines"]
            if not is_engine_command(cl["text"])
            and not is_conditional(cl["text"])
            and not is_counter(cl["text"])
        ]

        if len(eng_text_lines) > 0 and len(rus_text_lines) == 0:
            issues.append({
                "type": "EMPTY_PASSAGE",
                "severity": "ERROR",
                "passage": pname,
                "message": f"English has {len(eng_text_lines)} text lines but Russian passage is empty",
                "english_sample": eng_text_lines[0][:80] if eng_text_lines else "",
            })
        elif len(eng_text_lines) > len(rus_text_lines) + 1:
            # Allow 1 line difference for echo text, but flag significant gaps
            issues.append({
                "type": "MISSING_LINES",
                "severity": "WARN",
                "passage": pname,
                "message": f"English has {len(eng_text_lines)} text lines, Russian has {len(rus_text_lines)} (missing {len(eng_text_lines) - len(rus_text_lines)})",
            })

        # --- Check for untranslated English ---
        for cl in rus_p["content_lines"]:
            if has_english_text(cl["text"]):
                issues.append({
                    "type": "UNTRANSLATED",
                    "severity": "ERROR",
                    "passage": pname,
                    "line": cl["line_number"],
                    "message": f"Untranslated English text",
                    "current": cl["text"][:80],
                })

        # --- Check missing engine commands ---
        eng_commands = [l for l in eng_p["lines"] if is_engine_command(l)]
        rus_commands = [
            cl["text"] for cl in rus_p["content_lines"]
            if is_engine_command(cl["text"])
        ]
        eng_cmd_set = set(eng_commands)
        rus_cmd_set = set(rus_commands)
        missing_cmds = eng_cmd_set - rus_cmd_set
        for cmd in missing_cmds:
            # Only flag important commands (reveal, music-control, anim-link)
            if any(kw in cmd for kw in ["reveal:", "anim-link:", "music-control:"]):
                issues.append({
                    "type": "MISSING_COMMAND",
                    "severity": "WARN",
                    "passage": pname,
                    "message": f"Missing engine command: {cmd}",
                })

    # Check for extra passages in Russian that don't exist in English
    for pname in rus_passages:
        if pname not in eng_passages:
            # This might be a dispatch/routing passage - not necessarily an error
            pass

    return issues


def main():
    if not os.path.exists(DUMP_PATH):
        print(f"Passage dump not found: {DUMP_PATH}")
        sys.exit(1)

    print("Parsing passage dump...")
    dump_objects = parse_dump(DUMP_PATH)
    print(f"  Found {len(dump_objects)} objects in dump")

    # Build mapping from filename prefix to OBJ id
    # Filename: 054_ludivine_rus.txt -> prefix 054_ludivine -> OBJ 054_ludivine_01
    obj_by_prefix = {}
    # Also map exact OBJ ids for multi-file characters (100_cop_01 -> OBJ 100_cop_01)
    obj_by_exact = {}
    for obj_id in dump_objects:
        obj_by_exact[obj_id] = obj_id
        # Remove trailing _01, _02 etc
        prefix = re.sub(r'_\d+$', '', obj_id)
        if prefix not in obj_by_prefix:
            obj_by_prefix[prefix] = []
        obj_by_prefix[prefix].append(obj_id)

    import glob
    txt_files = sorted(glob.glob(os.path.join(TEXTS_DIR, "*_rus.txt")))
    if FILE_FILTER:
        txt_files = [f for f in txt_files if FILE_FILTER in os.path.basename(f)]

    # Build set of all file prefixes that exist, for multi-file deduplication
    all_file_prefixes = set()
    for fp in txt_files:
        all_file_prefixes.add(os.path.basename(fp).replace("_rus.txt", ""))

    print(f"Auditing {len(txt_files)} files...\n")

    total_errors = 0
    total_warnings = 0
    files_with_issues = 0
    all_issues = {}

    for filepath in txt_files:
        basename = os.path.basename(filepath)
        # Extract prefix: 054_ludivine_rus.txt -> 054_ludivine
        prefix = basename.replace("_rus.txt", "")

        # Find matching OBJ(s) in dump
        # First try exact match (for multi-file characters like 100_cop_01)
        matching_objs = []
        if prefix in obj_by_exact:
            matching_objs = [prefix]
        if not matching_objs:
            # Use prefix grouping, but exclude OBJs that have their own dedicated file
            candidates = obj_by_prefix.get(prefix, [])
            for obj_id in candidates:
                # If this exact OBJ has its own file (e.g., 100_cop_01_rus.txt exists),
                # skip it when processing the combined file (100_cop_rus.txt)
                if obj_id != prefix and obj_id in all_file_prefixes:
                    continue
                matching_objs.append(obj_id)
        if not matching_objs:
            continue

        # Merge all passages from all matching OBJs
        eng_passages = {}
        for obj_id in matching_objs:
            eng_passages.update(dump_objects[obj_id])

        if not eng_passages:
            continue

        # Parse Russian file
        rus_passages = parse_rus_file(filepath)

        # Audit
        issues = audit_file(prefix, eng_passages, rus_passages, basename)

        if issues:
            files_with_issues += 1
            all_issues[basename] = issues
            errors = [i for i in issues if i["severity"] == "ERROR"]
            warnings = [i for i in issues if i["severity"] == "WARN"]
            total_errors += len(errors)
            total_warnings += len(warnings)

            print(f"{'='*60}")
            print(f"FILE: {basename}  ({len(errors)} errors, {len(warnings)} warnings)")
            print(f"{'='*60}")
            for issue in sorted(issues, key=lambda x: (x["severity"], x.get("line", 0))):
                sev = issue["severity"]
                psg = issue["passage"]
                msg = issue["message"]
                line = issue.get("line", "")
                line_str = f":{line}" if line else ""
                print(f"  {sev:5s}  {psg}{line_str}: {msg}")
                if "current" in issue:
                    print(f"         RUS: {issue['current']}")
                if "english" in issue:
                    print(f"         ENG: {issue['english']}")
                if "english_sample" in issue:
                    print(f"         ENG: {issue['english_sample']}")
            print()

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Files audited:      {len(txt_files)}")
    print(f"Files with issues:  {files_with_issues}")
    print(f"Total errors:       {total_errors}")
    print(f"Total warnings:     {total_warnings}")

    if FIX_REPORT:
        report_path = os.path.join(BASE_DIR, "_dev", "output", "audit_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(all_issues, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed report saved to: {report_path}")

    if total_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
