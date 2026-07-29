"""Bộ điều phối quy trình nhập sách (QT-02 & QT-03).

Chạy trong luồng nền để không làm đóng băng giao diện.
Tự mở kết nối UserDb riêng cho luồng nền để tránh lỗi SQLite threading.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from hanzi_app.adapter.aiclient import AiClient
from hanzi_app.adapter.pdfsource import PdfSource
from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import LessonBoundary
from hanzi_app.data.userdb import UserDb
from hanzi_app.service.splitter import Splitter
from hanzi_app.service.vocab import VocabExtractor


class BookImporterWorker(QThread):
    """Pha 1: nhận diện bài học, dừng lại để người dùng duyệt ranh giới."""

    progress = Signal(int, str)  # (phần trăm 0..100, thông điệp)
    boundaries_ready = Signal(int, str)  # (book_id, book_title)
    failed_import = Signal(str)  # (lý do lỗi)

    def __init__(
        self,
        pdf_path: str | Path,
        db_path: str,
        api_key: str | None = None,
        dict_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.db_path = db_path
        self.dict_path = dict_path
        self.ai_client = AiClient(api_key=api_key)

    def run(self) -> None:
        thread_db: UserDb | None = None
        try:
            thread_db = UserDb(self.db_path)

            self.progress.emit(10, "Mở tệp PDF và tính mã băm...")
            hasher = hashlib.md5()
            with open(self.pdf_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()

            book_title = self.pdf_path.stem

            self.progress.emit(20, "Trích xuất danh sách trang PDF...")
            with PdfSource(self.pdf_path) as pdf:
                page_count = pdf.page_count()

                existing_id = thread_db.find_book_by_hash(file_hash)
                if existing_id:
                    book_id = existing_id
                    thread_db.set_import_state(book_id, "importing")
                else:
                    book_id = thread_db.add_book(
                        title=book_title,
                        file_path=str(self.pdf_path),
                        file_hash=file_hash,
                        page_count=page_count,
                    )

                self.progress.emit(40, "Phân tích bản tóm lược các trang...")
                summaries = pdf.summarize_pages()

                mode_str = "Lớp 2 (Cloud AI)" if self.ai_client.is_configured() else "Lớp 1 (Local Engine)"
                self.progress.emit(60, f"Phân tách bài học [{mode_str}]...")
                splitter = Splitter()
                boundaries = splitter.split(summaries, ai_client=self.ai_client)

                # Nạp danh sách bài học vào DB
                thread_db.replace_lessons(book_id, boundaries)
                thread_db.set_import_state(book_id, "review_bounds")
                self.progress.emit(65, "Đã tìm ranh giới bài — hãy kiểm tra trước khi OCR.")
                self.boundaries_ready.emit(book_id, book_title)

        except Exception as err:
            self.failed_import.emit(str(err))
        finally:
            if thread_db:
                thread_db.close()


class VocabImporterWorker(QThread):
    """Pha 2: OCR bảng từ mới sau khi ranh giới bài đã được xác nhận."""

    progress = Signal(int, str)
    finished_import = Signal(int, str)
    failed_import = Signal(str)

    def __init__(
        self,
        book_id: int,
        pdf_path: str | Path,
        db_path: str,
        api_key: str | None = None,
        dict_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.book_id = book_id
        self.pdf_path = Path(pdf_path)
        self.db_path = db_path
        self.dict_path = dict_path
        self.ai_client = AiClient(api_key=api_key)

    def run(self) -> None:
        thread_db: UserDb | None = None
        thread_dict: DictDb | None = None
        try:
            thread_db = UserDb(self.db_path)
            if self.dict_path:
                thread_dict = DictDb(self.dict_path)
            book = thread_db.get_book(self.book_id)
            if book is None:
                raise ValueError("Không tìm thấy sách cần OCR")
            lessons = thread_db.get_lessons(self.book_id)
            thread_db.set_import_state(self.book_id, "extracting")
            extractor = VocabExtractor(thread_dict)
            mode = "Cloud AI" if self.ai_client.is_configured() else "Local Engine"
            with PdfSource(self.pdf_path) as pdf:
                for i, lesson in enumerate(lessons):
                    if lesson["index_no"] < 0:
                        continue
                    if thread_db.get_lesson_words(lesson["id"]):
                        pct = 65 + int((i + 1) / max(len(lessons), 1) * 34)
                        self.progress.emit(
                            pct,
                            f"Bỏ qua Bài {lesson['index_no']} đã có dữ liệu [{mode}]...",
                        )
                        continue
                    boundary = LessonBoundary(
                        index_no=lesson["index_no"],
                        title=lesson.get("title"),
                        page_start=lesson["page_start"],
                        page_end=lesson["page_end"],
                        confidence=float(lesson.get("confidence", 1.0)),
                        kind="review" if lesson["index_no"] < 0 else "lesson",
                    )
                    rows = extractor.extract_lesson(
                        pdf, boundary, ai_client=self.ai_client
                    )
                    if not rows:
                        raise RuntimeError(
                            f"Bài {lesson['index_no']} không trích xuất được từ mới; "
                            "đã giữ nguyên các bài hoàn thành trước đó."
                        )
                    thread_db.replace_vocab(lesson["id"], rows)
                    pct = 65 + int((i + 1) / max(len(lessons), 1) * 34)
                    self.progress.emit(
                        pct, f"Đã OCR bài {i + 1}/{len(lessons)} [{mode}]..."
                    )
            thread_db.set_import_state(self.book_id, "review")
            self.progress.emit(100, "Đã OCR — hãy duyệt các dòng từ mới.")
            self.finished_import.emit(self.book_id, book["title"])
        except Exception as err:
            if thread_db:
                thread_db.set_import_state(self.book_id, "review_bounds")
            self.failed_import.emit(str(err))
        finally:
            if thread_db:
                thread_db.close()
            if thread_dict:
                thread_dict.close()


class VisionRepairWorker(QThread):
    """Ép Vision đọc lại crop bảng từ mới của đúng một bài."""

    finished_rows = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        pdf_path: str | Path,
        lesson: LessonBoundary,
        api_key: str,
        dict_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.lesson = lesson
        self.dict_path = dict_path
        self.ai_client = AiClient(api_key=api_key)

    def run(self) -> None:
        thread_dict: DictDb | None = None
        try:
            if not self.ai_client.is_configured():
                raise ValueError("Cần API Key để chạy Vision")
            if self.dict_path:
                thread_dict = DictDb(self.dict_path)
            extractor = VocabExtractor(thread_dict)
            rows = []
            located = []
            found = False
            with PdfSource(self.pdf_path) as pdf:
                for page in range(self.lesson.page_start, self.lesson.page_end + 1):
                    if page >= pdf.page_count():
                        break
                    spans = pdf.spans(page)
                    if extractor.is_vocab_page(spans):
                        found = True
                        located.append((page, spans))
                    elif found:
                        joined = " ".join(span.text for span in spans)
                        if "STT" in joined or any(
                            span.text.strip().isdigit() for span in spans
                        ):
                            located.append((page, spans))
                        break
                if not located:
                    raise ValueError("Không tìm thấy bảng từ mới trong bài đã chọn")
                for page, spans in located:
                    bbox = extractor.table_bbox(spans)
                    image = (
                        pdf.get_page_crop_image_bytes(page, bbox, dpi=250)
                        if bbox
                        else pdf.get_page_image_bytes(page, dpi=200)
                    )
                    rows.extend(
                        extractor.extract_by_llm_image(
                            image, self.ai_client, source_page=page + 1
                        )
                    )
            checked = [
                replace(row, order_no=index)
                for index, row in enumerate(extractor.validate_rows(rows), start=1)
            ]
            self.finished_rows.emit(checked)
        except Exception as err:
            self.failed.emit(str(err))
        finally:
            if thread_dict:
                thread_dict.close()


class PreviewWorker(QThread):
    """Kết xuất ảnh nguồn ở luồng nền để thao tác duyệt không khóa giao diện."""

    loaded = Signal(bytes)
    failed = Signal(str)

    def __init__(
        self,
        pdf_path: str | Path,
        page_start: int,
        page_end: int,
        dpi: int = 125,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.page_start = page_start
        self.page_end = page_end
        self.dpi = dpi

    def run(self) -> None:
        try:
            self.loaded.emit(
                render_vocab_table_preview(
                    self.pdf_path,
                    self.page_start,
                    self.page_end,
                    dpi=self.dpi,
                )
            )
        except Exception as err:
            self.failed.emit(str(err))


def render_page_preview(
    pdf_path: str | Path,
    page_index: int,
    dpi: int = 110,
    section: str = "full",
) -> bytes:
    """Kết xuất preview qua tầng service để UI không đọc PDF trực tiếp."""
    with PdfSource(pdf_path) as pdf:
        return pdf.get_page_vertical_section_image_bytes(
            page_index, section=section, dpi=dpi
        )


@lru_cache(maxsize=64)
def render_vocab_table_preview(
    pdf_path: str | Path,
    page_start: int,
    page_end: int,
    dpi: int = 125,
) -> bytes:
    """Kết xuất đúng các crop bảng từ mới của một bài để giao diện duyệt nguồn."""
    extractor = VocabExtractor()
    located = []
    found = False
    with PdfSource(pdf_path) as pdf:
        for page in range(page_start, page_end + 1):
            if page >= pdf.page_count():
                break
            spans = pdf.spans(page)
            if extractor.is_vocab_page(spans):
                found = True
                located.append((page, spans))
            elif found:
                if any(span.text.strip().isdigit() for span in spans):
                    located.append((page, spans))
                break

        if not located:
            raise ValueError("Không tìm thấy bảng từ mới trong ranh giới bài")

        images = []
        for page, spans in located:
            bbox = extractor.table_bbox(spans)
            if bbox:
                image = pdf.get_page_crop_image_bytes(page, bbox, dpi=dpi)
                if image:
                    images.append(image)
        if not images:
            raise ValueError("Không kết xuất được crop bảng từ mới")
        return pdf.stack_image_bytes(images, max_width=1200)
