# Stale Vocabulary Manifest Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent invalid STT evidence from entering manifests and safely repair already-persisted automatic blocks during resume.

**Architecture:** `VocabExtractor` produces only positive, fully consecutive order ranges and blocks ambiguous coverage. `VocabImporterWorker` detects stale records, uniquely matches them to fresh locator results by page/IoU, writes fresh crops atomically, then asks `UserDb` to repair matched blocks in one transaction while preserving ids and AI attempts.

**Tech Stack:** Python 3.12, PySide6, SQLite, pytest; no new dependencies.

## Global Constraints

- Code is implemented by Codex subagents; controller only coordinates and verifies.
- Do not open a real PDF, write real `user.sqlite`, or call AI/Vision.
- Preserve manual blocks and the sum of `ai_attempts`.
- Do not run Vision across the book or delete/re-import the book.
- Use `--basetemp` inside the worktree for every pytest command.
- Preserve unrelated patches and `book_crops/`.

---

### Task 1: Strict order evidence and blocking coverage

**Files:**
- Modify: `hanzi_app/service/vocab.py`
- Modify: `tests/unit/test_vocab.py`

**Interfaces:**
- Produces locator blocks whose order range is either two positive fully consecutive endpoints or `(None, None)`.
- Produces blocking coverage issues `duplicate_orders` and `expected_row_mismatch`.

- [ ] **Step 1: Add RED locator tests**

Use synthetic `TextSpan` data and the existing fake PDF pattern. Add one region containing heading/rows plus numeric evidence `0, 1, 3`; assert the located block does not persist `first_order`/`last_order`. Add a positive control `1, 2, 3` asserting range `1..3`.

- [ ] **Step 2: Add RED coverage tests**

```python
def test_coverage_rejects_duplicate_orders_with_different_rows():
    block = VocabBlock(7, 2, 1, 10, (0, 0, 100, 200), None, 2, 1, 2)
    rows = [_block_row("甲", 1, 7), _block_row("乙", 1, 7)]
    report = VocabExtractor().validate_block_coverage(block, rows, [], rows)
    assert report.passed is False
    assert "duplicate_orders" in report.issues


def test_coverage_rejects_extra_rows():
    block = VocabBlock(7, 2, 1, 10, (0, 0, 100, 200), None, 2, 1, 2)
    rows = [_block_row(str(i), i, 7) for i in range(1, 4)]
    report = VocabExtractor().validate_block_coverage(block, rows, [], rows)
    assert report.passed is False
    assert "expected_row_mismatch" in report.issues
```

- [ ] **Step 3: Run RED**

```powershell
pytest tests/unit/test_vocab.py -q --basetemp=.pytest-tmp-stale-task1-red
```

Expected: only the new strict-sequence/coverage assertions fail for the described missing behavior.

- [ ] **Step 4: Implement minimal locator rules**

- Filter `_numeric_column_clusters` candidates to integer values `>= 1`.
- Define `sequential` as `len(unique_orders) >= 2 and all(right == left + 1 ...)`.
- In `locate_blocks`, set `first_order` and `last_order` only when `sequential_orders` is true.
- Preserve existing aligned-row fallback for `expected_rows`.

- [ ] **Step 5: Implement blocking coverage**

Collect non-`None` final `order_no` values. Add `duplicate_orders` when their count differs from the set count. Add both `duplicate_orders` and `expected_row_mismatch` to the blocking set; do not change exact-key deduplication.

- [ ] **Step 6: Run GREEN and regression**

```powershell
pytest tests/unit/test_vocab.py -q --basetemp=.pytest-tmp-stale-task1-green
pytest tests/unit/test_universal_engine.py -q --basetemp=.pytest-tmp-stale-task1-regression
```

- [ ] **Step 7: Commit**

```powershell
git add hanzi_app/service/vocab.py tests/unit/test_vocab.py
git commit -m "fix: require strict vocabulary order evidence"
```

---

### Task 2: Atomic repair of stale persisted blocks

**Files:**
- Modify: `hanzi_app/data/userdb.py`
- Modify: `hanzi_app/service/importer.py`
- Modify: `tests/unit/test_userdb.py`
- Modify: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces `UserDb.repair_import_blocks(lesson_id: int, repairs: list[tuple[int, VocabBlock]]) -> list[dict]`.
- Importer considers automatic metadata stale for nonpositive, half-null, reversed, or range-length-mismatched endpoints.

- [ ] **Step 1: Add RED UserDb transaction tests**

Create blocks and rows in a temporary database. Repair one block and assert:

```python
assert repaired[0]["id"] == old_id
assert repaired[0]["ai_attempts"] == old_attempts
assert repaired[0]["first_order"] == 1
assert db.get_lesson_words(lesson_id) == []
```

Add a manual block case asserting `ValueError` and that both metadata and rows remain unchanged.

- [ ] **Step 2: Implement the atomic UserDb API**

Inside one `transaction()`:

1. Load every target id and verify it belongs to `lesson_id` and is not `manual`.
2. Perform all validation before the first delete/update.
3. Delete `lesson_word` only for the target block ids.
4. Update page, bbox, crop path, expected/order metadata and set status `pending`.
5. Do not update id, lesson id, block number, or `ai_attempts`.

Return `get_import_blocks(lesson_id)` after commit.

- [ ] **Step 3: Add RED importer recovery tests**

Using temporary SQLite plus fake PDF/locator:

- stale automatic record with `first_order=0` uniquely matches a fresh same-page block with IoU `>= 0.5`;
- repair preserves block id/attempts, clears old block rows, stores fresh metadata/crop and returns pending records;
- valid and manual records remain unchanged;
- tied/ambiguous or unmatched candidates raise an error containing `manifest_needs_review` before rows or metadata change.

- [ ] **Step 4: Implement stale detection and matching**

Add focused helpers in `service/importer.py`:

```python
def _manifest_record_stale(record: dict) -> bool: ...
def _bbox_iou(left: tuple[float, ...], right: tuple[float, ...]) -> float: ...
```

For nonmanual stale records, run `locate_blocks` once. Match only same-page candidates at IoU `>= 0.5`; the highest score must be unique and no fresh candidate may serve two old blocks. Validate the complete match set before writing crops or DB changes. On failure raise `RuntimeError("manifest_needs_review")`.

- [ ] **Step 5: Repair and resume safely**

For every validated pair, render the fresh block crop and save it through `_write_crop_atomic` under the existing book/lesson/block number. Build replacement `VocabBlock` values with fresh geometry/order metadata and the old id, block number and `ai_attempts`. Call `repair_import_blocks` once, then continue extraction using returned records. Skip manual records entirely.

- [ ] **Step 6: Run GREEN and affected regression**

```powershell
pytest tests/unit/test_userdb.py tests/unit/test_universal_engine.py -q --basetemp=.pytest-tmp-stale-task2-green
pytest tests/unit/test_vocab.py tests/unit/test_pdfsource.py -q --basetemp=.pytest-tmp-stale-task2-regression
```

- [ ] **Step 7: Commit**

```powershell
git add hanzi_app/data/userdb.py hanzi_app/service/importer.py tests/unit/test_userdb.py tests/unit/test_universal_engine.py
git commit -m "fix: repair stale vocabulary manifests on resume"
```

---

### Task 3: Verification and handoff

**Files:**
- Modify: `AGENTS.md`

- [ ] Run privacy/scope inspection and `git diff --check`.
- [ ] Run the full suite once with in-worktree `--basetemp`; record exact counts.
- [ ] Add B7r status and set the next step to user acceptance of Bài 3 only.
- [ ] Request a whole-branch independent review; fix Critical/Important findings with TDD.
- [ ] Re-run verification after review fixes and commit AGENTS.
- [ ] Do not claim the whole book or original import is complete until the user retries Bài 3.
