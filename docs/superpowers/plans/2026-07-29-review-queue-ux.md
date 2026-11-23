# Review Queue UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm hàng đợi tổng hợp giúp người dùng thấy rõ từ cần xác nhận thuộc bài/trang nào, sửa tại chỗ và xác nhận chọn lọc bằng nút lớn.

**Architecture:** Giữ `DialogReviewBook` làm cửa sổ duyệt duy nhất và thêm hai chế độ bằng `QTabWidget`: hàng đợi cần xác nhận là mặc định, màn duyệt từng bài hiện có được giữ nguyên ở tab thứ hai. Hàng đợi chỉ tổng hợp dữ liệu đã có trong `UserDb`; khi xác nhận, nó nhóm các thay đổi theo bài và dùng `replace_vocab_many()` để bảo toàn toàn bộ các dòng không được chọn trong một giao dịch nguyên tử.

**Tech Stack:** Python 3.12, PySide6 6.11.1, SQLite qua `UserDb`, pytest 9.1.1, PyMuPDF qua `PreviewWorker`.

## Global Constraints

- Không thêm migration hoặc cột mới.
- Không gọi thêm AI.
- Không sửa thuật toán OCR, Vision, tách bài hoặc crop ảnh nguồn.
- Không thêm phụ thuộc ngoài thư viện chuẩn, PySide6, PyMuPDF và pytest.
- `data/` không import Qt; `service/` không tự mở SQLite hoặc đọc PDF trực tiếp.
- Viết test đỏ trước mỗi thay đổi mã sản phẩm.
- Không tự động tích hoặc xác nhận bất kỳ dòng nào.
- Kết thúc phiên phải cập nhật `AGENTS.md`.

---

## File Map

- Modify: `hanzi_app/ui/screen_books.py`
  - Dựng tab **Cần xác nhận**.
  - Tổng hợp, lọc, chọn, sửa và xác nhận các dòng thuộc nhiều bài.
  - Điều phối preview theo bài của dòng đang chọn.
  - Giữ tab **Tất cả các bài** và luồng Vision hiện có.
- Modify: `tests/unit/test_review_dialog.py`
  - Kiểm thử hàng đợi, xác nhận chọn lọc, bộ lọc, preview và điều kiện hoàn tất.
- Modify: `hanzi_app/data/userdb.py`
  - Lưu thay thế bảng từ của nhiều bài trong một giao dịch.
- Modify: `tests/unit/test_userdb.py`
  - Kiểm thử rollback toàn bộ nếu một bài trong nhóm lưu lỗi.
- Modify: `AGENTS.md`
  - Ghi phiên B7l hoàn thành và trạng thái test/QA thực tế.

Không tạo module Python mới và không đổi schema SQLite.

---

### Task 1: Dựng hàng đợi tổng hợp và bộ lọc theo bài

**Files:**
- Modify: `tests/unit/test_review_dialog.py`
- Modify: `hanzi_app/ui/screen_books.py:12-247`

**Interfaces:**
- Consumes: `UserDb.get_lessons(book_id) -> list[dict]`,
  `UserDb.get_lesson_words(lesson_id) -> list[dict]`.
- Produces: `DialogReviewBook.review_table: QTableWidget`,
  `DialogReviewBook.review_filter: QComboBox`,
  `DialogReviewBook.review_search: QLineEdit`,
  `DialogReviewBook._reload_review_queue() -> None`,
  `DialogReviewBook._apply_review_filter() -> None`.

- [ ] **Step 1: Viết test đỏ cho dữ liệu tổng hợp và trạng thái mặc định**

Thêm các helper sau vào `tests/unit/test_review_dialog.py`:

```python
def _row(order, word, page, needs_review):
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
            _row(1, "教室", 5, True),
            _row(2, "老师", 5, True),
            _row(3, "医院", 6, False),
        ],
    )
    db.replace_vocab(
        lessons[1]["id"],
        [_row(1, "无聊", 9, True)],
    )
    db.set_import_state(book_id, "review")
    return db, book_id


def _visible_review_words(dialog):
    return [
        dialog.review_table.item(row, 4).text()
        for row in range(dialog.review_table.rowCount())
        if not dialog.review_table.isRowHidden(row)
    ]
```

Sau đó thêm test:

```python
def test_hang_doi_hien_ro_bai_trang_va_khong_tich_san(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
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
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

- [ ] **Step 2: Chạy test và xác nhận nó đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py::test_hang_doi_hien_ro_bai_trang_va_khong_tich_san -v --basetemp=tmp/pytest-review-queue-1
```

Expected: FAIL vì `DialogReviewBook` chưa có `tabs` và `review_table`.

- [ ] **Step 3: Dựng tab và hàng đợi tối thiểu**

Thêm import `QComboBox`, `QTabWidget`. Trong `DialogReviewBook.__init__`, tạo:

```python
self.tabs = QTabWidget()
self.review_tab = QWidget()
self.all_lessons_tab = QWidget()
self.tabs.addTab(self.review_tab, "Cần xác nhận")
self.tabs.addTab(self.all_lessons_tab, "Tất cả các bài")
```

Chuyển layout hiện tại vào `all_lessons_tab`. Trong tab đầu, tạo thanh tóm tắt,
lọc, tìm kiếm, bảng chín cột, vùng preview và thanh hành động. Mỗi bản ghi hàng
đợi giữ metadata bằng `Qt.ItemDataRole.UserRole`:

```python
{
    "lesson_id": lesson["id"],
    "lesson_index": lesson["index_no"],
    "page_start": lesson["page_start"],
    "page_end": lesson["page_end"],
    "word_id": word["id"],
}
```

`_reload_review_queue()` chỉ lấy `needs_review == 1`, sắp theo `index_no`,
`order_no`, `id`, rồi gọi `_apply_review_filter()`. Cột ô chọn dùng
`Qt.CheckState.Unchecked`.

- [ ] **Step 4: Viết và chạy test đỏ cho lọc**

```python
def test_loc_bai_va_tim_kiem_chi_an_hien_dong(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_filter.setCurrentText("Bài 2")
        assert _visible_review_words(dialog) == ["无聊"]

        dialog.review_filter.setCurrentIndex(0)
        dialog.review_search.setText("jiao")
        assert _visible_review_words(dialog) == ["教室"]
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py::test_loc_bai_va_tim_kiem_chi_an_hien_dong -v --basetemp=tmp/pytest-review-queue-2
```

Expected: FAIL trước khi kết nối signal và cài `_apply_review_filter()`.

- [ ] **Step 5: Cài lọc tối thiểu và chạy hai test**

Kết nối `currentIndexChanged` và `textChanged` tới `_apply_review_filter()`.
So khớp tìm kiếm không phân biệt hoa/thường trên chữ Hán, pinyin, Hán–Việt và
nghĩa; lọc bài dựa trên `lesson_id`. Dùng `setRowHidden()` thay vì dựng lại bảng
để không làm mất nội dung đang sửa hoặc trạng thái tích.

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -v --basetemp=tmp/pytest-review-queue-task1
```

Expected: toàn bộ test trong tệp PASS.

- [ ] **Step 6: Commit**

```powershell
git add hanzi_app/ui/screen_books.py tests/unit/test_review_dialog.py
git commit -m "feat: add review queue overview"
```

---

### Task 2: Chọn, sửa và xác nhận chọn lọc qua nhiều bài

**Files:**
- Modify: `tests/unit/test_review_dialog.py`
- Modify: `hanzi_app/ui/screen_books.py`

**Interfaces:**
- Consumes: metadata hàng đợi của Task 1,
  `UserDb.replace_vocab_many(rows_by_lesson) -> None`.
- Produces: `DialogReviewBook._select_visible_rows() -> None`,
  `DialogReviewBook._clear_review_selection() -> None`,
  `DialogReviewBook._confirm_selected_rows() -> None`,
  `DialogReviewBook._selected_review_rows() -> list[int]`.

- [ ] **Step 1: Viết test đỏ cho phạm vi chọn**

```python
def test_chon_tat_ca_chi_chon_dong_dang_hien(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog.review_filter.setCurrentText("Bài 2")
        dialog._select_visible_rows()

        assert dialog._selected_review_rows() == [2]
        assert dialog.btn_confirm_selected.text() == "Xác nhận các dòng đã chọn (1)"

        dialog._clear_review_selection()
        assert dialog._selected_review_rows() == []
        assert not dialog.btn_confirm_selected.isEnabled()
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

- [ ] **Step 2: Chạy test và xác nhận nó đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py::test_chon_tat_ca_chi_chon_dong_dang_hien -v --basetemp=tmp/pytest-review-select
```

Expected: FAIL vì chưa có các phương thức chọn và nút xác nhận.

- [ ] **Step 3: Cài chọn dòng và cập nhật nút**

`_select_visible_rows()` chỉ tích dòng có `not isRowHidden(row)`.
`_clear_review_selection()` bỏ tích mọi dòng. Kết nối `itemChanged` để cập nhật
nhãn `Xác nhận các dòng đã chọn (N)` và vô hiệu hóa nút khi `N == 0`.

- [ ] **Step 4: Viết test đỏ cho sửa và xác nhận một phần**

Monkeypatch `QMessageBox.question` trả `QMessageBox.StandardButton.Yes`:

```python
def test_xac_nhan_chon_loc_luu_sua_va_giu_nguyen_dong_khac(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    monkeypatch.setattr(
        QMessageBox, "question",
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
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

- [ ] **Step 5: Chạy test và xác nhận nó đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py::test_xac_nhan_chon_loc_luu_sua_va_giu_nguyen_dong_khac -v --basetemp=tmp/pytest-review-confirm
```

Expected: FAIL vì chưa có `_confirm_selected_rows()`.

- [ ] **Step 6: Cài xác nhận chọn lọc tối thiểu**

Với mỗi bài có dòng được chọn:

1. Đọc lại toàn bộ từ của bài.
2. Ánh xạ `word_id` tới dòng đang hiển thị.
3. Dựng `VocabRow` cho mọi từ.
4. Chỉ dòng được chọn lấy giá trị đã sửa và `needs_review=False`.
5. Dòng còn lại giữ nguyên mọi trường và cờ.
6. Gom các bài và gọi `replace_vocab_many()` một lần cho toàn bộ nhóm.

Chặn xác nhận nếu chữ Hán của dòng được chọn rỗng. Trước khi lưu, hỏi
`Xác nhận N từ thuộc M bài?`. Chỉ sau khi tất cả lần lưu thành công mới gọi
`_reload_review_queue()`. Nếu có exception, báo lỗi và nạp lại hàng đợi từ DB để
màn hình phản ánh đúng trạng thái đã lưu thay vì báo thành công giả.

- [ ] **Step 7: Viết test nhiều bài và chạy toàn bộ test dialog**

Thêm test tích một dòng ở mỗi bài, xác nhận, rồi kiểm tra các dòng không tích của
cả hai bài vẫn còn nguyên. Sau đó chạy:

```powershell
python -m pytest tests/unit/test_review_dialog.py -v --basetemp=tmp/pytest-review-queue-task2
```

Expected: toàn bộ test trong tệp PASS.

- [ ] **Step 8: Commit**

```powershell
git add hanzi_app/ui/screen_books.py tests/unit/test_review_dialog.py
git commit -m "feat: confirm selected review rows"
```

---

### Task 3: Preview đúng bài và hoàn tất sách từ hàng đợi

**Files:**
- Modify: `tests/unit/test_review_dialog.py`
- Modify: `hanzi_app/ui/screen_books.py`

**Interfaces:**
- Consumes: metadata dòng của Task 1, `PreviewWorker`, hàng đợi sau Task 2.
- Produces: `DialogReviewBook._show_review_source(row, column) -> None`,
  `DialogReviewBook._finish_reviewed_book() -> None`.

- [ ] **Step 1: Viết test đỏ cho preview dùng đúng ranh giới bài**

Thêm import `QObject`, `Signal` và worker giả:

```python
from PySide6.QtCore import QObject, Signal
import hanzi_app.ui.screen_books as screen_books_module


class _FakePreviewWorker(QObject):
    loaded = Signal(bytes)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, calls, path, start, end, **kwargs):
        super().__init__(kwargs.get("parent"))
        calls.append((path, start, end))

    def start(self):
        return None
```

Monkeypatch `screen_books.PreviewWorker` bằng worker giả ghi lại tham số:

```python
def test_preview_hang_doi_dung_ranh_gioi_bai_duoc_chon(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    calls = []
    monkeypatch.setattr(
        screen_books_module,
        "PreviewWorker",
        lambda path, start, end, **kwargs:
            _FakePreviewWorker(calls, path, start, end, **kwargs),
    )
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._show_review_source(2, 4)
        assert calls[0][1:3] == (8, 12)
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

- [ ] **Step 2: Chạy test và xác nhận nó đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py::test_preview_hang_doi_dung_ranh_gioi_bai_duoc_chon -v --basetemp=tmp/pytest-review-preview
```

Expected: FAIL vì chưa có `_show_review_source()`.

- [ ] **Step 3: Cài preview và chống kết quả cũ**

Khi chọn dòng, vô hiệu hóa `self.review_preview_worker` cũ, xóa pixmap và hiện
`Đang tải ảnh nguồn…`. Tạo `PreviewWorker` bằng `page_start/page_end` trong
metadata dòng. Các callback phải nhận worker qua lambda và bỏ qua kết quả nếu
worker không còn là `self.review_preview_worker`, giống cơ chế B7k đang dùng cho
tab từng bài.

- [ ] **Step 4: Viết test đỏ cho điều kiện hoàn tất**

```python
def test_chi_hoan_tat_sach_khi_hang_doi_rong(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    try:
        dialog = DialogReviewBook(db, db.get_book(book_id))
        dialog._finish_reviewed_book()
        assert db.get_book(book_id)["import_state"] == "review"

        for row in range(dialog.review_table.rowCount()):
            dialog.review_table.item(row, 0).setCheckState(Qt.CheckState.Checked)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
        )
        dialog._confirm_selected_rows()
        assert dialog.btn_finish_book.isEnabled()
        dialog._finish_reviewed_book()
        assert db.get_book(book_id)["import_state"] == "ready"
    finally:
        dialog.deleteLater()
        app.processEvents()
        db.close()
```

- [ ] **Step 5: Cài trạng thái rỗng và hoàn tất**

Khi tổng hàng đợi còn dòng, `btn_finish_book` bị vô hiệu hóa và nút xác nhận hiển
thị số dòng đã chọn. Khi hàng đợi rỗng, hiện thông báo `Đã xác nhận toàn bộ từ`,
ẩn/vô hiệu hóa hành động chọn và bật nút `Hoàn tất nhập sách`.
`_finish_reviewed_book()` kiểm tra lại DB trước khi gọi
`set_import_state(book_id, "ready")`.

- [ ] **Step 6: Chạy test hồi quy preview và toàn bộ dialog**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -v --basetemp=tmp/pytest-review-queue-task3
```

Expected: toàn bộ test trong tệp PASS, gồm cả test preview bất đồng bộ B7i/B7k.

- [ ] **Step 7: Commit**

```powershell
git add hanzi_app/ui/screen_books.py tests/unit/test_review_dialog.py
git commit -m "feat: complete review queue workflow"
```

---

### Task 4: QA Boya thật, hồi quy toàn dự án và cập nhật bộ nhớ phiên

**Files:**
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: toàn bộ chức năng từ Tasks 1–3.
- Produces: bằng chứng QA và trạng thái phiên B7l trong `AGENTS.md`.

- [ ] **Step 1: Chạy test riêng của màn duyệt**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -v --basetemp=tmp/pytest-review-final
```

Expected: PASS toàn bộ test.

- [ ] **Step 2: Chạy toàn bộ test**

Run:

```powershell
python -m pytest tests -q --basetemp=tmp/pytest-all-review-queue
```

Expected: không có test đỏ; một test có thể skip theo trạng thái nền tảng hiện có.

- [ ] **Step 3: QA Qt offscreen với dữ liệu Boya thật**

Mở `user.sqlite` hiện tại bằng `UserDb`, tạo `DialogReviewBook` cho Boya và kiểm
tra tự động:

- Tab mặc định là **Cần xác nhận**.
- Số dòng bằng đúng số `needs_review = 1` trong DB.
- Mỗi dòng có Bài và Trang không rỗng.
- Không ô nào được tích sẵn.
- Nút xác nhận đủ cao ít nhất 38 px và bị vô hiệu hóa khi chưa chọn.
- Chọn một dòng rồi trả vòng lặp sự kiện; giao diện không bị khóa trong lúc ảnh
  nguồn tải.

Không xác nhận hoặc sửa dữ liệu thật trong bước QA tự động này.

- [ ] **Step 4: QA bằng mắt**

Chạy ứng dụng, mở Boya → **Duyệt kết quả** và xác nhận:

- 17 dòng thật xuất hiện trong một bảng.
- Bộ lọc bài và tìm kiếm dễ dùng.
- Chọn Bài 20 và Bài 23 hiển thị đúng bài/trang.
- Ảnh nguồn không làm treo cửa sổ.
- Thanh hành động luôn nhìn thấy ở kích thước 1180×760.

- [ ] **Step 5: Cập nhật `AGENTS.md`**

Thêm dòng B7l mô tả bảng tổng hợp theo bài/trang, lọc, sửa, xác nhận chọn lọc và
preview nền. Ghi chính xác số test pass/skip vừa đọc ở Step 2 và kết quả QA Boya
ở Steps 3–4. Đổi dòng **Phiên tiếp theo phải làm** thành trạng thái thực tế sau
QA; không ghi số test dự đoán.

- [ ] **Step 6: Chạy kiểm tra sạch lần cuối**

Run:

```powershell
git diff --check
git status --short
```

Expected: không có lỗi whitespace; chỉ các tệp đúng phạm vi phiên đang chờ commit.

- [ ] **Step 7: Commit**

```powershell
git add AGENTS.md
git commit -m "docs: record review queue completion"
```

- [ ] **Step 8: Dùng verification-before-completion**

Chạy lại các lệnh kiểm thử cuối ngay trước khi báo hoàn thành, đọc trực tiếp số
test pass/skip và không dùng kết quả cũ.
