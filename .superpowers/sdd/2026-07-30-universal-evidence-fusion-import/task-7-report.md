# Task 7 Report — Block Extraction and Coverage Validator

## Scope

Modified only:

- `hanzi_app/service/vocab.py`
- `tests/unit/test_vocab.py`

No new dependency, live PDF, API, or database was used.

## TDD Evidence

RED:

`pytest tests/unit/test_vocab.py -k "coverage_rejects or different_blocks" -v --basetemp .pytest-task7-red`

Result: 2 failed for the expected missing methods
`validate_block_coverage` and `merge_block_rows`.

GREEN and regression:

- Focused Task 7: 7 passed.
- Required extraction regression: 50 passed.
- Full unit suite: 288 passed, 1 skipped.

## Implementation

- Added block-local extraction that attaches `source_block_id`, merges local
  and AI rows by the exact source-aware key, and preserves repeated words in
  different blocks.
- Added per-block coverage for empty results, missing order numbers, expected
  row thresholds, unknown expected counts, and exact duplicates.
- Kept the Hanzi cell as the only mandatory content column so optional pinyin,
  part-of-speech and meaning cells may remain `None`.

## Fix Round 1

Reviewer findings:

1. Header-free or unfamiliar-header tables were not truly inferred as 2-7
   columns because the fallback still depended on fixed positions.
2. `extract_blocks()` deduplicated before coverage validation, preventing raw
   exact duplicates from producing `abnormal_exact_duplicates`.

Root causes:

- The parser only had a recognized-header path plus a fixed-layout fallback;
  neither inferred column centers from repeated x positions.
- Coverage inspected only merged rows, after exact-key deduplication had erased
  duplicate evidence.

RED tests added before the implementation:

- `test_shifted_four_columns_without_recognized_headers_are_inferred`
- `test_two_columns_without_headers_keep_hanzi_as_only_required_field`
- `test_extract_blocks_reports_raw_exact_duplicates_before_dedup`

GREEN implementation:

- Clustered repeated x positions into 2-7 inferred column centers, selected
  the Hanzi column from CJK evidence, and treated order, pinyin and meaning as
  optional inferred columns.
- Checked exact duplicates independently in raw local and AI rows before
  validating the final deduplicated rows. Final output remains deduplicated by
  the exact source-aware key.

Verification:

- Three fix tests: 3 passed.
- `test_vocab.py` plus `test_universal_engine.py`: 53 passed.
- Full unit suite: 291 passed, 1 skipped.
- All pytest runs used a `--basetemp` directory inside the worktree.
## Fix Round 2

### Root Cause (before implementation)

The inferred parser began its body at the fixed fallback `header_y = 80`, so
headerless tables whose rows appeared above that coordinate produced no body
spans at all. For rows that did reach inference, the role assignment only kept
order, Hanzi, pinyin, and the final remaining column: it hard-coded `pos=None`
and never populated `hanviet_src`. It also chose the pinyin column by the sum of
per-cell pinyin evidence. Vietnamese meanings such as `xin chào` can be
segmentable as pinyin syllables, so a meaning-only column could win that score
and leave no remaining column to preserve the meaning.

### RED

Command:

`pytest tests/unit/test_vocab.py -k "headerless_two_column_table_does_not_depend_on_a_fixed_header_y or headerless_six_columns_preserve_pos_and_hanviet or headerless_meaning_column_is_not_misclassified_as_pinyin" -v --basetemp .pytest-task7-round2-red`

Result: 3 failed, 26 deselected. The failures reproduced the fixed-header-Y
empty result, omitted `pos` and `hanviet_src`, and Vietnamese meanings stored as
`pinyin_src` with `meaning_src=None`.
### GREEN

- Six focused Task 7 regressions: 6 passed.
- `test_vocab.py` plus `test_universal_engine.py`: 56 passed.
- Full unit suite: 294 passed, 1 skipped.
- All runs used a worktree-local `--basetemp` directory.
### Final 7-column regression

- RED: English meanings were returned as `hanviet_src`.
- GREEN: the first auxiliary column is retained as Hán-Việt when both English
  and Vietnamese meaning columns are present.
- Focused regression: 1 passed.
- Final unit suite after the last code change: 295 passed, 1 skipped.
