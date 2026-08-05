import sys
import threading
from pathlib import Path
from unittest.mock import Mock

from hanzi_app import main


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


def test_debug_batch_captures_unbuffered_python_output():
    script = (ROOT / "chay-app-go-loi.bat").read_text(encoding="utf-8")
    assert 'set "HANZI_DEBUG=1"' in script
    assert "debug-latest.log" in script
    assert "-u -X faulthandler -m hanzi_app.main" in script
    assert "2>&1" in script
