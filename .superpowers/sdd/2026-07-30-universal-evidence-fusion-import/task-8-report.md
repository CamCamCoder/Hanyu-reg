# Task 8 Report — Targeted AI Budget, Checkpoint and Resume

## Scope

Modified:

- `hanzi_app/adapter/aiclient.py`
- `hanzi_app/service/vocab.py`
- `hanzi_app/service/importer.py`
- `hanzi_app/data/userdb.py`
- `tests/unit/test_aiclient.py`
- `tests/unit/test_universal_engine.py`

No network, Vision API, real PDF, or live SQLite database was used.

## TDD Evidence

Initial RED command covered issue context, the three-request lesson budget,
consumed 429 attempts, and block resume. Result: 4 failed for the expected
missing interface/helper/checkpoint behavior.

GREEN:

- Initial Task 8 targets: 4 passed.
- Legacy fallback plus block-resume compatibility: 2 passed.
- Resume-budget and shorter-checkpoint regressions: 2 passed.
- Persisted manifest/crop reuse: 1 passed.
- Task 8 module regression: 126 passed.
- Final unit suite: 302 passed, 1 skipped.

All pytest runs used a worktree-local `--basetemp` directory.

## Implementation

- Vision vocabulary calls now accept validator issue context and perform exactly
  one HTTP request; retry policy moved to `VocabExtractor.extract_blocks()`.
- Block extraction shares a maximum of three AI attempts per lesson, counts
  empty/error/429 requests, stops immediately on 429, and carries attempt counts
  into persisted block state.
- `VocabImporterWorker` creates or reloads persisted block manifests and crops,
  resumes only unfinished blocks, checkpoints rows before status, preserves a
  longer existing block result, and uses `book_import_complete()` for the final
  transition to `review`.
- Books with incomplete block coverage remain `incomplete`; failures before any
  manifest exists retain the legacy `review_bounds` recovery state.
