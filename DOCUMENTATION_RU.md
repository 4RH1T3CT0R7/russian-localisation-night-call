# Night Call Russian Localization Mod - Technical Documentation

## Overview

BepInEx 5.4.23 mod for Unity 2018.4 (Mono/.NET 3.5) game "Night Call".
Translates UI, dialogue text, choice options, and speaker names from English to Russian.

**Version**: 6.1.0
**Author**: Artem Lytkin (4RH1T3CT0R)
**License**: CC BY 4.0

---

## Game Engine Architecture

### Dialogue System: Prompter Runtime

The game uses a custom dialogue engine called **Prompter**. Key types (namespace `Prompter.Runtime`):

```
DialogObjectScript (UnityEngine.Object)
  └─ dialogs: List<DialogI18N>
       └─ DialogI18N
            ├─ lang: string ("eng", "fre", "ger")
            └─ dialog: Dialog
                 └─ _passages: List<PassageSection>
                      └─ PassageSection
                           ├─ _title: string          // passage identifier
                           ├─ _lines: List<string>     // dialogue/narrative lines
                           ├─ _link: string             // next passage (linear flow)
                           └─ _choices: List<ChoiceSection>
                                └─ ChoiceSection (class)
                                     ├─ _text: string    // display text + optional emote prefix
                                     ├─ _link: string    // target passage
                                     ├─ _ending: bool
                                     └─ <word_count>k__BackingField: int
```

### How Dialogues Load

1. Game loads `DialogObjectScript` Unity objects (200 total in the game)
2. Each object has multiple `DialogI18N` entries (one per language)
3. Game selects the `eng` entry at runtime
4. Prompter iterates through `_passages`, displaying `_lines` one by one
5. When `_choices` is non-empty, player selects an option which navigates to `_link`

### Compiled vs Source Format

**Source format** (Prompter .txt files):
```
=== passage-title
    $$ command $$
SPEAKER : "Dialogue text"
Narrative text in italics.
    -> next-passage

* "Choice text" -> target-passage
* :emote: (Action text) -> target-passage
```

**Compiled format** (`_lines` in PassageSection):
- Commands (`$$ ... $$`) are stored as lines
- Speaker lines use various quote styles:
  - `BOSS: \u201cWell...\u201d` (curly quotes, no space before colon)
  - `BUSSET : \u00ab text \u00bb` (guillemets, space before colon)
  - `NAME: "text"` (straight quotes)
- Narrative text stored as plain strings
- Passage titles may differ from source (compiler can merge passages)

**Important**: The game's dialogue parser recognises speaker names ONLY in Latin uppercase.
Cyrillic names (e.g. `САЛИМ:`) are treated as narration (grey text). The mod therefore
keeps English speaker names in passage data and translates the displayed name through
the TMP_Text interceptor.

### Choice Emotes

Choice `_text` can include an emote prefix that the UI renders as an icon:
```
:silence: (Say nothing.)     -> shows "..." icon
:anger: "Angry response"     -> shows anger icon
:puzzled: "Question"         -> shows puzzled icon
:smile: "Happy response"     -> shows smile icon
:sad: "Sad response"         -> shows sad icon
:taxi: (Drive away.)         -> shows taxi icon
:positive: "Positive"        -> shows positive icon
```

The emote prefix MUST remain in `_text` for icons to display. Removing it causes icons to disappear.
Emote prefixes must NOT appear in JSON translation values — they are preserved at the passage level only.

### Localization System

Game uses `LocalizationManager` with key-value dictionaries:
- Keys like `UI.MENU.QUIT`, `UI.ENDSHIFT.SUMUP.KM.TRAVELED`
- Values are localized strings per language
- `GetLocalizedString(key)` returns the translated value

Text rendering uses **TextMeshPro** (`TMPro.TMP_Text`) and legacy **UnityEngine.UI.Text`.

---

## Mod Architecture

### Translation Layers (in order of priority)

1. **Key-based UI injection** — `KeyTranslations` dictionary (789 entries)
   - Patched via `LocalizationManager` Harmony postfix
   - Maps localization keys directly to Russian: `UI.MENU.QUIT` -> `"Выход"`

2. **Dialogue replacement** — `RussianPassages` + `RussianChoices`
   - Replaces `_lines` and `_choices` in PassageSection objects
   - Matches by passage `_title`
   - Per-passage speaker name mapping (Russian -> English for parser, English -> Russian for display)
   - **200/200** DialogObjectScript objects processed, **5371** passages replaced

3. **TMP text translation** — `Translations` dictionary (30,533 entries)
   - Harmony prefix on `TMP_Text.set_text`
   - Translates any English text displayed via TextMeshPro
   - Includes Cyrillic detection (skips already-translated text)
   - Fallback for text not caught by other layers

### Speaker Name Handling

The mod builds a bidirectional mapping between Russian and English speaker names:

- **passageRuToEng**: Built by comparing speaker order in English and Russian passage lines.
  Used in `ReplaceDialogueObjects()` to restore English speaker names in passage data,
  so the game's dialogue parser correctly identifies dialogue lines (white text) vs narration (grey text).

- **JSON translations**: Uppercase English names (`SALIM`, `ALPH`, etc.) are mapped to
  Russian in `full_translation_mapping.json`. When the game displays the speaker name
  via TMP_Text, the interceptor translates it to Russian (`САЛИМ`, `АЛЬФ`).

### Data Files

| File | Format | Count | Purpose |
|------|--------|-------|---------|
| `Russian_UI/full_translation_mapping.json` | `{"eng": "rus", ...}` | 30,533 | English->Russian text pairs for TMP fallback |
| `Russian_UI/key_based_translations.json` | `{"KEY": "rus", ...}` | 789 | Localization key->Russian for UI |
| `Russian_Texts/*_rus.txt` | Prompter source | 155 files | Russian dialogue source files |
| `Fonts_Cyrillic/*.ttf` | TrueType | 16 fonts | Cyrillic-capable fonts |
| `Generated_SDF/*.png + *.txt` | SDF atlas + glyphs | 5 fonts | Pre-generated Cyrillic SDF data |
| `passage_dump.txt` | Custom dump | 39,629 lines | Sequential fallback for passage matching |

### Key Dictionaries in Code

```csharp
Translations          // eng_text -> rus_text (from full_translation_mapping.json)
KeyTranslations       // loc_key -> rus_text (from key_based_translations.json)
DialogueTexts         // file_key -> raw_content (from Russian_Texts/*.txt)
RussianPassages       // passage_title -> List<string> lines
RussianChoices        // passage_title -> List<string[]> {text, link, emote}
GlobalLinkToChoiceTexts // choice_link -> List<string> texts (across all passages)
SpeakerNameMap        // eng_speaker -> rus_speaker (global fallback)
passageRuToEng        // rus_speaker -> eng_speaker (per-passage, built from line order)
```

---

## Font Patching & SDF System

### Problem

The game uses TextMesh Pro (TMP) for text rendering. Original fonts (LiberationSans, AvenirLTStd) don't have Cyrillic glyphs.

### Solution

Runtime patching of TMP_FontAsset objects:

1. **On Scene Load**: `EnumerateAndPatchAllFonts()` finds all TMP fonts in the game
2. **For Each Font**: `PatchSingleFontWithCyrillic()` replaces:
   - Atlas texture with our Cyrillic SDF atlas
   - Glyph list with our glyph definitions
   - Font metrics (scaled proportionally)

### SDF Atlas Generation

The `generate_sdf_atlas.py` script:
1. Loads TTF font file using FreeType
2. Renders each glyph at specified size (90pt)
3. Calculates Signed Distance Field for each glyph
4. Packs glyphs into 1024x1024 atlas
5. Outputs:
   - `{FontName}_SDF_atlas.png` — Grayscale atlas texture
   - `{FontName}_SDF_glyphs.txt` — Glyph metrics (position, size, bearing, advance)

### Glyph Data Format

Tab-separated values:
```
char=A	unicode=1040	x=238	y=550	w=36	h=44	bx=0	by=44	adv=36
```
- `unicode` — Unicode code point
- `x, y` — Position in atlas (pixels)
- `w, h` — Glyph dimensions
- `bx, by` — Bearing (offset from baseline)
- `adv` — Advance width (spacing to next character)

### Font Metrics Scaling

Original game fonts have different PointSize values (86-108). Our atlas uses 90pt.
The patching code calculates scale ratio and adjusts:
- LineHeight, Ascender, Descender
- CapHeight, Baseline
- UnderlineOffset, strikethroughOffset
- TabWidth, Padding

### Game Fonts

Original TMP fonts found in game:

| Font Name | PointSize | Atlas Size |
|-----------|-----------|------------|
| LiberationSans SDF | 86 | 1024x1024 |
| AvenirLTStd-Light | 106 | 1024x1024 |
| AvenirLTStd-Light-complete | 108 | 1024x1024 |
| AvenirLTStd-LightOblique-complete | 103 | 1024x1024 |
| AvenirLTStd-Light-Shadow | varies | 1024x1024 |

### Generated SDF Atlases

| Font | Files | Used For |
|------|-------|----------|
| PTSans | `PTSans_SDF_atlas.png` + `_glyphs.txt` | Main body text |
| PTSansBold | `PTSansBold_SDF_atlas.png` + `_glyphs.txt` | Bold text |
| Anton | `Anton_SDF_atlas.png` + `_glyphs.txt` | Title/heading text |
| Bangers | `Bangers_SDF_atlas.png` + `_glyphs.txt` | Stylised text |
| Oswald | `Oswald_SDF_atlas.png` + `_glyphs.txt` | UI labels |

### Cyrillic Font Files

Located in `Fonts_Cyrillic/`:
- **PTSans-Regular.ttf** — Primary font (loaded as Unity legacy Font)
- **PTSans-Bold.ttf**, **PTSans-Italic.ttf** — Variants
- Other TTF files — Backup/alternative Cyrillic fonts

### Font Troubleshooting

**Squares Instead of Text**:
- Check `BepInEx/LogOutput.log` for patching errors
- Verify `Generated_SDF/` files exist and are not corrupted
- Ensure DLL is compiled from latest source

**Text Size Issues**:
- Font metrics may not match original
- Check `TMP_Font_Metrics.txt` for original values
- Adjust `FontScale` config value (default: 1.05)

---

## Problems Discovered & Solutions

### Problem 1: Speaker Name Detection (SOLVED)

**Issue**: English compiled lines use curly quotes `\u201c` / `\u201d`, not straight `"`.
```
Compiled: BOSS: \u201cWell...\u201d
Code searched for: ": \""
```

**Fix**: `ExtractSpeakerName()` and `ExtractSpeakerText()` now handle 3 quote formats:
- `": "` (straight quotes)
- `": \u00ab` (guillemets)
- `": \u201c` (curly left quote)
- Plus ` : ` variants (with space before colon)

### Problem 2: Passage Structure Mismatch (SOLVED)

**Issue**: Compiled game can merge multiple source passages into one compiled PassageSection.

**Fix for choices**: `GlobalLinkToChoiceTexts` — global link->text map across ALL passages. If per-passage match fails, searches globally.

**Fix for lines**: Sequential fallback via `passage_dump.txt` — matches passages by order of appearance in the dump.

### Problem 3: Dialogue Objects Not Translated (SOLVED)

**Issue**: 88 Russian passenger dialogue files were plain text without `=== passage-title` markers. The mod matches by passage title, so these files produced zero `RussianPassages` entries.

**Fix**: All 155 Russian text files now have `===` passage markers. The `add_speaker_names.py` script added passage structure to all files. **200/200** DialogObjectScript objects are now translated (**5371** passages).

### Problem 4: Choice Emote Icons (SOLVED)

**Issue**: Russian choice text was set WITHOUT emote prefix.

**Fix**: Emote prefix preserved from Russian source file and prepended to replacement text.

### Problem 5: Choice Duplicate/Wrong Text (SOLVED)

**Issue**: When English passage has more choices than Russian, TMP hook fallback matched wrong text.

**Fix**: Removed `TranslateTextDirect` fallback for choices. Now only uses link-based matching (local then global).

### Problem 6: Italic Narrative Text (SOLVED)

**Issue**: English game displays narrative text in italic. Russian replacement lost italic.

**Fix**: Non-speaker, non-command lines wrapped in `<i>...</i>` TMP rich text tags.

### Problem 7: Navigation Loop from MemberwiseClone (SOLVED)

**Issue**: Early attempt to replace choices used `MemberwiseClone()`. This broke navigation.

**Fix**: Only modify `_text` field on existing choice objects. Never clone ChoiceSection instances.

### Problem 8: Dialogue Rendered as Grey Narration (SOLVED)

**Issue**: After replacing passage lines with Russian text, ALL text appeared grey (narration style) instead of white (dialogue style). The game's dialogue parser only recognises Latin uppercase speaker names.

**Root cause**: The mod was inserting Russian speaker names (e.g. `САЛИМ: "text"`) into passage data. The game's parser did not recognise Cyrillic names as speakers -> treated everything as narration.

**Fix**: Use `passageRuToEng` mapping to restore English speaker names in passage data:
```csharp
string engSp;
if (!passageRuToEng.TryGetValue(ruSp, out engSp))
    engSp = ruSp;
processedLine = engSp + " : " + textPart;
```
The TMP_Text interceptor then translates the displayed speaker name to Russian via JSON.

### Problem 9: Emote Tags in JSON Values (SOLVED)

**Issue**: Some JSON translation values contained emote prefixes like `:silence:`, `:smile:` that leaked into displayed text.

**Fix**: Stripped emote tags from 707 JSON values via `fix_polish.py`.

### Problem 10: Imperative Verb Forms in UI (SOLVED)

**Issue**: UI buttons and choice labels used imperative mood ("Примите", "Возьмите") instead of infinitive ("Принять", "Взять").

**Fix**: Replaced imperative forms with infinitive in JSON translations for UI elements and choice labels. Preserved imperative in actual dialogue speech.

---

## Russian Source File Format

All 155 Russian text files use Prompter source format with passage markers:

```
%% Comment
    VAR variable = value
    +++ directive: value
=== passage-title
    $$ command: param $$
SPEAKER : "Dialogue text"
Narrative text
    { variable += 1 }
    -> next-passage
* "Choice text" -> target-passage
* :emote: (Action text) -> target-passage
=== next-passage
...
```

Parsing rules:
- `===` lines -> passage boundaries
- `%%` lines -> comments (skip)
- `$$ ... $$` -> commands (keep in _lines)
- `{ ... }` -> variable modifiers (skip)
- `-> target` -> navigation (skip)
- `* text -> target` -> choice (parse into RussianChoices)
- `+++ directive` -> header directives (skip)
- Bare lines matching known passage titles -> navigation references (skip)
- Everything else -> dialogue/narrative lines (add to _lines)

---

## Compiled Game Statistics

- Total DialogObjectScript objects: **200**
- Replaced: **200/200**
- Total passages replaced: **5,371**
- UI translations: **789** key-based + **30,533** text-based
- Passenger full names translated: **115** (87 passengers + variants)
- Uppercase speaker names in JSON: **110** (for TMP display translation)
- Russian dialogue files: **155** (all with passage markers)

---

## Build & Deploy

```bash
cd BepInExMod
dotnet build -c Release
copy bin\Release\net46\NightCallRussian.dll ..\BepInEx\plugins\
```

Target: .NET Framework 4.6 (Unity Mono runtime)
C# Language Version: 5 (no string interpolation, no null-conditional, no pattern matching)
Key constraint: `object.ReferenceEquals()` instead of `!=` for FieldInfo/Type null checks.

---

## File Locations

```
Night Call/
├── BepInEx/
│   ├── core/                        # BepInEx framework DLLs
│   ├── plugins/
│   │   └── NightCallRussian.dll     # Compiled mod (v6.1.0)
│   └── LogOutput.log                # Runtime log
├── BepInExMod/
│   ├── RussianLocalization.cs       # Main mod source (~4,091 lines)
│   └── NightCallRussian.csproj      # Build project
├── Russian_Texts/                   # 155 Russian dialogue files
├── Russian_UI/
│   ├── full_translation_mapping.json  # 30,533 eng->rus pairs
│   └── key_based_translations.json    # 789 key->rus pairs
├── Fonts_Cyrillic/                  # 16 .ttf font files
├── Generated_SDF/                   # 5 SDF atlas+glyph sets
├── passage_dump.txt                 # Sequential fallback data
├── winhttp.dll                      # BepInEx doorstop proxy
├── doorstop_config.ini              # BepInEx config
└── LICENSE                          # CC BY 4.0
```

---

## Known Issues

### Open
- **9 missing passages**: `geraldine-01-restaurant-var-no`, `geraldine-01-hub`, `apollonie-proposition-furiosa-hub`, `apollonie-proposition-napo-hub`, `apollonie-end`, `gilda-01-speaking-hub-special`, `gilda-01-end-city-hub`, `gilda-02-speech02-hub-joker`, `gilda-02-speech02-hub` — these passages are absent from Russian text files. LineFallback covers them via TMP translation.
- **Missing reveal/tip commands** in 9 passenger files — affects gameplay mechanics (content unlock, tip amounts). See CRITICAL_ISSUES_REPORT.txt.
- **Card subtitles** (e.g. location text) are generated at runtime and not stored in binary data — some may remain untranslated.

### Resolved
- All 200 dialogue objects translated
- Speaker name rendering fixed (English in data, Russian in display)
- Emote tag leakage fixed
- Imperative verb forms fixed
- Quote format normalised (straight quotes in passages, guillemets where needed)
