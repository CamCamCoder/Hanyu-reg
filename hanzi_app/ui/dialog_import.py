"""Hộp thoại nhập sách từ tệp PDF.

Cho phép chọn tệp PDF, gõ API Key (tùy chọn) và hiển thị thanh tiến trình nhập sách trong luồng nền.
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import Qt
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

from hanzi_app.data.models import LessonBoundary
from hanzi_app.service.importer import BookImporterWorker, VocabImporterWorker
from hanzi_app.ui.theme import PALETTE, ui_font


class DialogReviewBoundaries(QDialog):
    """Cho sửa và xác nhận ranh giới toàn bộ bài trước khi chạy OCR."""

    _HEADERS = ("Bài", "Tiêu đề", "Trang đầu", "Trang cuối", "Độ tin cậy")

    def __init__(self, user_db, book_id: int, page_count: int, parent=None) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.book_id = book_id
        self.page_count = page_count
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

        lessons = user_db.get_lessons(book_id)
        self.table = QTableWidget(len(lessons), len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row, lesson in enumerate(lessons):
            values = (
                lesson["index_no"],
                lesson.get("title") or "",
                lesson["page_start"] + 1,
                lesson["page_end"] + 1,
                f"{float(lesson.get('confidence', 0.0)):.0%}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (0, 4):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Để sau")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        confirm = QPushButton("Xác nhận và bắt đầu OCR")
        confirm.setStyleSheet(
            f"background: {PALETTE['accent']}; color: white; padding: 7px 14px;"
        )
        confirm.clicked.connect(self._confirm)
        actions.addWidget(confirm)
        root.addLayout(actions)

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
        try:
            bounds = self.boundaries()
        except (AttributeError, TypeError, ValueError):
            QMessageBox.warning(self, "Dữ liệu chưa hợp lệ", "Trang đầu/cuối phải là số.")
            return
        for boundary in bounds:
            if not (
                0 <= boundary.page_start <= boundary.page_end < self.page_count
            ):
                QMessageBox.warning(
                    self,
                    "Khoảng trang chưa hợp lệ",
                    f"Bài {boundary.index_no} phải nằm trong trang 1–{self.page_count}.",
                )
                return
        ordered = sorted(bounds, key=lambda item: item.page_start)
        for previous, current in zip(ordered, ordered[1:]):
            if current.page_start <= previous.page_end:
                QMessageBox.warning(
                    self,
                    "Các bài đang chồng trang",
                    f"Bài {previous.index_no} và Bài {current.index_no} đang chồng nhau.",
                )
                return
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

    def _on_boundaries_ready(self, book_id: int, title: str) -> None:
        book = self.user_db.get_book(book_id)
        if book is None:
            self._on_failed("Không đọc lại được thông tin sách")
            return
        review = DialogReviewBoundaries(
            self.user_db, book_id, int(book["page_count"]), self
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
