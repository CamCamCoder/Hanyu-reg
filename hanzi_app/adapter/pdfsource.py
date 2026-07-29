"""Bọc PyMuPDF, che khác biệt giữa trang chữ và trang ảnh.

Tầng adapter duy nhất trực tiếp tương tác với PyMuPDF (fitz).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import fitz

from hanzi_app.adapter.ocr import OcrAdapter
from hanzi_app.data.models import PageSummary, TextSpan

# Biểu thức chính quy phát hiện ký tự CJK (chữ Hán).
RE_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


class PdfSource:
    """Bọc PyMuPDF bóc tách văn bản từ PDF.

    Che đi sự khác biệt giữa trang chữ (native text) và trang ảnh quét (OCR).
    """

    def __init__(self, path: str | Path, ocr_adapter: OcrAdapter | None = None) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp PDF: {self.path}")

        self._doc = fitz.open(str(self.path))
        self._ocr = ocr_adapter or OcrAdapter()

    def page_count(self) -> int:
        """Tổng số trang của tệp PDF."""
        return len(self._doc)

    def close(self) -> None:
        """Đóng tệp PDF."""
        if self._doc and not self._doc.is_closed:
            self._doc.close()

    def __enter__(self) -> PdfSource:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_page_image_bytes(self, page_index: int, dpi: int = 150) -> bytes:
        """Lấy dữ liệu ảnh PNG của trang PDF phục vụ Vision AI đọc ảnh."""
        if page_index < 0 or page_index >= len(self._doc):
            return b""
        page = self._doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("png")

    def get_page_crop_image_bytes(
        self,
        page_index: int,
        bbox: tuple[float, float, float, float],
        source_dpi: int = 250,
        dpi: int = 250,
    ) -> bytes:
        """Kết xuất đúng một vùng bảng; ``bbox`` dùng tọa độ ảnh OCR."""
        if page_index < 0 or page_index >= len(self._doc):
            return b""
        scale = 72.0 / source_dpi
        page = self._doc[page_index]
        rect = fitz.Rect(*(value * scale for value in bbox)) & page.rect
        if rect.is_empty:
            return b""
        return page.get_pixmap(dpi=dpi, clip=rect, alpha=False).tobytes("png")

    def stack_image_bytes(
        self, images: list[bytes], max_width: int = 1600
    ) -> bytes:
        """Ghép dọc các crop của cùng một bài và co chiều rộng để tránh ảnh quá lớn."""
        valid = [image for image in images if image]
        if not valid:
            return b""
        if max_width <= 0:
            raise ValueError("Chiều rộng ảnh ghép phải lớn hơn 0")

        sizes: list[tuple[int, int]] = []
        canvas_width = 0
        canvas_height = 0
        for image in valid:
            pix = fitz.Pixmap(image)
            width = min(pix.width, max_width)
            height = max(1, round(pix.height * width / pix.width))
            sizes.append((width, height))
            canvas_width = max(canvas_width, width)
            canvas_height += height

        document = fitz.open()
        try:
            page = document.new_page(width=canvas_width, height=canvas_height)
            top = 0
            for image, (width, height) in zip(valid, sizes):
                page.insert_image(
                    fitz.Rect(0, top, width, top + height),
                    stream=image,
                    keep_proportion=False,
                )
                top += height
            return page.get_pixmap(dpi=72, alpha=False).tobytes("png")
        finally:
            document.close()

    def get_page_vertical_section_image_bytes(
        self, page_index: int, section: str, dpi: int = 130
    ) -> bytes:
        """Kết xuất nửa trên/dưới để UI duyệt bảng không phải xem cả trang."""
        if page_index < 0 or page_index >= len(self._doc):
            return b""
        page = self._doc[page_index]
        mid = page.rect.y0 + page.rect.height / 2
        if section == "upper":
            clip = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, mid)
        elif section == "lower":
            clip = fitz.Rect(page.rect.x0, mid, page.rect.x1, page.rect.y1)
        else:
            clip = page.rect
        return page.get_pixmap(dpi=dpi, clip=clip, alpha=False).tobytes("png")

    def ocr_spans(
        self, page_index: int, language: str = "zh-Hans-CN", dpi: int = 250
    ) -> list[TextSpan]:
        """Chạy OCR chỉ định ngôn ngữ, dùng khi cần hợp nhất Trung–Anh."""
        image = self.get_page_image_bytes(page_index, dpi=dpi)
        return self._ocr.ocr_png_bytes(image, language=language)

    def get_page_half_images(self, page_index: int, dpi: int = 150) -> list[bytes]:
        """Tự động phát hiện trang đôi 2-in-1 (xếp dọc hoặc ngang) và tách thành từng trang lẻ."""
        if page_index < 0 or page_index >= len(self._doc):
            return []
        page = self._doc[page_index]
        rect = page.rect
        
        # Nếu chiều cao lớn hơn nhiều chiều rộng (2 trang in xếp dọc trên 1 trang PDF)
        if rect.height > rect.width * 1.2:
            half_h = rect.height / 2
            top_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + half_h)
            bot_rect = fitz.Rect(rect.x0, rect.y0 + half_h, rect.x1, rect.y1)
            
            img_top = page.get_pixmap(dpi=dpi, clip=top_rect).tobytes("png")
            img_bot = page.get_pixmap(dpi=dpi, clip=bot_rect).tobytes("png")
            return [img_top, img_bot]
            
        # Nếu là 2 trang in xếp ngang (rect.width > rect.height * 1.2)
        if rect.width > rect.height * 1.2:
            half_w = rect.width / 2
            left_rect = fitz.Rect(rect.x0, rect.y0, rect.x0 + half_w, rect.y1)
            right_rect = fitz.Rect(rect.x0 + half_w, rect.y0, rect.x1, rect.y1)
            
            img_left = page.get_pixmap(dpi=dpi, clip=left_rect).tobytes("png")
            img_right = page.get_pixmap(dpi=dpi, clip=right_rect).tobytes("png")
            return [img_left, img_right]

        pix = page.get_pixmap(dpi=dpi)
        return [pix.tobytes("png")]

    def spans(self, page_index: int) -> list[TextSpan]:
        """Lấy toàn bộ TextSpan trên trang ``page_index`` (đánh số từ 0).

        Nếu trang có text native, trích xuất trực tiếp. Nếu là trang quét
        hoặc không có text native, tự động chạy OCR.
        """
        if page_index < 0 or page_index >= len(self._doc):
            raise IndexError(f"Trang {page_index} nằm ngoài dải [0, {len(self._doc) - 1}]")

        page = self._doc[page_index]
        native_spans = self._extract_native_spans(page)

        # Text layer của sách scan thường chỉ chứa vài ký tự rác. Chỉ tin
        # native text khi có ít nhất 20 ký tự CJK như QT-02 bước 2.
        native_cjk = sum(len(RE_CJK.findall(s.text)) for s in native_spans)
        native_chars = sum(len(s.text) for s in native_spans)
        if native_cjk >= 20 or (native_chars >= 20 and not page.get_images(full=True)):
            return native_spans

        # Ngược lại: tự động gọi OCR
        return self._ocr.ocr_page(page)

    def _extract_native_spans(self, page: fitz.Page) -> list[TextSpan]:
        """Trích xuất các TextSpan từ trang text native."""
        spans: list[TextSpan] = []
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 là text block, 1 là image block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        bbox = tuple(span.get("bbox", (0, 0, 0, 0)))
                        font_size = float(span.get("size", 12.0))
                        spans.append(
                            TextSpan(
                                text=text,
                                bbox=bbox,
                                font_size=font_size,
                                is_ocr=False,
                            )
                        )
        return spans

    def summarize_pages(self) -> list[PageSummary]:
        """Tạo bản tóm lược toàn bộ các trang để phục vụ splitter."""
        summaries: list[PageSummary] = []
        for i in range(len(self._doc)):
            spans_list = self.spans(i)

            cjk_count = 0
            max_size = 0.0
            head_text = ""

            # Tìm max_size và tính cjk_count
            for s in spans_list:
                cjk_count += len(RE_CJK.findall(s.text))
                if s.font_size > max_size:
                    max_size = s.font_size

            # Head text: lấy các span ở 25% trên cùng trang, font to nhất
            top_spans = [
                s for s in spans_list
                if s.bbox[1] < 200  # y0 < 200 (phần trên trang)
            ]
            if top_spans:
                top_spans.sort(key=lambda s: s.font_size, reverse=True)
                head_text = top_spans[0].text[:30]

            summaries.append(
                PageSummary(
                    id=i + 1,
                    pdf_page=i,
                    folio=str(i + 1),
                    max_size=max_size,
                    head=head_text,
                    cjk=cjk_count,
                )
            )
        return summaries
