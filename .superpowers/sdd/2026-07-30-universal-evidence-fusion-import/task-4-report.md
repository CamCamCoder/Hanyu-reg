# Task 4 report — Boundary Dialog CRUD and Validation UX

## Status

Complete.

## Commit

`df9dab74364ea0cf7587440b65471d4e1320287b feat: make lesson boundary review repairable`

## Files

- `hanzi_app/ui/dialog_import.py`
- `tests/unit/test_review_dialog.py`

## Verification

RED:

```text
$ pytest tests/unit/test_review_dialog.py -k "boundary_dialog_can or shows_evidence" -v --basetemp .pytest-task4-red
2 failed, 16 deselected
```

The failures were the intended missing `btn_confirm` and unsupported fourth
`split_result` constructor argument.

Reviewer regression RED:

```text
$ pytest tests/unit/test_review_dialog.py -k "reversed_page_range or deleting_every_lesson" -v --basetemp .pytest-task4-rereview-red
2 failed, 18 deselected
```

Final:

```text
$ pytest tests/unit/test_review_dialog.py tests/unit/test_splitter.py -v --basetemp .pytest-task4-final
32 passed in 1.05s
```

`git diff --check` produced no whitespace errors before the final amend.

## Review and concerns

An independent read-only review found that the first implementation accepted
reversed page ranges and an empty lesson list. Both are now guarded in the
live dialog validation and covered by regression tests. Painting invalid cells
also required a re-entrancy guard because `QTableWidgetItem.setBackground()`
emits `itemChanged` in this Qt binding.

`toc_heading_conflict` remains a blocking `Splitter.validate()` error. The
task brief explicitly requires confirmation to stay disabled while validation
errors remain, but the current UI has no evidence-override control. A future
product decision is needed if manual confirmation should be allowed to resolve
an immutable TOC-versus-heading disagreement.

## Fix round 1 — manual evidence override

### Status

Complete.

### RED

```text
$ pytest tests/unit/test_review_dialog.py tests/unit/test_universal_engine.py -k "manual_override or refreshes_evidence or ignores_missing_source or invalid_conflict" -v --basetemp .pytest-task4-fix1-red
3 failed, 1 passed, 44 deselected
```

The failed cases confirmed that the dialog did not load an invalid nonempty
`SplitResult`, source text stayed tied to the original row, and the worker
emitted no repair signal for a nonempty invalid result. The partial-source
case was vacuous before the dialog could load the supplied result.

### GREEN and final verification

```text
$ pytest tests/unit/test_review_dialog.py tests/unit/test_universal_engine.py -k "manual_override or refreshes_evidence or ignores_missing_source or invalid_conflict" -v --basetemp .pytest-task4-fix1-green
4 passed, 44 deselected

$ pytest tests/unit/test_review_dialog.py tests/unit/test_splitter.py tests/unit/test_universal_engine.py -v --basetemp .pytest-task4-fix1-final
60 passed in 1.16s
```

### Changes

- Added the explicit `Dùng ranh giới đang nhập` action. It marks selected rows
  as `Thủ công` and substitutes auditable in-memory `BoundaryEvidence` records
  (`source='manual'`, confidence `1.0`, detail `Người dùng xác nhận`) for
  conflicting original lesson/page evidence during validation.
- New and duplicated rows are manual by default; source text refreshes after
  lesson-number edits and remains attached to the row through sorting.
- The dialog now loads `split_result.boundaries` when the database has no
  lessons, so a nonempty invalid proposal is repairable.
- The phase-one worker now transitions a nonempty invalid proposal to
  `review_bounds` and emits it without persisting lessons. Empty proposals and
  exceptions keep their existing failure/recovery flow.
- Guarded partial `QTableWidgetItem` cells when coloring errors and copying or
  sorting rows.

### Remaining concern

The manual evidence is intentionally session-scoped: the schema has no
boundary-evidence storage and this round was explicitly barred from adding a
migration. Confirmed lesson boundaries are persisted as before; the manual
source evidence remains visible and validated only during this dialog session.

## Fix round 2 — preserve other lessons' shared-page evidence

### RED

```text
$ pytest tests/unit/test_review_dialog.py -k "manual_override_keeps_other" -v --basetemp .pytest-task4-fix2-red
1 failed, 23 deselected
```

The manual override for lesson 1 on page 5 removed a TOC evidence item for
lesson 2 that happened to use page 5, which could hide lesson 2's independent
TOC/heading conflict.

### Fix and verification

The manual replacement now removes original evidence by lesson number only.
It therefore replaces every source for the manually confirmed lesson, while
retaining evidence for any other lesson even if a source points at the same
page.

```text
$ pytest tests/unit/test_review_dialog.py -k "manual_override_keeps_other" -v --basetemp .pytest-task4-fix2-green
1 passed, 23 deselected

$ pytest tests/unit/test_review_dialog.py tests/unit/test_universal_engine.py -k "manual_override or refreshes_evidence or ignores_missing_source or invalid_conflict" -v --basetemp .pytest-task4-fix2-focused
5 passed, 44 deselected

$ pytest tests/unit/test_review_dialog.py tests/unit/test_splitter.py tests/unit/test_universal_engine.py -v --basetemp .pytest-task4-fix2-final
61 passed in 1.34s
```
