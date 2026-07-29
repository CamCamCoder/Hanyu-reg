"""Kiểm thử logic dialog duyệt nhập sách ở chế độ Qt offscreen."""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

import hanzi_app.service.importer as importer_module
import hanzi_app.ui.screen_books as screen_books_module
from hanzi_app.data.models import LessonBoundary, VocabRow
from hanzi_app.data.userdb import UserDb
from hanzi_app.ui.dialog_import import DialogReviewBoundaries
from hanzi_app.ui.screen_books import DialogReviewBook


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
