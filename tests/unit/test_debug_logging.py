import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hanzi_app import main
from hanzi_app.ui.dialog_import import DialogImport


ROOT = Path(__file__).resolve().parents[2]


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



def test_debug_handlers_record_tracebacks_and_allow_missing_thread(caplog):
    try:
        raise RuntimeError("python boom")
    except RuntimeError:
        python_info = sys.exc_info()

    try:
        raise ValueError("thread boom")
    except ValueError:
        thread_info = sys.exc_info()

    with caplog.at_level(logging.DEBUG):
        main._log_unhandled_exception(*python_info)
        main._log_thread_exception(
            SimpleNamespace(
                exc_type=thread_info[0],
                exc_value=thread_info[1],
                exc_traceback=thread_info[2],
                thread=None,
            )
        )
        main._log_qt_message("warning", None, "Qt diagnostic")

    crash_records = [
        record for record in caplog.records if record.name == "hanzi_app.crash"
    ]
    assert [record.exc_info[0] for record in crash_records] == [RuntimeError, ValueError]
    assert "<unknown>" in crash_records[1].getMessage()
    assert any(
        record.name == "hanzi_app.qt" and "Qt diagnostic" in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
def test_debug_batch_truncates_log_and_captures_exit_code(tmp_path):
    script = ROOT / "chay-app-go-loi.bat"
    launcher = tmp_path / script.name
    launcher.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "python.bat").write_text(
        "@echo stdout from fake python\n@echo stderr from fake python 1>&2\n@exit /b 23\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "debug-latest.log"
    log_path.write_text("stale log", encoding="utf-8")
    env = os.environ | {"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}

    result = subprocess.run(
        ["cmd", "/d", "/c", "echo.| call chay-app-go-loi.bat"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    log = log_path.read_text(encoding="utf-8")
    assert result.returncode == 23
    assert "stale log" not in log
    assert "stdout from fake python" in log
    assert "stderr from fake python" in log
    assert "=== Exit code: 23 ===" in log


def test_normal_mode_import_failure_is_silent_without_logging_handlers(capsys):
    class _ProgressBar:
        def setValue(self, _value):
            return None

    class _Label:
        def setText(self, _text):
            return None

    class _Button:
        def setEnabled(self, _enabled):
            return None

    class _FakeDialog:
        progress_bar = _ProgressBar()
        lbl_status = _Label()
        btn_chon = _Button()

    root = logging.getLogger()
    handlers = root.handlers[:]
    root.handlers.clear()
    try:
        DialogImport._on_failed(_FakeDialog(), "expected failure")
        assert capsys.readouterr().err == ""
    finally:
        root.handlers[:] = handlers