"""Màn hình Sách: quản lý giáo trình PDF, duyệt bài học và thêm từ vào Ôn tập.

QT-02, QT-03 & QT-04 bước 2. Bổ sung ô cấu hình API Key cố định & sửa từ vựng bài học.
"""

from __future__ import annotations

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.data.models import LessonBoundary, VocabRow
from hanzi_app.service.importer import (
    PreviewWorker,
    VisionRepairWorker,
)
from hanzi_app.ui.dialog_import import DialogImport
from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['line']};")
    return line


class DialogEditVocab(QDialog):
    """Hộp thoại chỉnh sửa danh sách từ vựng của bài học."""

    def __init__(self, lesson_title: str, words: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Chỉnh sửa từ vựng — {lesson_title}")
        self.setFixedSize(540, 420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)

        lbl = QLabel(f"Nhập danh sách từ vựng cho {lesson_title} (Mỗi từ 1 dòng):")
        lbl.setFont(ui_font(12, bold=True))
        lbl.setStyleSheet(f"color: {PALETTE['ink']};")
        lay.addWidget(lbl)

        lbl_sub = QLabel("Định dạng: TừHán  Pinyin  TừLoại  Nghĩa (Ví dụ: 你好 nǐhǎo v. Xin chào)")
        lbl_sub.setFont(mono_font(10))
        lbl_sub.setStyleSheet(f"color: {PALETTE['muted']};")
        lay.addWidget(lbl_sub)

        self.txt_content = QTextEdit()
        self.txt_content.setFont(han_font(14))

        # Điền sẵn các từ đang có
        lines = []
        for w in words:
            word_str = w.get("word", "")
            py_str = w.get("pinyin_src") or ""
            pos_str = w.get("pos") or ""
            mean_str = w.get("meaning_src") or ""
            lines.append(f"{word_str}  {py_str}  {pos_str}  {mean_str}".strip())

        self.txt_content.setText("\n".join(lines))
        lay.addWidget(self.txt_content, 1)

        h_lay = QHBoxLayout()
        h_lay.addStretch(1)

        btn_luu = QPushButton("Lưu thay đổi")
        btn_luu.setFont(ui_font(12, bold=True))
        btn_luu.setMinimumSize(110, 34)
        btn_luu.setStyleSheet(
            f"QPushButton {{ background: {PALETTE['accent']}; color: {PALETTE['card']}; border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}"
        )
        btn_luu.clicked.connect(self.accept)
        h_lay.addWidget(btn_luu)

        btn_huy = QPushButton("Hủy")
        btn_huy.setFont(ui_font(12))
        btn_huy.setMinimumSize(80, 34)
        btn_huy.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['ink2']}; border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
        )
        btn_huy.clicked.connect(self.reject)
        h_lay.addWidget(btn_huy)

        lay.addLayout(h_lay)

    def get_parsed_rows(self, source_page: int = 1) -> list[VocabRow]:
        """Tách text đã sửa thành danh sách VocabRow."""
        text = self.txt_content.toPlainText().strip()
        if not text:
            return []

        rows: list[VocabRow] = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if not parts:
                continue

            word = parts[0]
            py = parts[1] if len(parts) > 1 else None
            pos = parts[2] if len(parts) > 2 else None
            meaning = " ".join(parts[3:]) if len(parts) > 3 else None

            rows.append(
                VocabRow(
                    order_no=i + 1,
                    word=word,
                    pinyin_src=py,
                    pos=pos,
                    meaning_src=meaning,
                    source_page=source_page,
                    extract_by="manual",
                    needs_review=False,
                    review_reason=None,
                )
            )
        return rows


class DialogReviewBook(QDialog):
    """Duyệt ranh giới và bảng từ mới trước khi chuyển sách sang ready."""

    _HEADERS = ("STT", "Chữ Hán", "Pinyin", "Từ loại", "Hán-Việt", "Nghĩa Việt", "Trang")
    _REVIEW_HEADERS = (
        "Chọn", "Bài", "Trang", "STT", "Chữ Hán",
        "Pinyin", "Từ loại", "Hán-Việt", "Nghĩa Việt",
    )

    def __init__(
        self, user_db, book: dict, api_key: str | None = None,
        dict_path: str | None = None, parent=None
    ) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.book = book
        self.api_key = api_key
        self.dict_path = dict_path
        self.vision_worker: VisionRepairWorker | None = None
        self.preview_worker: PreviewWorker | None = None
        self._preview_workers: set[PreviewWorker] = set()
        self.review_preview_worker: PreviewWorker | None = None
        self._review_preview_workers: set[PreviewWorker] = set()
        self.lessons = user_db.get_lessons(book["id"])
        self.current_lesson: dict | None = None
        self.setWindowTitle(f"Duyệt kết quả nhập — {book['title']}")
        self.resize(1180, 760)

        root = QVBoxLayout(self)
        self.review_note = QLabel(
            "Chọn một dòng để xem ảnh nguồn, sửa nếu cần rồi tích ô. "
            "Bấm “Xác nhận các dòng đã chọn” để lưu phần đã kiểm tra."
        )
        self.review_note.setWordWrap(True)
        self.review_note.setStyleSheet(
            f"background: {PALETTE['warn_bg']}; color: {PALETTE['warn_ink']}; "
            f"padding: 9px; border: 1px solid {PALETTE['warn']};"
        )
        root.addWidget(self.review_note)

        self.tabs = QTabWidget()
        self.review_tab = QWidget()
        self.all_lessons_tab = QWidget()
        self.tabs.addTab(self.review_tab, "Cần xác nhận")
        self.tabs.addTab(self.all_lessons_tab, "Tất cả các bài")
        root.addWidget(self.tabs, 1)

        review_lay = QVBoxLayout(self.review_tab)
        review_toolbar = QHBoxLayout()
        self.lbl_review_count = QLabel()
        self.lbl_review_count.setFont(ui_font(12, bold=True))
        review_toolbar.addWidget(self.lbl_review_count)
        review_toolbar.addStretch(1)
        review_toolbar.addWidget(QLabel("Bài"))
        self.review_filter = QComboBox()
        self.review_filter.addItem("Tất cả các bài", None)
        for lesson in self.lessons:
            self.review_filter.addItem(
                f"Bài {lesson['index_no']}", lesson["id"]
            )
        review_toolbar.addWidget(self.review_filter)
        self.review_search = QLineEdit()
        self.review_search.setPlaceholderText("Tìm chữ Hán, pinyin hoặc nghĩa…")
        self.review_search.setMinimumWidth(240)
        review_toolbar.addWidget(self.review_search)
        review_lay.addLayout(review_toolbar)

        self.review_table = QTableWidget(0, len(self._REVIEW_HEADERS))
        self.review_table.setHorizontalHeaderLabels(self._REVIEW_HEADERS)
        self.review_table.setAlternatingRowColors(True)
        self.review_table.cellClicked.connect(self._show_review_source)
        review_header = self.review_table.horizontalHeader()
        review_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        review_header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        review_lay.addWidget(self.review_table, 1)
        self.review_preview = QLabel(
            "Chọn một dòng để xem ảnh nguồn của đúng bài"
        )
        self.review_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.review_preview.setMinimumHeight(220)
        self.review_preview.setStyleSheet(
            f"background: {PALETTE['bg']}; "
            f"border: 1px solid {PALETTE['line']};"
        )
        review_lay.addWidget(self.review_preview, 1)
        self.review_filter.currentIndexChanged.connect(self._apply_review_filter)
        self.review_search.textChanged.connect(self._apply_review_filter)
        self.review_table.itemChanged.connect(self._update_review_actions)

        review_actions = QHBoxLayout()
        self.btn_select_visible = QPushButton("Chọn tất cả đang hiển thị")
        self.btn_select_visible.clicked.connect(self._select_visible_rows)
        review_actions.addWidget(self.btn_select_visible)
        self.btn_clear_selection = QPushButton("Bỏ chọn")
        self.btn_clear_selection.clicked.connect(self._clear_review_selection)
        review_actions.addWidget(self.btn_clear_selection)
        review_actions.addStretch(1)
        self.btn_confirm_selected = QPushButton(
            "Xác nhận các dòng đã chọn (0)"
        )
        self.btn_confirm_selected.setMinimumHeight(42)
        self.btn_confirm_selected.setStyleSheet(
            f"background: {PALETTE['accent']}; color: white; padding: 8px 18px;"
        )
        self.btn_confirm_selected.setEnabled(False)
        self.btn_confirm_selected.clicked.connect(self._confirm_selected_rows)
        review_actions.addWidget(self.btn_confirm_selected)
        self.btn_finish_book = QPushButton("Hoàn tất nhập sách")
        self.btn_finish_book.setMinimumHeight(42)
        self.btn_finish_book.setEnabled(False)
        self.btn_finish_book.clicked.connect(self._finish_reviewed_book)
        review_actions.addWidget(self.btn_finish_book)
        review_lay.addLayout(review_actions)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.list_lessons = QListWidget()
        self.list_lessons.setMinimumWidth(210)
        for lesson in self.lessons:
            item = QListWidgetItem(self._lesson_label(lesson))
            item.setData(Qt.ItemDataRole.UserRole, lesson["id"])
            self.list_lessons.addItem(item)
        self.list_lessons.currentItemChanged.connect(self._load_selected)
        split.addWidget(self.list_lessons)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        boundary = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.start_spin = QSpinBox()
        self.end_spin = QSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(0, max(0, int(book.get("page_count") or 1) - 1))
        boundary.addWidget(QLabel("Tên bài"))
        boundary.addWidget(self.title_edit, 1)
        boundary.addWidget(QLabel("Từ trang"))
        boundary.addWidget(self.start_spin)
        boundary.addWidget(QLabel("đến"))
        boundary.addWidget(self.end_spin)
        right_lay.addLayout(boundary)

        content = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self._show_row_source)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        content.addWidget(self.table)

        self.preview = QLabel("Chọn một dòng để xem ảnh nguồn")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(250)
        self.preview.setStyleSheet(
            f"background: {PALETTE['bg']}; border: 1px solid {PALETTE['line']};"
        )
        content.addWidget(self.preview)
        right_lay.addWidget(content, 1)

        actions = QHBoxLayout()
        self.lbl_count = QLabel()
        actions.addWidget(self.lbl_count)
        actions.addStretch(1)
        self.btn_vision = QPushButton("Chạy Vision bài này")
        self.btn_vision.clicked.connect(self._run_vision)
        actions.addWidget(self.btn_vision)
        btn_save = QPushButton("Lưu bài đang xem")
        btn_save.clicked.connect(self._save_current)
        actions.addWidget(btn_save)
        btn_confirm = QPushButton("Xác nhận toàn bộ")
        btn_confirm.setStyleSheet(
            f"background: {PALETTE['accent']}; color: white; padding: 7px 14px;"
        )
        btn_confirm.clicked.connect(self._confirm_all)
        actions.addWidget(btn_confirm)
        right_lay.addLayout(actions)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        all_lessons_lay = QVBoxLayout(self.all_lessons_tab)
        all_lessons_lay.setContentsMargins(0, 0, 0, 0)
        all_lessons_lay.addWidget(split)

        self._reload_review_queue()

        if self.list_lessons.count():
            self.list_lessons.setCurrentRow(0)

    @staticmethod
    def _lesson_label(lesson: dict) -> str:
        return f"Bài {lesson['index_no']}  ·  {lesson['page_start'] + 1}–{lesson['page_end'] + 1}"

    def _reload_review_queue(self) -> None:
        self.review_preview_worker = None
        self.review_preview.setPixmap(QPixmap())
        self.review_preview.setText(
            "Chọn một dòng để xem ảnh nguồn của đúng bài"
        )
        queue: list[tuple[dict, dict]] = []
        for lesson in self.lessons:
            for word in self.user_db.get_lesson_words(lesson["id"]):
                if word.get("needs_review"):
                    queue.append((lesson, word))
        queue.sort(
            key=lambda pair: (
                pair[0]["index_no"],
                pair[1].get("order_no") or 0,
                pair[1]["id"],
            )
        )

        self.review_table.blockSignals(True)
        try:
            self.review_table.setRowCount(len(queue))
            lesson_ids: set[int] = set()
            for row, (lesson, word) in enumerate(queue):
                lesson_ids.add(lesson["id"])
                metadata = {
                    "lesson_id": lesson["id"],
                    "lesson_index": lesson["index_no"],
                    "page_start": lesson["page_start"],
                    "page_end": lesson["page_end"],
                    "word_id": word["id"],
                }
                check_item = QTableWidgetItem()
                check_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                check_item.setCheckState(Qt.CheckState.Unchecked)
                check_item.setData(Qt.ItemDataRole.UserRole, metadata)
                self.review_table.setItem(row, 0, check_item)

                values = (
                    f"Bài {lesson['index_no']}",
                    word.get("source_page"),
                    word.get("order_no"),
                    word.get("word"),
                    word.get("pinyin_src"),
                    word.get("pos"),
                    word.get("hanviet_src"),
                    word.get("meaning_src"),
                )
                for column, value in enumerate(values, start=1):
                    item = QTableWidgetItem(
                        "" if value is None else str(value)
                    )
                    if column <= 3:
                        item.setFlags(
                            Qt.ItemFlag.ItemIsEnabled
                            | Qt.ItemFlag.ItemIsSelectable
                        )
                    self.review_table.setItem(row, column, item)
        finally:
            self.review_table.blockSignals(False)

        if queue:
            self.lbl_review_count.setText(
                f"{len(queue)} từ cần xác nhận · thuộc {len(lesson_ids)} bài"
            )
        else:
            self.lbl_review_count.setText("Đã xác nhận toàn bộ từ")
        self._apply_review_filter()
        self._update_review_actions()

    def _apply_review_filter(self) -> None:
        lesson_id = self.review_filter.currentData()
        query = self.review_search.text().strip().casefold()
        for row in range(self.review_table.rowCount()):
            check_item = self.review_table.item(row, 0)
            metadata = check_item.data(Qt.ItemDataRole.UserRole)
            matches_lesson = (
                lesson_id is None or metadata["lesson_id"] == lesson_id
            )
            searchable = " ".join(
                self.review_table.item(row, column).text()
                for column in (4, 5, 7, 8)
            ).casefold()
            self.review_table.setRowHidden(
                row, not (matches_lesson and query in searchable)
            )

    def _selected_review_rows(self) -> list[int]:
        return [
            row
            for row in range(self.review_table.rowCount())
            if self.review_table.item(row, 0) is not None
            and self.review_table.item(row, 0).checkState()
            == Qt.CheckState.Checked
        ]

    def _update_review_actions(self, _item=None) -> None:
        selected_count = len(self._selected_review_rows())
        has_pending = self.review_table.rowCount() > 0
        self.btn_confirm_selected.setText(
            f"Xác nhận các dòng đã chọn ({selected_count})"
        )
        self.btn_confirm_selected.setEnabled(selected_count > 0)
        self.btn_select_visible.setEnabled(has_pending)
        self.btn_clear_selection.setEnabled(has_pending)
        self.btn_finish_book.setEnabled(not has_pending)

    def _select_visible_rows(self) -> None:
        self.review_table.blockSignals(True)
        try:
            for row in range(self.review_table.rowCount()):
                if not self.review_table.isRowHidden(row):
                    self.review_table.item(row, 0).setCheckState(
                        Qt.CheckState.Checked
                    )
        finally:
            self.review_table.blockSignals(False)
        self._update_review_actions()

    def _confirm_selected_rows(self) -> None:
        selected_rows = self._selected_review_rows()
        if not selected_rows:
            return

        selected_by_lesson: dict[int, dict[int, int]] = {}
        for row in selected_rows:
            word = self.review_table.item(row, 4).text().strip()
            if not word:
                QMessageBox.warning(
                    self,
                    "Thiếu chữ Hán",
                    "Chữ Hán không được để trống trước khi xác nhận.",
                )
                self.review_table.setCurrentCell(row, 4)
                return
            metadata = self.review_table.item(row, 0).data(
                Qt.ItemDataRole.UserRole
            )
            selected_by_lesson.setdefault(
                metadata["lesson_id"], {}
            )[metadata["word_id"]] = row

        answer = QMessageBox.question(
            self,
            "Xác nhận các từ đã chọn",
            f"Xác nhận {len(selected_rows)} từ thuộc "
            f"{len(selected_by_lesson)} bài?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            for lesson_id, selected_words in selected_by_lesson.items():
                saved_rows: list[VocabRow] = []
                for word in self.user_db.get_lesson_words(lesson_id):
                    table_row = selected_words.get(word["id"])
                    if table_row is None:
                        saved_rows.append(
                            VocabRow(
                                order_no=word.get("order_no"),
                                word=word["word"],
                                pinyin_src=word.get("pinyin_src"),
                                pos=word.get("pos"),
                                hanviet_src=word.get("hanviet_src"),
                                meaning_src=word.get("meaning_src"),
                                source_page=word.get("source_page"),
                                extract_by=word.get("extract_by") or "manual",
                                needs_review=bool(word.get("needs_review")),
                                review_reason=None,
                            )
                        )
                        continue

                    def value(column: int) -> str:
                        item = self.review_table.item(table_row, column)
                        return "" if item is None else item.text().strip()

                    order_text = value(3)
                    page_text = value(2)
                    saved_rows.append(
                        VocabRow(
                            order_no=(
                                int(order_text)
                                if order_text.isdigit()
                                else word.get("order_no")
                            ),
                            word=value(4),
                            pinyin_src=value(5) or None,
                            pos=value(6) or None,
                            hanviet_src=value(7) or None,
                            meaning_src=value(8) or None,
                            source_page=(
                                int(page_text)
                                if page_text.isdigit()
                                else word.get("source_page")
                            ),
                            extract_by="manual",
                            needs_review=False,
                            review_reason=None,
                        )
                    )
                self.user_db.replace_vocab(lesson_id, saved_rows)
        except Exception as exc:
            self._reload_review_queue()
            QMessageBox.warning(
                self, "Không lưu được", f"Không thể xác nhận các từ: {exc}"
            )
            return

        self._reload_review_queue()

    def _clear_review_selection(self) -> None:
        self.review_table.blockSignals(True)
        try:
            for row in range(self.review_table.rowCount()):
                self.review_table.item(row, 0).setCheckState(
                    Qt.CheckState.Unchecked
                )
        finally:
            self.review_table.blockSignals(False)
        self._update_review_actions()

    def _show_review_source(self, row: int, _column: int) -> None:
        check_item = self.review_table.item(row, 0)
        if check_item is None:
            return
        metadata = check_item.data(Qt.ItemDataRole.UserRole)
        self.review_preview_worker = None
        self.review_preview.setPixmap(QPixmap())
        self.review_preview.setText(
            f"Đang tải ảnh nguồn Bài {metadata['lesson_index']}…"
        )
        worker = PreviewWorker(
            self.book["file_path"],
            metadata["page_start"],
            metadata["page_end"],
            dpi=125,
            parent=self,
        )
        self.review_preview_worker = worker
        self._review_preview_workers.add(worker)
        worker.loaded.connect(
            lambda data, w=worker: self._on_review_preview_loaded(w, data)
        )
        worker.failed.connect(
            lambda error, w=worker: self._on_review_preview_failed(w, error)
        )
        worker.finished.connect(
            lambda w=worker: self._on_review_preview_finished(w)
        )
        worker.start()

    def _on_review_preview_loaded(
        self, worker: PreviewWorker, data: bytes
    ) -> None:
        if worker is not self.review_preview_worker:
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(data, "PNG"):
            self.review_preview.setText(
                "Không mở được ảnh nguồn: dữ liệu ảnh không hợp lệ"
            )
            return
        self.review_preview.setPixmap(
            pixmap.scaled(
                self.review_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )

    def _on_review_preview_failed(
        self, worker: PreviewWorker, error: str
    ) -> None:
        if worker is self.review_preview_worker:
            self.review_preview.setText(
                f"Không mở được ảnh nguồn: {error}"
            )

    def _on_review_preview_finished(self, worker: PreviewWorker) -> None:
        self._review_preview_workers.discard(worker)
        if worker is self.review_preview_worker:
            self.review_preview_worker = None
        worker.deleteLater()

    def _finish_reviewed_book(self) -> None:
        remaining = sum(
            int(word.get("needs_review") or 0)
            for lesson in self.user_db.get_lessons(self.book["id"])
            for word in self.user_db.get_lesson_words(lesson["id"])
        )
        if remaining:
            QMessageBox.warning(
                self,
                "Còn từ chưa xác nhận",
                f"Còn {remaining} từ cần xác nhận trước khi hoàn tất sách.",
            )
            return
        self.user_db.set_import_state(self.book["id"], "ready")
        self.accept()

    def _load_selected(self, current, _previous=None) -> None:
        if current is None:
            return
        # Worker của bài trước có thể vẫn đang render. Vô hiệu hóa kết quả đó;
        # thread vẫn tự kết thúc và được dọn mà không ghi đè preview bài mới.
        self.preview_worker = None
        lesson_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_lesson = next(
            lesson for lesson in self.lessons if lesson["id"] == lesson_id
        )
        lesson = self.current_lesson
        self.title_edit.setText(lesson.get("title") or "")
        self.start_spin.setValue(lesson["page_start"])
        self.end_spin.setValue(lesson["page_end"])
        words = self.user_db.get_lesson_words(lesson_id)
        self._populate_rows(words)
        self.preview.setText("Chọn một dòng để xem ảnh nguồn")

    def _populate_rows(self, words) -> None:
        self.table.setRowCount(len(words))
        warning_count = 0
        for row_index, word in enumerate(words):
            get = word.get if isinstance(word, dict) else lambda key: getattr(word, key, None)
            values = (
                get("order_no"),
                get("word"),
                get("pinyin_src"),
                get("pos"),
                get("hanviet_src"),
                get("meaning_src"),
                get("source_page"),
            )
            warning = bool(get("needs_review"))
            warning_count += int(warning)
            for column, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                if warning:
                    item.setBackground(QColor(PALETTE["warn_bg"]))
                    item.setToolTip("Dòng OCR cần kiểm tra lại")
                self.table.setItem(row_index, column, item)
        self.lbl_count.setText(f"{len(words)} dòng · {warning_count} cần kiểm tra")

    def _run_vision(self) -> None:
        if self.current_lesson is None:
            return
        if not self.api_key:
            QMessageBox.warning(
                self, "Thiếu API Key", "Nhập API Key ở màn hình Sách để chạy Vision."
            )
            return
        start, end = self.start_spin.value(), self.end_spin.value()
        if end < start:
            QMessageBox.warning(
                self, "Khoảng trang sai", "Trang cuối phải từ trang đầu trở đi."
            )
            return
        boundary = LessonBoundary(
            index_no=self.current_lesson["index_no"],
            title=self.title_edit.text().strip() or None,
            page_start=start,
            page_end=end,
            confidence=float(self.current_lesson.get("confidence", 1.0)),
            kind="review" if self.current_lesson["index_no"] < 0 else "lesson",
        )
        self.btn_vision.setEnabled(False)
        self.lbl_count.setText("Vision đang đọc lại crop bảng từ mới...")
        self.vision_worker = VisionRepairWorker(
            self.book["file_path"],
            boundary,
            self.api_key,
            dict_path=self.dict_path,
            parent=self,
        )
        self.vision_worker.finished_rows.connect(self._on_vision_rows)
        self.vision_worker.failed.connect(self._on_vision_failed)
        self.vision_worker.start()

    def _on_vision_rows(self, rows: list[VocabRow]) -> None:
        self._populate_rows(rows)
        self.btn_vision.setEnabled(True)
        self.lbl_count.setText(
            f"Vision trả về {len(rows)} dòng · kiểm tra rồi bấm “Lưu bài đang xem”"
        )

    def _on_vision_failed(self, error: str) -> None:
        self.btn_vision.setEnabled(True)
        self.lbl_count.setText("Vision không hoàn tất.")
        QMessageBox.warning(self, "Lỗi Vision", error)

    def _rows_from_table(self) -> list[VocabRow]:
        rows: list[VocabRow] = []
        for row in range(self.table.rowCount()):
            def value(column: int) -> str:
                item = self.table.item(row, column)
                return "" if item is None else item.text().strip()

            word = value(1)
            if not word:
                continue
            order = int(value(0)) if value(0).isdigit() else len(rows) + 1
            page = int(value(6)) if value(6).isdigit() else self.start_spin.value() + 1
            rows.append(
                VocabRow(
                    order_no=order,
                    word=word,
                    pinyin_src=value(2) or None,
                    pos=value(3) or None,
                    hanviet_src=value(4) or None,
                    meaning_src=value(5) or None,
                    source_page=page,
                    extract_by="manual",
                    needs_review=False,
                    review_reason=None,
                )
            )
        return rows

    def _save_current(self) -> bool:
        if self.current_lesson is None:
            return False
        start, end = self.start_spin.value(), self.end_spin.value()
        if end < start:
            QMessageBox.warning(self, "Khoảng trang sai", "Trang cuối phải từ trang đầu trở đi.")
            return False
        lesson_id = self.current_lesson["id"]
        self.user_db.update_lesson_boundary(
            lesson_id, self.title_edit.text().strip() or None, start, end
        )
        self.user_db.replace_vocab(lesson_id, self._rows_from_table())
        self.current_lesson.update(
            title=self.title_edit.text().strip() or None,
            page_start=start,
            page_end=end,
        )
        current = self.list_lessons.currentItem()
        if current:
            current.setText(self._lesson_label(self.current_lesson))
        self._load_selected(current)
        return True

    def _show_row_source(self, row: int, _column: int) -> None:
        if self.current_lesson is None:
            return
        if self.preview_worker is not None:
            return
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Đang tải ảnh nguồn…")
        self.preview_worker = PreviewWorker(
            self.book["file_path"],
            self.current_lesson["page_start"],
            self.current_lesson["page_end"],
            dpi=125,
            parent=self,
        )
        worker = self.preview_worker
        self._preview_workers.add(worker)
        worker.loaded.connect(lambda data, w=worker: self._on_preview_loaded(w, data))
        worker.failed.connect(lambda error, w=worker: self._on_preview_failed(w, error))
        worker.finished.connect(lambda w=worker: self._on_preview_finished(w))
        worker.start()

    def _on_preview_loaded(self, worker: PreviewWorker, data: bytes) -> None:
        if worker is not self.preview_worker:
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(data, "PNG"):
            self.preview.setText("Không mở được ảnh nguồn: dữ liệu ảnh không hợp lệ")
            return
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )

    def _on_preview_failed(self, worker: PreviewWorker, error: str) -> None:
        if worker is not self.preview_worker:
            return
        self.preview.setText(f"Không mở được ảnh nguồn: {error}")

    def _on_preview_finished(self, worker: PreviewWorker) -> None:
        self._preview_workers.discard(worker)
        if worker is self.preview_worker:
            self.preview_worker = None
        worker.deleteLater()

    def _confirm_all(self) -> None:
        if not self._save_current():
            return
        lessons = self.user_db.get_lessons(self.book["id"])
        by_page = sorted(lessons, key=lambda item: item["page_start"])
        for previous, current in zip(by_page, by_page[1:]):
            if current["page_start"] <= previous["page_end"]:
                QMessageBox.warning(
                    self,
                    "Bài học chồng trang",
                    f"Bài {previous['index_no']} và Bài {current['index_no']} đang chồng nhau.",
                )
                return
        remaining = sum(
            int(word.get("needs_review") or 0)
            for lesson in lessons
            for word in self.user_db.get_lesson_words(lesson["id"])
        )
        if remaining:
            QMessageBox.warning(
                self,
                "Còn dòng chưa duyệt",
                f"Còn {remaining} dòng màu vàng. Hãy mở từng bài, sửa hoặc bấm "
                "“Lưu bài đang xem” để xác nhận.",
            )
            return
        self.user_db.set_import_state(self.book["id"], "ready")
        self.accept()


class ScreenBooks(QWidget):
    """Màn hình Sách: quản lý sách, xem danh sách bài học và đưa từ vào Ôn tập."""

    progress_changed = Signal()

    def __init__(self, user_db, dict_db=None, parent=None) -> None:
        super().__init__(parent)
        self.user_db = user_db
        self.dict_db = dict_db
        self._current_book_id: int | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left(), 0)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {PALETTE['line']};")
        root.addWidget(sep)

        self._right_panel = QWidget()
        self._right_lay = QVBoxLayout(self._right_panel)
        self._right_lay.setContentsMargins(20, 20, 20, 20)
        self._right_lay.setSpacing(12)
        self._hien_placeholder()
        root.addWidget(self._right_panel, 1)

        self.load_books()

    # =========================================================== panel trái
    def _build_left(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(350)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        tieu_de = QLabel("Thư viện Sách")
        tieu_de.setFont(ui_font(18, bold=True))
        tieu_de.setStyleSheet(f"color: {PALETTE['ink']};")
        lay.addWidget(tieu_de)

        # Ô cấu hình API Key cố định
        lbl_key = QLabel("CẤU HÌNH AI SMART IMPORT:")
        lbl_key.setFont(ui_font(10, bold=True))
        lbl_key.setStyleSheet(f"color: {PALETTE['muted']};")
        lay.addWidget(lbl_key)

        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("Nhập Gemini / LLM API Key…")
        saved_key = self.user_db.get_setting("api_key") or ""
        self.txt_api_key.setText(saved_key)
        os.environ["GEMINI_API_KEY"] = saved_key
        os.environ["LLM_API_KEY"] = saved_key
        self.txt_api_key.setMinimumHeight(32)
        self.txt_api_key.editingFinished.connect(self._luu_api_key)
        lay.addWidget(self.txt_api_key)

        self.btn_nhap_pdf = QPushButton("  + Nhập sách PDF...")
        self.btn_nhap_pdf.setFont(ui_font(13, bold=True))
        self.btn_nhap_pdf.setFixedHeight(38)
        self.btn_nhap_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nhap_pdf.setStyleSheet(
            f"QPushButton {{ background: {PALETTE['accent']}; color: {PALETTE['card']}; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}"
        )
        self.btn_nhap_pdf.clicked.connect(self._mo_dialog_nhap)
        lay.addWidget(self.btn_nhap_pdf)

        lay.addWidget(_sep())

        lbl_ds = QLabel("SÁCH ĐÃ NHẬP")
        lbl_ds.setFont(ui_font(11, bold=True))
        lbl_ds.setStyleSheet(f"color: {PALETTE['muted']};")
        lay.addWidget(lbl_ds)

        self.list_books = QListWidget()
        self.list_books.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; }}"
            f"QListWidget::item {{ padding: 10px; border-radius: 6px; color: {PALETTE['ink']}; }}"
            f"QListWidget::item:hover {{ background: {PALETTE['card']}; }}"
            f"QListWidget::item:selected {{ background: {PALETTE['accent2_bg']}; color: {PALETTE['accent2']}; font-weight: bold; }}"
        )
        self.list_books.itemClicked.connect(self._on_book_selected)
        lay.addWidget(self.list_books, 1)

        return panel

    def _luu_api_key(self) -> None:
        key = self.txt_api_key.text().strip()
        self.user_db.set_setting("api_key", key)
        os.environ["GEMINI_API_KEY"] = key
        os.environ["LLM_API_KEY"] = key

    def load_books(self) -> None:
        """Đọc danh sách sách từ user_db và nạp vào danh sách trái."""
        self.list_books.clear()
        books = self.user_db.get_books()

        if not books:
            item = QListWidgetItem("Chưa có sách nào. Bấm nút '+' để nhập sách.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_books.addItem(item)
            return

        for b in books:
            state = b.get("import_state")
            if state == "review_bounds":
                suffix = "  ·  chờ duyệt ranh giới"
            elif state == "extracting":
                suffix = "  ·  đang OCR"
            elif state == "review":
                suffix = "  ·  cần duyệt từ mới"
            else:
                suffix = ""
            item = QListWidgetItem(f"📖  {b['title']}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, b["id"])
            self.list_books.addItem(item)

    # =========================================================== panel phải
    def _hien_placeholder(self) -> None:
        self._xoa_right()
        lbl = QLabel("Chọn một quyển sách ở bên trái để xem danh sách bài học")
        lbl.setFont(ui_font(14))
        lbl.setStyleSheet(f"color: {PALETTE['muted']};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_lay.addWidget(lbl, 1, Qt.AlignmentFlag.AlignCenter)

    def _xoa_right(self) -> None:
        while self._right_lay.count():
            item = self._right_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_book_selected(self, item: QListWidgetItem) -> None:
        book_id = item.data(Qt.ItemDataRole.UserRole)
        if not book_id:
            return
        self._current_book_id = book_id
        self._hien_bai_hoc_cua_sach(book_id, item.text().replace("📖  ", ""))

    def _hien_bai_hoc_cua_sach(self, book_id: int, book_title: str) -> None:
        self._xoa_right()
        book = self.user_db.get_book(book_id)
        if book is None:
            self._hien_placeholder()
            return

        h_top = QHBoxLayout()

        lbl_tieu_de = QLabel(book_title)
        lbl_tieu_de.setFont(ui_font(20, bold=True))
        lbl_tieu_de.setStyleSheet(f"color: {PALETTE['ink']};")
        h_top.addWidget(lbl_tieu_de)

        h_top.addStretch(1)

        btn_xoa = QPushButton("  🗑 Xoá sách  ")
        btn_xoa.setFont(ui_font(11, bold=True))
        btn_xoa.setFixedHeight(32)
        btn_xoa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_xoa.setStyleSheet(
            f"QPushButton {{ background: transparent; color: #d9534f; border: 1px solid #d9534f; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: #d9534f; color: #ffffff; }}"
        )
        btn_xoa.clicked.connect(lambda _, b_id=book_id, b_t=book_title: self._xoa_sach(b_id, b_t))
        h_top.addWidget(btn_xoa)

        self._right_lay.addLayout(h_top)
        self._right_lay.addWidget(_sep())

        if book.get("import_state") == "review":
            review_box = QFrame()
            review_box.setStyleSheet(
                f"background: {PALETTE['warn_bg']}; border: 1px solid {PALETTE['warn']};"
            )
            review_lay = QHBoxLayout(review_box)
            review_text = QLabel("Kết quả OCR chưa được duyệt nên chưa thể thêm vào Ôn tập.")
            review_text.setStyleSheet(f"color: {PALETTE['warn_ink']}; border: none;")
            review_lay.addWidget(review_text, 1)
            btn_review = QPushButton("Duyệt kết quả")
            btn_review.clicked.connect(
                lambda: self._review_book(book)
            )
            review_lay.addWidget(btn_review)
            self._right_lay.addWidget(review_box)

        lessons = self.user_db.get_lessons(book_id)
        if not lessons:
            lbl_khong = QLabel("Quyển sách này chưa có bài học nào")
            lbl_khong.setFont(mono_font(12))
            lbl_khong.setStyleSheet(f"color: {PALETTE['muted']};")
            self._right_lay.addWidget(lbl_khong)
            self._right_lay.addStretch(1)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cont = QWidget()
        v_lay = QVBoxLayout(cont)
        v_lay.setSpacing(12)
        v_lay.setContentsMargins(0, 0, 0, 0)

        for l in lessons:
            words = self.user_db.get_lesson_words(l["id"])
            card = self._build_lesson_card(
                l, words, ready=book.get("import_state") == "ready"
            )
            v_lay.addWidget(card)

        v_lay.addStretch(1)
        scroll.setWidget(cont)
        self._right_lay.addWidget(scroll, 1)

    def _format_lesson_title(self, index_no: int, raw_title: str | None) -> str:
        title = (raw_title or "").strip()
        if not title:
            return f"Bài {index_no}"
        if title.startswith("Bài") or title.startswith("Lesson") or title.startswith("第"):
            return title
        return f"Bài {index_no}: {title}"

    def _build_lesson_card(
        self, lesson: dict, words: list[dict], ready: bool = True
    ) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {PALETTE['card']}; border: 1px solid {PALETTE['line']}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        h_lay = QHBoxLayout()

        ten_bai = self._format_lesson_title(lesson["index_no"], lesson.get("title"))
        lbl_ten = QLabel(ten_bai)
        lbl_ten.setFont(ui_font(14, bold=True))
        lbl_ten.setStyleSheet(f"color: {PALETTE['ink']}; border: none;")
        h_lay.addWidget(lbl_ten)

        h_lay.addStretch(1)

        # Nút Sửa từ vựng bài học
        btn_sua = QPushButton("  ✏ Sửa từ vựng  ")
        btn_sua.setFont(ui_font(11))
        btn_sua.setFixedHeight(30)
        btn_sua.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sua.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['ink2']}; border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {PALETTE['bg']}; }}"
        )
        btn_sua.clicked.connect(lambda _, l=lesson, w=words: self._mo_dialog_sua_vocab(l, w))
        h_lay.addWidget(btn_sua)

        if words and ready:
            btn_them = QPushButton("  + Thêm vào Ôn tập  ")
            btn_them.setFont(ui_font(11, bold=True))
            btn_them.setFixedHeight(30)
            btn_them.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_them.setStyleSheet(
                f"QPushButton {{ background: {PALETTE['accent2_bg']}; color: {PALETTE['accent2']}; border: 1px solid {PALETTE['accent2_line']}; border-radius: 4px; }}"
                f"QPushButton:hover {{ background: {PALETTE['accent2']}; color: {PALETTE['card']}; }}"
            )
            btn_them.clicked.connect(lambda _, w=words, btn=btn_them: self._them_vao_on_tap(w, btn))
            h_lay.addWidget(btn_them)

        lay.addLayout(h_lay)

        # Danh sách từ vựng trong bài
        if words:
            lbl_sub = QLabel(f"Tổng số {len(words)} từ vựng:")
            lbl_sub.setFont(ui_font(11, bold=True))
            lbl_sub.setStyleSheet(f"color: {PALETTE['muted']}; border: none;")
            lay.addWidget(lbl_sub)

            grid_w = QWidget()
            grid_lay = QGridLayout(grid_w)
            grid_lay.setContentsMargins(0, 0, 0, 0)
            grid_lay.setSpacing(6)

            cols = 4
            for i, w in enumerate(words):
                w_str = w.get("word", "")
                py_str = w.get("pinyin_src") or ""
                mean_str = w.get("meaning_src") or ""

                tag_box = QFrame()
                tag_box.setStyleSheet(
                    f"QFrame {{ background: {PALETTE['bg']}; border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
                )
                t_lay = QVBoxLayout(tag_box)
                t_lay.setContentsMargins(6, 4, 6, 4)
                t_lay.setSpacing(1)

                lbl_w = QLabel(w_str)
                lbl_w.setFont(han_font(16))
                lbl_w.setStyleSheet(f"color: {PALETTE['ink']}; border: none;")
                t_lay.addWidget(lbl_w)

                if py_str or mean_str:
                    sub_txt = f"{py_str} {mean_str}".strip()
                    short_sub = sub_txt[:15] + "…" if len(sub_txt) > 15 else sub_txt
                    lbl_s = QLabel(short_sub)
                    lbl_s.setFont(mono_font(9))
                    lbl_s.setStyleSheet(f"color: {PALETTE['muted']}; border: none;")
                    if sub_txt:
                        lbl_s.setToolTip(sub_txt)
                    t_lay.addWidget(lbl_s)

                grid_lay.addWidget(tag_box, i // cols, i % cols)

            lay.addWidget(grid_w)
        else:
            lbl_empty = QLabel("Chưa có từ vựng bóc tách (Bấm nút '✏ Sửa từ vựng' ở góc phải để thêm thủ công)")
            lbl_empty.setFont(mono_font(10))
            lbl_empty.setStyleSheet(f"color: {PALETTE['muted']}; border: none;")
            lay.addWidget(lbl_empty)

        return card

    def _mo_dialog_sua_vocab(self, lesson: dict, words: list[dict]) -> None:
        title = self._format_lesson_title(lesson["index_no"], lesson.get("title"))
        dlg = DialogEditVocab(title, words, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_rows = dlg.get_parsed_rows(source_page=lesson.get("page_start", 0) + 1)
            self.user_db.replace_vocab(lesson["id"], new_rows)
            if self._current_book_id:
                self._hien_bai_hoc_cua_sach(self._current_book_id, "")

    def _them_vao_on_tap(self, words: list[dict], btn: QPushButton) -> None:
        """Đưa danh sách từ vựng của bài vào tiến độ ôn tập (UserDb.upsert_progress)."""
        from datetime import date
        from hanzi_app.data.models import ReviewOutcome

        init_outcome = ReviewOutcome(
            ease=2.5,
            interval_days=0,
            repetition=0,
            lapse_count=0,
            status="new",
            due_date=date.today(),
        )

        count = 0
        for w in words:
            word_str = w.get("word")
            if word_str:
                self.user_db.upsert_progress(word_str, outcome=init_outcome, source_lw_id=w.get("id"))
                count += 1

        btn.setText(f"  ✓ Đã thêm {count} từ vào Ôn tập  ")
        btn.setStyleSheet(
            f"QPushButton {{ background: {PALETTE['accent2']}; color: {PALETTE['card']}; border: none; border-radius: 4px; }}"
        )
        self.progress_changed.emit()

    def _mo_dialog_nhap(self) -> None:
        self._luu_api_key()
        dlg = DialogImport(self.user_db, self.dict_db, self)
        if dlg.exec() == DialogImport.DialogCode.Accepted:
            self.load_books()
            if dlg.imported_book_id:
                for i in range(self.list_books.count()):
                    item = self.list_books.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == dlg.imported_book_id:
                        self.list_books.setCurrentItem(item)
                        self._on_book_selected(item)
                        break

    def _review_book(self, book: dict) -> None:
        dialog = DialogReviewBook(
            self.user_db,
            book,
            api_key=self.txt_api_key.text().strip() or None,
            dict_path=getattr(self.dict_db, "path", None),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_books()
            self._hien_bai_hoc_cua_sach(book["id"], book["title"])

    def _xoa_sach(self, book_id: int, book_title: str) -> None:
        """Xoá quyển sách đang chọn và toàn bộ bài học thuộc sách sau khi xác nhận."""
        reply = QMessageBox.question(
            self,
            "Xác nhận xoá sách",
            f"Bạn có chắc chắn muốn xoá quyển sách '{book_title}' và toàn bộ bài học của sách này không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.user_db.delete_book(book_id)
            self._current_book_id = None
            self.load_books()
            self._hien_placeholder()
