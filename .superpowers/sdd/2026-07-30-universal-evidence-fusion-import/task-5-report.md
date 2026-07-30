# Task 5 report — Migration 3 and persistent block manifest

## Scope completed

- Added schema migration 3 in `hanzi_app/data/migrate.py`.
  - Creates `import_block` with a unique `(lesson_id, block_no)` manifest key.
  - Rebuilds `lesson_word` with nullable `source_block_id` and without the old
    `UNIQUE(lesson_id, word)` constraint.
  - Copies every legacy `lesson_word.id` unchanged.
  - Temporarily saves non-null `progress.source_lw_id` values before the table
    rebuild and restores them afterwards.
  - Recreates `idx_lw_lesson`, `idx_lw_word`, and `idx_lw_lesson_word`.
- Added the five requested `UserDb` methods only:
  `replace_import_blocks`, `get_import_blocks`, `update_import_block`,
  `replace_vocab_block`, and `book_import_complete`.
- Added migration/manifest tests and updated the existing schema expectations
  from version 2 to version 3.

## TDD evidence

1. Wrote the migration, atomic-manifest, and book-completeness tests first.
2. RED command:

   ```powershell
   pytest tests/unit/test_userdb.py -k "migration_3 or replace_import_blocks" -v --basetemp .tmp-pytest-task5-red-verified
   ```

   Result: 2 failures, both because `UserDb.replace_import_blocks` did not
   exist. The test fixture was first corrected to create `schema_version`, so
   the failure represented the missing Task 5 behavior rather than invalid
   fixture setup.
3. GREEN command:

   ```powershell
   pytest tests/unit/test_userdb.py -k "migration_3 or replace_import_blocks or book_import_complete" -v --basetemp .tmp-pytest-task5-green-verified
   ```

   Result: 3 passed.

## Verification

All commands used a `--basetemp` directory inside this worktree. The temporary
directories were removed before committing.

```text
pytest tests/unit/test_userdb.py -v --basetemp .tmp-pytest-task5-userdb
58 passed in 1.04s

pytest tests/unit -v --basetemp .tmp-pytest-task5-unit
268 passed, 1 skipped in 5.93s

pytest -v --basetemp .tmp-pytest-task5-full
268 passed, 3 skipped in 5.49s
```

`test_migration_3_preserves_progress_source_and_allows_repeated_word` also
asserts `PRAGMA foreign_key_check` returns no rows.

## Decisions and concern

- The Task 5 brief's migration test creates one legacy `lesson_word` and then
  writes two new rows from two blocks. Its stated expected count of two rows
  conflicts with the simultaneous requirement to preserve every old
  `lesson_word.id`; preservation requires three rows. The test therefore
  asserts the exact IDs `[7, 8, 9]`, which verifies both preservation and
  repeated-word insertion.
- `book_import_complete` returns false for a book with no positive lesson, so a
  book cannot be marked complete vacuously before it has importable lessons.
- No live `user.sqlite`, HSK data, PDFs, or network API were opened or written.
- `update_import_block` is implemented with the exact requested signature; its
  first end-to-end use is scheduled by the later importer checkpoint task.
