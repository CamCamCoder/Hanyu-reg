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
from uuid import uuid4

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
from hanzi_app.service.vocab import MAX_AI_ATTEMPTS_PER_BLOCK, VocabExtractor, render_block_crop

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

                mode_str = "Lớp 2 (Cloud AI)" if self.ai_client.is_configured() else "Lớp 1 (Local Engine)"
                self.progress.emit(60, f"Phân tách bài học [{mode_str}]...")
                splitter = Splitter()
                remaining_ai_calls = self._remaining_ai_calls(thread_db, file_hash)
                evidence_image = (
                    pdf.boundary_contact_sheet(evidence)
                    if remaining_ai_calls > 0 and self.ai_client.is_configured() else None
                )
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
            record.get("region_decision", "auto"), record.get("region_revision", 0),
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
                if record["status"] == "manual" or record["region_decision"] != "auto":
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
            with db.transaction():
                current = next((b for b in db.get_import_blocks(block.lesson_id) if b["id"] == block.id), None)
                if not current or current["region_revision"] != block.region_revision:
                    continue
                if len(rows) >= len(existing):
                    db.replace_vocab_block(block.id, rows, preserve_manual=block.region_decision == "accepted")
                db.update_import_block(
                    block.id, status=block.status, ai_attempts=block.ai_attempts, crop_path=block.crop_path,
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
                        and block.region_decision not in {"review", "skipped"}
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

                cleanup_import_issues(thread_db, self.book_id, pdf=pdf)

            remaining_issues = collect_import_issues(thread_db, self.book_id)
            if not thread_db.book_import_complete(self.book_id):
                thread_db.set_import_state(self.book_id, "incomplete")
                count = len(remaining_issues) or len(incomplete_messages) or 1
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


class RegionPageWorker(QThread):
    loaded = Signal(bytes)
    failed = Signal(str)

    def __init__(self, path, page_index, parent=None):
        super().__init__(parent)
        self.path = path
        self.page_index = page_index

    def run(self):
        try:
            with PdfSource(self.path) as pdf:
                self.loaded.emit(pdf.get_page_image_bytes(self.page_index, dpi=125))
        except Exception as err:
            self.failed.emit(str(err))


class RegionSaveWorker(QThread):
    saved = Signal()
    failed = Signal(str)

    def __init__(self, db_path, book, lesson_id, page_index, bbox, record, decision, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.book = book
        self.lesson_id = lesson_id
        self.page_index = page_index
        self.bbox = bbox
        self.record = record or {}
        self.decision = decision

    def run(self):
        db = None
        crop = None
        try:
            rows = []
            status = "pending"
            if self.decision == "accepted":
                block = VocabBlock(self.record.get("id"), self.lesson_id, self.record.get("block_no", 1),
                                   self.page_index, self.bbox, None, None, None, None)
                with PdfSource(self.book["file_path"]) as pdf:
                    data = render_block_crop(pdf, block)
                    if not data:
                        raise ValueError("Không đọc được vùng đã chọn")
                    result = VocabExtractor().extract_blocks(pdf, [block])
                rows = list(result.rows)
                status = result.blocks[0].status
                folder = Path(self.db_path).parent / "book_crops" / f"book-{self.book['id']}" / f"lesson-{self.lesson_id}"
                folder.mkdir(parents=True, exist_ok=True)
                crop = folder / f"review-{uuid4().hex}.png"
                crop.write_bytes(data)
            db = UserDb(self.db_path)
            db.save_region_review(self.lesson_id, self.page_index, self.bbox, self.decision,
                                  self.record.get("id"), self.record.get("region_revision", 0),
                                  str(crop) if crop else None, rows, status)
            crop = None
            self.saved.emit()
        except Exception as err:
            self.failed.emit(str(err))
        finally:
            if crop is not None:
                crop.unlink(missing_ok=True)
            if db is not None:
                db.close()


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

_GRAMMAR_TABLE_TERMS = frozenset({
    "名词", "动词", "形容", "形容词", "代词", "量词", "助动", "助动词",
    "数量", "来自本册", "新词", "汉字", "拼音", "词类",
})


def _row_words(rows: list[dict]) -> list[str]:
    return [str(row.get("word") or "").strip() for row in rows]


def _stored_rows_look_like_local_ocr_noise(rows: list[dict]) -> bool:
    if not rows:
        return False
    if any(row.get("extract_by") != "regex" for row in rows):
        return False
    suspicious = 0
    for row in rows:
        word = str(row.get("word") or "").strip()
        weak_payload = not row.get("pinyin_src") and not row.get("meaning_src")
        tiny_reviewed = len(word) <= 1 and bool(row.get("needs_review"))
        heading_fragment = word in {"生", "词", "新", "课"}
        if weak_payload or tiny_reviewed or heading_fragment:
            suspicious += 1
    return suspicious * 5 >= len(rows) * 3

def _grammar_table_score(words: list[str]) -> int:
    return sum(1 for word in words if word in _GRAMMAR_TABLE_TERMS)


def _classify_import_block(record: dict, rows: list[dict]) -> tuple[str, ...]:
    issues: list[str] = []
    first = record["first_order"]
    last = record["last_order"]
    expected = record["expected_rows"]
    orders = [row["order_no"] for row in rows if row.get("order_no") is not None]
    words = _row_words(rows)

    if record["status"] not in {"local_ok", "ai_ok", "manual"}:
        issues.append("INCOMPLETE_BLOCK")
    if not rows:
        issues.append("EMPTY_BLOCK")
    if len(orders) != len(set(orders)):
        issues.append("DUPLICATE_ORDERS")
    if first is not None and last is not None:
        observed = set(orders)
        if any(order not in observed for order in range(first, last + 1)):
            issues.append("MISSING_ORDERS")
    if expected is not None and len(rows) != expected:
        issues.append("ROW_COUNT_MISMATCH")
    if _grammar_table_score(words) >= 2 or any(
        token in words for token in ("来自本册", "新词")
    ):
        issues.append("GRAMMAR_TABLE_FALSE_POSITIVE")
    if rows and all((row.get("extract_by") == "regex") for row in rows):
        short_rows = [word for word in words if len(word) <= 2]
        if len(short_rows) == len(words) and any(
            issue in issues for issue in ("MISSING_ORDERS", "ROW_COUNT_MISMATCH")
        ):
            issues.append("OCR_NOISE")
    if _stored_rows_look_like_local_ocr_noise(rows):
        issues.append("OCR_NOISE")
    if record["status"] not in {"local_ok", "ai_ok", "manual"} and record[
        "ai_attempts"
    ] >= MAX_AI_ATTEMPTS_PER_BLOCK:
        issues.append("AI_EXHAUSTED")
    return tuple(dict.fromkeys(issues))


def collect_import_issues(db: UserDb, book_id: int) -> list[dict]:
    """Return a read-only, whole-book import issue report for triage."""
    issues: list[dict] = []
    for lesson in db.get_lessons(book_id):
        if lesson["index_no"] < 0:
            continue
        blocks = db.get_import_blocks(lesson["id"])
        if not blocks:
            issues.append({
                "lesson_id": lesson["id"],
                "lesson_no": lesson["index_no"],
                "lesson_title": lesson.get("title"),
                "page_start": lesson["page_start"],
                "page_end": lesson["page_end"],
                "block_id": None,
                "block_no": None,
                "status": "missing",
                "issues": ("NO_BLOCKS",),
                "saved_rows": 0,
                "ai_attempts": 0,
                "sample_words": (),
                "crop_path": None,
            })
            continue
        lesson_rows = db.get_lesson_words(lesson["id"])
        for block in blocks:
            if block["region_decision"] == "skipped":
                continue
            rows = [
                row for row in lesson_rows
                if row.get("source_block_id") == block["id"]
            ]
            block_issues = _classify_import_block(block, rows)
            if not block_issues:
                continue
            issues.append({
                "lesson_id": lesson["id"],
                "lesson_no": lesson["index_no"],
                "lesson_title": lesson.get("title"),
                "page_start": lesson["page_start"],
                "page_end": lesson["page_end"],
                "block_id": block["id"],
                "region_decision": block["region_decision"],
                "block_no": block["block_no"],
                "page_index": block["page_index"],
                "status": block["status"],
                "issues": block_issues,
                "expected_rows": block["expected_rows"],
                "first_order": block["first_order"],
                "last_order": block["last_order"],
                "saved_rows": len(rows),
                "ai_attempts": block["ai_attempts"],
                "sample_words": tuple(_row_words(rows)[:8]),
                "crop_path": block["crop_path"],
            })
    return issues

def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = bbox
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _bbox_overlap_ratio(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    x0 = max(left[0], right[0])
    y0 = max(left[1], right[1])
    x1 = min(left[2], right[2])
    y1 = min(left[3], right[3])
    overlap = _bbox_area((x0, y0, x1, y1))
    smaller = min(_bbox_area(left), _bbox_area(right))
    if smaller <= 0:
        return 0.0
    return overlap / smaller


def _block_supported_by_locator(record: dict, located: list[VocabBlock]) -> bool:
    record_block = VocabImporterWorker._record_to_block(record)
    for block in located:
        if block.page_index != record_block.page_index:
            continue
        if _bbox_overlap_ratio(record_block.bbox, block.bbox) < 0.55:
            continue
        if (
            record_block.first_order is not None
            and record_block.last_order is not None
            and block.first_order is not None
            and block.last_order is not None
            and (
                record_block.first_order != block.first_order
                or record_block.last_order != block.last_order
            )
        ):
            continue
        return True
    return False



def _orders_contiguous(orders: set[int]) -> bool:
    if not orders:
        return False
    return orders == set(range(min(orders), max(orders) + 1))


def _dedupe_ai_rows_by_order(rows: list[VocabRow]) -> list[VocabRow]:
    by_order: dict[int, VocabRow] = {}
    for row in rows:
        if row.order_no is None:
            continue
        current = by_order.get(row.order_no)
        if current is None:
            by_order[row.order_no] = row
            continue
        current_key = (len(current.word.strip()), not current.needs_review)
        row_key = (len(row.word.strip()), not row.needs_review)
        if row_key > current_key:
            by_order[row.order_no] = row
    return [by_order[order] for order in sorted(by_order)]


def _finish_cleanup_repair(
    db: UserDb,
    actions: list[dict],
    *,
    lesson_id: int,
    issue: dict,
    block: dict,
    repaired_block: VocabBlock,
    repaired_rows: list[VocabRow],
    reason: str,
) -> None:
    db.repair_import_blocks(lesson_id, [(block["id"], repaired_block)])
    db.replace_vocab_block(block["id"], repaired_rows)
    db.update_import_block(
        block["id"],
        status=repaired_block.status,
        ai_attempts=repaired_block.ai_attempts,
        crop_path=repaired_block.crop_path,
    )
    actions.append({
        "lesson_id": lesson_id,
        "lesson_no": issue["lesson_no"],
        "block_id": block["id"],
        "block_no": block["block_no"],
        "reason": reason,
        "issues_before": issue["issues"],
        "expected_rows_before": block["expected_rows"],
        "expected_rows_after": repaired_block.expected_rows,
        "status_after": repaired_block.status,
        "saved_rows": len(repaired_rows),
    })

def cleanup_import_issues(
    db: UserDb, book_id: int, pdf: PdfSource | None = None
) -> list[dict]:
    """Repair safe whole-book import issues without touching manual work."""
    actions: list[dict] = []
    def automatic_issues():
        return [i for i in collect_import_issues(db, book_id) if i.get("region_decision", "auto") == "auto"]

    issues = automatic_issues()
    by_lesson: dict[int, list[dict]] = {}
    for issue in issues:
        if issue.get("block_id") is None:
            continue
        if "GRAMMAR_TABLE_FALSE_POSITIVE" not in issue["issues"]:
            continue
        by_lesson.setdefault(issue["lesson_id"], []).append(issue)

    for lesson_id, lesson_issues in by_lesson.items():
        blocks = db.get_import_blocks(lesson_id)
        block_ids = {issue["block_id"] for issue in lesson_issues}
        removable = [
            block for block in blocks
            if block["id"] in block_ids and block["status"] != "manual"
        ]
        if not removable:
            continue
        if len(removable) >= len(blocks):
            actions.append({
                "lesson_id": lesson_id,
                "lesson_no": lesson_issues[0]["lesson_no"],
                "removed_block_ids": (),
                "removed_block_nos": (),
                "reason": "SKIPPED_ALL_BLOCKS_FALSE_POSITIVE",
            })
            continue
        db.delete_import_blocks(lesson_id, [block["id"] for block in removable])
        actions.append({
            "lesson_id": lesson_id,
            "lesson_no": lesson_issues[0]["lesson_no"],
            "removed_block_ids": tuple(block["id"] for block in removable),
            "removed_block_nos": tuple(block["block_no"] for block in removable),
            "reason": "GRAMMAR_TABLE_FALSE_POSITIVE",
        })

    issues = automatic_issues()
    by_lesson = {}
    for issue in issues:
        if issue.get("block_id") is None:
            continue
        if issue["status"] != "local_ok" or issue["issues"] != ("OCR_NOISE",):
            continue
        by_lesson.setdefault(issue["lesson_id"], []).append(issue)

    for lesson_id, lesson_issues in by_lesson.items():
        blocks = db.get_import_blocks(lesson_id)
        blocks_by_id = {block["id"]: block for block in blocks}
        removable = [
            blocks_by_id[issue["block_id"]]
            for issue in lesson_issues
            if issue["block_id"] in blocks_by_id
            and blocks_by_id[issue["block_id"]]["status"] != "manual"
        ]
        if not removable:
            continue
        if len(removable) >= len(blocks):
            actions.append({
                "lesson_id": lesson_id,
                "lesson_no": lesson_issues[0]["lesson_no"],
                "removed_block_ids": (),
                "removed_block_nos": (),
                "reason": "SKIPPED_ALL_LOCAL_OK_OCR_NOISE_BLOCKS",
            })
            continue
        db.delete_import_blocks(lesson_id, [block["id"] for block in removable])
        actions.append({
            "lesson_id": lesson_id,
            "lesson_no": lesson_issues[0]["lesson_no"],
            "removed_block_ids": tuple(block["id"] for block in removable),
            "removed_block_nos": tuple(block["block_no"] for block in removable),
            "reason": "LOCAL_OK_OCR_NOISE_FALSE_POSITIVE",
        })
    if pdf is not None:
        located_by_lesson: dict[int, list[VocabBlock]] = {}
        lessons_by_id = {lesson["id"]: lesson for lesson in db.get_lessons(book_id)}
        for lesson in lessons_by_id.values():
            boundary = LessonBoundary(
                lesson["index_no"],
                lesson.get("title"),
                lesson["page_start"],
                lesson["page_end"],
                lesson["confidence"],
                "lesson",
            )
            located_by_lesson[lesson["id"]] = VocabExtractor().locate_blocks(
                pdf, boundary
            )
        issues = automatic_issues()
        by_lesson = {}
        for issue in issues:
            if issue.get("block_id") is None:
                continue
            if "GRAMMAR_TABLE_FALSE_POSITIVE" in issue["issues"]:
                continue
            by_lesson.setdefault(issue["lesson_id"], []).append(issue)
        for lesson_id, lesson_issues in by_lesson.items():
            blocks = db.get_import_blocks(lesson_id)
            blocks_by_id = {block["id"]: block for block in blocks}
            stale = [
                blocks_by_id[issue["block_id"]]
                for issue in lesson_issues
                if issue["block_id"] in blocks_by_id
                and blocks_by_id[issue["block_id"]]["status"] != "manual"
                and not _block_supported_by_locator(
                    blocks_by_id[issue["block_id"]],
                    located_by_lesson.get(lesson_id, []),
                )
            ]
            if not stale:
                continue
            if len(stale) >= len(blocks):
                actions.append({
                    "lesson_id": lesson_id,
                    "lesson_no": lesson_issues[0]["lesson_no"],
                    "removed_block_ids": (),
                    "removed_block_nos": (),
                    "reason": "SKIPPED_ALL_STALE_LOCATOR_BLOCKS",
                })
                continue
            db.delete_import_blocks(lesson_id, [block["id"] for block in stale])
            actions.append({
                "lesson_id": lesson_id,
                "lesson_no": lesson_issues[0]["lesson_no"],
                "removed_block_ids": tuple(block["id"] for block in stale),
                "removed_block_nos": tuple(block["block_no"] for block in stale),
                "reason": "STALE_LOCATOR_FALSE_POSITIVE",
            })

    extractor = VocabExtractor()
    issues = automatic_issues()
    by_lesson = {}
    for issue in issues:
        if issue.get("block_id") is None:
            continue
        if "GRAMMAR_TABLE_FALSE_POSITIVE" in issue["issues"]:
            continue
        by_lesson.setdefault(issue["lesson_id"], []).append(issue)

    for lesson_id, lesson_issues in by_lesson.items():
        blocks = db.get_import_blocks(lesson_id)
        blocks_by_id = {block["id"]: block for block in blocks}
        lesson_rows = db.get_lesson_words(lesson_id)
        rows_by_block: dict[int, list[dict]] = {}
        for row in lesson_rows:
            if row.get("source_block_id") is not None:
                rows_by_block.setdefault(row["source_block_id"], []).append(row)

        for issue in lesson_issues:
            block = blocks_by_id.get(issue["block_id"])
            if block is None or block["status"] == "manual":
                continue
            cached = rows_by_block.get(block["id"], [])
            if not cached:
                continue
            record_block = VocabImporterWorker._record_to_block(block)
            vocab_rows = [
                VocabImporterWorker._row_record_to_vocab(row)
                for row in cached
            ]
            result = extractor.reconcile_checkpointed_block(
                record_block,
                vocab_rows,
            )
            if result is None:
                orders = [row.order_no for row in vocab_rows]
                ai_rows = [
                    row for row in vocab_rows
                    if row.extract_by != "regex" and row.order_no is not None
                ]
                deduped_ai_rows = _dedupe_ai_rows_by_order(ai_rows)
                can_use_deduped_ai_rows = (
                    "DUPLICATE_ORDERS" in issue["issues"]
                    and block["first_order"] is None
                    and block["last_order"] is None
                    and vocab_rows
                    and all(row.extract_by != "regex" for row in vocab_rows)
                    and len(deduped_ai_rows) < len(ai_rows)
                    and len(deduped_ai_rows) > 0
                )
                if can_use_deduped_ai_rows:
                    candidate_block = replace(
                        record_block,
                        expected_rows=len(deduped_ai_rows),
                        status="ai_ok",
                    )
                    report = extractor.validate_block_coverage(
                        candidate_block, [], deduped_ai_rows, deduped_ai_rows
                    )
                    if report.passed:
                        _finish_cleanup_repair(
                            db, actions,
                            lesson_id=lesson_id,
                            issue=issue,
                            block=block,
                            repaired_block=candidate_block,
                            repaired_rows=deduped_ai_rows,
                            reason="RECONCILED_DEDUPED_AI_ROWS",
                        )
                        continue

                ai_orders = {row.order_no for row in ai_rows}
                can_drop_regex_noise_without_range = (
                    block["first_order"] is None
                    and block["last_order"] is None
                    and ai_rows
                    and len(ai_rows) == len(ai_orders)
                    and len(ai_rows) < len(vocab_rows)
                )
                if can_drop_regex_noise_without_range:
                    candidate_block = replace(
                        record_block,
                        expected_rows=len(ai_rows),
                        status="ai_ok",
                    )
                    report = extractor.validate_block_coverage(
                        candidate_block, [], ai_rows, ai_rows
                    )
                    if report.passed:
                        _finish_cleanup_repair(
                            db, actions,
                            lesson_id=lesson_id,
                            issue=issue,
                            block=block,
                            repaired_block=candidate_block,
                            repaired_rows=ai_rows,
                            reason="RECONCILED_AI_ROWS_DROPPED_REGEX_NOISE",
                        )
                        continue

                can_replace_stale_range_with_ai_rows = (
                    "MISSING_ORDERS" in issue["issues"]
                    and block["first_order"] is not None
                    and block["last_order"] is not None
                    and len(ai_rows) >= 2
                    and len(ai_rows) == len(ai_orders)
                    and _orders_contiguous(ai_orders)
                )
                if can_replace_stale_range_with_ai_rows:
                    candidate_block = replace(
                        record_block,
                        first_order=min(ai_orders),
                        last_order=max(ai_orders),
                        expected_rows=len(ai_rows),
                        status="ai_ok",
                    )
                    report = extractor.validate_block_coverage(
                        candidate_block, [], ai_rows, ai_rows
                    )
                    if report.passed:
                        _finish_cleanup_repair(
                            db, actions,
                            lesson_id=lesson_id,
                            issue=issue,
                            block=block,
                            repaired_block=candidate_block,
                            repaired_rows=ai_rows,
                            reason="RECONCILED_AI_ROWS_REPLACED_STALE_RANGE",
                        )
                        continue
                can_shrink_sibling_range = (
                    "MISSING_ORDERS" in issue["issues"]
                    and block["first_order"] is not None
                    and block["last_order"] is not None
                    and ai_rows
                    and len(ai_rows) == len({row.order_no for row in ai_rows})
                )
                if can_shrink_sibling_range:
                    target_orders = set(range(block["first_order"], block["last_order"] + 1))
                    ai_orders = {row.order_no for row in ai_rows}
                    observed_orders = ai_orders & target_orders
                    missing_orders = target_orders - observed_orders
                    sibling_orders = {
                        row["order_no"]
                        for other_block_id, other_rows in rows_by_block.items()
                        if other_block_id != block["id"]
                        for row in other_rows
                        if row.get("order_no") is not None
                    }
                    range_rows = [row for row in ai_rows if row.order_no in observed_orders]
                    if (
                        observed_orders
                        and missing_orders
                        and missing_orders <= sibling_orders
                        and _orders_contiguous(observed_orders)
                        and len(range_rows) == len(observed_orders)
                    ):
                        candidate_block = replace(
                            record_block,
                            first_order=min(observed_orders),
                            last_order=max(observed_orders),
                            expected_rows=len(range_rows),
                            status="ai_ok",
                        )
                        report = extractor.validate_block_coverage(
                            candidate_block, [], range_rows, range_rows
                        )
                        if report.passed:
                            _finish_cleanup_repair(
                                db, actions,
                                lesson_id=lesson_id,
                                issue=issue,
                                block=block,
                                repaired_block=candidate_block,
                                repaired_rows=range_rows,
                                reason="RECONCILED_RANGE_SPLIT_BY_SIBLING_BLOCK",
                            )
                            continue

                trusted_ai_rows = (
                    issue["issues"] == ("INCOMPLETE_BLOCK", "ROW_COUNT_MISMATCH")
                    and block["first_order"] is None
                    and block["last_order"] is None
                    and vocab_rows
                    and all(row.extract_by != "regex" for row in vocab_rows)
                    and all(order is not None for order in orders)
                    and len(orders) == len(set(orders))
                )
                if not trusted_ai_rows:
                    continue
                candidate_block = replace(
                    record_block,
                    expected_rows=len(vocab_rows),
                    status="ai_ok",
                )
                report = extractor.validate_block_coverage(
                    candidate_block, [], vocab_rows, vocab_rows
                )
                if not report.passed:
                    continue
                _finish_cleanup_repair(
                    db, actions,
                    lesson_id=lesson_id,
                    issue=issue,
                    block=block,
                    repaired_block=candidate_block,
                    repaired_rows=vocab_rows,
                    reason="RECONCILED_TRUSTED_AI_ROWS_WITHOUT_RANGE",
                )
                continue
            repaired_block, repaired_rows = result
            _finish_cleanup_repair(
                db, actions,
                lesson_id=lesson_id,
                issue=issue,
                block=block,
                repaired_block=repaired_block,
                repaired_rows=repaired_rows,
                reason="RECONCILED_CHECKPOINTED_BLOCK",
            )
    return actions
def _manifest_record_stale(record: dict) -> bool:
    if record["status"] == "manual" or record["region_decision"] != "auto":
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
    if record["status"] == "manual" or record["region_decision"] != "auto":
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
