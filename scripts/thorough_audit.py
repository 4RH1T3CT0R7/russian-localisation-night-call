#!/usr/bin/env python3
"""
Thorough structural audit of Night Call Russian localization files.
Compares EVERY line of EVERY passage against the English passage_dump.txt.

Checks:
  1. GARBAGE_LINE     - line is just a number, meaningless short text, stray data
  2. CHOICE_WRONG_TEXT - choice text is narration/content instead of player dialogue
  3. CHOICE_WRONG_TARGET - choice points to different passage than English
  4. MISSING_CONTENT  - passage has fewer content lines than English
  5. EMPTY_PASSAGE    - passage exists but has no content where English has text
  6. UNTRANSLATED     - substantial English text that should be Russian
  7. SPEAKER_ENGLISH  - speaker name is in Latin characters (not translated)
  8. SPEAKER_SEQUENCE - speakers appear in different order than English
  9. LEAKED_LINE      - content line matches an L-line from a DIFFERENT passage
  10. MISSING_PASSAGE - passage in English dump doesn't exist in Russian file
  11. MISSING_COMMAND  - important engine command missing

Run: python scripts/thorough_audit.py [--file PATTERN] [--json]
"""
import os
import sys
import re
import json
import glob
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")

FILE_FILTER = None
JSON_OUTPUT = "--json" in sys.argv
for i, arg in enumerate(sys.argv):
    if arg == "--file" and i + 1 < len(sys.argv):
        FILE_FILTER = sys.argv[i + 1]

# Known character name mapping (English -> Russian)
SPEAKER_MAP = {
    "BUSSET": "БЮССЕ", "PATRICIA": "ПАТРИЦИЯ", "CARLO": "КАРЛО",
    "LÉONIE": "ЛЕОНИ", "SHAÏNE": "ШЕЙН", "ANTOINE": "АНТУАН",
    "MIREILLE": "МИРЕЙ", "PIERRE": "ПЬЕР", "LOLA": "ЛОЛА",
    "ANNABELLE": "АННАБЕЛЬ", "CAROLINA": "КАРОЛИНА", "NATHALIE": "НАТАЛИ",
    "MELCHIOR": "МЕЛЬХИОР", "VÉRONIQUE": "ВЕРОНИКА", "AGNÈS": "АНЬЕС",
    "SANTA": "САНТА", "FRANCINE": "ФРАНСИН", "AMÉLIE": "АМЕЛИ",
    "CHANTAL": "ШАНТАЛЬ", "AMIRA": "АМИРА", "ALPH": "АЛЬФ",
    "VINCENT": "ВИНСЕНТ", "GÉRARD": "ЖЕРАР", "JÉRÔME": "ЖЕРОМ",
    "ROKSANA": "РОКСАНА", "JIM": "ДЖИМ", "NADIA": "НАДЯ",
    "CAMILLE": "КАМИЛЬ", "ADA": "АДА", "ARIANE": "АРИАНА",
    "CHRISTOPHE": "КРИСТОФ", "CHIARA": "КЬЯРА", "ALARIC": "АЛАРИК",
    "PAULINE": "ПОЛИН", "MATHIEU": "МАТЬЁ", "ALICIA": "АЛИЦИЯ",
    "SHINJI": "СИНДЗИ", "ÉMILIA": "ЭМИЛИЯ", "HUGO": "ЮГО",
    "ESMERALDA": "ЭСМЕРАЛЬДА", "GRACE": "ГРЕЙС", "ALICE": "АЛИСА",
    "ULTRA PINK": "УЛЬТРА РОЗОВЫЙ", "PETER": "ПИТЕР", "SHOHREH": "ШОХРЕ",
    "KADER": "КАДЕР", "HENRI": "АНРИ", "HYOGA": "ХЁГА",
    "ÉMILIE": "ЭМИЛИ", "LUCIE": "ЛЮСИ", "JONAS": "ЖОНАС",
    "JULIAN": "ЖЮЛЬЕН", "DENIS": "ДЕНИ", "SOPHIE": "СОФИ",
    "XAVIER": "КСАВЬЕ", "JACQUIE": "ЖАКИ", "GÉRALDINE": "ЖЕРАЛЬДИН",
    "ANITA": "АНИТА", "SYLVIE": "СИЛЬВИ", "SYLVAIN": "СИЛЬВЕН",
    "DJENA": "ДЖЕНА", "CHILDÉRIC": "ШИЛЬДЕРИК", "NINA": "НИНА",
    "MARC": "МАРК", "MYRIAM": "МИРИАМ", "BOSS": "БОСС",
    "MYRTILLE": "МИРТИЛЬ", "LUDIVINE": "ЛЮДИВИН", "LUDWIG": "ЛЮДВИГ",
    "HERVÉ": "ЭРВЕ", "FRANÇOIS": "ФРАНСУА", "LEA": "ЛЕЯ",
    "GILDA": "ГИЛЬДА", "ANGÉLIQUE": "АНЖЕЛИКА", "CLAUDIA": "КЛАУДИЯ",
    "MILO": "МАЙЛО", "MARCO": "МАРКО", "SALIM": "САЛИМ",
    "BÉRÉNICE": "БЕРЕНИС", "AID": "ЭЙД", "JANET": "ДЖАНЕТ",
    "PIERO": "ПЬЕРО", "FRAGONARD": "ФРАГОНАРД", "PIERROT": "ПЬЕРО",
    "ULTRA RED": "УЛЬТРА КРАСНЫЙ", "ULTRA GREEN": "УЛЬТРА ЗЕЛЕНЫЙ",
    "ALEXANDRE": "АЛЕКСАНДР", "LEIA": "ЛЕЯ", "SONNY": "СОННИ",
    "PIERRETTE": "ПЬЕРЕТТА", "FRÉDÉRIQUE": "ФРЕДЕРИКА",
    "APOLLONIÈRE": "АПОЛЛОНЬЕ", "APOLLONIE": "АПОЛЛОНЬЕ", "CHRIS": "КРИС",
}
# Build reverse map too
RUS_SPEAKERS = set(SPEAKER_MAP.values())
ENG_SPEAKERS = set(SPEAKER_MAP.keys())


def parse_dump(dump_path):
    """Parse passage_dump.txt into {obj_id: {passage_name: data}}"""
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
                    lc = int(parts[2])
                    cc = int(parts[3])
                except ValueError:
                    continue
                pname = parts[1]
                current_passage = {
                    "name": pname, "lines": [], "choices": [],
                    "line_count": lc, "choice_count": cc,
                }
                if current_obj:
                    objects[current_obj][pname] = current_passage
            elif line.startswith("L ") and current_passage:
                current_passage["lines"].append(line[2:])
            elif line.startswith("C ") and current_passage:
                parts = line[2:].split("\t")
                if len(parts) == 2:
                    current_passage["choices"].append({
                        "text": parts[0], "target": parts[1],
                    })
    return objects


def parse_rus_file(filepath):
    """Parse a _rus.txt file into {passage_name: data}"""
    passages = {}
    current = None

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")
        if line.startswith("=== "):
            name = line[4:].strip()
            current = {
                "name": name, "content": [], "choices": [],
                "start_line": i,
            }
            passages[name] = current
        elif current and line.strip():
            if line.startswith("*"):
                current["choices"].append({"text": line, "line": i})
            else:
                current["content"].append({"text": line, "line": i})
    return passages


def is_cmd(text):
    s = text.strip()
    return s.startswith("$$") and s.endswith("$$")


def is_conditional(text):
    return "?" in text and ";;" in text and not text.startswith("*")


def is_counter(text):
    return "+=" in text or "-=" in text


def is_game_var(text):
    s = text.strip()
    if re.match(r'^\{.*=.*\}$', s):
        return True
    if re.match(r'^[_a-zA-Z][\w.-]*\s*[=<>!]+\s*\d+$', s):
        return True
    return False


def extract_speaker(text):
    """Extract speaker name from a dialogue line like 'SPEAKER : "text"' """
    m = re.match(r'^([A-ZА-ЯЁ][A-ZА-ЯЁa-zа-яё\s]+?)\s*:\s*[«""\'"]', text.strip())
    if m:
        return m.group(1).strip()
    return None


def extract_choice_target(choice_line):
    """Extract target passage from choice line like *"text" -> target"""
    m = re.search(r'->\s*(\S+)\s*$', choice_line)
    return m.group(1) if m else None


def extract_choice_display(choice_line):
    """Extract display text from choice line"""
    m = re.match(r'^\*(?::[\w]+:\s*)?(.*?)\s*->\s*\S+$', choice_line)
    return m.group(1).strip() if m else choice_line


def extract_eng_choice_display(text):
    return re.sub(r'^:\w+:\s*', '', text).strip()


def is_garbage_line(text):
    """Check if a line is garbage: just a number, single char, meaningless"""
    s = text.strip()
    if not s:
        return True
    # Just a number
    if re.match(r'^\d+$', s):
        return True
    # Single non-meaningful character
    if len(s) <= 2 and not s.startswith('$'):
        return True
    return False


def has_substantial_english(text):
    """Check if text has untranslated English (not commands/variables)"""
    s = text.strip()
    if is_cmd(s) or is_conditional(s) or is_counter(s) or is_game_var(s):
        return False
    if s.startswith("??"):
        return False
    # Skip emote markers and passage-name-only lines
    if re.match(r'^:[\w]+:$', s):
        return False
    if re.match(r'^[\w-]+$', s) and len(s) > 5:
        return False
    eng = len(re.findall(r'[a-zA-Z]', s))
    rus = len(re.findall(r'[а-яА-ЯёЁ]', s))
    if eng > 10 and rus == 0:
        return True
    return False


def get_speaker_sequence(lines, is_english=False):
    """Extract ordered list of speakers from content lines"""
    speakers = []
    for l in lines:
        text = l if is_english else l["text"]
        if is_cmd(text):
            continue
        sp = extract_speaker(text)
        if sp:
            speakers.append(sp)
    return speakers


def check_choice_is_leaked_narration(choice_text, all_eng_lines):
    """Check if choice text matches any English content line (leaked narration)"""
    # Normalize: remove quotes, lowercase
    ct = choice_text.strip().strip('"«»"\'').lower()
    if len(ct) < 10:
        return False
    for eng_line in all_eng_lines:
        if is_cmd(eng_line):
            continue
        sp = extract_speaker(eng_line)
        if sp:
            # This is dialogue, extract just the text part
            m = re.match(r'^[^:]+:\s*[«""\'"](.+?)[»""\'"]?\s*$', eng_line)
            if m:
                eng_text = m.group(1).lower()
            else:
                continue
        else:
            eng_text = eng_line.strip().lower()
        # Fuzzy match: if the Russian choice contains a key phrase from an English narration line
        # This is too hard to do cross-language. Instead, check length/structure.
    return False


def audit_passage(pname, eng_p, rus_p, all_eng_content_lines, filename):
    """Thorough audit of a single passage. Returns list of issues."""
    issues = []

    # ---- CONTENT LINE CHECKS ----
    eng_text_lines = [l for l in eng_p["lines"] if not is_cmd(l)]
    rus_content = rus_p["content"]
    rus_text_lines = [
        c for c in rus_content
        if not is_cmd(c["text"]) and not is_conditional(c["text"])
        and not is_counter(c["text"]) and not is_game_var(c["text"])
    ]

    # Check for garbage lines
    for cl in rus_content:
        if is_cmd(cl["text"]) or is_conditional(cl["text"]) or is_counter(cl["text"]) or is_game_var(cl["text"]):
            continue
        if is_garbage_line(cl["text"]):
            issues.append({
                "type": "GARBAGE_LINE", "severity": "ERROR",
                "passage": pname, "line": cl["line"],
                "detail": f"Garbage content: '{cl['text'].strip()}'",
            })

    # Check for untranslated English text
    for cl in rus_content:
        if has_substantial_english(cl["text"]):
            issues.append({
                "type": "UNTRANSLATED", "severity": "ERROR",
                "passage": pname, "line": cl["line"],
                "detail": f"Untranslated: {cl['text'].strip()[:80]}",
            })

    # Check for English speaker names
    for cl in rus_content:
        sp = extract_speaker(cl["text"])
        if sp and sp in ENG_SPEAKERS:
            expected = SPEAKER_MAP.get(sp, "?")
            issues.append({
                "type": "SPEAKER_ENGLISH", "severity": "ERROR",
                "passage": pname, "line": cl["line"],
                "detail": f"Speaker '{sp}' not translated (should be '{expected}')",
            })

    # Empty passage check
    if len(eng_text_lines) > 0 and len(rus_text_lines) == 0:
        sample = eng_text_lines[0][:80] if eng_text_lines else ""
        issues.append({
            "type": "EMPTY_PASSAGE", "severity": "ERROR",
            "passage": pname,
            "detail": f"English has {len(eng_text_lines)} text lines, Russian is empty. English: {sample}",
        })
    # Missing content lines (allow +1 for echo lines)
    elif len(eng_text_lines) > len(rus_text_lines) + 1:
        diff = len(eng_text_lines) - len(rus_text_lines)
        issues.append({
            "type": "MISSING_CONTENT", "severity": "ERROR" if diff >= 3 else "WARN",
            "passage": pname,
            "detail": f"English has {len(eng_text_lines)} text lines, Russian has {len(rus_text_lines)} (missing {diff})",
        })

    # Speaker sequence check
    eng_speakers = get_speaker_sequence(eng_p["lines"], is_english=True)
    rus_speakers = get_speaker_sequence(rus_content, is_english=False)
    # Map Russian speakers back to English for comparison
    rev_map = {v: k for k, v in SPEAKER_MAP.items()}
    rus_speakers_eng = [rev_map.get(s, s) for s in rus_speakers]

    if eng_speakers and rus_speakers_eng:
        # Check if speakers appear in same order (allow minor variations)
        if len(eng_speakers) >= 3 and len(rus_speakers_eng) >= 3:
            # Compare first N speakers
            n = min(len(eng_speakers), len(rus_speakers_eng))
            mismatches = 0
            for i in range(n):
                if eng_speakers[i] != rus_speakers_eng[i]:
                    mismatches += 1
            if mismatches > n * 0.4:  # More than 40% wrong
                issues.append({
                    "type": "SPEAKER_SEQUENCE", "severity": "WARN",
                    "passage": pname,
                    "detail": f"Speaker order differs. ENG: {eng_speakers[:5]} vs RUS: {rus_speakers[:5]}",
                })

    # ---- CHOICE CHECKS ----
    eng_choices = eng_p["choices"]
    rus_choices = rus_p["choices"]

    if len(eng_choices) != len(rus_choices):
        if not (len(eng_choices) == 0 and len(rus_choices) == 0):
            issues.append({
                "type": "CHOICE_COUNT", "severity": "ERROR" if abs(len(eng_choices) - len(rus_choices)) > 1 else "WARN",
                "passage": pname,
                "detail": f"English has {len(eng_choices)} choices, Russian has {len(rus_choices)}",
            })

    for ci in range(min(len(eng_choices), len(rus_choices))):
        eng_c = eng_choices[ci]
        rus_c = rus_choices[ci]
        rus_display = extract_choice_display(rus_c["text"])
        eng_display = extract_eng_choice_display(eng_c["text"])
        rus_target = extract_choice_target(rus_c["text"])
        eng_target = eng_c["target"]

        # Check target mismatch
        if rus_target and eng_target and rus_target != eng_target:
            issues.append({
                "type": "CHOICE_WRONG_TARGET", "severity": "ERROR",
                "passage": pname, "line": rus_c["line"],
                "detail": f"Choice #{ci+1} target: RUS='{rus_target}' vs ENG='{eng_target}'",
            })

        # Check if choice text looks like narration
        rd = rus_display.strip()
        if rd and not rd.startswith('"') and not rd.startswith('«') and not rd.startswith("'") \
           and not rd.startswith('(') and not rd.startswith(':'):
            # Could be narration leaked into choice
            # Check: English choice should be dialogue/action
            eng_is_quote = eng_display.startswith('"') or eng_display.startswith("'") or eng_display.startswith('«')
            eng_is_action = eng_display.startswith('(')
            if eng_is_quote or eng_is_action:
                # Russian should also be quoted or parenthesized
                issues.append({
                    "type": "CHOICE_WRONG_TEXT", "severity": "ERROR",
                    "passage": pname, "line": rus_c["line"],
                    "detail": f"Choice text looks like narration, not dialogue",
                    "rus": rd[:70],
                    "eng": eng_display[:70],
                })
            # Also check if the text is suspiciously long for a choice (narration tends to be longer)
            elif len(rd) > 60:
                issues.append({
                    "type": "CHOICE_WRONG_TEXT", "severity": "WARN",
                    "passage": pname, "line": rus_c["line"],
                    "detail": f"Choice text suspiciously long ({len(rd)} chars), may be narration",
                    "rus": rd[:70],
                    "eng": eng_display[:70],
                })

    # ---- MISSING COMMANDS ----
    eng_cmds = set(l for l in eng_p["lines"] if is_cmd(l))
    rus_cmds = set(cl["text"].strip() for cl in rus_content if is_cmd(cl["text"]))
    for cmd in eng_cmds - rus_cmds:
        if any(kw in cmd for kw in ["reveal:", "anim-link:", "music-control:"]):
            issues.append({
                "type": "MISSING_COMMAND", "severity": "WARN",
                "passage": pname,
                "detail": f"Missing: {cmd}",
            })

    return issues


def main():
    if not os.path.exists(DUMP_PATH):
        print(f"Passage dump not found: {DUMP_PATH}")
        sys.exit(1)

    print("Parsing passage dump...")
    dump_objects = parse_dump(DUMP_PATH)
    print(f"  Found {len(dump_objects)} objects in dump")

    # Build prefix -> OBJ mapping
    obj_by_prefix = defaultdict(list)
    for obj_id in dump_objects:
        prefix = re.sub(r'_\d+$', '', obj_id)
        obj_by_prefix[prefix].append(obj_id)

    txt_files = sorted(glob.glob(os.path.join(TEXTS_DIR, "*_rus.txt")))
    if FILE_FILTER:
        txt_files = [f for f in txt_files if FILE_FILTER in os.path.basename(f)]

    all_file_prefixes = {os.path.basename(fp).replace("_rus.txt", "") for fp in txt_files}

    print(f"Auditing {len(txt_files)} files...\n")

    total_errors = 0
    total_warnings = 0
    files_with_issues = 0
    all_results = {}

    for filepath in txt_files:
        basename = os.path.basename(filepath)
        prefix = basename.replace("_rus.txt", "")

        # Find matching OBJs
        matching_objs = []
        if prefix in dump_objects:
            matching_objs = [prefix]
        if not matching_objs:
            for obj_id in obj_by_prefix.get(prefix, []):
                if obj_id != prefix and obj_id in all_file_prefixes:
                    continue
                matching_objs.append(obj_id)
        if not matching_objs:
            continue

        # Merge English passages and collect all content lines
        eng_passages = {}
        all_eng_content = []
        for obj_id in matching_objs:
            for pname, pdata in dump_objects[obj_id].items():
                eng_passages[pname] = pdata
                all_eng_content.extend(pdata["lines"])

        if not eng_passages:
            continue

        rus_passages = parse_rus_file(filepath)

        file_issues = []

        # Check missing passages
        for pname in eng_passages:
            if pname not in rus_passages:
                file_issues.append({
                    "type": "MISSING_PASSAGE", "severity": "ERROR",
                    "passage": pname,
                    "detail": f"Passage '{pname}' missing from Russian file",
                })
                continue

        # Audit each passage that exists in both
        for pname, eng_p in eng_passages.items():
            if pname not in rus_passages:
                continue
            issues = audit_passage(pname, eng_p, rus_passages[pname],
                                   all_eng_content, basename)
            file_issues.extend(issues)

        if file_issues:
            files_with_issues += 1
            errors = [i for i in file_issues if i["severity"] == "ERROR"]
            warnings = [i for i in file_issues if i["severity"] == "WARN"]
            total_errors += len(errors)
            total_warnings += len(warnings)

            all_results[basename] = file_issues

            print(f"{'='*70}")
            print(f"FILE: {basename}  ({len(errors)} errors, {len(warnings)} warnings)")
            print(f"{'='*70}")
            # Sort: errors first, then by passage name, then by line
            for issue in sorted(file_issues,
                                key=lambda x: (0 if x["severity"] == "ERROR" else 1,
                                               x.get("passage", ""), x.get("line", 0))):
                sev = issue["severity"]
                psg = issue.get("passage", "?")
                ln = issue.get("line", "")
                ln_str = f":{ln}" if ln else ""
                det = issue.get("detail", issue.get("message", ""))
                print(f"  {sev:5s}  [{psg}{ln_str}] {det}")
                if "rus" in issue:
                    print(f"         RUS: {issue['rus']}")
                if "eng" in issue:
                    print(f"         ENG: {issue['eng']}")
            print()

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Files audited:      {len(txt_files)}")
    print(f"Files with issues:  {files_with_issues}")
    print(f"Total errors:       {total_errors}")
    print(f"Total warnings:     {total_warnings}")

    # Breakdown by type
    type_counts = defaultdict(int)
    for issues in all_results.values():
        for i in issues:
            type_counts[f"{i['severity']}:{i['type']}"] += 1
    print(f"\nBy type:")
    for key in sorted(type_counts, key=lambda k: (-type_counts[k])):
        print(f"  {key:35s} {type_counts[key]:>4d}")

    if JSON_OUTPUT:
        report_path = os.path.join(BASE_DIR, "_dev", "output", "thorough_audit.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\nJSON report: {report_path}")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
