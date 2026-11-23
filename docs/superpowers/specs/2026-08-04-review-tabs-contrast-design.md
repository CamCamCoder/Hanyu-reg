# Review Tabs Contrast Design

## Problem

In `DialogReviewBook`, the inactive tab text inherits a very light platform
color and blends into the warm background. Users can mistake "Tat ca cac bai"
for a disabled tab.

## Design

- Apply a stylesheet only to `DialogReviewBook.tabs`.
- Give inactive tabs a light neutral background and `PALETTE["ink2"]` text.
- Give the selected tab `PALETTE["accent"]` background and white text.
- Keep tab dimensions stable and preserve all existing tab behavior.
- Do not change the global theme or other dialogs.

## Verification

- Add an offscreen Qt test asserting the tab widget has explicit inactive and
  selected foreground/background colors.
- Run `tests/unit/test_review_dialog.py`, then the full unit suite.
