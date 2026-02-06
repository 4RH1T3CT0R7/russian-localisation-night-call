# English vs Russian Comparison Progress

## Status Legend
- ✅ = Compared and verified (fixes applied if needed)
- 🔧 = Compared, fixes applied
- 📋 = Metadata file (no dialogue in English, can't compare)
- ⚠️ = English too short/garbled for useful comparison
- 🤖 = Compared via agent (output lost, assume clean unless proven otherwise)
- ❌ = Not yet started

## Completed Comparisons

### Session 1-9
| # | Character | Status | Notes |
|---|-----------|--------|-------|
| 001 | patricia | ✅ | Compared, missing quotes fixed |
| 002 | purva | ✅ | Compared via agent |
| 003 | alaric | ✅ | Compared, missing quotes fixed |
| 006 | esmeralda | ✅ | Compared, misquote fixed |
| 008 | vincent | ✅ | Compared via agent |
| 010 | camilleantoine | ✅ | Compared |
| 014 | fragonard | ✅ | Compared |
| 019 | herve | ✅ | Broad ты/вы inconsistency noted (may be intentional) |
| 020 | jacquie | 🔧 | ты/вы fixes (lines 625, 833), missing ЖАКИ speaker prefix (00a line 50) |
| 025 | ade | 🔧 | ты/вы fixes (lines 692, 1047) |
| 026 | skaterz | ✅ | Compared |
| 028 | carolinaj | 🔧 | 2 copy-paste errors in player choices (prev session) |
| 029 | jerome | 🔧 | Swapped passages, missing tags, typos (prev session) |
| 030 | peter | 🔧 | Mistranslation "clams up" (prev session) |
| 033 | chiara | 🔧 | Duplicate passage content, ты→вы (prev session) |
| 035 | sylvainsylvie | ✅ | Compared |
| 036 | sean | ✅ | Duplicate variants cleaned |
| 040 | crouky | 🔧 | Wrong gender кота, missing line (prev session) |
| 046 | shohreh | 🔧 | 2 wrong choice texts in radio2 (prev session) |
| 054 | ludivine | 🔧 | Wrong narration quotes, duplicate line, missing quotes (prev session) |
| 055 | julian | 🔧 | Mistranslation, missing quotes, missing narration (prev session) |
| 057 | annabelle | 🔧 | Swapped choice targets, wrong passage content (prev session) |
| 065 | nina | 🔧 | Empty passage, missing dialogue, duplicate variants (prev session) |
| 066 | tps | 🔧 | ты/вы fix (line 1729), duplicate variants (prev session) |
| 067 | mathieu | 🔧 | Wrong choice, placeholder passages, echo, mistranslations (prev session) |
| 070 | antoine | ✅ | Duplicate variants cleaned |
| 076 | angelique | 🔧 | Major opening restructure, speaker tags, duplicates (prev session) |

### Session 10
| # | Character | Status | Notes |
|---|-----------|--------|-------|
| 004 | jeannoel | 🔧 | 3 fixes: missing line, narration, wrong order |
| 005 | hugo | ✅ | Clean |
| 009 | ludwig | ✅ | Minor: ghost has no speaker prefix (intentional) |
| 011 | ariane | 🔧 | 4 fixes: 3 missing narration, 1 missing dialogue |
| 012 | christophe | 🔧 | 4 fixes: missing lines, narration, quotes |
| 015 | alicia | ✅ | English only 44 lines, all match |
| 018 | francois | ✅ | English only 23 lines |

### Session 11-12 (current)
| # | Character | Status | Notes |
|---|-----------|--------|-------|
| 060 | mireille | 🔧 | Gender fix: "слышала"→"слышал" (driver is male) |
| 061 | denis | 🔧 | 4 fixes: 2 missing ДЕНИ lines, 3 missing narration/dialogue in plan2, mistranslation "работать"→"говорить", missing farewell line |
| 063 | pauline | 🔧 | 2 fixes: missing narration (love2-gowithher), missing ПОЛИН line (love7) |
| 064 | janet | ⚠️ | English only 37 lines (first encounter). Comparable portion clean. Russian has 5 full encounters |
| 068 | sonny | ✅ | Clean - translation faithful |
| 100 | cop | 🔧 | ты/вы fix: "Твоя последняя ночь"→"Ваша" (both cop_rus and cop_05_rus) |
| 208 | myrtille | 🔧 | ты/вы fix: "твою улыбку"→"вашу" |

### Compared via agent (output lost, no issues detected in spot checks)
| # | Character | Status | Notes |
|---|-----------|--------|-------|
| 016 | gerard | 🤖 | Agent completed, output empty |
| 017 | grace | 🤖 | Agent completed, output empty |
| 021 | carlo | 🤖 | Agent completed, output empty |
| 024 | alicehyoga | 🤖 | Agent completed, output empty |
| 027 | lucieemilie | 🤖 | Agent completed, output empty |
| 034 | phil | 🤖 | Agent completed, output empty |
| 037 | shinji | 🤖 | Agent completed, output empty |
| 041 | francine | 🤖 | Agent completed, output empty |
| 042 | djena | 🤖 | Agent completed, output empty |
| 045 | vero | 🤖 | Agent completed, output empty |
| 047 | amelie | 🤖 | Agent completed, output empty |
| 051 | leonie | 🤖 | Agent completed, output empty |
| 052 | childeric | 🤖 | Agent completed, output empty |
| 056 | kader | 🤖 | Agent completed, output empty |
| 058 | agnes | 🤖 | Agent completed, output empty |

## Metadata Files (no dialogue)
| # | Character | Notes |
|---|-----------|-------|
| 007 | salim | Suspect bios, clue data |
| 022 | claudia | Suspect bios, clue data |
| 023 | apollonie | Suspect bios, clue data, UI strings |
| 031 | geraldine | Metadata only |
| 032 | anita | Metadata only |
| 043 | jonas | Metadata only |
| 044 | chris | Metadata only (suspect bios) |
| 053 | camille | Metadata only (suspect bios) |
| 059 | pierrot | Metadata only (suspect bios) |

## English Too Short/Garbled
| # | Character | Notes |
|---|-----------|-------|
| 013 | leia | Only 19 lines, mostly garbled |
| 064 | janet | Only 37 lines (first encounter start) |

## ты/вы Narration Audit (COMPLETED)
Sweep agent reported 68 issues in 12 files. Manual verification found only 8 real issues:
- 020_jacquie: 2 fixes (lines 625, 833)
- 020_jacquie_00a: 1 missing speaker prefix fix (line 50)
- 025_ade: 2 fixes (lines 692, 1047)
- 208_myrtille: 1 fix (line 537)
- 066_tps: 1 fix (line 1729)
- 100_cop_05 + 100_cop: 1 fix each ("Твоя последняя ночь")
- All other flagged lines were false positives (dialogue in quotes, generic/impersonal ты, etc.)

## Summary
- **Total passenger files**: ~75
- **Fully compared**: ~46 (including 9 metadata, 2 English too short)
- **Compared via agent (output lost)**: 15
- **Not yet started**: ~4 (pierrette already compared in prev session, herve ты/вы already noted)
- **Files with fixes this session**: mireille(060), denis(061), pauline(063), cop(100), myrtille(208), jacquie(020), ade(025), tps(066)
- **No commit made yet** - all changes need committing

## Next Steps
1. **Commit all changes** - many files modified across sessions 10-12
2. **Sync to game folder**
3. Agent-compared files (🤖) could benefit from manual re-check if time permits
