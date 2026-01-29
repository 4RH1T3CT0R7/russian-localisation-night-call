# Night Call Russian Localization - Font & SDF Documentation

> **Note**: For the complete mod architecture and translation system documentation, see [DOCUMENTATION_RU.md](DOCUMENTATION_RU.md).
> This file covers only the font patching subsystem.

## Font Patching Architecture

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

### Troubleshooting

**Squares Instead of Text**:
- Check `BepInEx/LogOutput.log` for patching errors
- Verify `Generated_SDF/` files exist and are not corrupted
- Ensure DLL is compiled from latest source

**Text Size Issues**:
- Font metrics may not match original
- Check `TMP_Font_Metrics.txt` for original values
- Adjust `FontScale` config value (default: 1.05)
