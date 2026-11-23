# Inline Vocabulary Block Detection Design

## Problem

Some scanned textbooks place several small vocabulary boxes inside a lesson
instead of one conventional table. OCR can split a heading into spans, mix the
heading and first row on one line, omit row numbers, or place the first data row
far below the heading. The current locator then returns no block or reports a
physical OCR line count as the expected vocabulary-row count.

The observed non-Boya acceptance book exposes all three cases, but the solution
must not contain its title, page numbers, coordinates, or a book-specific layout
template.

## Decision

Extend the existing evidence-fusion locator. A block is inferred from independent
heading and table-geometry evidence, then passed through the existing local,
selective-Vision, coverage, checkpoint, and manual-review pipeline.

Rejected alternatives:

- A per-book template is precise only for one edition and does not teach the
  importer a reusable layout rule.
- Relaxing heading text alone would confuse prose containing phrases such as
  "new words" with a vocabulary table.

## Heading Anchors

Heading recognition will normalize a complete OCR line and recognize exact
markers (`New Words`, `Vocabulary`, `生词`, `新词`, `Từ mới`) even when the marker
is split across adjacent spans or appears beside the first table row. A marker is
only heading evidence; it cannot make a block valid without table evidence.

The locator will preserve heading anchors separately from data lines so a heading
does not need to share a narrow vertical band with its first row.

## Region Formation

For each heading anchor, the locator will grow a candidate region downward to the
nearest table-like rows. The heading-to-first-row allowance is larger than the
normal row-to-row gap and scales from observed text height, while subsequent large
gaps still terminate the region. This joins a detached heading to its own box
without merging the following dialogue or exercise section.

Parallel mini-tables are separated by repeated X centers. Multiple order labels
on one physical line may seed horizontal regions even when each mini-table has
only one visible data row. Existing deterministic top-to-bottom, left-to-right
block ordering remains unchanged.

## Row Evidence And Coverage

The Hanzi column remains the only required content column. Pinyin, part of speech,
Han-Viet, and meanings strengthen evidence but may be absent or damaged by OCR.
Repeated X centers across two to seven columns provide table evidence independently
from headers and row numbers.

`expected_rows`, `first_order`, and `last_order` are populated only from reliable
logical-row evidence. A physical OCR line count is not used when a layout may hold
parallel entries. If the locator can identify a real box but cannot prove its row
count, it emits a block with unknown coverage; the existing pipeline then requests
selective evidence for that crop or leaves the block incomplete for review. It
must never silently turn that box into a successful zero-row lesson.

## Scope

Production changes stay in `hanzi_app/service/vocab.py`. Regression coverage stays
in `tests/unit/test_vocab.py`, with importer behavior covered only if an existing
contract needs adjustment. No schema migration, UI redesign, new dependency, real
SQLite write, full-book Vision run, or book-specific fixture is allowed.

## Verification

Tests will model these generic OCR shapes:

1. A split heading followed by a table after a large initial gap.
2. A heading interleaved with the first row on the same OCR line.
3. Side-by-side mini-tables whose order labels share one physical line.

Each new test must fail against the current locator for the diagnosed reason, then
pass after the smallest implementation change. Verification runs the focused new
tests, all of `test_vocab.py` and `test_universal_engine.py`, then the full unit
suite with `--basetemp` inside the worktree.
