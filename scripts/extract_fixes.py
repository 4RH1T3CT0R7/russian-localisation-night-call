#!/usr/bin/env python3
"""
Extract the correct English text for every error found by thorough_audit.
Produces a fix manifest: for each error, the file, line number, what's wrong,
and what the correct English text should be.

Output: _dev/output/fix_manifest.txt
Format: FILE|LINE|TYPE|CURRENT_RUS|CORRECT_ENG
"""
import os
import sys
import re
import json
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")
AUDIT_PATH = os.path.join(BASE_DIR, "_dev", "output", "thorough_audit.json")


def parse_dump(path):
    objects = {}
    cur_obj = None
    cur_p = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("OBJ "):
                cur_obj = line.split()[1]
                objects[cur_obj] = {}
            elif line.startswith("P "):
                parts = line.split()
                if len(parts) < 4:
                    continue
                pname = parts[1]
                cur_p = {"lines": [], "choices": []}
                if cur_obj:
                    objects[cur_obj][pname] = cur_p
            elif line.startswith("L ") and cur_p:
                cur_p["lines"].append(line[2:])
            elif line.startswith("C ") and cur_p:
                parts = line[2:].split("\t")
                if len(parts) == 2:
                    cur_p["choices"].append({"text": parts[0], "target": parts[1]})
    return objects


def parse_rus_file(filepath):
    passages = {}
    current = None
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")
        if line.startswith("=== "):
            name = line[4:].strip()
            current = {"content": [], "choices": []}
            passages[name] = current
        elif current and line.strip():
            if line.startswith("*"):
                current["choices"].append({"text": line, "line": i})
            else:
                current["content"].append({"text": line, "line": i})
    return passages


def is_cmd(t):
    s = t.strip()
    return s.startswith("$$") and s.endswith("$$")


def extract_choice_target(text):
    m = re.search(r'->\s*(\S+)\s*$', text)
    return m.group(1) if m else None


def main():
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    dump = parse_dump(DUMP_PATH)
    # Flatten dump: passage_name -> data (across all OBJs)
    all_passages = {}
    for obj_id, passages in dump.items():
        for pname, pdata in passages.items():
            all_passages[pname] = pdata

    # Build prefix -> OBJ mapping
    obj_by_prefix = defaultdict(list)
    for obj_id in dump:
        prefix = re.sub(r'_\d+$', '', obj_id)
        obj_by_prefix[prefix].append(obj_id)

    fixes = []
    stats = defaultdict(int)

    for filename, issues in audit.items():
        prefix = filename.replace("_rus.txt", "")
        filepath = os.path.join(TEXTS_DIR, filename)
        if not os.path.exists(filepath):
            continue

        rus_passages = parse_rus_file(filepath)

        for issue in issues:
            if issue["severity"] != "ERROR":
                continue

            itype = issue["type"]
            pname = issue.get("passage", "")
            line_num = issue.get("line", 0)
            eng_p = all_passages.get(pname)

            if not eng_p:
                continue

            if itype == "CHOICE_WRONG_TEXT":
                # Find which choice index this is
                if pname not in rus_passages:
                    continue
                rus_p = rus_passages[pname]
                choice_idx = None
                for ci, rc in enumerate(rus_p["choices"]):
                    if rc["line"] == line_num:
                        choice_idx = ci
                        break
                if choice_idx is None:
                    continue
                if choice_idx >= len(eng_p["choices"]):
                    continue

                eng_choice = eng_p["choices"][choice_idx]
                rus_choice = rus_p["choices"][choice_idx]
                rus_target = extract_choice_target(rus_choice["text"])
                eng_target = eng_choice["target"]

                fixes.append({
                    "file": filename,
                    "line": line_num,
                    "type": "CHOICE",
                    "current": rus_choice["text"].strip(),
                    "eng_text": eng_choice["text"],
                    "eng_target": eng_target,
                    "rus_target": rus_target,
                    "passage": pname,
                })
                stats["CHOICE"] += 1

            elif itype == "GARBAGE_LINE":
                # Find what English line should be at this position
                if pname not in rus_passages:
                    continue
                rus_p = rus_passages[pname]

                # Find position of this garbage line within content
                garbage_idx = None
                for ci, cl in enumerate(rus_p["content"]):
                    if cl["line"] == line_num:
                        garbage_idx = ci
                        break
                if garbage_idx is None:
                    continue

                # Count non-command content lines before this one in Russian
                text_idx = 0
                for ci in range(garbage_idx):
                    t = rus_p["content"][ci]["text"]
                    if not is_cmd(t) and "?" not in t or ";;" not in t:
                        text_idx += 1

                # Find corresponding English text line
                eng_text_lines = [l for l in eng_p["lines"] if not is_cmd(l)]
                # The garbage line is at text_idx position
                eng_line = ""
                if text_idx < len(eng_text_lines):
                    eng_line = eng_text_lines[text_idx]
                elif eng_text_lines:
                    eng_line = eng_text_lines[0]  # fallback to first

                current_text = ""
                for cl in rus_p["content"]:
                    if cl["line"] == line_num:
                        current_text = cl["text"].strip()
                        break

                fixes.append({
                    "file": filename,
                    "line": line_num,
                    "type": "GARBAGE",
                    "current": current_text,
                    "eng_text": eng_line,
                    "passage": pname,
                    "text_idx": text_idx,
                })
                stats["GARBAGE"] += 1

            elif itype == "CHOICE_WRONG_TARGET":
                if pname not in rus_passages:
                    continue
                rus_p = rus_passages[pname]
                choice_idx = None
                for ci, rc in enumerate(rus_p["choices"]):
                    if rc["line"] == line_num:
                        choice_idx = ci
                        break
                if choice_idx is None or choice_idx >= len(eng_p["choices"]):
                    continue

                eng_choice = eng_p["choices"][choice_idx]
                rus_choice = rus_p["choices"][choice_idx]

                fixes.append({
                    "file": filename,
                    "line": line_num,
                    "type": "TARGET",
                    "current": rus_choice["text"].strip(),
                    "eng_text": eng_choice["text"],
                    "eng_target": eng_choice["target"],
                    "passage": pname,
                })
                stats["TARGET"] += 1

            elif itype == "EMPTY_PASSAGE":
                eng_text_lines = [l for l in eng_p["lines"] if not is_cmd(l)]
                fixes.append({
                    "file": filename,
                    "line": 0,
                    "type": "EMPTY",
                    "current": "",
                    "eng_text": " | ".join(eng_text_lines[:3]),
                    "passage": pname,
                })
                stats["EMPTY"] += 1

    # Write manifest
    out_path = os.path.join(BASE_DIR, "_dev", "output", "fix_manifest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixes, f, ensure_ascii=False, indent=2)

    print(f"Fix manifest: {len(fixes)} fixes")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"Saved to: {out_path}")

    # Also write a simpler text file for translation
    txt_path = os.path.join(BASE_DIR, "_dev", "output", "to_translate.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for fix in fixes:
            if fix["type"] == "CHOICE":
                f.write(f"CHOICE|{fix['file']}|{fix['line']}|{fix['passage']}|{fix['eng_text']}|{fix.get('eng_target','')}\n")
            elif fix["type"] == "GARBAGE":
                f.write(f"GARBAGE|{fix['file']}|{fix['line']}|{fix['passage']}|{fix['eng_text']}\n")
            elif fix["type"] == "TARGET":
                f.write(f"TARGET|{fix['file']}|{fix['line']}|{fix['passage']}|{fix['eng_text']}|{fix['eng_target']}\n")
            elif fix["type"] == "EMPTY":
                f.write(f"EMPTY|{fix['file']}|{fix['line']}|{fix['passage']}|{fix['eng_text']}\n")
    print(f"Translation file: {txt_path}")


if __name__ == "__main__":
    main()
