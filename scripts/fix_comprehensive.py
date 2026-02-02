#!/usr/bin/env python3
"""
fix_comprehensive.py - Fix all remaining issues in Russian localization files.

Phase 1: Remove duplicate content lines (adjacent lines that are translations of the same English line)
Phase 2: Fix specific wrong choice texts (narration text appearing as player choices)
Phase 3: Restore missing engine commands from English reference
Phase 4: Fix structural issues (content lines appearing after choices)
Phase 5: Remove duplicate routing lines
"""

import os
import sys
import re
import shutil
from difflib import SequenceMatcher

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS_DIR = os.path.join(BASE_DIR, "data", "Russian_Texts")
DUMP_PATH = os.path.join(BASE_DIR, "_dev", "reference", "passage_dump.txt")
GAME_DIR = r"F:\SteamLibrary\steamapps\common\Night Call\Russian_Texts"


# ─── Parsing helpers ───────────────────────────────────────────────

def parse_dump(path):
    """Parse passage_dump.txt → {passage_name: {lines: [...], choices: [{text, target}]}}"""
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
    # Flatten across all OBJs
    all_p = {}
    for obj_id, passages in objects.items():
        for pname, pdata in passages.items():
            all_p[pname] = pdata
    return all_p


def norm(s):
    """Normalize text for comparison: strip quotes, normalize whitespace."""
    s = s.strip()
    for old, new in [('\u2018', "'"), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"'),
                     ('\u2013', '-'), ('\u2014', '-'), ('\u00ab', '"'), ('\u00bb', '"'),
                     ('\u2026', '...'), ('\xa0', ' ')]:
        s = s.replace(old, new)
    s = s.replace('«', '"').replace('»', '"')
    s = re.sub(r'["\']', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()


def extract_speaker(line):
    """Extract speaker name from dialogue line. Returns (speaker, rest) or (None, line)."""
    m = re.match(r'^([A-ZА-ЯЁ][A-ZА-ЯЁa-zа-яё\s\-]*?)\s*:\s*(.+)$', line.strip())
    if m:
        return m.group(1).strip().upper(), m.group(2).strip()
    return None, line.strip()


def is_cmd(line):
    s = line.strip()
    return s.startswith('$$') and s.endswith('$$') and len(s) > 4


def is_choice(line):
    return line.strip().startswith('*')


def is_routing(line):
    s = line.strip()
    if not s or s.startswith('*') or s.startswith('$$') or s.startswith('==='):
        return False
    # Pattern: something=value?target;;...
    if re.match(r'^[\w._-]+=\d+\?', s):
        return True
    if '?' in s and ';;' in s:
        return True
    return False


def is_var_assign(line):
    s = line.strip()
    return bool(re.match(r'^[\w.-]+(=|\+=)\d+$', s))


def is_passage_header(line):
    return line.strip().startswith('=== ')


def is_structural(line):
    """Return True if line is NOT regular content text."""
    s = line.strip()
    if not s:
        return True
    return is_cmd(s) or is_choice(s) or is_routing(s) or is_var_assign(s) or is_passage_header(s)


def text_similarity(s1, s2):
    """Normalized similarity between two strings."""
    n1, n2 = norm(s1), norm(s2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    return SequenceMatcher(None, n1, n2).ratio()


# ─── Phase 1: Duplicate content line removal ──────────────────────

def remove_duplicates_in_passage(content_lines, eng_content_count):
    """
    Given a list of content lines (text only, no commands/choices/routing),
    remove duplicates. Returns cleaned list.

    A duplicate is detected when:
    - Two lines have >70% normalized similarity
    - Same or compatible speaker
    """
    if len(content_lines) <= eng_content_count:
        return content_lines  # No extras, don't remove anything

    # Try to find and remove duplicates
    # Mark lines for removal
    to_remove = set()

    # Check all pairs (not just adjacent) within the passage
    for i in range(len(content_lines)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(content_lines)):
            if j in to_remove:
                continue

            si = content_lines[i].strip()
            sj = content_lines[j].strip()

            spk_i, text_i = extract_speaker(si)
            spk_j, text_j = extract_speaker(sj)

            # Same speaker (or both narration)?
            same_spk = (spk_i == spk_j) or (spk_i is None and spk_j is None)
            if not same_spk:
                continue

            sim = text_similarity(text_i, text_j)
            if sim > 0.70:
                # Remove the one with older formatting (straight quotes vs guillemets)
                has_guillemets_i = '«' in si or '»' in si
                has_guillemets_j = '«' in sj or '»' in sj

                if has_guillemets_j and not has_guillemets_i:
                    to_remove.add(i)  # Remove older format
                elif has_guillemets_i and not has_guillemets_j:
                    to_remove.add(j)  # Remove older format
                else:
                    # Both same format, remove the first (keep later)
                    to_remove.add(i)

                # Stop if we've removed enough
                if len(content_lines) - len(to_remove) <= eng_content_count:
                    break
        if len(content_lines) - len(to_remove) <= eng_content_count:
            break

    return [l for idx, l in enumerate(content_lines) if idx not in to_remove]


# ─── Phase 2: Wrong choice fixes ─────────────────────────────────

# Hardcoded choice fixes: {filename: {old_choice_text: new_choice_text}}
# These are choices where narration/dialogue was placed instead of player choice text
CHOICE_FIXES = {
    "051_leonie_rus.txt": {
        '*"Хммм... -> leonie-01-question-music-rock':
            '*«Рок?» -> leonie-01-question-music-rock',
        '*На мгновение она замолкает. -> leonie-01-question-music-africa':
            '*«Африканскую?» -> leonie-01-question-music-africa',
        '*:radio: "Да... Я в порядке, спасибо". -> leonie-01-question-music':
            '*:radio: «Хотите музыку?» -> leonie-01-question-music',
        '*"Да, это так. Спасибо. -> leonie-01-silence2-stopworking':
            '*«Иногда нужно отдыхать от работы.» -> leonie-01-silence2-stopworking',
        "*'Ah!' -> leonie-01-thesis-surprise":
            '*«А!» -> leonie-01-thesis-surprise',
        '*"...остальная Европа... -> leonie-01-thesis-precise':
            '*«Звучит очень специфично.» -> leonie-01-thesis-precise',
        "*:smile: 'Ты не должен говорить такие вещи...' -> leonie-01-thesis4-dontsay":
            '*:smile: «Не стоит так говорить…» -> leonie-01-thesis4-dontsay',
        '*"А что, если ты попробуешь что-то новое?" -> leonie-01-thesis4-somethingelse':
            '*«А если попробовать что-то новое?» -> leonie-01-thesis4-somethingelse',
        '*Микс подходит к концу. Перед рекламной паузой радиоведущий объявляет название группы. -> leonie-01-thesis4-people':
            '*«Что думают ваши друзья?» -> leonie-01-thesis4-people',
        '*"Мне двадцать восемь. Я пишу докторскую диссертацию о монахинях XVIII века". -> leonie-01-job-service':
            '*«Это услуга, как и любая другая.» -> leonie-01-job-service',
    },
}


# ─── Phase 4: Structural fixes ───────────────────────────────────

# Passages where content lines appear AFTER choices and need to be moved before
STRUCTURAL_FIXES = {
    "051_leonie_rus.txt": {
        "leonie-01-thesis3": {
            "action": "rewrite",
            "new_content": [
                "",
                'ЛЕОНИ : «Так и бывает. Я привыкла к диссертации… к теме…»',
                'ЛЕОНИ : «Докторские диссертации редко бывают интересными, знаете ли.»',
                'ЛЕОНИ : «Но моя… Кажется, я достигла дна…»',
                '*:smile: «Не стоит так говорить…» -> leonie-01-thesis3-dontsay',
                '*«Уверен, это интересно.» -> leonie-01-thesis3-interesting',
                '*«Полезная тема, не так ли?» -> leonie-01-thesis3-interesting',
                '*:silence: (Ничего не говорить.) -> leonie-01-thesis3-silence',
            ],
        },
    },
}


# ─── Main processing ─────────────────────────────────────────────

def parse_passages(lines):
    """Parse file lines into passages. Returns list of {name, start_idx, end_idx}."""
    passages = []
    current = None
    for i, raw in enumerate(lines):
        line = raw.rstrip('\n').rstrip('\r')
        if line.startswith('=== '):
            if current:
                current['end_idx'] = i
                passages.append(current)
            name = line[4:].strip()
            current = {'name': name, 'start_idx': i}
    if current:
        current['end_idx'] = len(lines)
        passages.append(current)
    return passages


def process_file(filepath, filename, all_passages):
    """Process a single file. Returns (new_lines, stats_dict)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    stats = {
        'duplicates_removed': 0,
        'choices_fixed': 0,
        'commands_restored': 0,
        'structural_fixes': 0,
        'routing_dedup': 0,
    }

    # ── Phase 2: Apply hardcoded choice fixes ──
    if filename in CHOICE_FIXES:
        fixes = CHOICE_FIXES[filename]
        for i, raw in enumerate(lines):
            line = raw.rstrip('\n').rstrip('\r')
            s = line.strip()
            if s in fixes:
                lines[i] = fixes[s] + '\n'
                stats['choices_fixed'] += 1

    # ── Phase 4: Apply structural fixes (passage rewrites) ──
    if filename in STRUCTURAL_FIXES:
        passages = parse_passages(lines)
        for p in reversed(passages):  # Reverse to preserve indices
            pname = p['name']
            if pname in STRUCTURAL_FIXES[filename]:
                fix = STRUCTURAL_FIXES[filename][pname]
                if fix['action'] == 'rewrite':
                    # Find the end of this passage (next passage header or EOF)
                    start = p['start_idx']
                    end = p['end_idx']

                    # Build new passage
                    new_lines = ['=== ' + pname + '\n']
                    for cl in fix['new_content']:
                        new_lines.append(cl + '\n')
                    new_lines.append('\n')
                    new_lines.append('\n')

                    # Replace
                    lines[start:end] = new_lines
                    stats['structural_fixes'] += 1

    # ── Phase 5: Remove duplicate routing lines ──
    i = 0
    new_lines = []
    while i < len(lines):
        raw = lines[i]
        s = raw.rstrip('\n').rstrip('\r').strip()

        if is_routing(s) and i + 1 < len(lines):
            next_s = lines[i + 1].rstrip('\n').rstrip('\r').strip()
            if s == next_s:
                # Exact duplicate routing line, skip this one
                stats['routing_dedup'] += 1
                i += 1
                continue

        new_lines.append(raw)
        i += 1
    lines = new_lines

    # ── Phase 1: Remove duplicate content lines per passage ──
    passages = parse_passages(lines)

    # Process passages in reverse order to preserve line indices
    for p in reversed(passages):
        pname = p['name']
        start = p['start_idx'] + 1  # Skip the === header
        end = p['end_idx']

        # Get English reference for this passage
        eng_p = all_passages.get(pname)
        if not eng_p:
            continue

        eng_content_count = sum(1 for l in eng_p['lines'] if not is_cmd(l))

        # Classify lines in this passage
        passage_lines = lines[start:end]
        content_indices = []  # Indices relative to passage_lines
        content_texts = []

        for idx, raw in enumerate(passage_lines):
            s = raw.rstrip('\n').rstrip('\r').strip()
            if s and not is_structural(raw.rstrip('\n').rstrip('\r')):
                content_indices.append(idx)
                content_texts.append(s)

        if len(content_texts) <= eng_content_count:
            continue  # No extras

        # Find duplicates
        cleaned = remove_duplicates_in_passage(content_texts, eng_content_count)
        removed_texts = set()

        # Determine which original lines were removed
        cleaned_set = list(cleaned)  # Keep order
        temp = list(content_texts)
        indices_to_remove = []

        for ct_idx, ct in enumerate(content_texts):
            if ct in cleaned_set:
                cleaned_set.remove(ct)
            else:
                # This line was removed
                indices_to_remove.append(content_indices[ct_idx])

        if indices_to_remove:
            # Remove lines from passage (reverse order to preserve indices)
            for idx in sorted(indices_to_remove, reverse=True):
                abs_idx = start + idx
                if abs_idx < len(lines):
                    lines.pop(abs_idx)
                    stats['duplicates_removed'] += 1

    # ── Phase 3: Restore missing engine commands ──
    passages = parse_passages(lines)  # Re-parse after modifications

    for p in reversed(passages):
        pname = p['name']
        eng_p = all_passages.get(pname)
        if not eng_p:
            continue

        start = p['start_idx'] + 1
        end = p['end_idx']

        # Get existing commands in this passage
        existing_cmds = set()
        for idx in range(start, min(end, len(lines))):
            s = lines[idx].rstrip('\n').rstrip('\r').strip()
            if is_cmd(s):
                existing_cmds.add(s)

        # Get English commands
        eng_cmds = [l.strip() for l in eng_p['lines'] if is_cmd(l.strip())]

        # Find missing commands
        missing_cmds = [c for c in eng_cmds if c not in existing_cmds]

        if not missing_cmds:
            continue

        # For each missing command, find the right insertion position
        # Strategy: Insert at the same relative position as in English
        # Build English line type sequence: [('cmd', text), ('content', text), ...]
        eng_sequence = []
        for l in eng_p['lines']:
            ls = l.strip()
            if is_cmd(ls):
                eng_sequence.append(('cmd', ls))
            else:
                eng_sequence.append(('content', ls))

        # Build Russian line type sequence
        rus_items = []
        for idx in range(start, min(end, len(lines))):
            s = lines[idx].rstrip('\n').rstrip('\r').strip()
            if not s:
                rus_items.append(('empty', '', idx))
            elif is_cmd(s):
                rus_items.append(('cmd', s, idx))
            elif is_choice(s):
                rus_items.append(('choice', s, idx))
            elif is_routing(s):
                rus_items.append(('routing', s, idx))
            elif is_var_assign(s):
                rus_items.append(('var', s, idx))
            else:
                rus_items.append(('content', s, idx))

        # For each missing command, determine where it should go
        insertions = []  # [(absolute_line_index, command_text)]

        for mc in missing_cmds:
            # Find position of this command in English sequence
            eng_pos = None
            for ei, (etype, etext) in enumerate(eng_sequence):
                if etype == 'cmd' and etext == mc:
                    eng_pos = ei
                    break

            if eng_pos is None:
                continue

            # Count content lines before this command in English
            content_before = sum(1 for et, _ in eng_sequence[:eng_pos] if et == 'content')
            # Count commands before this command in English
            cmds_before = sum(1 for et, _ in eng_sequence[:eng_pos] if et == 'cmd')

            # In Russian, find the position after the Nth content line
            # (or after the Nth command, whichever gives a better position)
            content_count = 0
            insert_idx = start  # Default: right after header

            if content_before == 0 and cmds_before == 0:
                # Command is at the very start of the passage
                # Insert right after header, before any content
                for ri, (rtype, rtext, ridx) in enumerate(rus_items):
                    if rtype == 'empty':
                        continue
                    insert_idx = ridx
                    break
            else:
                # Find position after the Nth content line
                for ri, (rtype, rtext, ridx) in enumerate(rus_items):
                    if rtype == 'content':
                        content_count += 1
                        if content_count == content_before:
                            insert_idx = ridx + 1
                            break
                else:
                    # Couldn't find enough content lines; insert at end of passage
                    if rus_items:
                        # Find last non-empty, non-choice line
                        for ri in reversed(range(len(rus_items))):
                            if rus_items[ri][0] not in ('empty', 'choice'):
                                insert_idx = rus_items[ri][2] + 1
                                break

            insertions.append((insert_idx, mc))

        # Apply insertions in reverse order to preserve indices
        for ins_idx, cmd_text in sorted(insertions, reverse=True):
            lines.insert(ins_idx, cmd_text + '\n')
            stats['commands_restored'] += 1

    return lines, stats


def main():
    print("Loading English reference dump...")
    all_passages = parse_dump(DUMP_PATH)
    print(f"  Loaded {len(all_passages)} passages")

    total_stats = {
        'duplicates_removed': 0,
        'choices_fixed': 0,
        'commands_restored': 0,
        'structural_fixes': 0,
        'routing_dedup': 0,
    }
    files_modified = 0

    filenames = sorted(f for f in os.listdir(TEXTS_DIR) if f.endswith('_rus.txt'))
    print(f"Processing {len(filenames)} files...")

    for filename in filenames:
        filepath = os.path.join(TEXTS_DIR, filename)
        new_lines, stats = process_file(filepath, filename, all_passages)

        total_changes = sum(stats.values())
        if total_changes > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            files_modified += 1

            parts = []
            if stats['duplicates_removed']:
                parts.append(f"{stats['duplicates_removed']} dups")
            if stats['choices_fixed']:
                parts.append(f"{stats['choices_fixed']} choices")
            if stats['commands_restored']:
                parts.append(f"{stats['commands_restored']} cmds")
            if stats['structural_fixes']:
                parts.append(f"{stats['structural_fixes']} structure")
            if stats['routing_dedup']:
                parts.append(f"{stats['routing_dedup']} routing")

            print(f"  {filename}: {', '.join(parts)}")

            for k in total_stats:
                total_stats[k] += stats[k]

    print(f"\n{'='*60}")
    print(f"TOTAL: {files_modified} files modified")
    print(f"  Duplicates removed:   {total_stats['duplicates_removed']}")
    print(f"  Choices fixed:        {total_stats['choices_fixed']}")
    print(f"  Commands restored:    {total_stats['commands_restored']}")
    print(f"  Structural fixes:     {total_stats['structural_fixes']}")
    print(f"  Routing deduped:      {total_stats['routing_dedup']}")

    # Deploy to game directory
    print(f"\nDeploying to {GAME_DIR}...")
    os.makedirs(GAME_DIR, exist_ok=True)
    deployed = 0
    for filename in filenames:
        src = os.path.join(TEXTS_DIR, filename)
        dst = os.path.join(GAME_DIR, filename)
        shutil.copy2(src, dst)
        deployed += 1
    print(f"  Deployed {deployed} files")
    print("Done!")


if __name__ == '__main__':
    main()
