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
