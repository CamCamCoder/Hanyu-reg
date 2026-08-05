# Command Debug Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `chay-app-go-loi.bat` produce one self-contained `debug-latest.log` that captures startup failures, worker tracebacks, and the last visible import progress without requiring screenshots.

**Architecture:** The batch launcher owns the log file lifecycle and redirects both Python streams. `hanzi_app.main` only enables verbose logging and global exception hooks when `HANZI_DEBUG=1`; import workers log caught exceptions before emitting their existing Qt signals, while `DialogImport` logs the progress/result already shown to the user.

**Tech Stack:** Python 3.12 standard `logging`, `threading`, `faulthandler`; PySide6 6.11.1; Windows batch; pytest 9.1.1.

## Global Constraints

- Do not change `chay-app.bat` or normal application behavior.
- Do not open a real PDF, write real SQLite, or call Vision/AI.
- Never log API keys, AI request bodies, raw full-page OCR, or SQLite data.
- Use only the standard library, PySide6, and current project dependencies.
- Run every pytest command with `--basetemp` inside `D:\Hanyu recognize`.
- Preserve all unrelated untracked patch files and `book_crops/`.

---

### Task 1: Debug launcher and global exception hooks

**Files:**
- Create: `tests/unit/test_debug_logging.py`
- Modify: `hanzi_app/main.py`
- Modify: `chay-app-go-loi.bat`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: environment variable `HANZI_DEBUG=1` set only by the debug batch launcher.
- Produces: `configure_debug_logging() -> bool`; returns `True` only when debug hooks were installed. The launcher produces `debug-latest.log` in the repository root.

- [ ] **Step 1: Write failing contracts for disabled/enabled debug and the batch launcher**

Add tests that isolate global state and restore `sys.excepthook` and `threading.excepthook` after each assertion:

```python
def test_debug_logging_is_opt_in(monkeypatch):
    monkeypatch.delenv("HANZI_DEBUG", raising=False)
    assert main.configure_debug_logging() is False


def test_debug_logging_installs_python_and_thread_hooks(monkeypatch):
    monkeypatch.setenv("HANZI_DEBUG", "1")
    monkeypatch.setattr(main.logging, "basicConfig", Mock())
    monkeypatch.setattr(main, "qInstallMessageHandler", Mock())
    old_sys = sys.excepthook
    old_thread = threading.excepthook
    try:
        assert main.configure_debug_logging() is True
        assert sys.excepthook is main._log_unhandled_exception
        assert threading.excepthook is main._log_thread_exception
    finally:
        sys.excepthook = old_sys
        threading.excepthook = old_thread


def test_debug_batch_captures_unbuffered_python_output():
    script = (ROOT / "chay-app-go-loi.bat").read_text(encoding="utf-8")
    assert 'set "HANZI_DEBUG=1"' in script
    assert "debug-latest.log" in script
    assert "-u -X faulthandler -m hanzi_app.main" in script
    assert '2>&1' in script
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
pytest tests/unit/test_debug_logging.py -q --basetemp=.pytest-tmp-debug-log-red
```

Expected: failures because `configure_debug_logging` and the batch contract do not yet exist.

- [ ] **Step 3: Add minimal opt-in logging and hooks**

In `hanzi_app/main.py`, add standard logging plus these exact responsibilities:

```python
def _log_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
    logging.getLogger("hanzi_app.crash").critical(
        "Unhandled Python exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def _log_thread_exception(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("hanzi_app.crash").critical(
        "Unhandled thread exception: %s", args.thread.name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def configure_debug_logging() -> bool:
    if os.environ.get("HANZI_DEBUG") != "1":
        return False
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
        force=True,
    )
    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_thread_exception
    qInstallMessageHandler(_log_qt_message)
    logging.getLogger(__name__).info("Debug session started")
    return True
```

Implement `_log_qt_message` as a non-throwing adapter that records the Qt message and its message type without reading application data. Reconfigure both `sys.stdout` and `sys.stderr` to UTF-8 when their `reconfigure` method exists, then call `configure_debug_logging()` before creating `QApplication`.

- [ ] **Step 4: Make the batch own one fresh log**

Update `chay-app-go-loi.bat` to:

```bat
@echo off
setlocal
cd /d "%~dp0"
set "HANZI_DEBUG=1"
set "LOG_FILE=%~dp0debug-latest.log"
>"%LOG_FILE%" echo === Debug session: %date% %time% ===
python -u -X faulthandler -m hanzi_app.main >>"%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
>>"%LOG_FILE%" echo === Exit code: %EXIT_CODE% ===
echo Log da ghi tai: "%LOG_FILE%"
echo Ma thoat: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
```

Keep the existing `python` behavior; do not add a second launcher. Add `debug-latest.log` to `.gitignore`.

- [ ] **Step 5: Run Task 1 tests GREEN and regression**

Run:

```powershell
pytest tests/unit/test_debug_logging.py -q --basetemp=.pytest-tmp-debug-log-green
pytest tests/unit/test_pdfsource.py tests/unit/test_universal_engine.py -q --basetemp=.pytest-tmp-debug-log-task1
```

Expected: all pass; no debug log is created by the normal test process.

- [ ] **Step 6: Commit Task 1**

```powershell
git add .gitignore chay-app-go-loi.bat hanzi_app/main.py tests/unit/test_debug_logging.py
git commit -m "feat: capture app failures in debug log"
```

---

### Task 2: Preserve worker tracebacks and visible import progress

**Files:**
- Modify: `hanzi_app/service/importer.py`
- Modify: `hanzi_app/ui/dialog_import.py`
- Modify: `tests/unit/test_universal_engine.py`
- Modify: `tests/unit/test_review_dialog.py`

**Interfaces:**
- Consumes: the root logging configuration installed by Task 1.
- Produces: log records under `hanzi_app.service.importer` and `hanzi_app.ui.dialog_import`; existing Qt signals and UI messages remain unchanged.

- [ ] **Step 1: Add failing tests for a caught worker exception and dialog breadcrumbs**

Extend an existing `VocabImporterWorker` failure test with `caplog` and assert that a caught failure still has traceback data:

```python
with caplog.at_level(logging.ERROR, logger="hanzi_app.service.importer"):
    worker.run()

records = [r for r in caplog.records if r.name == "hanzi_app.service.importer"]
assert records
assert records[-1].exc_info is not None
assert "Vocabulary import failed" in records[-1].getMessage()
```

In `test_review_dialog.py`, call the real unbound callbacks with a small fake object containing `progress_bar`, `lbl_status`, and `btn_chon` test doubles:

```python
with caplog.at_level(logging.INFO, logger="hanzi_app.ui.dialog_import"):
    DialogImport._on_progress(fake, 65, "Dang OCR bai 1")
assert "65%" in caplog.text
assert "Dang OCR bai 1" in caplog.text

with caplog.at_level(logging.ERROR, logger="hanzi_app.ui.dialog_import"):
    DialogImport._on_failed(fake, "khong tim thay block")
assert "khong tim thay block" in caplog.text
```

- [ ] **Step 2: Run the new assertions and verify RED**

Run:

```powershell
pytest tests/unit/test_universal_engine.py tests/unit/test_review_dialog.py -q --basetemp=.pytest-tmp-debug-worker-red
```

Expected: the new logging assertions fail while existing behavioral assertions stay green.

- [ ] **Step 3: Log exceptions at worker boundaries**

Add `logger = logging.getLogger(__name__)` in `service/importer.py`. Immediately before each existing failure signal in `BookImporterWorker`, `VocabImporterWorker`, `VisionRepairWorker`, and `PreviewWorker`, call `logger.exception(...)`. Include only stable identifiers already held by the worker, for example:

```python
logger.exception(
    "Vocabulary import failed: book_id=%s pdf=%s",
    self.book_id,
    self.pdf_path,
)
self.failed_import.emit(str(err))
```

Do not change exception handling, database state restoration, emitted strings, retries, or AI behavior.

- [ ] **Step 4: Log dialog progress and result without secrets**

Add a module logger in `ui/dialog_import.py` and preserve all UI behavior:

```python
def _on_progress(self, pct: int, msg: str) -> None:
    logger.info("Import progress: %d%% %s", pct, msg)
    self.progress_bar.setValue(pct)
    self.lbl_status.setText(msg)

def _on_failed(self, err: str) -> None:
    logger.error("Import failed in UI: %s", err)
    self.lbl_status.setText(f"Lỗi nhập sách: {err}")
    self.btn_chon.setEnabled(True)
```

Also log `_on_finished` with `book_id` and title. Never log `self._api_key` or `txt_api`.

- [ ] **Step 5: Run Task 2 tests GREEN and affected regression**

Run:

```powershell
pytest tests/unit/test_universal_engine.py tests/unit/test_review_dialog.py -q --basetemp=.pytest-tmp-debug-worker-green
pytest tests/unit/test_pdfsource.py tests/unit/test_vocab.py -q --basetemp=.pytest-tmp-debug-worker-affected
```

Expected: all pass and the logging records include `exc_info` for caught worker errors.

- [ ] **Step 6: Commit Task 2**

```powershell
git add hanzi_app/service/importer.py hanzi_app/ui/dialog_import.py tests/unit/test_universal_engine.py tests/unit/test_review_dialog.py
git commit -m "feat: trace import failures in debug mode"
```

---

### Task 3: Project verification and handoff state

**Files:**
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: both implementation commits and their verified test counts.
- Produces: one B7q status row and a next-session instruction telling the user to run `chay-app-go-loi.bat`, reproduce once, and report `xong`.

- [ ] **Step 1: Verify privacy and diff scope**

Run:

```powershell
rg -n "api_key|txt_api|request|raw OCR" hanzi_app/main.py hanzi_app/service/importer.py hanzi_app/ui/dialog_import.py
git diff HEAD~2 --check
git status --short
```

Inspect every logging call and confirm no secret-bearing values are arguments. Confirm unrelated patch files and `book_crops/` remain untouched.

- [ ] **Step 2: Run full verification**

Run:

```powershell
pytest -q --basetemp=.pytest-tmp-debug-log-full
```

Record the exact pass/skip count; do not infer it from earlier runs.

- [ ] **Step 3: Update AGENTS.md with evidence**

Add B7q describing command debug logging, exact test counts, and no real PDF/SQLite/AI use. Set the next session to user acceptance: close the old app, run `chay-app-go-loi.bat`, reproduce the import failure once, then report `xong` so the agent reads `debug-latest.log`.

- [ ] **Step 4: Request independent review**

Reviewer checks the two implementation commits against the design, with findings ordered Critical, Important, Minor. Fix all Critical/Important findings with TDD before proceeding.

- [ ] **Step 5: Run verification-before-completion and commit state**

Run the full suite and `git diff --check` again after any review fixes, then:

```powershell
git add AGENTS.md
git commit -m "docs: record command debug logging"
```

Do not claim the original app import bug is fixed. Claim only that diagnostic capture is ready until the user reproduces it and the log identifies the current failure.
