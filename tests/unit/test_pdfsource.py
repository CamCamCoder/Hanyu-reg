"""Kiểm thử unit cho adapter/pdfsource.py và adapter/ocr.py."""

import base64
import json
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from hanzi_app.adapter.ocr import OcrAdapter, _WINDOWS_OCR_SCRIPT
from hanzi_app.adapter.pdfsource import PdfSource
from hanzi_app.data.models import PageEvidence, TextSpan


@pytest.fixture
def temp_pdf_path(tmp_path: Path) -> Path:
    """Tạo một file PDF tạm 2 trang: trang 1 có text native, trang 2 rỗng."""
    pdf_path = tmp_path / "test_sample.pdf"
    doc = fitz.open()

    # Trang 1: Có text native (dùng text Latin để kiểm thử không phụ thuộc font hệ thống)
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 100), "Lesson 1: Hello", fontsize=24)
    page1.insert_text((50, 150), "Ni hao - Xin chao", fontsize=12)

    # Trang 2: Trang rỗng (không có text native)
    doc.new_page(width=595, height=842)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_pdfsource_open_and_count(temp_pdf_path: Path):
    with PdfSource(temp_pdf_path) as pdf:
        assert pdf.page_count() == 2


def test_pdfsource_spans_native(temp_pdf_path: Path):
    with PdfSource(temp_pdf_path) as pdf:
        spans = pdf.spans(0)
        assert len(spans) >= 2
        texts = [s.text for s in spans]
        assert any("Lesson 1" in t for t in texts)
        assert all(isinstance(s, TextSpan) for s in spans)
        assert all(s.is_ocr is False for s in spans)


def test_pdfsource_summarize_pages(temp_pdf_path: Path):
    with PdfSource(temp_pdf_path) as pdf:
        summaries = pdf.summarize_pages()
        assert len(summaries) == 2
        assert summaries[0].pdf_page == 0
        assert summaries[0].max_size == 24.0
        assert "Lesson 1" in summaries[0].head


def test_pdfsource_invalid_file():
    with pytest.raises(FileNotFoundError):
        PdfSource("path/khong/ton/tai.pdf")


def test_ocr_adapter_fallback():
    ocr = OcrAdapter()
    assert ocr.is_available() is True


def test_windows_ocr_decodes_base64_json_without_console_codepage(monkeypatch):
    payload = [{
        "text": "\u8c22\u8c22",
        "x0": 10,
        "y0": 20,
        "x1": 30,
        "y1": 40,
    }]
    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    completed = SimpleNamespace(
        returncode=0,
        stdout=encoded,
        stderr="",
    )
    monkeypatch.setattr(
        "hanzi_app.adapter.ocr.subprocess.run",
        lambda *_args, **_kwargs: completed,
    )

    spans = OcrAdapter().ocr_png_bytes(b"png")
    assert [span.text for span in spans] == ["\u8c22\u8c22"]


def test_windows_ocr_script_encodes_utf8_json_as_base64():
    assert "ToBase64String" in _WINDOWS_OCR_SCRIPT
    assert "UTF8.GetBytes($json)" in _WINDOWS_OCR_SCRIPT


def test_windows_ocr_rejects_empty_stdout(monkeypatch):
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(
        "hanzi_app.adapter.ocr.subprocess.run",
        lambda *_args, **_kwargs: completed,
    )
    ocr = OcrAdapter()

    assert ocr.ocr_png_bytes(b"png") == []
    assert ocr._windows_available is False


def test_pdfsource_get_page_half_images(temp_pdf_path: Path):
    with PdfSource(temp_pdf_path) as pdf:
        images = pdf.get_page_half_images(0)
        assert isinstance(images, list)
        assert len(images) >= 1
        assert isinstance(images[0], bytes)


def test_pdfsource_stacks_images_with_bounded_width(temp_pdf_path: Path):
    """Two page crops become one valid image without exceeding the requested width."""
    with PdfSource(temp_pdf_path) as pdf:
        first = pdf.get_page_image_bytes(0, dpi=72)
        second = pdf.get_page_image_bytes(1, dpi=72)
        combined = pdf.stack_image_bytes([first, second], max_width=400)

    image = fitz.Pixmap(combined)
    assert image.width == 400
    assert image.height > image.width


def test_page_census_classifies_pages_and_reads_toc(monkeypatch, temp_pdf_path):
    """Census uses inexpensive page bands and limits full-page OCR to the TOC."""
    full_ocr_calls: list[int] = []

    with PdfSource(temp_pdf_path) as pdf:
        monkeypatch.setattr(
            pdf,
            "_band_text",
            lambda page, band: {
                (0, "top"): "Contents",
                (0, "bottom"): "1",
                (1, "top"): "Lesson 1 Hello",
                (1, "bottom"): "5",
            }[(page, band)],
        )

        def full_ocr(page: int) -> str:
            full_ocr_calls.append(page)
            return "Lesson 1 005"

        monkeypatch.setattr(pdf, "_full_ocr_text", full_ocr)
        evidence = pdf.page_census()

    assert evidence[0].is_toc_candidate is True
    assert evidence[0].toc_text == "Lesson 1 005"
    assert evidence[1].heading_lesson_no == 1
    assert evidence[1].printed_page == 5
    assert evidence[0].page_kind in {"native", "scan", "mixed"}
    assert full_ocr_calls == [0, 1]


def test_boundary_contact_sheet_is_bounded(temp_pdf_path):
    with PdfSource(temp_pdf_path) as pdf:
        evidence = [
            PageEvidence(0, "native", "Contents", "1", "Lesson 1 005",
                         1, None, None, True),
            PageEvidence(1, "native", "Lesson 1", "5", None,
                         5, 1, "Lesson 1", False),
        ]
        image = pdf.boundary_contact_sheet(evidence)
    pix = fitz.Pixmap(image)
    assert pix.width <= 1200
    assert pix.height > 0


def test_native_text_box_matches_rendered_250_dpi_crop(temp_pdf_path):
    with PdfSource(temp_pdf_path) as pdf:
        first = pdf.spans(0)[0]
        crop = fitz.Pixmap(pdf.get_page_crop_image_bytes(0, first.bbox))
        assert abs(crop.width - (first.bbox[2] - first.bbox[0])) <= 2
        assert min(crop.samples) < 50
        assert first.bbox[0] == pytest.approx(50 * 250 / 72)


def test_windows_ocr_starts_powershell_without_a_console(monkeypatch):
    import subprocess

    no_window = 0x08000000
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", no_window, raising=False)

    def run(command, *, creationflags, **kwargs):
        assert command[0] == "powershell"
        assert creationflags & no_window
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    assert OcrAdapter().ocr_png_bytes(b"png") == []
