"""
fix_polish.py - Post-processing polish fixes for Russian localization JSON.

Fixes three categories of issues:
  1. Quoted subtitle strings missing from mapping (e.g. "Saint-Ouen." with quotes)
  2. Emote tags leaking into displayed values (e.g. :silence:, :negative:, etc.)
  3. Imperative mood -> Infinitive form for UI/choice labels

Reads and writes full_translation_mapping.json in the Russian_UI folder.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
JSON_PATH = Path(
    r"F:\SteamLibrary\steamapps\common\Night Call\Russian_UI"
    r"\full_translation_mapping.json"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_mapping(path: Path) -> dict[str, str]:
    """Load the JSON translation mapping preserving key order."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=lambda pairs: dict(pairs))


def save_mapping(path: Path, data: dict[str, str]) -> None:
    """Write JSON with 2-space indent and ensure_ascii=False for Cyrillic."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ===================================================================
# FIX 1 - Add quoted subtitle entries for passenger card strings
# ===================================================================

def fix_quoted_subtitles(data: dict[str, str]) -> int:
    """
    The game's TMP_Text sometimes sends short subtitle strings wrapped in
    literal double-quotes, e.g. the key arrives as  "Saint-Ouen."  (with
    the quotes being part of the string).  The JSON already maps the bare
    version, so we add entries for the quoted version too.

    Strategy:
      - Explicitly add the two Saint-Ouen quoted variants requested.
      - Scan for other short strings (<= 50 chars) that look like passenger
        card subtitles (locations, short descriptions) and create quoted
        variants for those as well, if missing.
    """
    added = 0

    # --- Explicit Saint-Ouen entries requested ---
    explicit_pairs: list[tuple[str, str]] = [
        ('"Saint-Ouen."', '"\u0421\u0435\u043d\u0442-\u0423\u044d\u043d."'),
        ('"Saint-Ouen"',  '"\u0421\u0435\u043d\u0442-\u0423\u044d\u043d"'),
    ]

    for key, val in explicit_pairs:
        if key not in data:
            data[key] = val
            added += 1
            print(f"  [+] Added quoted entry: {key!r} -> {val!r}")
        else:
            print(f"  [=] Already exists: {key!r}")

    # --- Scan for other short subtitle-like strings that may appear quoted ---
    # Passenger card subtitles are typically short: location names, character
    # descriptions, or short factual lines.  We look for unquoted entries
    # whose keys are short, contain no emote tags, and are NOT dialogue
    # (no colon speaker prefix, no parenthetical actions).
    # We create the "..." quoted variant if it is missing.

    subtitle_candidates: list[tuple[str, str]] = []
    for key, val in list(data.items()):
        # Skip if already a quoted string, or too long, or is dialogue/action
        if len(key) > 50:
            continue
        if key.startswith('"') or key.startswith("(") or key.startswith(":"):
            continue
        # Skip dialogue lines (SPEAKER: ...)
        if re.match(r"^[A-Z\u00C0-\u024F]{2,}[\s]*:", key):
            continue
        # Skip clue source keys like "clue_angel_..."
        if key.startswith("clue_") or key.startswith("_"):
            continue
        # Skip keys with format placeholders
        if "{" in key:
            continue
        # Skip very short generic UI keys (single words that aren't locations)
        if len(key) < 3:
            continue

        # The quoted variant
        quoted_key = f'"{key}"'
        quoted_val = f'"{val}"'

        # Only add if the quoted version is missing AND the bare version exists
        if quoted_key not in data:
            # Heuristic: only add for strings that look like they could be
            # passenger card content -- short descriptive strings ending with
            # period, or location-like names.
            is_location_like = (
                re.match(r"^[A-Z\u00C0-\u024F][\w\s\-\'\.\,\u00C0-\u024F]+\.?$", key)
                and not key.endswith("=")
                and "=" not in key
            )
            if is_location_like and len(key) <= 40:
                subtitle_candidates.append((quoted_key, quoted_val))

    # Only add truly short location/subtitle entries (avoid adding thousands)
    # Filter to entries near the passenger-card section (short location names,
    # character descriptors) -- entries with period at end, or very short.
    actually_added_auto = 0
    for qk, qv in subtitle_candidates:
        inner = qk[1:-1]  # strip our added quotes
        # Must be a short location-style string (no long sentences)
        words = inner.split()
        if len(words) <= 4 and len(inner) <= 30:
            if qk not in data:
                data[qk] = qv
                actually_added_auto += 1

    if actually_added_auto > 0:
        print(f"  [+] Auto-added {actually_added_auto} quoted variants for"
              f" short location/subtitle strings")
    added += actually_added_auto

    return added


# ===================================================================
# FIX 2 - Strip emote tag prefixes from VALUES
# ===================================================================

# Pattern: starts with :<word>: optionally followed by a space
EMOTE_PREFIX_RE = re.compile(r"^(:[a-z]+:)\s*")


def fix_emote_tags(data: dict[str, str]) -> dict[str, int]:
    """
    Strip emote tag prefixes from VALUES.

    Two sub-cases:
      a) Value starts with an emote tag like ':silence: (text)' -- strip the
         tag so it becomes '(text)'.
      b) Value IS an emote tag mapping to wrong text -- same rule, strip prefix.

    We do NOT touch keys -- the key must keep the tag for game matching.
    """
    stats: dict[str, int] = Counter()

    for key in list(data.keys()):
        val = data[key]
        m = EMOTE_PREFIX_RE.match(val)
        if m:
            tag = m.group(1)
            new_val = val[m.end():]
            # If stripping leaves empty string, skip
            if not new_val.strip():
                stats["skipped_empty"] += 1
                continue
            data[key] = new_val
            stats[tag] = stats.get(tag, 0) + 1
            stats["total_stripped"] += 1

    return dict(stats)


# ===================================================================
# FIX 3 - Imperative mood -> Infinitive in UI/choice values
# ===================================================================

# Mapping of imperative -> infinitive forms
IMPERATIVE_TO_INFINITIVE: dict[str, str] = {
    "\u0412\u043e\u0437\u044c\u043c\u0438\u0442\u0435":    "\u0412\u0437\u044f\u0442\u044c",         # Возьмите -> Взять
    "\u041f\u0440\u0438\u043c\u0438\u0442\u0435":           "\u041f\u0440\u0438\u043d\u044f\u0442\u044c",  # Примите -> Принять
    "\u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435":     "\u041e\u0442\u043a\u0440\u044b\u0442\u044c",  # Откройте -> Открыть
    "\u0417\u0430\u043a\u0440\u043e\u0439\u0442\u0435":     "\u0417\u0430\u043a\u0440\u044b\u0442\u044c",  # Закройте -> Закрыть
    "\u041f\u043e\u0441\u043c\u043e\u0442\u0440\u0438\u0442\u0435": "\u041f\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c",  # Посмотрите -> Посмотреть
    "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u0439\u0442\u0435": "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u0442\u044c",  # Прочитайте -> Прочитать
    "\u041f\u043e\u0437\u0432\u043e\u043d\u0438\u0442\u0435": "\u041f\u043e\u0437\u0432\u043e\u043d\u0438\u0442\u044c",  # Позвоните -> Позвонить
    "\u041e\u0442\u043a\u0430\u0436\u0438\u0442\u0435":     "\u041e\u0442\u043a\u0430\u0437\u0430\u0442\u044c",  # Откажите -> Отказать
    "\u041e\u0442\u043f\u0443\u0441\u0442\u0438\u0442\u0435": "\u041e\u0442\u043f\u0443\u0441\u0442\u0438\u0442\u044c",  # Отпустите -> Отпустить
    "\u041e\u0441\u0442\u0430\u0432\u044c\u0442\u0435":     "\u041e\u0441\u0442\u0430\u0432\u0438\u0442\u044c",  # Оставьте -> Оставить
    "\u041f\u043e\u0434\u043e\u0436\u0434\u0438\u0442\u0435": "\u041f\u043e\u0434\u043e\u0436\u0434\u0430\u0442\u044c",  # Подождите -> Подождать
}

# Words that should NOT be changed in dialogue (they are correct imperative
# forms when used in character speech)
DIALOGUE_SAFE_WORDS = {
    "\u0421\u043a\u0430\u0436\u0438\u0442\u0435",     # Скажите
    "\u041f\u043e\u0441\u043b\u0443\u0448\u0430\u0439\u0442\u0435",  # Послушайте
}

# Special case: "Прочитайте в газете..." -> "Прочитано в газете..."
NEWSPAPER_IMPERATIVE = "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u0439\u0442\u0435 \u0432 \u0433\u0430\u0437\u0435\u0442\u0435"
NEWSPAPER_REPLACEMENT = "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u043d\u043e \u0432 \u0433\u0430\u0437\u0435\u0442\u0435"


def _is_dialogue_context(value: str) -> bool:
    """
    Heuristic: a value is 'dialogue' if it is a long sentence that is
    clearly character speech -- contains quotation marks, guillemets, or
    is a long narrative string (>30 chars) that doesn't look like a
    UI label or parenthetical choice.
    """
    # Parenthetical actions like "(Принять это.)" are NOT dialogue
    if value.startswith("(") and value.endswith(")"):
        return False
    # Short strings (< 30 chars) are likely UI/choice labels
    if len(value) < 30:
        return False
    # Strings with speaker names (CAPS + colon) are dialogue
    if re.match(r'^[A-Z\u0410-\u042F\u00C0-\u024F]{2,}\s*:', value):
        return True
    # Strings in quotes are dialogue
    if value.startswith('"') or value.startswith('\u00ab') or value.startswith('\u201c'):
        return True
    # Long strings with sentence structure are likely dialogue
    if len(value) > 60:
        return True
    return False


def _contains_dialogue_safe_word_in_context(value: str, word: str) -> bool:
    """
    Check if the word appears in a dialogue-safe context -- i.e. the value
    is clearly a dialogue line and the word is used mid-sentence.
    """
    if not _is_dialogue_context(value):
        return False
    # Check if the word appears NOT at the very start
    # (if it starts the value, it could still be a label)
    stripped = value.lstrip('"(\u00ab\u201c ')
    if stripped.startswith(word):
        # Starting a quoted dialogue line -- still dialogue
        return True
    # Word in the middle of dialogue -- definitely dialogue
    return True


def fix_imperative_mood(data: dict[str, str]) -> dict[str, int]:
    """
    Replace imperative forms with infinitive in UI/choice values.

    Rules:
      - Exact value match or short value (< 30 chars): always replace
      - Parenthetical values like "(Примите это.)": replace
      - "Прочитайте в газете..." entries: replace with "Прочитано в газете..."
      - Long dialogue values: do NOT replace
      - Скажите/Послушайте in dialogue: do NOT replace
    """
    stats: dict[str, int] = Counter()

    for key in list(data.keys()):
        val = data[key]

        # --- Special case: newspaper source entries ---
        if NEWSPAPER_IMPERATIVE in val:
            new_val = val.replace(NEWSPAPER_IMPERATIVE, NEWSPAPER_REPLACEMENT)
            if new_val != val:
                data[key] = new_val
                stats["newspaper_fixed"] += 1
                continue

        # --- General imperative -> infinitive replacement ---
        for imp_form, inf_form in IMPERATIVE_TO_INFINITIVE.items():
            if imp_form not in val:
                continue

            # Skip "Прочитайте" entries already handled by newspaper case above
            if imp_form == "\u041f\u0440\u043e\u0447\u0438\u0442\u0430\u0439\u0442\u0435" and NEWSPAPER_IMPERATIVE in val:
                continue

            # Check if this is a dialogue-safe word in dialogue context
            is_safe = False
            for safe_word in DIALOGUE_SAFE_WORDS:
                if safe_word in val and _contains_dialogue_safe_word_in_context(val, safe_word):
                    is_safe = True
                    break

            if is_safe:
                stats["skipped_dialogue"] += 1
                continue

            # Check if value is dialogue context for THIS specific word
            if _is_dialogue_context(val):
                # In dialogue, only replace if it's a parenthetical
                if val.startswith("(") and val.endswith(")"):
                    pass  # OK to replace
                else:
                    stats["skipped_dialogue"] += 1
                    continue

            # Exact match (the entire value is just the imperative word)
            if val == imp_form:
                data[key] = inf_form
                stats[f"{imp_form}->{inf_form}"] += 1
                stats["total_replaced"] += 1
                break

            # Short value or parenthetical -- replace occurrence at word
            # boundary (start of value or after space/quote/paren)
            pattern = re.compile(
                r'(?<![A-Za-z\u0400-\u04FF])' + re.escape(imp_form) + r'(?![A-Za-z\u0400-\u04FF])'
            )
            new_val = pattern.sub(inf_form, val, count=1)
            if new_val != val:
                data[key] = new_val
                stats[f"{imp_form}->{inf_form}"] += 1
                stats["total_replaced"] += 1
                break  # one replacement per value to avoid double-counting

    return dict(stats)


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    print("=" * 70)
    print("  Russian Localization Polish Script")
    print("  Input: " + str(JSON_PATH))
    print("=" * 70)

    if not JSON_PATH.exists():
        print(f"ERROR: File not found: {JSON_PATH}")
        sys.exit(1)

    data = load_mapping(JSON_PATH)
    original_count = len(data)
    print(f"\nLoaded {original_count} entries.\n")

    # --- Fix 1: Quoted subtitle strings ---
    print("-" * 70)
    print("FIX 1: Adding quoted subtitle entries for passenger cards")
    print("-" * 70)
    fix1_count = fix_quoted_subtitles(data)
    print(f"\n  Total entries added: {fix1_count}")

    # --- Fix 2: Emote tags in values ---
    print("\n" + "-" * 70)
    print("FIX 2: Stripping emote tag prefixes from values")
    print("-" * 70)
    fix2_stats = fix_emote_tags(data)
    total_stripped = fix2_stats.pop("total_stripped", 0)
    skipped_empty = fix2_stats.pop("skipped_empty", 0)
    print(f"\n  Total values with emote tags stripped: {total_stripped}")
    if skipped_empty:
        print(f"  Skipped (would be empty after strip): {skipped_empty}")
    print("  Breakdown by tag:")
    for tag, count in sorted(fix2_stats.items()):
        print(f"    {tag}: {count}")

    # --- Fix 3: Imperative -> Infinitive ---
    print("\n" + "-" * 70)
    print("FIX 3: Imperative mood -> Infinitive form in UI/choice values")
    print("-" * 70)
    fix3_stats = fix_imperative_mood(data)
    total_replaced = fix3_stats.pop("total_replaced", 0)
    newspaper_fixed = fix3_stats.pop("newspaper_fixed", 0)
    skipped_dialogue = fix3_stats.pop("skipped_dialogue", 0)
    print(f"\n  Total imperative->infinitive replacements: {total_replaced}")
    print(f"  Newspaper source entries fixed: {newspaper_fixed}")
    print(f"  Skipped (dialogue context): {skipped_dialogue}")
    print("  Breakdown by form:")
    for form_change, count in sorted(fix3_stats.items()):
        print(f"    {form_change}: {count}")

    # --- Save ---
    print("\n" + "=" * 70)
    print("  Saving...")
    save_mapping(JSON_PATH, data)
    final_count = len(data)
    print(f"  Done. Final entry count: {final_count} (was {original_count},"
          f" added {final_count - original_count})")
    print("=" * 70)

    # --- Summary ---
    print("\n  SUMMARY")
    print(f"    Fix 1 (quoted subtitles added):      {fix1_count}")
    print(f"    Fix 2 (emote tags stripped):          {total_stripped}")
    print(f"    Fix 3 (imperative->infinitive):       {total_replaced}")
    print(f"    Fix 3 (newspaper sources):            {newspaper_fixed}")
    print(f"    Fix 3 (dialogue skipped):             {skipped_dialogue}")
    total_changes = fix1_count + total_stripped + total_replaced + newspaper_fixed
    print(f"    ----------------------------------------")
    print(f"    Total modifications:                  {total_changes}")


if __name__ == "__main__":
    main()
