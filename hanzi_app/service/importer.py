"""Bộ điều phối quy trình nhập sách (QT-02 & QT-03).

Chạy trong luồng nền để không làm đóng băng giao diện.
Tự mở kết nối UserDb riêng cho luồng nền để tránh lỗi SQLite threading.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QThread, Qt, Signal
from PySide6.QtGui import QImage, QPainter

from hanzi_app.adapter.aiclient import AiClient
from hanzi_app.adapter.pdfsource import PdfSource
from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import (
    LessonBoundary,
    SplitResult,
    VocabBlock,
    VocabRow,
)
from hanzi_app.data.userdb import UserDb
from hanzi_app.service.splitter import Splitter
from hanzi_app.service.vocab import VocabExtractor, render_block_crop

_REAL_VOCAB_EXTRACTOR = VocabExtractor

logger = logging.getLogger(__name__)


def _log_exception_if_configured(message: str, *args: object) -> None:
    if logging.getLogger().handlers:
        logger.exception(message, *args)


def _write_crop_atomic(
    root: str | Path,
    book_id: int,
    lesson_id: int,
    block_no: int,
    data: bytes,
) -> str:
    """Persist a crop by replacing the final path only after a complete write."""
    target = (
        Path(root)
        / f"book-{book_id}"
        / f"lesson-{lesson_id}"
        / f"block-{block_no}.png"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return str(target)

class BookImporterWorker(QThread):
    """Pha 1: nhận diện bài học, dừng lại để người dùng duyệt ranh giới."""

    progress = Signal(int, str)  # (phần trăm 0..100, thông điệp)
    boundaries_ready = Signal(int, str, object)  # (book_id, book_title, SplitResult)
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
        book_id: int | None = None
        previous_state: str | None = None
        created_book = False
        boundaries_persisted = False
        splitter: Splitter | None = None
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
                    existing_book = thread_db.get_book(book_id)
                    previous_state = existing_book["import_state"] if existing_book else None
                    thread_db.set_import_state(book_id, "importing")
                else:
                    book_id = thread_db.add_book(
                        title=book_title,
                        file_path=str(self.pdf_path),
                        file_hash=file_hash,
                        page_count=page_count,
                    )
                    created_book = True

                self.progress.emit(40, "Phân tích bản tóm lược các trang...")
                evidence = pdf.page_census()
                evidence_image = pdf.boundary_contact_sheet(evidence)

                mode_str = "Lớp 2 (Cloud AI)" if self.ai_client.is_configured() else "Lớp 1 (Local Engine)"
                self.progress.emit(60, f"Phân tách bài học [{mode_str}]...")
                splitter = Splitter()
                remaining_ai_calls = self._remaining_ai_calls(thread_db, file_hash)
                try:
                    result = splitter.propose(
                        [],
                        evidence,
                        ai_client=self.ai_client,
                        evidence_image=evidence_image,
                        remaining_ai_calls=remaining_ai_calls,
                    )
                finally:
                    self._record_ai_calls(thread_db, file_hash, splitter.ai_calls_used)

                if result.boundaries and not result.report.valid:
                    thread_db.set_import_state(book_id, "review_bounds")
                    self.progress.emit(
                        65,
                        "Ranh giới cần sửa — hãy kiểm tra trước khi OCR.",
                    )
                    self.boundaries_ready.emit(book_id, book_title, result)
                    return

                # Nạp danh sách bài học vào DB
                self._store_boundaries_or_raise(thread_db, book_id, result)
                boundaries_persisted = True
                thread_db.set_import_state(book_id, "review_bounds")
                self.progress.emit(65, "Đã tìm ranh giới bài — hãy kiểm tra trước khi OCR.")
                self.boundaries_ready.emit(book_id, book_title, result)

        except Exception as err:
            if thread_db is not None and book_id is not None:
                if boundaries_persisted:
                    thread_db.set_import_state(book_id, "review_bounds")
                elif created_book:
                    thread_db.delete_book(book_id)
                elif previous_state is not None:
                    thread_db.set_import_state(book_id, previous_state)
            _log_exception_if_configured(
                "Book import failed: book_id=%s pdf=%s",
                book_id,
                self.pdf_path,
            )
            self.failed_import.emit(str(err))
        finally:
            if thread_db:
                thread_db.close()

    @staticmethod
    def _store_boundaries_or_raise(
        db: UserDb, book_id: int, result: SplitResult
    ) -> None:
        """Persist a complete, validated split or leave the current lessons untouched."""
        if not result.report.valid:
            messages = "; ".join(issue.message for issue in result.report.issues)
            raise RuntimeError(messages)
        if not result.boundaries:
            raise RuntimeError("No valid lesson boundaries found.")
        db.replace_lessons(book_id, list(result.boundaries))

    @staticmethod
    def _ai_budget_key(file_hash: str) -> str:
        return f"import.split_ai_calls.{file_hash}"

    @classmethod
    def _remaining_ai_calls(cls, db: UserDb, file_hash: str) -> int:
        raw_calls = db.get_setting(cls._ai_budget_key(file_hash))
        try:
            calls_used = int(raw_calls) if raw_calls is not None else 0
        except ValueError:
            calls_used = 0
        return max(0, 2 - calls_used)

    @classmethod
    def _record_ai_calls(cls, db: UserDb, file_hash: str, calls_used: int) -> None:
        if calls_used <= 0:
            return
        key = cls._ai_budget_key(file_hash)
        raw_calls = db.get_setting(key)
        try:
            previous_calls = int(raw_calls) if raw_calls is not None else 0
        except ValueError:
            previous_calls = 0
        db.set_setting(key, str(min(2, previous_calls + calls_used)))


class VocabImporterWorker(QThread):
    """Pha 2: extract vocabulary with persistent per-block checkpoints."""

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

    @staticmethod
    def _record_to_block(record: dict) -> VocabBlock:
        return VocabBlock(
            record["id"],
            record["lesson_id"],
            record["block_no"],
            record["page_index"],
            tuple(record["bbox"]),
            record["crop_path"],
            record["expected_rows"],
            record["first_order"],
            record["last_order"],
            record["status"],
            record["ai_attempts"],
        )

    @staticmethod
    def _row_record_to_vocab(row: dict) -> VocabRow:
        return VocabRow(
            row["order_no"],
            row["word"],
            row["pinyin_src"],
            row["pos"],
            row["meaning_src"],
            row["source_page"],
            row["extract_by"],
            bool(row["needs_review"]),
            None,
            hanviet_src=row.get("hanviet_src"),
            source_block_id=row.get("source_block_id"),
        )

    def _load_or_create_blocks(
        self,
        db: UserDb,
        pdf: PdfSource,
        extractor: VocabExtractor,
        lesson: dict,
        boundary: LessonBoundary,
    ) -> list[VocabBlock]:
        records = db.get_import_blocks(lesson["id"])
        lesson_rows = db.get_lesson_words(lesson["id"]) if records else []
        rows_by_block: dict[int, list[dict]] = {}
        for row in lesson_rows:
            if row.get("source_block_id") is not None:
                rows_by_block.setdefault(row["source_block_id"], []).append(row)
        reconciled = False
        if isinstance(extractor, _REAL_VOCAB_EXTRACTOR):
            for record in records:
                if record["status"] == "manual":
                    continue
                cached = rows_by_block.get(record["id"], [])
                if not cached:
                    continue
                result = extractor.reconcile_checkpointed_block(
                    self._record_to_block(record),
                    [self._row_record_to_vocab(row) for row in cached],
                )
                if result is None:
                    continue
                block, rows = result
                db.repair_import_blocks(lesson["id"], [(record["id"], block)])
                db.replace_vocab_block(record["id"], rows)
                db.update_import_block(
                    record["id"],
                    status=block.status,
                    ai_attempts=block.ai_attempts,
                    crop_path=block.crop_path,
                )
                reconciled = True
        if reconciled:
            records = db.get_import_blocks(lesson["id"])
            lesson_rows = db.get_lesson_words(lesson["id"])
            rows_by_block = {}
            for row in lesson_rows:
                if row.get("source_block_id") is not None:
                    rows_by_block.setdefault(row["source_block_id"], []).append(row)

        stale_manifest = [
            record for record in records
            if _manifest_record_stale(record)
        ]
        stale_rows = [
            record for record in records
            if _manifest_rows_stale(record, rows_by_block.get(record["id"], []))
        ]
        if stale_manifest or stale_rows:
            repairs_by_id: dict[int, VocabBlock] = {}
            if stale_manifest:
                located = extractor.locate_blocks(pdf, boundary)
                matches = []
                used = set()
                for record in stale_manifest:
                    candidates = sorted(
                        (
                            (_bbox_iou(record["bbox"], fresh.bbox), index, fresh)
                            for index, fresh in enumerate(located)
                            if fresh.page_index == record["page_index"]
                            and _bbox_iou(record["bbox"], fresh.bbox) >= 0.5
                        ),
                        key=lambda item: item[0],
                        reverse=True,
                    )
                    if (
                        not candidates
                        or candidates[0][1] in used
                        or (
                            len(candidates) > 1
                            and candidates[0][0] == candidates[1][0]
                        )
                    ):
                        raise RuntimeError("manifest_needs_review")
                    used.add(candidates[0][1])
                    matches.append((record, candidates[0][2]))
                crop_root = Path(self.db_path).parent / "book_crops"
                for record, fresh in matches:
                    crop = render_block_crop(pdf, fresh)
                    crop_path = (
                        _write_crop_atomic(
                            crop_root, self.book_id, lesson["id"],
                            record["block_no"], crop,
                        )
                        if crop else None
                    )
                    repairs_by_id[record["id"]] = replace(
                        fresh,
                        id=record["id"],
                        lesson_id=lesson["id"],
                        block_no=record["block_no"],
                        crop_path=crop_path,
                        status="pending",
                        ai_attempts=record["ai_attempts"],
                    )
            for record in stale_rows:
                if record["id"] not in repairs_by_id:
                    repairs_by_id[record["id"]] = self._record_to_block(record)
            records = db.repair_import_blocks(
                lesson["id"], [(block.id, block) for block in repairs_by_id.values()]
            )
        if not records:
            located = extractor.locate_blocks(pdf, boundary)
            if not located:
                with PdfSource(self.pdf_path) as retry_pdf:
                    located = extractor.locate_blocks(retry_pdf, boundary)
            crop_root = Path(self.db_path).parent / "book_crops"
            prepared: list[VocabBlock] = []
            for block in located:
                crop = render_block_crop(pdf, block)
                crop_path = (
                    _write_crop_atomic(
                        crop_root,
                        self.book_id,
                        lesson["id"],
                        block.block_no,
                        crop,
                    )
                    if crop
                    else None
                )
                prepared.append(replace(
                    block,
                    lesson_id=lesson["id"],
                    crop_path=crop_path,
                ))
            records = db.replace_import_blocks(lesson["id"], prepared)
        return [self._record_to_block(record) for record in records]

    @staticmethod
    def _checkpoint_result(db: UserDb, result) -> None:
        for block in result.blocks:
            if block.id is None or block.lesson_id is None:
                continue
            rows = [
                row for row in result.rows
                if row.source_block_id == block.id
            ]
            existing = [
                row for row in db.get_lesson_words(block.lesson_id)
                if row.get("source_block_id") == block.id
            ]
            if len(rows) >= len(existing):
                db.replace_vocab_block(block.id, rows)
            db.update_import_block(
                block.id,
                status=block.status,
                ai_attempts=block.ai_attempts,
                crop_path=block.crop_path,
            )

    @staticmethod
    def _format_incomplete(lesson: dict, coverage) -> str:
        items = (
            coverage.items()
            if isinstance(coverage, dict)
            else enumerate(coverage, start=1)
        )
        for block_no, report in items:
            if report.passed:
                continue
            if report.missing_orders:
                first = report.missing_orders[0]
                last = report.missing_orders[-1]
                issue = f"thiếu STT {first}" if first == last else f"thiếu STT {first}-{last}"
            elif "rate_limited" in report.issues:
                issue = "HTTP 429"
            elif report.issues:
                issue = report.issues[0].replace("_", " ")
            else:
                issue = "coverage chưa đạt"
            return f"Bài {lesson['index_no']} · block {block_no} · {issue}"
        return f"Bài {lesson['index_no']} · dữ liệu chưa đầy đủ"

    @staticmethod
    def _coverage_has_issue(coverage, issue: str) -> bool:
        items = coverage.values() if isinstance(coverage, dict) else coverage
        return any(issue in report.issues for report in items)
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
            incomplete_messages: list[str] = []

            with PdfSource(self.pdf_path) as pdf:
                for index, lesson in enumerate(lessons):
                    if lesson["index_no"] < 0:
                        continue
                    if not hasattr(extractor, "extract_blocks"):
                        if thread_db.get_lesson_words(lesson["id"]):
                            continue
                        legacy_rows = extractor.extract_lesson(
                            pdf,
                            LessonBoundary(
                                lesson["index_no"],
                                lesson.get("title"),
                                lesson["page_start"],
                                lesson["page_end"],
                                float(lesson.get("confidence", 1.0)),
                                "lesson",
                            ),
                            self.ai_client,
                        )
                        if not legacy_rows:
                            raise RuntimeError(
                                f"Bài {lesson['index_no']} không trích xuất được từ mới"
                            )
                        thread_db.replace_vocab(lesson["id"], legacy_rows)
                        continue
                    boundary = LessonBoundary(
                        index_no=lesson["index_no"],
                        title=lesson.get("title"),
                        page_start=lesson["page_start"],
                        page_end=lesson["page_end"],
                        confidence=float(lesson.get("confidence", 1.0)),
                        kind="lesson",
                    )
                    blocks = self._load_or_create_blocks(
                        thread_db, pdf, extractor, lesson, boundary
                    )
                    if not blocks:
                        incomplete_messages.append(
                            f"Bài {lesson['index_no']} · không tìm thấy block từ mới"
                        )
                        continue
                    pending = [
                        block for block in blocks
                        if block.status not in {"local_ok", "ai_ok", "manual"}
                    ]
                    if pending:
                        extractor.lesson_ai_attempts = sum(
                            block.ai_attempts for block in blocks
                        )
                        result = extractor.extract_blocks(
                            pdf, pending, self.ai_client
                        )
                        self._checkpoint_result(thread_db, result)
                        if not result.complete:
                            by_block = {
                                block.block_no: report
                                for block, report in zip(
                                    result.blocks, result.coverage
                                )
                            }
                            message = self._format_incomplete(lesson, by_block)
                            if self._coverage_has_issue(by_block, "rate_limited"):
                                thread_db.set_import_state(
                                    self.book_id, "incomplete"
                                )
                                raise RuntimeError(message)
                            incomplete_messages.append(message)

                    pct = 65 + int(
                        (index + 1) / max(len(lessons), 1) * 34
                    )
                    self.progress.emit(
                        pct,
                        f"Đã OCR bài {index + 1}/{len(lessons)} [{mode}]...",
                    )

            if not thread_db.book_import_complete(self.book_id):
                thread_db.set_import_state(self.book_id, "incomplete")
                count = len(incomplete_messages) or 1
                self.progress.emit(
                    100,
                    f"Đã OCR phần đọc được — còn {count} mục cần sửa tay hoặc chạy lại.",
                )
                self.finished_import.emit(self.book_id, book["title"])
                return
            thread_db.set_import_state(self.book_id, "review")
            self.progress.emit(100, "Đã OCR — hãy duyệt các dòng từ mới.")
            self.finished_import.emit(self.book_id, book["title"])
        except Exception as err:
            if thread_db:
                current = thread_db.get_book(self.book_id)
                if current and current["import_state"] != "incomplete":
                    lessons = thread_db.get_lessons(self.book_id)
                    has_manifest = any(
                        thread_db.get_import_blocks(lesson["id"])
                        for lesson in lessons
                        if lesson["index_no"] > 0
                    )
                    thread_db.set_import_state(
                        self.book_id,
                        "incomplete" if has_manifest else "review_bounds",
                    )
            _log_exception_if_configured(
                "Vocabulary import failed: book_id=%s pdf=%s",
                self.book_id,
                self.pdf_path,
            )
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
            _log_exception_if_configured(
                "Vision repair failed: lesson=%s pdf=%s",
                self.lesson.index_no,
                self.pdf_path,
            )
            self.failed.emit(str(err))
        finally:
            if thread_dict:
                thread_dict.close()


def _load_saved_crop_preview(crop_paths: tuple[str | Path, ...]) -> bytes:
    paths = [Path(path) for path in crop_paths if path]
    if not paths:
        raise ValueError("Không có crop đã lưu")

    if len(paths) == 1:
        return paths[0].read_bytes()

    images: list[QImage] = []
    for path in paths:
        image = QImage(str(path))
        if image.isNull():
            raise ValueError(f"Không mở được crop: {path}")
        images.append(image)

    max_width = min(1200, max(image.width() for image in images))
    scaled = [
        image.scaledToWidth(
            min(image.width(), max_width),
            Qt.TransformationMode.SmoothTransformation,
        )
        for image in images
    ]
    canvas = QImage(
        max(image.width() for image in scaled),
        sum(image.height() for image in scaled),
        QImage.Format.Format_RGB32,
    )
    canvas.fill(0xFFFFFFFF)
    painter = QPainter(canvas)
    try:
        top = 0
        for image in scaled:
            painter.drawImage(0, top, image)
            top += image.height()
    finally:
        painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not canvas.save(buffer, "PNG"):
        raise ValueError("Không ghép được các crop đã lưu")
    return bytes(data)


class PreviewWorker(QThread):
    """Render a persisted crop, falling back to the legacy PDF preview."""

    loaded = Signal(bytes)
    failed = Signal(str)

    def __init__(
        self,
        pdf_path: str | Path,
        page_start: int | None = None,
        page_end: int | None = None,
        crop_paths: tuple[str | Path, ...] = (),
        dpi: int = 125,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.page_start = page_start
        self.page_end = page_end
        self.crop_paths = tuple(crop_paths)
        self.dpi = dpi

    def run(self) -> None:
        try:
            if self.crop_paths:
                preview = _load_saved_crop_preview(self.crop_paths)
            else:
                if self.page_start is None or self.page_end is None:
                    raise ValueError("Thiếu ranh giới trang cho preview cũ")
                preview = render_vocab_table_preview(
                    self.pdf_path,
                    self.page_start,
                    self.page_end,
                    dpi=self.dpi,
                )
            self.loaded.emit(preview)
        except Exception as err:
            _log_exception_if_configured(
                "Preview load failed: pdf=%s",
                self.pdf_path,
            )
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

def _manifest_record_stale(record: dict) -> bool:
    if record["status"] == "manual":
        return False
    first = record["first_order"]
    last = record["last_order"]
    expected = record["expected_rows"]
    if first is None or last is None:
        return (first is None) != (last is None)
    if first <= 0 or last <= 0 or last < first:
        return True
    return expected is not None and last - first + 1 != expected


def _manifest_rows_stale(record: dict, rows: list[dict]) -> bool:
    if record["status"] == "manual":
        return False
    expected = record["expected_rows"]
    if not rows:
        return record["status"] in {"local_ok", "ai_ok"} and expected not in {None, 0}
    orders = [row["order_no"] for row in rows if row["order_no"] is not None]
    if len(orders) != len(set(orders)):
        return True

    first = record["first_order"]
    last = record["last_order"]
    if first is not None and last is not None:
        observed = set(orders)
        if any(order not in observed for order in range(first, last + 1)):
            return True

    if expected is not None and len(rows) != expected:
        return True

    return False


def _bbox_iou(
    left: tuple[float, ...], right: tuple[float, ...]
) -> float:
    lx0, ly0, lx1, ly1 = left
    rx0, ry0, rx1, ry1 = right
    ix0, iy0 = max(lx0, rx0), max(ly0, ry0)
    ix1, iy1 = min(lx1, rx1), min(ly1, ry1)
    intersection = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    left_area = max(0.0, lx1 - lx0) * max(0.0, ly1 - ly0)
    right_area = max(0.0, rx1 - rx0) * max(0.0, ry1 - ry0)
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0
