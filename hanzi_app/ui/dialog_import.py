"""Hộp thoại nhập sách từ tệp PDF.

Cho phép chọn tệp PDF, gõ API Key (tùy chọn) và hiển thị thanh tiến trình nhập sách trong luồng nền.
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from hanzi_app.data.models import BoundaryEvidence, LessonBoundary, SplitResult
from hanzi_app.service.importer import BookImporterWorker, VocabImporterWorker
from hanzi_app.service.splitter import Splitter
from hanzi_app.ui.theme import PALETTE, ui_font


class DialogReviewBoundaries(QDialog):
    """Cho sửa và xác nhận ranh giới toàn bộ bài trước khi chạy OCR."""

    _HEADERS = (
        "Bài", "Tiêu đề", "Trang đầu", "Trang cuối", "Độ tin cậy", "Nguồn",
    )
    ISSUE_TEXT = {
        "duplicate_lesson": "Trùng số bài",
        "missing_lesson": "Thiếu bài",
        "start_not_increasing": "Trang đầu chưa tăng",
        "overlap": "Khoảng trang chồng nhau",
        "page_out_of_range": "Trang nằm ngoài PDF",
        "toc_heading_conflict": "Mục lục và trang mở bài mâu thuẫn",
    }
    _ERROR_COLOR = QColor("#ffe1e1")

    def __init__(
        self,
        user_db,
        book_id: int,
        page_count: int,
        split_result: SplitResult | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.book_id = book_id
        self.page_count = page_count
        self.evidence = tuple(split_result.evidence) if split_result else ()
        self._updating_table = False
        self.setWindowTitle("Xác nhận ranh giới bài trước khi OCR")
        self.resize(820, 560)

        root = QVBoxLayout(self)
        note = QLabel(
            "Kiểm tra mỗi bài đã bắt đầu và kết thúc đúng trang. "
            "OCR bảng từ mới chỉ chạy sau bước xác nhận này."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            f"background: {PALETTE['warn_bg']}; color: {PALETTE['warn_ink']}; "
            f"padding: 9px; border: 1px solid {PALETTE['warn']};"
        )
        root.addWidget(note)

        self.lbl_errors = QLabel()
        self.lbl_errors.setWordWrap(True)
        self.lbl_errors.setStyleSheet(f"color: {PALETTE['warn_ink']};")
        root.addWidget(self.lbl_errors)

        lessons = user_db.get_lessons(book_id)
        initial_bounds = (
            split_result.boundaries if not lessons and split_result is not None else ()
        )
        row_count = len(lessons) if lessons else len(initial_bounds)
        self.table = QTableWidget(row_count, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row, lesson in enumerate(lessons):
            self._set_row_values(
                row,
                (
                    lesson["index_no"],
                    lesson.get("title") or "",
                    lesson["page_start"] + 1,
                    lesson["page_end"] + 1,
                    f"{float(lesson.get('confidence', 0.0)):.0%}",
                ),
            )
        for row, boundary in enumerate(initial_bounds):
            self._set_row_values(
                row,
                (
                    boundary.index_no,
                    boundary.title or "",
                    boundary.page_start + 1,
                    boundary.page_end + 1,
                    f"{boundary.confidence:.0%}",
                ),
            )
        self.table.itemChanged.connect(self._validate_rows)
        root.addWidget(self.table, 1)

        edit_actions = QHBoxLayout()
        self.btn_add = QPushButton("Thêm bài")
        self.btn_add.clicked.connect(self._add_row)
        edit_actions.addWidget(self.btn_add)
        self.btn_duplicate = QPushButton("Nhân bản")
        self.btn_duplicate.clicked.connect(self._duplicate_row)
        edit_actions.addWidget(self.btn_duplicate)
        self.btn_delete = QPushButton("Xóa")
        self.btn_delete.clicked.connect(self._delete_row)
        edit_actions.addWidget(self.btn_delete)
        self.btn_manual = QPushButton("Dùng ranh giới đang nhập")
        self.btn_manual.clicked.connect(self._use_manual_boundaries)
        edit_actions.addWidget(self.btn_manual)
        self.btn_sort = QPushButton("Sắp xếp")
        self.btn_sort.clicked.connect(self._sort_rows)
        edit_actions.addWidget(self.btn_sort)
        edit_actions.addStretch(1)
        root.addLayout(edit_actions)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Để sau")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        self.btn_confirm = QPushButton("Xác nhận và bắt đầu OCR")
        self.btn_confirm.setStyleSheet(
            f"background: {PALETTE['accent']}; color: white; padding: 7px 14px;"
        )
        self.btn_confirm.clicked.connect(self._confirm)
        actions.addWidget(self.btn_confirm)
        root.addLayout(actions)
        self._validate_rows()

    def _evidence_text(self, lesson_no: int) -> str:
        entries = [
            f"{item.source}: {item.detail}"
            for item in self.evidence
            if item.lesson_no == lesson_no
        ]
        return " · ".join(entries)

    def _set_row_values(
        self, row: int, values: tuple[object, ...], manual: bool = False
    ) -> None:
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column == 4:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, column, item)
        source = QTableWidgetItem()
        source.setFlags(source.flags() & ~Qt.ItemFlag.ItemIsEditable)
        source.setData(Qt.ItemDataRole.UserRole, manual)
        self.table.setItem(row, 5, source)
        self._refresh_source(row)

    def _is_manual(self, row: int) -> bool:
        source = self.table.item(row, 5)
        return bool(source and source.data(Qt.ItemDataRole.UserRole))

    def _refresh_source(self, row: int) -> None:
        source = self.table.item(row, 5)
        if source is None:
            source = QTableWidgetItem()
            source.setFlags(source.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, source)
        if self._is_manual(row):
            source.setText("Thủ công")
            confidence = self.table.item(row, 4)
            if confidence is not None:
                confidence.setText("100%")
            return
        try:
            lesson_no = int(self.table.item(row, 0).text())
        except (AttributeError, TypeError, ValueError):
            lesson_no = 0
        source.setText(self._evidence_text(lesson_no))

    def _refresh_sources(self) -> None:
        for row in range(self.table.rowCount()):
            self._refresh_source(row)

    def _add_row(self) -> None:
        self._updating_table = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_row_values(row, ("", "", "", "", "100%"), manual=True)
        self._updating_table = False
        self._validate_rows()

    def _duplicate_row(self) -> None:
        source_row = self.table.currentRow()
        if source_row < 0:
            source_row = self.table.rowCount() - 1
        if source_row < 0:
            self._add_row()
            return
        values = tuple(
            self.table.item(source_row, column).text()
            if self.table.item(source_row, column) is not None
            else ""
            for column in range(5)
        )
        self._updating_table = True
        row = source_row + 1
        self.table.insertRow(row)
        self._set_row_values(row, values, manual=True)
        self._updating_table = False
        self.table.setCurrentCell(row, 0)
        self._validate_rows()

    def _delete_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
        self._validate_rows()

    def _selected_rows(self) -> list[int]:
        rows = {index.row() for index in self.table.selectedIndexes()}
        if not rows and self.table.currentRow() >= 0:
            rows.add(self.table.currentRow())
        return sorted(rows)

    def _use_manual_boundaries(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        self._updating_table = True
        for row in rows:
            source = self.table.item(row, 5)
            if source is None:
                source = QTableWidgetItem()
                source.setFlags(source.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 5, source)
            source.setData(Qt.ItemDataRole.UserRole, True)
            self._refresh_source(row)
        self._updating_table = False
        self._validate_rows()

    def _sort_rows(self) -> None:
        rows = [
            (
                tuple(
                    self.table.item(row, column).text()
                    if self.table.item(row, column) is not None
                    else ""
                    for column in range(5)
                ),
                self._is_manual(row),
            )
            for row in range(self.table.rowCount())
        ]

        def sort_key(item: tuple[tuple[str, ...], bool]) -> tuple[int, int]:
            values = item[0]
            try:
                lesson_no = int(values[0])
            except ValueError:
                lesson_no = 10**9
            try:
                page_start = int(values[2])
            except ValueError:
                page_start = 10**9
            return lesson_no, page_start

        self._updating_table = True
        rows.sort(key=sort_key)
        self.table.setRowCount(0)
        for values, manual in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row_values(row, values, manual=manual)
        self._updating_table = False
        self._validate_rows()

    def _clear_error_colors(self) -> None:
        for row in range(self.table.rowCount()):
            for column in range(4):
                item = self.table.item(row, column)
                if item is not None:
                    item.setBackground(QColor("transparent"))

    def _color_issue(self, lesson_no: int | None, code: str) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (lesson_no is None or item.text() == str(lesson_no)):
                columns = (5,) if code == "toc_heading_conflict" else (0, 2, 3)
                for column in columns:
                    cell = self.table.item(row, column)
                    if cell is not None:
                        cell.setBackground(self._ERROR_COLOR)

    def _validate_rows(self) -> None:
        if self._updating_table:
            return
        self._updating_table = True
        try:
            self._refresh_sources()
            self._clear_error_colors()
            try:
                bounds = self.boundaries()
            except (AttributeError, TypeError, ValueError):
                self.lbl_errors.setText("Dữ liệu bài và trang phải là số hợp lệ.")
                self.btn_confirm.setEnabled(False)
                return

            report = Splitter().validate(
                bounds, self._effective_evidence(bounds), self.page_count
            )
            self._last_report = report
            local_messages = []
            if not bounds:
                local_messages.append("Cần ít nhất một bài trước khi OCR.")
            for boundary in bounds:
                if boundary.page_start > boundary.page_end:
                    self._color_issue(boundary.index_no, "page_out_of_range")
                    local_messages.append("Trang đầu không được sau Trang cuối.")
            for issue in report.issues:
                self._color_issue(issue.lesson_no, issue.code)
            messages = [
                self.ISSUE_TEXT.get(issue.code, issue.message)
                for issue in report.issues
            ]
            self.lbl_errors.setText(
                " · ".join(dict.fromkeys((*local_messages, *messages)))
            )
            self.btn_confirm.setEnabled(report.valid and not local_messages)
        finally:
            self._updating_table = False

    def _effective_evidence(
        self, bounds: list[LessonBoundary]
    ) -> tuple[BoundaryEvidence, ...]:
        lesson_nos = {boundary.index_no for boundary in bounds}
        evidence = [
            item
            for item in self.evidence
            if item.lesson_no is None or item.lesson_no in lesson_nos
        ]
        for row, boundary in enumerate(bounds):
            if self._is_manual(row):
                evidence = [
                    item
                    for item in evidence
                    if item.lesson_no != boundary.index_no
                    and item.page_index != boundary.page_start
                ]
                evidence.append(
                    BoundaryEvidence(
                        "manual",
                        boundary.page_start,
                        boundary.index_no,
                        boundary.title,
                        1.0,
                        "Người dùng xác nhận",
                    )
                )
        return tuple(evidence)

    def boundaries(self) -> list[LessonBoundary]:
        result = []
        for row in range(self.table.rowCount()):
            index_no = int(self.table.item(row, 0).text())
            title = self.table.item(row, 1).text().strip() or None
            page_start = int(self.table.item(row, 2).text()) - 1
            page_end = int(self.table.item(row, 3).text()) - 1
            confidence_text = self.table.item(row, 4).text().strip().rstrip("%")
            result.append(
                LessonBoundary(
                    index_no=index_no,
                    title=title,
                    page_start=page_start,
                    page_end=page_end,
                    confidence=float(confidence_text) / 100,
                    kind="review" if index_no < 0 else "lesson",
                )
            )
        return result

    def _confirm(self) -> None:
        self._validate_rows()
        if not self.btn_confirm.isEnabled():
            return
        bounds = self.boundaries()
        self.user_db.replace_lessons(self.book_id, bounds)
        self.accept()


class DialogImport(QDialog):
    """Hộp thoại nhập sách PDF."""

    def __init__(self, user_db, dict_db=None, parent=None) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.dict_db = dict_db
        self.worker: BookImporterWorker | VocabImporterWorker | None = None
        self.imported_book_id: int | None = None
        self._pdf_path: str | None = None
        self._api_key: str | None = None

        self.setWindowTitle("Nhập sách từ file PDF")
        self.setFixedSize(520, 280)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        tieu_de = QLabel("Nhập giáo trình PDF (Boya / Hán ngữ)")
        tieu_de.setFont(ui_font(16, bold=True))
        tieu_de.setStyleSheet(f"color: {PALETTE['ink']};")
        lay.addWidget(tieu_de)

        self.lbl_status = QLabel("Hãy chọn tệp PDF sách để bắt đầu nhập:")
        self.lbl_status.setFont(ui_font(12))
        self.lbl_status.setStyleSheet(f"color: {PALETTE['ink2']};")
        lay.addWidget(self.lbl_status)

        # Ô nhập API Key (tùy chọn)
        self.txt_api = QLineEdit()
        self.txt_api.setPlaceholderText("LLM / Gemini API Key (Tùy chọn cho Smart Import AI)…")
        env_key = os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
        if env_key:
            self.txt_api.setText(env_key)
        self.txt_api.setMinimumHeight(32)
        lay.addWidget(self.txt_api)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        lay.addWidget(self.progress_bar)

        h_lay = QHBoxLayout()
        h_lay.addStretch(1)

        self.btn_chon = QPushButton("Chọn file PDF...")
        self.btn_chon.setFont(ui_font(13))
        self.btn_chon.setMinimumSize(120, 36)
        self.btn_chon.setStyleSheet(
            f"QPushButton {{ background: {PALETTE['accent']}; color: {PALETTE['card']}; border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}"
        )
        self.btn_chon.clicked.connect(self._chon_file)
        h_lay.addWidget(self.btn_chon)

        self.btn_dong = QPushButton("Đóng")
        self.btn_dong.setFont(ui_font(13))
        self.btn_dong.setMinimumSize(90, 36)
        self.btn_dong.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['ink2']}; border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
        )
        self.btn_dong.clicked.connect(self.reject)
        h_lay.addWidget(self.btn_dong)

        lay.addLayout(h_lay)

    def _chon_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file PDF giáo trình",
            "",
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        api_key = self.txt_api.text().strip() or None
        self._pdf_path = file_path
        self._api_key = api_key

        self.btn_chon.setEnabled(False)
        self.lbl_status.setText("Đang chuẩn bị nhập...")

        self.worker = BookImporterWorker(
            file_path,
            self.user_db.path,
            api_key=api_key,
            dict_path=getattr(self.dict_db, "path", None),
            parent=self,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.boundaries_ready.connect(self._on_boundaries_ready)
        self.worker.failed_import.connect(self._on_failed)
        self.worker.start()

    def _on_boundaries_ready(
        self, book_id: int, title: str, split_result: SplitResult
    ) -> None:
        book = self.user_db.get_book(book_id)
        if book is None:
            self._on_failed("Không đọc lại được thông tin sách")
            return
        review = DialogReviewBoundaries(
            self.user_db, book_id, int(book["page_count"]), split_result, self
        )
        if review.exec() != QDialog.DialogCode.Accepted:
            self.imported_book_id = book_id
            self.lbl_status.setText(
                f"Đã lưu ranh giới dự đoán của '{title}', chưa chạy OCR."
            )
            self.btn_chon.setEnabled(True)
            return
        self.lbl_status.setText("Ranh giới đã xác nhận. Đang OCR bảng từ mới...")
        self.worker = VocabImporterWorker(
            book_id,
            self._pdf_path or book["file_path"],
            self.user_db.path,
            api_key=self._api_key,
            dict_path=getattr(self.dict_db, "path", None),
            parent=self,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_import.connect(self._on_finished)
        self.worker.failed_import.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_finished(self, book_id: int, title: str) -> None:
        self.imported_book_id = book_id
        self.lbl_status.setText(f"Đã phân tích '{title}'. Hãy duyệt kết quả trước khi học.")
        self.progress_bar.setValue(100)
        self.btn_chon.setText("Xong")
        self.btn_chon.setEnabled(True)
        self.btn_chon.clicked.disconnect()
        self.btn_chon.clicked.connect(self.accept)

    def _on_failed(self, err: str) -> None:
        self.lbl_status.setText(f"Lỗi nhập sách: {err}")
        self.btn_chon.setEnabled(True)
