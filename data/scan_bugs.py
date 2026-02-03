#!/usr/bin/env python3
"""
Scan all .txt files in Russian_Texts/ for translation/formatting bugs.
Research only - does not modify any files.
"""

import os
import re
import glob
from collections import defaultdict

TEXT_DIR = r"C:\Users\artem\NightCallRussian\data\Russian_Texts"

# Known emote tags that appear in choice lines as :tag:
EMOTE_TAGS = {
    'anger', 'smile', 'silence', 'positive', 'negative', 'irony',
    'love', 'money', 'puzzled', 'sad', 'radio', 'smoking', 'taxi',
    'violence', 'angry'
}

# Build regex for emote tags to exclude from English detection
EMOTE_PATTERN = re.compile(r':(' + '|'.join(EMOTE_TAGS) + r'):')

def get_txt_files():
    """Get all .txt files (not .bak) in the directory."""
    files = glob.glob(os.path.join(TEXT_DIR, "*.txt"))
    # Exclude .txt.bak files
    files = [f for f in files if not f.endswith('.bak')]
    files.sort()
    return files

def read_file(filepath):
    """Read file with encoding detection."""
    for enc in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.readlines()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []

# ============================================================
# BUG 1: Single-quote choices
# Choice lines starting with * that use 'text' instead of "text"
# ============================================================
def find_single_quote_choices(files):
    results = []
    for filepath in files:
        lines = read_file(filepath)
        fname = os.path.basename(filepath)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith('*'):
                continue
            # Check if it uses single quotes for the choice text
            # Pattern: *'text' -> or *:emote: 'text' ->
            # Must start with * then optional :emote: then single-quoted text
            after_star = stripped[1:].strip()
            # Remove optional emote tag
            temp = after_star
            emote_match = re.match(r'^:\w+:\s*', temp)
            if emote_match:
                temp = temp[emote_match.end():]
            # Now check if text portion starts with single quote
            if temp.startswith("'") and "'" in temp[1:]:
                results.append((fname, i, stripped))
    return results

# ============================================================
# BUG 2: Untranslated English in choices
# Choice lines with English words (3+ chars) that aren't emote tags
# ============================================================
def find_english_in_choices(files):
    results = []
    # Pattern to match English words (3+ consecutive ASCII letters)
    english_word_pattern = re.compile(r'\b([A-Za-z]{3,})\b')

    # Additional known safe English words that appear in target names, etc.
    # We'll be permissive about the -> target part

    for filepath in files:
        lines = read_file(filepath)
        fname = os.path.basename(filepath)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith('*'):
                continue

            # Split off the -> target part (we don't care about passage names)
            parts = stripped.split('->')
            choice_text = parts[0] if parts else stripped

            # Remove the leading *
            choice_text = choice_text[1:].strip()

            # Remove emote tags like :anger:, :smile: etc.
            choice_text_clean = EMOTE_PATTERN.sub('', choice_text)

            # Find all English words (3+ chars)
            english_words = english_word_pattern.findall(choice_text_clean)

            # Filter out known emote tag names (in case they appear without colons)
            english_words = [w for w in english_words if w.lower() not in EMOTE_TAGS]

            if english_words:
                results.append((fname, i, stripped, english_words))
    return results

# ============================================================
# BUG 3: Period outside quotes in choices
# Choice lines where period comes after closing quote: *"text". ->
# ============================================================
def find_period_outside_quotes(files):
    results = []
    # Pattern: a closing double-quote followed by a period, then optional space and ->
    # Also catch end-of-choice-text cases
    period_outside = re.compile(r'"\.\s*(->|$)')

    for filepath in files:
        lines = read_file(filepath)
        fname = os.path.basename(filepath)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith('*'):
                continue
            if period_outside.search(stripped):
                results.append((fname, i, stripped))
    return results

# ============================================================
# BUG 4: Mismatched echo lines
# Passages with 2+ incoming choices where the first content line
# echoes only one of the incoming choices
# ============================================================
def parse_passages(filepath):
    """Parse a file into passages: dict of name -> {lines, line_numbers, start_line}"""
    lines = read_file(filepath)
    passages = {}
    current_name = None
    current_lines = []
    current_start = 0
    current_line_nums = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Passage header: === passage-name
        m = re.match(r'^===\s+(.+)$', stripped)
        if m:
            if current_name is not None:
                passages[current_name] = {
                    'lines': current_lines,
                    'line_numbers': current_line_nums,
                    'start_line': current_start
                }
            current_name = m.group(1).strip()
            current_lines = []
            current_line_nums = []
            current_start = i
        elif current_name is not None:
            current_lines.append(stripped)
            current_line_nums.append(i)

    if current_name is not None:
        passages[current_name] = {
            'lines': current_lines,
            'line_numbers': current_line_nums,
            'start_line': current_start
        }

    return passages, lines

def extract_choice_text(choice_line):
    """Extract the display text from a choice line like *"text" -> target or *:emote: "text" -> target."""
    stripped = choice_line.strip()
    if not stripped.startswith('*'):
        return None

    after_star = stripped[1:].strip()

    # Remove -> target
    arrow_idx = after_star.find('->')
    if arrow_idx >= 0:
        text_part = after_star[:arrow_idx].strip()
    else:
        text_part = after_star.strip()

    return text_part

def extract_echo_text(content_line):
    """Extract text from an echo line like "text" or :emote: "text" or (text)."""
    stripped = content_line.strip()
    if not stripped:
        return None
    return stripped

def normalize_text(text):
    """Normalize text for comparison: remove emotes, quotes, parens, whitespace."""
    if text is None:
        return ''
    t = text.strip()
    # Remove emote tags
    t = EMOTE_PATTERN.sub('', t).strip()
    # Remove surrounding quotes or parens
    t = re.sub(r'^[""\u201c\u201d(]', '', t)
    t = re.sub(r'["""\u201c\u201d)]$', '', t)
    t = t.strip()
    return t

def find_mismatched_echoes(files):
    results = []

    for filepath in files:
        fname = os.path.basename(filepath)
        passages, all_lines = parse_passages(filepath)

        # Build map: passage_name -> list of (source_passage, choice_line, choice_text)
        incoming_choices = defaultdict(list)

        for pname, pdata in passages.items():
            for line in pdata['lines']:
                stripped = line.strip()
                if stripped.startswith('*'):
                    # Extract target passage
                    arrow_match = re.search(r'->\s*(.+)$', stripped)
                    if arrow_match:
                        target = arrow_match.group(1).strip()
                        choice_display = extract_choice_text(stripped)
                        incoming_choices[target].append({
                            'source': pname,
                            'choice_line': stripped,
                            'choice_text': choice_display
                        })

        # Now check each passage with 2+ incoming choices
        for pname, pdata in passages.items():
            inc = incoming_choices.get(pname, [])
            if len(inc) < 2:
                continue

            # Find first non-$$ non-empty content line
            first_content = None
            first_content_linenum = None
            for idx, line in enumerate(pdata['lines']):
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith('$$') and stripped.endswith('$$'):
                    continue
                # This is the first content line
                first_content = stripped
                first_content_linenum = pdata['line_numbers'][idx]
                break

            if first_content is None:
                continue

            # Check if first content line looks like an echo
            # Echoes: "text", :emote: "text", (text), :emote: (text)
            is_echo = False
            fc = first_content.strip()
            # Remove leading emote
            fc_no_emote = EMOTE_PATTERN.sub('', fc).strip()

            if (fc_no_emote.startswith('"') or fc_no_emote.startswith('\u201c') or
                fc_no_emote.startswith('(')) and not ' : ' in first_content:
                # Looks like player speech echo (not CHARACTER : "text")
                is_echo = True

            if not is_echo:
                continue

            # Check: does the echo match only ONE of the incoming choices?
            echo_normalized = normalize_text(first_content)

            matches = []
            for choice_info in inc:
                choice_normalized = normalize_text(choice_info['choice_text'])
                if echo_normalized and choice_normalized and echo_normalized == choice_normalized:
                    matches.append(choice_info)

            # Bug condition: echo matches exactly 1 out of 2+ incoming choices
            if len(matches) == 1 and len(inc) >= 2:
                results.append({
                    'file': fname,
                    'passage': pname,
                    'passage_line': pdata['start_line'],
                    'echo_line': first_content_linenum,
                    'echo_text': first_content,
                    'matching_choice': matches[0],
                    'all_incoming': inc
                })

    return results

# ============================================================
# MAIN
# ============================================================
def main():
    files = get_txt_files()
    print(f"Scanning {len(files)} .txt files in {TEXT_DIR}\n")
    print("=" * 80)

    # BUG 1: Single-quote choices
    print("\n" + "=" * 80)
    print("BUG 1: SINGLE-QUOTE CHOICES")
    print("Choice lines using 'text' instead of \"text\"")
    print("=" * 80)
    sq_results = find_single_quote_choices(files)
    if sq_results:
        for fname, linenum, content in sq_results:
            print(f"  {fname}:{linenum}")
            print(f"    {content}")
        print(f"\n  TOTAL: {len(sq_results)} occurrence(s)")
    else:
        print("  No occurrences found.")

    # BUG 2: Untranslated English in choices
    print("\n" + "=" * 80)
    print("BUG 2: UNTRANSLATED ENGLISH IN CHOICES")
    print("Choice lines containing English words (3+ chars, excluding emote tags)")
    print("=" * 80)
    en_results = find_english_in_choices(files)
    if en_results:
        for fname, linenum, content, words in en_results:
            print(f"  {fname}:{linenum}")
            print(f"    {content}")
            print(f"    English words: {', '.join(words)}")
        print(f"\n  TOTAL: {len(en_results)} occurrence(s)")
    else:
        print("  No occurrences found.")

    # BUG 3: Period outside quotes
    print("\n" + "=" * 80)
    print("BUG 3: PERIOD OUTSIDE QUOTES IN CHOICES")
    print("Choice lines with period after closing quote: \"text\". ->")
    print("=" * 80)
    pq_results = find_period_outside_quotes(files)
    if pq_results:
        for fname, linenum, content in pq_results:
            print(f"  {fname}:{linenum}")
            print(f"    {content}")
        print(f"\n  TOTAL: {len(pq_results)} occurrence(s)")
    else:
        print("  No occurrences found.")

    # BUG 4: Mismatched echoes
    print("\n" + "=" * 80)
    print("BUG 4: MISMATCHED ECHO LINES")
    print("Passages with 2+ incoming choices where echo matches only one choice")
    print("=" * 80)
    me_results = find_mismatched_echoes(files)
    if me_results:
        for r in me_results:
            print(f"\n  {r['file']}: passage === {r['passage']} (line {r['passage_line']})")
            print(f"    Echo at line {r['echo_line']}: {r['echo_text']}")
            print(f"    Matches choice: {r['matching_choice']['choice_line']}")
            print(f"      (from passage: {r['matching_choice']['source']})")
            print(f"    All {len(r['all_incoming'])} incoming choices:")
            for inc in r['all_incoming']:
                marker = " <-- MATCH" if inc == r['matching_choice'] else ""
                print(f"      - {inc['choice_line']} (from {inc['source']}){marker}")
        print(f"\n  TOTAL: {len(me_results)} occurrence(s)")
    else:
        print("  No occurrences found.")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Files scanned:                  {len(files)}")
    print(f"  Bug 1 (single-quote choices):   {len(sq_results)}")
    print(f"  Bug 2 (English in choices):     {len(en_results)}")
    print(f"  Bug 3 (period outside quotes):  {len(pq_results)}")
    print(f"  Bug 4 (mismatched echoes):      {len(me_results)}")
    total = len(sq_results) + len(en_results) + len(pq_results) + len(me_results)
    print(f"  TOTAL issues found:             {total}")

if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    main()
