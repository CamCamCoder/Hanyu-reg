"""Kiểm thử unit cho adapter/pdfsource.py và adapter/ocr.py."""

from pathlib import Path
import pytest
import fitz

from hanzi_app.adapter.ocr import OcrAdapter
from hanzi_app.adapter.pdfsource import PdfSource
from hanzi_app.data.models import TextSpan


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
