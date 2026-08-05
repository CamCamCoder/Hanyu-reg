# Command Debug Log Final Fix Report

## RED Evidence

Command:

```powershell
pytest tests/unit/test_debug_logging.py -q --basetemp=.pytest-tmp-debug-log-final-red
```

Output: `3 failed, 3 passed in 0.43s`.

- `_log_thread_exception` raised `AttributeError` when `args.thread` was `None`.
- Normal-mode `DialogImport._on_failed()` emitted `Import failed in UI: expected failure` to stderr through `logging.lastResort`.
- The initial batch harness invocation exposed a quoting issue; after exercising the batch by name, it showed that the exit-code footer was not written to the log until the batch redirection and return behavior were corrected.

## GREEN Evidence

Commands:

```powershell
pytest tests/unit/test_debug_logging.py -q --basetemp=.pytest-tmp-debug-log-final-green
pytest tests/unit/test_universal_engine.py tests/unit/test_review_dialog.py tests/unit/test_pdfsource.py tests/unit/test_vocab.py -q --basetemp=.pytest-tmp-debug-log-final-affected
git diff --check
```

Outputs:

- `5 passed in 0.35s`
- `113 passed in 4.06s`
- `git diff --check` exited 0.

## Changed Files

- `chay-app-go-loi.bat`: truncates and appends to the log with valid redirection, and returns from a command shim before recording its exit code.

## Privacy And Normal Mode

The logging calls retain only existing book, lesson, PDF-path, progress, title, and exception metadata. They do not log API keys, AI request bodies, raw OCR, or SQLite content. With no root handlers, import logging is skipped, so `logging.lastResort` cannot write normal-mode diagnostics to stderr. Debug mode installs a root handler and continues to capture the same worker/UI records.

## Commit And Concerns

Commit: `HEAD` (`fix: keep debug logging out of normal mode`).

Concerns: no full suite was run by request; only focused debug and affected Task 2 groups were run. No real PDF, SQLite, AI, or book crops were accessed.
