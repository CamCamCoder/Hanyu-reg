"""Kiểm thử logic dialog duyệt nhập sách ở chế độ Qt offscreen."""

import os
import logging
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox

import hanzi_app.service.importer as importer_module
import hanzi_app.ui.screen_books as screen_books_module
from hanzi_app.data.models import (
    BoundaryEvidence,
    BoundaryIssue,
    BoundaryReport,
    LessonBoundary,
    SplitResult,
    VocabBlock,
    VocabRow,
)
from hanzi_app.data.userdb import UserDb
from hanzi_app.ui.dialog_import import DialogImport, DialogReviewBoundaries
from hanzi_app.ui.screen_books import DialogReviewBook, ScreenBooks
from hanzi_app.ui.theme import PALETTE


def test_dialog_import_logs_progress_and_failure_breadcrumbs(caplog):
    class _ProgressBar:
        def setValue(self, _value):
            return None

    class _Label:
        def setText(self, _text):
            return None

    class _Button:
        def setEnabled(self, _enabled):
            return None

    class _FakeDialog:
        progress_bar = _ProgressBar()
        lbl_status = _Label()
        btn_chon = _Button()

    fake = _FakeDialog()
    with caplog.at_level(logging.INFO, logger="hanzi_app.ui.dialog_import"):
        DialogImport._on_progress(fake, 65, "Dang OCR bai 1")
    assert "65%" in caplog.text
    assert "Dang OCR bai 1" in caplog.text

    with caplog.at_level(logging.ERROR, logger="hanzi_app.ui.dialog_import"):
        DialogImport._on_failed(fake, "khong tim thay block")
    assert "khong tim thay block" in caplog.text
class _FakePreviewWorker(QObject):
    loaded = Signal(bytes)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, calls, path, start, end, **kwargs):
        super().__init__(kwargs.get("parent"))
        calls.append((path, start, end))

    def start(self):
        return None


def _review_row(order, word, page, needs_review):

    return VocabRow(
        order_no=order,
        word=word,
        pinyin_src={
            "教室": "jidoshi",
            "老师": "lǎoshī",
            "无聊": "wúliáo",
            "医院": "yīyuàn",
        }[word],
        pos="n.",
        hanviet_src=None,
        meaning_src={
            "教室": "lớp học",
            "老师": "giáo viên",
            "无聊": "buồn, vô vị",
            "医院": "bệnh viện",
        }[word],
        source_page=page,
        extract_by="regex",
        needs_review=needs_review,
        review_reason=None,
    )


def _make_review_queue_book(tmp_path):
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book(
        title="Boya queue",
        file_path=str(tmp_path / "book.pdf"),
        file_hash="review-queue",
        page_count=20,
    )
    db.replace_lessons(
        book_id,
        [
            LessonBoundary(1, "Bài 1", 3, 7, 0.9, "lesson"),
            LessonBoundary(2, "Bài 2", 8, 12, 0.9, "lesson"),
        ],
    )
    lessons = db.get_lessons(book_id)
    db.replace_vocab(
        lessons[0]["id"],
        [
            _review_row(1, "教室", 5, True),
            _review_row(2, "老师", 5, True),
            _review_row(3, "医院", 6, False),
        ],
    )
    db.replace_vocab(
        lessons[1]["id"],
        [_review_row(1, "无聊", 9, True)],
    )
    db.set_import_state(book_id, "review")
    return db, book_id


def _visible_review_words(dialog):
    return [
        dialog.review_table.item(row, 4).text()
        for row in range(dialog.review_table.rowCount())
        if not dialog.review_table.isRowHidden(row)
    ]


def test_review_tabs_render_with_readable_contrast(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.show()
        app.processEvents()

        bar = dialog.tabs.tabBar()
        image = bar.grab().toImage()
        selected = bar.tabRect(0)
        inactive = bar.tabRect(1)

        def count_near(rect, color_name, tolerance=8):
            target = QColor(color_name)
            return sum(
                abs(image.pixelColor(x, y).red() - target.red()) <= tolerance
                and abs(image.pixelColor(x, y).green() - target.green()) <= tolerance
                and abs(image.pixelColor(x, y).blue() - target.blue()) <= tolerance
                for y in range(rect.top(), rect.bottom() + 1)
                for x in range(rect.left(), rect.right() + 1)
            )

        assert count_near(selected, PALETTE["accent"]) > selected.width() * selected.height() // 4
        assert count_near(selected, "white") >= 2
        assert count_near(inactive, PALETTE["card"]) > inactive.width() * inactive.height() // 4
        assert count_near(inactive, PALETTE["ink2"]) >= 2
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_hang_doi_hien_ro_bai_trang_va_khong_tich_san(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))

        assert dialog.tabs.currentIndex() == 0
        assert dialog.review_table.rowCount() == 3
        assert dialog.lbl_review_count.text() == "3 từ cần xác nhận · thuộc 2 bài"
        assert dialog.review_table.item(0, 1).text() == "Bài 1"
        assert dialog.review_table.item(0, 2).text() == "5"
        assert all(
            dialog.review_table.item(row, 0).checkState()
            == Qt.CheckState.Unchecked
            for row in range(dialog.review_table.rowCount())
        )
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_huong_dan_mo_ta_dung_luong_xac_nhan_chon_loc(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        text = dialog.review_note.text()
        assert "tích ô" in text
        assert "Xác nhận các dòng đã chọn" in text
        assert "dòng màu vàng" not in text
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_loc_bai_va_tim_kiem_chi_an_hien_dong(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_filter.setCurrentText("Bài 2")
        assert _visible_review_words(dialog) == ["无聊"]

        dialog.review_filter.setCurrentIndex(0)
        dialog.review_search.setText("jido")
        assert _visible_review_words(dialog) == ["教室"]
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_chon_tat_ca_chi_chon_dong_dang_hien(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_filter.setCurrentText("Bài 2")
        dialog._select_visible_rows()

        assert dialog._selected_review_rows() == [2]
        assert (
            dialog.btn_confirm_selected.text()
            == "Xác nhận các dòng đã chọn (1)"
        )

        dialog._clear_review_selection()
        assert dialog._selected_review_rows() == []
        assert not dialog.btn_confirm_selected.isEnabled()
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_xac_nhan_chon_loc_luu_sua_va_giu_nguyen_dong_khac(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_table.item(0, 4).setText("教室")
        dialog.review_table.item(0, 5).setText("jiàoshì")
        dialog.review_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog._confirm_selected_rows()

        lessons = db.get_lessons(book_id)
        first = db.get_lesson_words(lessons[0]["id"])
        second = db.get_lesson_words(lessons[1]["id"])
        assert first[0]["word"] == "教室"
        assert first[0]["pinyin_src"] == "jiàoshì"
        assert first[0]["needs_review"] == 0
        assert first[1]["needs_review"] == 1
        assert second[0]["needs_review"] == 1
        assert dialog.review_table.rowCount() == 2
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_xac_nhan_cac_dong_thuoc_nhieu_bai(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog.review_table.item(2, 0).setCheckState(Qt.CheckState.Checked)
        dialog._confirm_selected_rows()

        lessons = db.get_lessons(book_id)
        first = db.get_lesson_words(lessons[0]["id"])
        second = db.get_lesson_words(lessons[1]["id"])
        assert [row["needs_review"] for row in first] == [0, 1, 0]
        assert [row["needs_review"] for row in second] == [0]
        assert _visible_review_words(dialog) == ["老师"]
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_xac_nhan_hang_doi_lam_moi_bang_tat_ca_cac_bai(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        assert dialog.table.item(0, 2).text() == "jidoshi"

        dialog.review_table.item(0, 5).setText("jiàoshì")
        dialog.review_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog._confirm_selected_rows()

        assert dialog.table.item(0, 2).text() == "jiàoshì"
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_loi_luu_nhieu_bai_giu_noi_dung_sua_va_lua_chon(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok,
    )

    def fail_atomically(_rows_by_lesson):
        raise RuntimeError("ổ đĩa lỗi")

    monkeypatch.setattr(db, "replace_vocab_many", fail_atomically)
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_table.item(0, 5).setText("pinyin đã sửa")
        dialog.review_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog.review_table.item(2, 0).setCheckState(Qt.CheckState.Checked)

        dialog._confirm_selected_rows()

        assert dialog.review_table.rowCount() == 3
        assert dialog.review_table.item(0, 5).text() == "pinyin đã sửa"
        assert dialog._selected_review_rows() == [0, 2]
        remaining = sum(
            word["needs_review"]
            for lesson in db.get_lessons(book_id)
            for word in db.get_lesson_words(lesson["id"])
        )
        assert remaining == 3
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_preview_hang_doi_dung_ranh_gioi_bai_duoc_chon(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    calls = []
    monkeypatch.setattr(
        screen_books_module,
        "PreviewWorker",
        lambda path, start, end, **kwargs: _FakePreviewWorker(
            calls, path, start, end, **kwargs
        ),
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._show_review_source(2, 4)
        assert calls[0][1:3] == (8, 12)
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_preview_hang_doi_chi_chay_mot_worker_moi_luc(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    calls = []
    workers = []

    def make_worker(path, start, end, **kwargs):
        worker = _FakePreviewWorker(calls, path, start, end, **kwargs)
        workers.append(worker)
        return worker

    monkeypatch.setattr(screen_books_module, "PreviewWorker", make_worker)
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._show_review_source(0, 4)
        dialog._show_review_source(2, 4)

        assert len(calls) == 1

        workers[0].finished.emit()
        app.processEvents()
        assert len(calls) == 2
        assert calls[1][1:3] == (8, 12)
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_tai_lai_hang_doi_vo_hieu_hoa_anh_cu(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        old_worker = object()
        dialog.review_preview_worker = old_worker
        dialog.review_preview.setText("Đang tải ảnh cũ…")

        dialog._reload_review_queue()
        dialog._on_review_preview_failed(old_worker, "lỗi ảnh cũ")

        assert dialog.review_preview_worker is None
        assert dialog.review_preview.text() != "Không mở được ảnh nguồn: lỗi ảnh cũ"
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_chi_hoan_tat_sach_khi_hang_doi_rong(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._finish_reviewed_book()
        assert db.get_book(book_id)["import_state"] == "review"

        for row in range(dialog.review_table.rowCount()):
            dialog.review_table.item(row, 0).setCheckState(
                Qt.CheckState.Checked
            )
        dialog._confirm_selected_rows()
        assert dialog.btn_finish_book.isEnabled()
        dialog._finish_reviewed_book()
        assert db.get_book(book_id)["import_state"] == "ready"
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_source_preview_khong_chan_luong_giao_dien(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    try:
        book_id = db.add_book(
            title="Boya preview",
            file_path=str(tmp_path / "book.pdf"),
            file_hash="preview-async",
            page_count=20,
        )
        db.replace_lessons(
            book_id,
            [LessonBoundary(1, "Bài 1", 3, 8, 0.8, "lesson")],
        )

        def slow_preview(*_args, **_kwargs):
            time.sleep(0.25)
            return b"not-a-png"

        monkeypatch.setattr(
            importer_module, "render_vocab_table_preview", slow_preview
        )
        dialog = DialogReviewBook(db, db.get_book(book_id))

        started = time.perf_counter()
        dialog._show_row_source(0, 0)
        elapsed = time.perf_counter() - started

        assert elapsed < 0.1
        assert "Đang tải" in dialog.preview.text()

        deadline = time.perf_counter() + 2
        while dialog.preview_worker is not None and time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert dialog.preview_worker is None
        dialog.deleteLater()
        app.processEvents()
    finally:
        db.close()


def test_preview_cu_khong_ghi_de_bai_moi(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    try:
        book_id = db.add_book(
            title="Boya stale preview",
            file_path=str(tmp_path / "book.pdf"),
            file_hash="preview-stale",
            page_count=20,
        )
        db.replace_lessons(
            book_id,
            [LessonBoundary(1, "Bài 1", 3, 8, 0.8, "lesson")],
        )
        dialog = DialogReviewBook(db, db.get_book(book_id))
        old_worker = object()
        new_worker = object()
        dialog.preview_worker = new_worker
        dialog.preview.setText("Đang tải ảnh nguồn…")

        dialog._on_preview_failed(old_worker, "lỗi của bài trước")

        assert dialog.preview.text() == "Đang tải ảnh nguồn…"
        dialog.deleteLater()
        app.processEvents()
    finally:
        db.close()


def test_review_dialog_sua_dong_va_xac_nhan_sach(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    try:
        book_id = db.add_book(
            title="Boya test",
            file_path=str(tmp_path / "book.pdf"),
            file_hash="review-dialog",
            page_count=20,
        )
        db.replace_lessons(
            book_id,
            [LessonBoundary(1, "Bài 1", 3, 8, 0.8, "lesson")],
        )
        lesson = db.get_lessons(book_id)[0]
        db.replace_vocab(
            lesson["id"],
            [
                VocabRow(
                    order_no=1,
                    word="扌攵室",
                    pinyin_src="jidoshi",
                    pos="n.",
                    hanviet_src="giáo thất",
                    meaning_src="lớp học",
                    source_page=5,
                    extract_by="regex",
                    needs_review=True,
                    review_reason="từ OCR không có trong từ điển",
                )
            ],
        )
        db.set_import_state(book_id, "review")

        dialog = DialogReviewBook(db, db.get_book(book_id))
        assert dialog.table.rowCount() == 1
        assert dialog.table.item(0, 1).background().color().isValid()

        dialog.table.item(0, 1).setText("教室")
        dialog.table.item(0, 2).setText("jiàoshì")
        dialog._confirm_all()

        saved = db.get_lesson_words(lesson["id"])
        assert saved[0]["word"] == "教室"
        assert saved[0]["pinyin_src"] == "jiàoshì"
        assert saved[0]["needs_review"] == 0
        assert db.get_book(book_id)["import_state"] == "ready"
        dialog.deleteLater()
        app.processEvents()
    finally:
        db.close()


def test_boundary_dialog_luu_truoc_khi_ocr(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    try:
        book_id = db.add_book(
            title="Boya boundaries",
            file_path=str(tmp_path / "book.pdf"),
            file_hash="boundary-dialog",
            page_count=30,
        )
        db.replace_lessons(
            book_id,
            [
                LessonBoundary(1, "Bài 1", 2, 7, 0.82, "lesson"),
                LessonBoundary(2, "Bài 2", 8, 14, 0.76, "lesson"),
            ],
        )
        dialog = DialogReviewBoundaries(db, book_id, 30)
        dialog.table.item(0, 1).setText("Chào hỏi")
        dialog.table.item(0, 3).setText("8")
        dialog.table.item(1, 2).setText("9")
        dialog._confirm()

        saved = db.get_lessons(book_id)
        assert dialog.result() == dialog.DialogCode.Accepted
        assert saved[0]["title"] == "Chào hỏi"
        assert (saved[0]["page_start"], saved[0]["page_end"]) == (2, 7)
        assert (saved[1]["page_start"], saved[1]["page_end"]) == (8, 14)
        assert saved[0]["confidence"] == 0.82
        dialog.deleteLater()
        app.processEvents()
    finally:
        db.close()


def test_boundary_dialog_can_add_sort_and_blocks_missing_lesson(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-crud", 40)
    db.replace_lessons(book_id, [
        LessonBoundary(1, "Một", 0, 9, 0.7, "lesson"),
        LessonBoundary(3, "Ba", 20, 29, 0.7, "lesson"),
    ])
    dialog = DialogReviewBoundaries(db, book_id, 40)
    try:
        assert dialog.btn_confirm.isEnabled() is False

        dialog._add_row()
        row = dialog.table.rowCount() - 1
        for column, text in ((0, "2"), (1, "Hai"), (2, "11"), (3, "20")):
            dialog.table.item(row, column).setText(text)
        dialog._sort_rows()

        assert [int(dialog.table.item(row, 0).text())
                for row in range(dialog.table.rowCount())] == [1, 2, 3]
        assert dialog.btn_confirm.isEnabled() is True
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_boundary_dialog_shows_evidence_source(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-source", 40)
    boundary = LessonBoundary(1, "Một", 5, 39, 0.9, "lesson")
    db.replace_lessons(book_id, [boundary])
    source = BoundaryEvidence("toc", 5, 1, "Một", 0.8, "mục lục")
    result = SplitResult(
        (boundary,), (source,), BoundaryReport(True, (), ()), False
    )
    dialog = DialogReviewBoundaries(db, book_id, 40, result)
    try:
        assert "mục lục" in dialog.table.item(0, 5).text().lower()
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_boundary_dialog_blocks_reversed_page_range(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-range", 40)
    db.replace_lessons(book_id, [
        LessonBoundary(1, "Một", 0, 9, 0.7, "lesson"),
    ])
    dialog = DialogReviewBoundaries(db, book_id, 40)
    try:
        dialog.table.item(0, 2).setText("10")
        dialog.table.item(0, 3).setText("5")

        assert dialog.btn_confirm.isEnabled() is False
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_boundary_dialog_blocks_deleting_every_lesson(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-delete", 40)
    db.replace_lessons(book_id, [
        LessonBoundary(1, "Một", 0, 39, 0.7, "lesson"),
    ])
    dialog = DialogReviewBoundaries(db, book_id, 40)
    try:
        dialog.table.setCurrentCell(0, 0)
        dialog._delete_row()

        assert dialog.table.rowCount() == 0
        assert dialog.btn_confirm.isEnabled() is False
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def _conflicting_boundary_result():
    boundary = LessonBoundary(1, "Một", 5, 39, 0.9, "lesson")
    evidence = (
        BoundaryEvidence("toc", 5, 1, "Một", 0.8, "mục lục"),
        BoundaryEvidence("heading", 8, 1, "Một", 0.8, "trang mở bài"),
    )
    issue = BoundaryIssue(
        "toc_heading_conflict", "error", 1, None, "conflicting evidence"
    )
    return SplitResult(
        (boundary,), evidence, BoundaryReport(False, (issue,), ()), True
    )


def test_boundary_dialog_loads_invalid_result_and_manual_override_confirms(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-manual", 40)
    dialog = DialogReviewBoundaries(db, book_id, 40, _conflicting_boundary_result())
    try:
        assert dialog.table.rowCount() == 1
        assert dialog.btn_confirm.isEnabled() is False

        dialog.table.setCurrentCell(0, 0)
        dialog._use_manual_boundaries()

        assert dialog.table.item(0, 5).text() == "Thủ công"
        assert dialog.btn_confirm.isEnabled() is True
        dialog._confirm()
        assert db.get_lessons(book_id)[0]["page_start"] == 5
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_boundary_dialog_refreshes_evidence_after_edit_duplicate_and_sort(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-alignment", 40)
    first = LessonBoundary(1, "Một", 0, 9, 0.9, "lesson")
    second = LessonBoundary(2, "Hai", 10, 39, 0.9, "lesson")
    result = SplitResult(
        (first, second),
        (
            BoundaryEvidence("toc", 0, 1, "Một", 0.8, "nguồn một"),
            BoundaryEvidence("heading", 10, 2, "Hai", 0.8, "nguồn hai"),
        ),
        BoundaryReport(True, (), ()),
        False,
    )
    dialog = DialogReviewBoundaries(db, book_id, 40, result)
    try:
        dialog.table.item(0, 0).setText("2")
        assert "nguồn hai" in dialog.table.item(0, 5).text()
        assert "nguồn một" not in dialog.table.item(0, 5).text()

        dialog.table.setCurrentCell(0, 0)
        dialog._duplicate_row()
        dialog._sort_rows()

        assert any(
            dialog.table.item(row, 5).text() == "Thủ công"
            for row in range(dialog.table.rowCount())
        )
        assert all(
            "nguồn một" not in dialog.table.item(row, 5).text()
            for row in range(dialog.table.rowCount())
        )
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_boundary_dialog_ignores_missing_source_cell_while_coloring_error(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-partial", 40)
    dialog = DialogReviewBoundaries(db, book_id, 40, _conflicting_boundary_result())
    try:
        assert dialog.table.rowCount() == 1
        dialog.table.takeItem(0, 5)
        dialog._color_issue(1, "toc_heading_conflict")
        dialog._validate_rows()

        assert dialog.btn_confirm.isEnabled() is False
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_manual_override_keeps_other_lessons_evidence_on_same_page(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-shared-page", 40)
    first = LessonBoundary(1, "Một", 5, 5, 0.9, "lesson")
    second = LessonBoundary(2, "Hai", 6, 39, 0.9, "lesson")
    result = SplitResult(
        (first, second),
        (
            BoundaryEvidence("toc", 5, 1, "Một", 0.8, "một mục lục"),
            BoundaryEvidence("heading", 8, 1, "Một", 0.8, "một mở bài"),
            BoundaryEvidence("toc", 5, 2, "Hai", 0.8, "hai mục lục"),
            BoundaryEvidence("heading", 6, 2, "Hai", 0.8, "hai mở bài"),
        ),
        BoundaryReport(False, (), ()),
        True,
    )
    dialog = DialogReviewBoundaries(db, book_id, 40, result)
    try:
        dialog.table.setCurrentCell(0, 0)
        dialog._use_manual_boundaries()

        effective = dialog._effective_evidence(dialog.boundaries())
        assert any(
            item.lesson_no == 2 and item.page_index == 5
            for item in effective
        )
        assert dialog.btn_confirm.isEnabled() is False
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_books_screen_labels_incomplete_and_offers_resume(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    screen = None
    try:
        db.set_import_state(book_id, "incomplete")
        screen = ScreenBooks(db)
        screen.show()
        screen.load_books()

        assert "ch\u01b0a \u0111\u1ee7 d\u1eef li\u1ec7u" in screen.list_books.item(0).text()
        screen._hien_bai_hoc_cua_sach(book_id, "S\u00e1ch ki\u1ec3m th\u1eed")
        app.processEvents()
        assert screen.btn_resume_import.isVisible()
    finally:
        if screen is not None:
            screen.deleteLater()
            app.processEvents()
        db.close()


def test_review_preview_prefers_saved_block_crop(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    dialog = None
    try:
        lesson = db.get_lessons(book_id)[0]
        crop = str(tmp_path / "block-1.png")
        block = db.replace_import_blocks(
            lesson["id"],
            [
                VocabBlock(
                    None,
                    lesson["id"],
                    1,
                    4,
                    (0, 0, 100, 200),
                    crop,
                    3,
                    1,
                    3,
                )
            ],
        )[0]
        first_word = db.get_lesson_words(lesson["id"])[0]
        with db.transaction() as conn:
            conn.execute(
                "UPDATE lesson_word SET source_block_id = ? WHERE id = ?",
                (block["id"], first_word["id"]),
            )

        calls = []

        class CapturePreviewWorker(_FakePreviewWorker):
            def __init__(self, path, start=None, end=None, **kwargs):
                super().__init__([], path, start, end, **kwargs)
                calls.append((path, start, end, kwargs.get("crop_paths", ())))

        monkeypatch.setattr(
            screen_books_module,
            "PreviewWorker",
            CapturePreviewWorker,
        )
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._show_review_source(0, 4)

        assert calls[0][3] == (crop,)
        assert db.get_word_source_crop(first_word["id"]) == crop
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_selected_confirmation_preserves_crops_for_the_whole_lesson(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    lesson_id = db.get_lessons(book_id)[0]["id"]
    dialog = None
    try:
        blocks = db.replace_import_blocks(lesson_id, [
            VocabBlock(None, lesson_id, n, 4, (0, 0, 100, 200),
                       str(tmp_path / f"{n}.png"), 1, n, n)
            for n in (1, 2)
        ])
        words = db.get_lesson_words(lesson_id)
        with db.transaction() as conn:
            for block, word in zip(blocks, words):
                conn.execute("UPDATE lesson_word SET source_block_id=? WHERE id=?",
                             (block["id"], word["id"]))
        dialog = DialogReviewBook(db, db.get_book(book_id))
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
        dialog.review_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog._confirm_selected_rows()
        saved = db.get_lesson_words(lesson_id)
        assert [db.get_word_source_crop(w["id"]) for w in saved] == [
            blocks[0]["crop_path"], blocks[1]["crop_path"], None,
        ]
        assert [w["needs_review"] for w in saved] == [0, 1, 0]
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_manual_block_confirmation_unblocks_book(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    dialog = None
    try:
        book_id = db.add_book(
            "S\u00e1ch th\u1ee7 c\u00f4ng",
            str(tmp_path / "book.pdf"),
            "manual-block",
            10,
        )
        db.replace_lessons(
            book_id,
            [LessonBoundary(1, "M\u1ed9t", 0, 9, 1.0, "lesson")],
        )
        lesson = db.get_lessons(book_id)[0]
        block = db.replace_import_blocks(
            lesson["id"],
            [
                VocabBlock(
                    None,
                    lesson["id"],
                    1,
                    4,
                    (0, 0, 100, 200),
                    "block.png",
                    3,
                    1,
                    3,
                    "incomplete",
                    3,
                )
            ],
        )[0]
        db.replace_vocab_block(
            block["id"],
            [
                VocabRow(
                    order_no=1,
                    word="\u4f60\u597d",
                    pinyin_src="n\u01d0h\u01ceo",
                    pos=None,
                    hanviet_src=None,
                    meaning_src=None,
                    source_page=5,
                    extract_by="manual",
                    needs_review=False,
                    review_reason=None,
                )
            ],
        )
        db.set_import_state(book_id, "incomplete")
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.current_lesson = lesson
        dialog.current_block_id = block["id"]
        dialog._confirm_current_block_manual()

        assert db.get_import_blocks(lesson["id"])[0]["status"] == "manual"
        assert db.get_book(book_id)["import_state"] == "review"
    finally:
        if dialog is not None:
            dialog.deleteLater()
            app.processEvents()
        db.close()


def test_compare_boundary_candidates_persists_selected_pdf_page(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QDialog, QPushButton
    import hanzi_app.ui.dialog_import as boundary_ui

    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "qa.sqlite"))
    bid = db.add_book("Sách", "book.pdf", "compare", 40)
    dialog = DialogReviewBoundaries(db, bid, 40, _conflicting_boundary_result())
    pages = []
    def render(path, page, dpi):
        pages.append(page)
        return b""
    def choose(popup):
        next(btn for btn in popup.findChildren(QPushButton) if btn.text() == "Dùng trang 9").click()
        return popup.result()
    monkeypatch.setattr(boundary_ui, "render_page_preview", render)
    monkeypatch.setattr(QDialog, "exec", choose)
    try:
        dialog.table.setCurrentCell(0, 0)
        assert dialog.btn_compare.isEnabled()
        dialog.btn_compare.click()
        assert pages == [5, 8]
        assert dialog.btn_confirm.isEnabled()
        dialog._confirm()
        assert db.get_lessons(bid)[0]["page_start"] == 8
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_region_draw_coordinates_after_zoom_and_scroll(tmp_path):
    from PySide6.QtCore import QRectF, QPointF
    from PySide6.QtTest import QTest
    from hanzi_app.ui.screen_books import RegionView

    app = QApplication.instance() or QApplication([])
    view = RegionView()
    view.resize(350, 250)
    view.setSceneRect(QRectF(0, 0, 800, 800))
    view.show()
    try:
        for scale in (1, 2):
            view.resetTransform()
            view.scale(scale, scale)
            view.centerOn(385, 420)
            app.processEvents()
            start = view.mapFromScene(QPointF(350, 400))
            end = view.mapFromScene(QPointF(410, 445))
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
            box = view.outline.rect()
            assert tuple(2 * v for v in box.getCoords()) == (700, 800, 820, 890)
    finally:
        view.close()


def test_region_editor_saves_new_box_on_empty_page_and_reopens(tmp_path, monkeypatch):
    import fitz
    from PySide6.QtCore import QRectF
    from hanzi_app.adapter.pdfsource import PdfSource
    from hanzi_app.ui.screen_books import DialogReviewRegion

    app = QApplication.instance() or QApplication([])
    path = tmp_path / "source.pdf"
    with fitz.open() as document:
        for number in range(2):
            page = document.new_page(width=300, height=350)
            page.insert_text((32, 72), f"Source page number {number + 1} with native text")
            page.draw_rect(fitz.Rect(34, 35, 42, 47), fill=(1, 0, 0))
        document.save(path)
    monkeypatch.setattr(PdfSource, "ocr_spans", lambda *args, **kwargs: [])
    db = UserDb(str(tmp_path / "user.sqlite"))
    bid = db.add_book("PDF", str(path), "region-pdf", 2)
    db.replace_lessons(bid, [LessonBoundary(1, None, 0, 1, 1, "lesson")])
    book = db.get_book(bid)
    lesson, = db.get_lessons(bid)
    def wait_until(predicate):
        end = time.monotonic() + 8
        while not predicate() and time.monotonic() < end:
            app.processEvents()
            time.sleep(.005)
        assert predicate()
    def open_editor():
        dialog = DialogReviewRegion(db, book, lesson)
        dialog.show()
        wait_until(lambda: not dialog.loaders)
        assert dialog.view.isEnabled()
        return dialog
    try:
        dialog = open_editor()
        dialog.page.setValue(2)
        dialog.page.setValue(1)
        dialog.page.setValue(2)
        wait_until(lambda: not dialog.loaders)
        rect = QRectF(50, 45, 125, 105)
        dialog.view.set_box(rect)
        dialog.save.click()
        wait_until(lambda: dialog.saver is None)
        assert dialog.committed
        block, = db.get_import_blocks(lesson["id"])
        assert (block["page_index"], block["region_decision"], block["bbox"]) == (1, "accepted", (100, 90, 350, 300))
        with PdfSource(path) as pdf:
            expected = pdf.get_page_crop_image_bytes(1, block["bbox"])
        from pathlib import Path
        assert Path(block["crop_path"]).read_bytes() == expected
        dialog = open_editor()
        assert dialog.page.value() == 2
        assert dialog.view.outline.rect() == rect
        dialog.view.set_box(QRectF(5, 5, 9, 9))
        dialog.cancel.click()
        assert db.get_import_blocks(lesson["id"])[0] == block
        dialog = open_editor()
        dialog.skip.click()
        wait_until(lambda: dialog.saver is None)
        assert db.get_import_blocks(lesson["id"])[0]["region_decision"] == "skipped"
        assert not db.book_import_complete(bid)
    finally:
        db.close()
