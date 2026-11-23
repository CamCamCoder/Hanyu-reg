# Inline Vocabulary Block Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the generic locator to find detached, interleaved, column-inferred, and single-line parallel vocabulary boxes without book-specific rules.

**Architecture:** Extend the private evidence helpers in `vocab.py`: normalize exact heading tokens independently from line position, preserve heading anchors while forming vertical regions, and treat repeated Hanzi X centers or parallel order labels as table evidence. Keep `VocabExtractor.locate_blocks()` and all downstream interfaces unchanged.

**Tech Stack:** Python 3.12, PySide6 project models, pytest 9.1.1

## Global Constraints

- Work only in `D:\Hanyu recognize\.worktrees\hsk-inline-vocab`.
- Modify production logic only in `hanzi_app/service/vocab.py` and tests only in `tests/unit/test_vocab.py`.
- Do not hard-code a book title, page number, PDF path, or measured coordinate from the acceptance PDF.
- Do not call Vision, write a real SQLite database, add a dependency, or scan the full book.
- Use TDD and keep every pytest `--basetemp` inside the worktree.

---

### Task 1: Preserve Split And Interleaved Heading Anchors

**Files:**
- Modify: `tests/unit/test_vocab.py`
- Modify: `hanzi_app/service/vocab.py:116-390`

**Interfaces:**
- Consumes: `_line_groups(spans)`, `_compact_line(spans)`, `_signal_line(line)`.
- Produces: unchanged `_line_has_vocab_heading(spans) -> bool` and `_split_page_regions(spans) -> list[list[TextSpan]]`.

- [ ] **Step 1: Add failing tests for detached and interleaved headings**

```python
def test_locator_joins_split_heading_to_rows_after_large_initial_gap():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("生", 20, 40, 20),
        _span("词", 45, 40, 20),
        _span("你好", 80, 300, 45),
        _span("ni3 hao3", 160, 300, 80),
        _span("谢谢", 80, 330, 45),
        _span("xie4xie", 160, 330, 80),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(17, "Lesson 17", 0, 0, 1.0, "lesson")
    )

    assert len(blocks) == 1
    assert blocks[0].expected_rows == 2
    assert blocks[0].bbox[1] < 50
    assert blocks[0].bbox[3] > 330


def test_locator_accepts_heading_tokens_interleaved_with_first_row():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("谢谢", 20, 40, 45),
        _span("New", 120, 40, 45),
        _span("Words", 170, 40, 55),
        _span("xie4xie", 250, 40, 80),
        _span("不客气", 20, 80, 55),
        _span("bu2 ke4qi", 120, 80, 90),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(18, "Lesson 18", 0, 0, 1.0, "lesson")
    )

    assert len(blocks) == 1
    assert blocks[0].expected_rows == 2
```

- [ ] **Step 2: Run both tests and confirm RED**

```powershell
pytest tests/unit/test_vocab.py -k "joins_split_heading or heading_tokens_interleaved" -v --basetemp=.pytest-tmp-inline-heading-red
```

Expected: both fail because the first heading is separated into another vertical band and the second marker is not at the start of the compact line.

- [ ] **Step 3: Implement exact token-sequence heading recognition**

Normalize each span independently. Preserve the existing compact-prefix rule, then recognize an exact marker formed by one to three adjacent normalized span tokens anywhere in the line. Do not match a partial token such as `new` alone.

- [ ] **Step 4: Join a heading-only band to nearby table rows**

In `_split_page_regions`, compute all lines once. Include repeated Hanzi-column lines as signals. When a gap exceeds the ordinary row gap, keep the next band attached only when the preceding band contains a heading, has fewer than two data rows, and the gap is no larger than `max(240.0, median_height * 12)`. Preserve the existing split for a completed table followed by another table.

- [ ] **Step 5: Run focused and existing locator tests**

```powershell
pytest tests/unit/test_vocab.py -k "locator" -v --basetemp=.pytest-tmp-inline-heading-green
```

Expected: all locator tests pass.

---

### Task 2: Infer Logical Rows From Repeated Columns

**Files:**
- Modify: `tests/unit/test_vocab.py`
- Modify: `hanzi_app/service/vocab.py:185-489`

**Interfaces:**
- Produces: `_repeated_cjk_column_lines(lines) -> list[list[TextSpan]]`; no public API changes.
- Preserves: `VocabBlock.expected_rows`, `first_order`, and `last_order` semantics.

- [ ] **Step 1: Add failing tests for damaged pinyin and parallel entries**

```python
def test_locator_uses_repeated_hanzi_column_when_pinyin_is_unreadable():
    page = [_span("New Words", 20, 40, 100, 18)]
    for index, word in enumerate(("大家", "学生", "老师", "你们")):
        y = 90 + index * 35
        page.extend([
            _span(word, 80, y, 50),
            _span("@@", 170, y, 45),
            _span("meaning", 280, y, 80),
        ])
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = page

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(19, "Lesson 19", 0, 0, 1.0, "lesson")
    )

    assert len(blocks) == 1
    assert blocks[0].expected_rows == 4


def test_locator_counts_parallel_entries_on_one_physical_line():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("Vocabulary", 20, 40, 100, 18),
        _span("1", 20, 90, 20),
        _span("你好", 70, 90, 45),
        _span("ni3 hao3", 130, 90, 80),
        _span("2", 400, 90, 20),
        _span("谢谢", 450, 90, 45),
        _span("xie4xie", 510, 90, 80),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(20, "Lesson 20", 0, 0, 1.0, "lesson")
    )

    assert len(blocks) == 1
    assert (blocks[0].expected_rows, blocks[0].first_order, blocks[0].last_order) == (2, 1, 2)
```

- [ ] **Step 2: Run both tests and confirm RED**

```powershell
pytest tests/unit/test_vocab.py -k "repeated_hanzi_column or parallel_entries" -v --basetemp=.pytest-tmp-inline-columns-red
```

- [ ] **Step 3: Implement repeated Hanzi-column evidence**

Group the first CJK span of each non-heading line by X center with the locator's existing 35-pixel tolerance. Return the deterministic largest cluster only when it covers at least two distinct lines. Add those lines to region signals and row evidence; heading plus this repeated column is sufficient table evidence.

- [ ] **Step 4: Implement same-line parallel order evidence**

When vertical numeric clusters are absent, accept two or more distinct numeric labels from one line only inside a heading-anchored region. Require their sorted values to contain a consecutive pair. Use that line as order evidence and derive `first_order`, `last_order`, and `expected_rows` from the logical labels.

- [ ] **Step 5: Keep row counts conservative**

Set `expected_rows` from consecutive order evidence first, otherwise from repeated-column logical rows. Leave it `None` when only weak physical OCR lines are available. This prevents a partial OCR count from falsely satisfying coverage.

- [ ] **Step 6: Run all affected and full tests**

```powershell
pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -q --basetemp=.pytest-tmp-inline-regression
pytest tests/unit -q --basetemp=.pytest-tmp-inline-unit
git diff --check
```

Expected: affected tests and the full unit suite pass; `git diff --check` prints nothing.

- [ ] **Step 7: Update project status and commit**

Update `AGENTS.md` with the new acceptance fix and the fresh test totals, then commit only `AGENTS.md`, `hanzi_app/service/vocab.py`, and `tests/unit/test_vocab.py`.
