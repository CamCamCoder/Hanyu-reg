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
