# Review Tabs Contrast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make both review-dialog tab labels readable by giving inactive and selected tabs explicit contrasting colors.

**Architecture:** Keep the change local to `DialogReviewBook.tabs`. Add one offscreen Qt regression test, then apply a small Qt stylesheet using the existing `PALETTE`; do not alter the global theme, import flow, or stored data.

**Tech Stack:** Python 3.12, PySide6, pytest

## Global Constraints

- Work only in `D:\Hanyu recognize\.worktrees\review-tabs-contrast`.
- Use TDD: observe the focused test fail before changing production code.
- Keep every pytest `--basetemp` inside the worktree.
- Do not call Vision, open a real SQLite database, or modify the PDF/import pipeline.
- Do not change `hanzi_app/ui/theme.py`; reuse its existing palette values.

---

## Task 1: Give Review Tabs Explicit Contrast

**Files:**
- Modify: `tests/unit/test_review_dialog.py`
- Modify: `hanzi_app/ui/screen_books.py:198`

- [ ] **Step 1: Add the failing regression test**

Add this import beside the existing UI imports:

```python
from hanzi_app.ui.theme import PALETTE
```

Add this test near the other `DialogReviewBook` construction tests:

```python
def test_review_tabs_have_explicit_readable_contrast(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        style = dialog.tabs.styleSheet()

        assert "QTabBar::tab" in style
        assert f"color: {PALETTE['ink2']}" in style
        assert "QTabBar::tab:selected" in style
        assert f"background: {PALETTE['accent']}" in style
        assert "color: white" in style
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
pytest tests/unit/test_review_dialog.py -k "review_tabs_have_explicit_readable_contrast" -v --basetemp=.pytest-tmp-tabs-red
```

Expected: FAIL because `dialog.tabs.styleSheet()` does not yet contain explicit tab colors.

- [ ] **Step 3: Add the minimal local stylesheet**

Immediately after `self.tabs = QTabWidget()` in `DialogReviewBook.__init__`, add:

```python
self.tabs.setStyleSheet(
    "QTabBar::tab {"
    f"background: {PALETTE['card']}; color: {PALETTE['ink2']}; "
    f"border: 1px solid {PALETTE['line']}; padding: 7px 14px;"
    "}"
    "QTabBar::tab:selected {"
    f"background: {PALETTE['accent']}; color: white;"
    "}"
)
```

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run:

```powershell
pytest tests/unit/test_review_dialog.py -k "review_tabs_have_explicit_readable_contrast" -v --basetemp=.pytest-tmp-tabs-green
```

Expected: PASS.

- [ ] **Step 5: Run the complete review-dialog test file**

Run:

```powershell
pytest tests/unit/test_review_dialog.py -v --basetemp=.pytest-tmp-review-dialog
```

Expected: all tests pass.

- [ ] **Step 6: Run the full unit suite and inspect the diff**

Run:

```powershell
pytest tests/unit -q --basetemp=.pytest-tmp-unit
git diff --check
git diff -- tests/unit/test_review_dialog.py hanzi_app/ui/screen_books.py
```

Expected: the unit suite passes, `git diff --check` prints nothing, and the diff contains only the regression test plus the local tab stylesheet.

- [ ] **Step 7: Commit the fix**

```powershell
git add tests/unit/test_review_dialog.py hanzi_app/ui/screen_books.py
git commit -m "fix: improve review tab contrast"
```
