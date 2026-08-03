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