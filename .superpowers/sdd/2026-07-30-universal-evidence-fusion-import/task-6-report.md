# Task 6 Report — Multi-Block Locator and Atomic Crop Storage

## Scope

Implemented only Task 6 interfaces in the isolated worktree at HEAD `bcdfbfc`:

- `VocabExtractor.locate_blocks(pdf, lesson) -> list[VocabBlock]`
- `render_block_crop(pdf, block, dpi=250) -> bytes`
- `_write_crop_atomic(root, book_id, lesson_id, block_no, data) -> str`

No live PDF, `user.sqlite`, HSK data, network API, or dependency was used or modified.

## TDD evidence

### RED 1 — missing Task 6 interfaces

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -k "locator_finds or crop_writer" -v --basetemp .pytest-tmp-task6-red
```

Result: collection failed with 2 expected `ImportError`s because `render_block_crop` and `_write_crop_atomic` did not exist.

### GREEN 1 — core locator/crop behaviors

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -k "locator or crop_writer or render_block_crop" -v --basetemp .pytest-tmp-task6-green2
```

Result: `8 passed, 28 deselected`.

### RED 2 — folio must not become a vocabulary order

Command:

```powershell
pytest tests/unit/test_vocab.py -k "deterministic_order" -v --basetemp .pytest-tmp-task6-folio-red
```

Result: 1 expected failure; a right-edge folio `99` was initially counted as the third row/order of block 2.

### GREEN 2 — geometric order column

Command:

```powershell
pytest tests/unit/test_vocab.py -k "deterministic_order" -v --basetemp .pytest-tmp-task6-folio-green
```

Result: `1 passed, 8 deselected`.

### Required regression

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v --basetemp .pytest-tmp-task6-regression2
```

Result: `36 passed`.

### Full unit regression

Command:

```powershell
pytest tests/unit -q --basetemp .pytest-tmp-task6-all-unit
```

Result: `274 passed, 1 skipped in 4.58s`.

## Decisions

- A region is accepted only when at least two of heading, repeated Hanzi+pinyin rows, and geometric structure are present.
- Every lesson page is scanned; headings split multiple blocks on one page into independent vertical regions.
- Numeric orders are taken from the dominant aligned x-column, preventing a page folio from changing `expected_rows`, `first_order`, or `last_order`.
- Results are sorted by `(page_index, bbox_y)` and assigned deterministic 1-based `block_no`; database IDs remain `None` until Task 5 persistence APIs assign them.
- Crop rendering forwards the exact page, bbox, and DPI from the block manifest.
- Crop writes use a sibling `.png.tmp`, atomic `Path.replace()`, and remove the temporary file on failure while preserving an existing final crop.

## Environment note

The Windows deny-read ACL blocked the normal `apply_patch` helper even after narrow escalation. File changes were therefore applied only inside the authorized Task 6 worktree under narrow escalated filesystem access. No paths outside the worktree were written.
## Fix round 1/5 — reviewer findings

### Root causes

1. Same-page segmentation used only heading Y coordinates, so one heading plus a later table and two side-by-side titled tables were collapsed into one manifest block.
2. `_is_pinyin_text()` accepted arbitrary Latin prose, while the row and aligned-column signals reused the same two spans and were not independent.
3. Generic heading markers `新词` and `Vocabulary` were absent.

### RED — all findings reproduced with real UTF-8 fixtures

Command:

```powershell
pytest tests/unit/test_vocab.py -k "vertically_separated or side_by_side or two_column_dialogue or generic_heading" -v --basetemp .pytest-tmp-task6-fix1-red-utf8
```

Result: `4 failed, 9 deselected`. The test source was inspected before the run and contained real UTF-8 `词`, `cí`, `新词`, `我`, `wǒ`, `门`, `mén`, `你好`, `再见`, and `Bài` strings.

### GREEN — focused reviewer cases

Command:

```powershell
pytest tests/unit/test_vocab.py -k "vertically_separated or side_by_side or two_column_dialogue or generic_heading" -v --basetemp .pytest-tmp-task6-fix1-green
```

Result: `4 passed, 9 deselected`.

### Compatibility RED/GREEN

The first required regression run produced `39 passed, 1 failed`: the existing split `生` + `词` test uses text-only spans without `bbox`. This identified a compatibility assumption, not a locator geometry failure.

Command after the text-only fallback:

```powershell
pytest tests/unit/test_universal_engine.py -k "header_sinh_tu" -v --basetemp .pytest-tmp-task6-fix1-compat-green
```

Result: `1 passed, 26 deselected`.

### Final required regression

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v --basetemp .pytest-tmp-task6-fix1-regression2
```

Result: `40 passed`.

### Full unit regression

Command:

```powershell
pytest tests/unit -q --basetemp .pytest-tmp-task6-fix1-all-unit
```

Result: `278 passed, 1 skipped in 5.57s`.

### Fix decisions

- Candidate regions are split first by a generic vertical whitespace threshold derived from line height, then by repeated numeric-column centers on X; multiple independent title centers provide the X fallback.
- Candidate order is deterministic by `(page_index, bbox_y, bbox_x)`.
- Latin evidence must be segmentable into Mandarin pinyin syllables; `hello` and `goodbye` no longer qualify.
- Without sequential STT, aligned structure requires a third repeated column in addition to Hanzi and pinyin, so a two-column dialogue cannot manufacture two signals from the same pair.
- Added `新词` and `Vocabulary` to the generic heading vocabulary; no textbook-specific page or title constants were introduced.
- Text-only legacy spans remain supported by heading detection without entering the geometric locator path.
## Fix round 2/5 — numbered pinyin and English ambiguity

### RED

Command:

```powershell
pytest tests/unit/test_vocab.py -k "numbered_pinyin or english_women or preserves_tone_marked" -v --basetemp .pytest-tmp-task6-fix2-red
```

Result: `2 failed, 1 passed, 13 deselected`.

- A vertically disjoint continuation using `ni3 hao3`, `zhong1guo2`, and `wo3` was not located because digits were outside the accepted pinyin alphabet.
- English `women` segmented as `wo` + `men`, so a three-column bilingual dialogue was incorrectly accepted as a block.
- Tone-marked `nǐhǎo` and distinctive plain `zhongguo` already passed and became the preservation test.

### GREEN

Command:

```powershell
pytest tests/unit/test_vocab.py -k "numbered_pinyin or english_women or preserves_tone_marked" -v --basetemp .pytest-tmp-task6-fix2-green
```

Result: `3 passed, 13 deselected`.

### Required regression

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v --basetemp .pytest-tmp-task6-fix2-regression
```

Result: `43 passed`.

### Full unit regression

Command:

```powershell
pytest tests/unit -q --basetemp .pytest-tmp-task6-fix2-all-unit
```

Result: `281 passed, 1 skipped in 5.50s`.

### Fix decisions

- Numbered pinyin accepts optional tone digits `0`–`5` after each syllable, including joined forms such as `zhong1guo2` and spaced forms such as `ni3 hao3`.
- Tone-marked pinyin remains strong evidence.
- Plain unspaced Latin must contain at least one pinyin-distinctive initial/final; this keeps `nihao`, `zhongguo`, and `ci`-style orthography while rejecting the English ambiguity `women`.
- Plain whitespace-separated input counts as a boundary signal only when every token is exactly one valid pinyin syllable, preventing a phrase such as `women men` from gaining confidence merely from spaces.
- No textbook-specific or English-word exception list was added.

## Fix round 3/5 — `u:` pinyin and independent block signals

### RED

Command:

```powershell
pytest tests/unit/test_vocab.py -k "u_colon or china_change" -v --basetemp .pytest-tmp-task6-fix3-red
```

Result: `2 failed, 16 deselected`.

- Numbered `u:` forms (`nu:3`, `lu:4`, spaced and compact) were rejected before
  segmentation because `:` was outside the accepted pinyin alphabet.
- `China` and `change` could both be segmented as plausible plain pinyin, so two
  CJK/Latin/Vietnamese prose rows manufactured both row and alignment signals.

### GREEN

Command:

```powershell
pytest tests/unit/test_vocab.py -k "u_colon or china_change" -v --basetemp .pytest-tmp-task6-fix3-green
```

Result: `2 passed, 16 deselected`.

### Required regression

Command:

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v --basetemp .pytest-tmp-task6-fix3-regression
```

Result: `45 passed in 0.63s`.

### Full unit regression

Command:

```powershell
pytest tests/unit -q --basetemp .pytest-tmp-task6-fix3-all-unit
```
Result: `283 passed, 1 skipped in 4.06s`.

### Fix decisions

- `u:` is accepted and normalized through the existing `u:` → `v` path before
  syllable segmentation, matching the project's pinyin service convention.
- Digit, tone mark, `u:`, and explicit valid syllable boundaries are strong
  pinyin evidence; distinctive unmarked plain pinyin is ambiguous evidence.
- Ambiguous Latin text alone no longer creates the row signal. It needs an
  independent vocabulary heading or sequential order column.
- Strong pinyin plus a genuine aligned third column still preserves legitimate
  no-heading/no-STT vocabulary tables.
