"""Bọc PyMuPDF, che khác biệt giữa trang chữ và trang ảnh.

Tầng adapter duy nhất trực tiếp tương tác với PyMuPDF (fitz).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

import fitz

from hanzi_app.adapter.ocr import OcrAdapter
from hanzi_app.data.models import PageEvidence, PageSummary, TextSpan

# Biểu thức chính quy phát hiện ký tự CJK (chữ Hán).
RE_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
RE_FOLIO = re.compile(r"\b(\d{1,4})\b")
RE_LESSON_HEADER = re.compile(
    r"(?:第\s*(\d+|[一二三四五六七八九十百]+)\s*课|^Bài\s+(\d+)|^Lesson\s+(\d+))",
    re.IGNORECASE,
)
CN_NUMS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
TOC_MARKERS = ("contents", "table of contents", "mục lục", "目录", "目錄")


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
        self._band_ocr_cache: dict[tuple[int, str], tuple[TextSpan, ...]] = {}

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

    def _band_text(self, page_index: int, band: str) -> str:
        """OCR the top or bottom 22% of a page at low resolution."""
        page = self._doc[page_index]
        band_height = page.rect.height * 0.22
        if band == "top":
            clip = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y0 + band_height)
        else:
            clip = fitz.Rect(page.rect.x0, page.rect.y1 - band_height, page.rect.x1, page.rect.y1)
        pix = page.get_pixmap(dpi=110, clip=clip, alpha=False)
        spans = tuple(self._ocr.ocr_png_bytes(pix.tobytes("png")))
        self._band_ocr_cache[(page_index, band)] = spans
        return " ".join(span.text for span in spans)

    def _full_ocr_text(self, page_index: int) -> str:
        """OCR one explicitly selected TOC page at a modest resolution."""
        page = self._doc[page_index]
        pix = page.get_pixmap(dpi=140, alpha=False)
        return " ".join(span.text for span in self._ocr.ocr_png_bytes(pix.tobytes("png")))

    def page_census(self) -> list[PageEvidence]:
        """Collect lightweight page signals before lesson splitting or extraction."""
        basic: list[dict[str, object]] = []
        toc_pages: set[int] = set()

        for page_index in range(len(self._doc)):
            page = self._doc[page_index]
            top_text = self._band_text(page_index, "top")
            bottom_text = self._band_text(page_index, "bottom")
            native_text = page.get_text("text").strip()
            has_useful_native_text = len(re.sub(r"\s+", "", native_text)) >= 20
            has_images = bool(page.get_images(full=True))
            lesson_no, title = self._heading(top_text)
            is_toc_candidate = self._is_toc_candidate(top_text)
            if is_toc_candidate:
                toc_pages.add(page_index)

            basic.append(
                {
                    "pdf_page": page_index,
                    "page_kind": self._page_kind(has_useful_native_text, has_images),
                    "top_text": top_text,
                    "bottom_text": bottom_text,
                    "printed_page": self._printed_page(bottom_text),
                    "heading_lesson_no": lesson_no,
                    "heading_title": title,
                    "is_toc_candidate": is_toc_candidate,
                    "layout_fingerprint": self._layout_fingerprint(
                        page,
                        self._band_ocr_cache.get((page_index, "top"), ()),
                    ),
                }
            )

        toc_ocr_pages = {
            page_index + offset
            for page_index in toc_pages
            for offset in range(4)
            if page_index + offset < len(self._doc)
        }
        toc_texts = {page_index: self._full_ocr_text(page_index) for page_index in toc_ocr_pages}

        return [
            PageEvidence(toc_text=toc_texts.get(item["pdf_page"]), **item)
            for item in basic
        ]

    def boundary_contact_sheet(self, evidence: list[PageEvidence]) -> bytes:
        """Render selected evidence pages in a four-column sheet no wider than 1200 px."""
        pages = [item.pdf_page for item in evidence if 0 <= item.pdf_page < len(self._doc)]
        if not pages:
            return b""

        columns = 4
        cell_width = 300.0
        cell_height = max(
            cell_width * self._doc[page_index].rect.height / self._doc[page_index].rect.width
            for page_index in pages
        )
        rows = (len(pages) + columns - 1) // columns
        sheet = fitz.open()
        try:
            output = sheet.new_page(width=columns * cell_width, height=rows * cell_height)
            for index, page_index in enumerate(pages):
                row, column = divmod(index, columns)
                source = self._doc[page_index].rect
                scale = min(cell_width / source.width, cell_height / source.height)
                width = source.width * scale
                height = source.height * scale
                left = column * cell_width + (cell_width - width) / 2
                top = row * cell_height + (cell_height - height) / 2
                output.show_pdf_page(
                    fitz.Rect(left, top, left + width, top + height),
                    self._doc,
                    page_index,
                    keep_proportion=True,
                )
            return output.get_pixmap(dpi=72, alpha=False).tobytes("png")
        finally:
            sheet.close()

    @staticmethod
    def _page_kind(has_useful_native_text: bool, has_images: bool) -> str:
        if has_useful_native_text and has_images:
            return "mixed"
        if has_useful_native_text:
            return "native"
        return "scan"

    @staticmethod
    def _printed_page(bottom_text: str) -> int | None:
        match = RE_FOLIO.search(bottom_text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_toc_candidate(top_text: str) -> bool:
        normalized = top_text.casefold()
        return any(marker in normalized for marker in TOC_MARKERS)

    @staticmethod
    def _heading(top_text: str) -> tuple[int | None, str | None]:
        match = RE_LESSON_HEADER.search(top_text.strip())
        if not match:
            return None, None
        number = next(group for group in match.groups() if group is not None)
        return PdfSource._lesson_number(number), top_text.strip()

    @staticmethod
    def _lesson_number(value: str) -> int:
        if value.isdigit():
            return int(value)
        if value in CN_NUMS:
            return CN_NUMS[value]
        if "十" in value:
            tens, _, ones = value.partition("十")
            return CN_NUMS.get(tens, 1) * 10 + CN_NUMS.get(ones, 0)
        return 1

    @staticmethod
    def _layout_fingerprint(page: fitz.Page, spans: tuple[TextSpan, ...]) -> str:
        """Hash a 12x4 occupancy grid of OCR boxes from the page's top band."""
        columns, rows = 12, 4
        occupied = [[False for _ in range(columns)] for _ in range(rows)]
        band_height = page.rect.height * 0.22 * 110 / 72
        band_width = page.rect.width * 110 / 72
        for span in spans:
            x0, y0, x1, y1 = span.bbox
            left = max(0, min(columns - 1, int(x0 * columns / band_width)))
            right = max(0, min(columns - 1, int(max(x0, x1 - 1) * columns / band_width)))
            top = max(0, min(rows - 1, int(y0 * rows / band_height)))
            bottom = max(0, min(rows - 1, int(max(y0, y1 - 1) * rows / band_height)))
            for row in range(top, bottom + 1):
                for column in range(left, right + 1):
                    occupied[row][column] = True
        grid = "".join("1" if cell else "0" for row in occupied for cell in row)
        return hashlib.sha256(grid.encode("ascii")).hexdigest()

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
