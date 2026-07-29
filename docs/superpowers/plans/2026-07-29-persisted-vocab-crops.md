# Persisted Vocab Crops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lưu đúng ảnh bảng từ mới theo từng bài ngay khi trích xuất, tạo bù 30 ảnh Boya hiện tại và cho màn duyệt chỉ đọc PNG đã lưu.

**Architecture:** `PdfSource` tiếp tục tạo bytes ảnh; `VocabExtractor` tạo một ảnh ghép duy nhất và chuyển bytes đó ra ngoài qua callback. `service/importer.py` chịu trách nhiệm ghi/đọc/xóa file PNG và điều phối backfill; `UserDb` chỉ lưu đường dẫn tương đối trong cột migration mới. UI không mở PDF hoặc OCR khi người dùng bấm xem nguồn.

**Tech Stack:** Python 3.12.9, PySide6 6.11.1, PyMuPDF, SQLite, pytest 9.1.1.

## Global Constraints

- Không gọi Gemini trong quá trình tạo bù.
- Không lưu ảnh dưới dạng SQLite BLOB.
- Không sửa các bậc migration đã phát hành; thêm bậc 3.
- `data/` không import Qt và không thao tác filesystem ảnh.
- UI không đọc PDF trực tiếp.
- Không thêm phụ thuộc ngoài thư viện chuẩn, PySide6, PyMuPDF và pytest.
- Ảnh tương lai phải là đúng ảnh ghép dùng làm đầu vào Vision.
- Repository chưa có `.git`; bỏ qua các bước commit cho tới khi người dùng khởi tạo Git.

---

### Task 1: Migration và API đường dẫn preview

**Files:**
- Modify: `hanzi_app/data/migrate.py`
- Modify: `hanzi_app/data/userdb.py`
- Modify: `tests/unit/test_userdb.py`

**Interfaces:**
- Produces: `UserDb.set_lesson_preview_path(lesson_id: int, preview_path: str | None) -> None`
- Produces: `lesson["preview_path"]` từ `UserDb.get_lessons(book_id)`

- [ ] **Step 1: Viết test đỏ cho migration bậc 3**

Thêm test tạo database bậc 2 có một lesson, gọi `upgrade`, rồi xác nhận:

```python
columns = {
    row[1] for row in db._conn.execute("PRAGMA table_info(lesson)")
}
assert "preview_path" in columns
assert db._conn.execute(
    "SELECT version FROM schema_version"
).fetchone()[0] == 3
```

- [ ] **Step 2: Viết test đỏ cho setter**

```python
db.set_lesson_preview_path(lesson_id, "data/book_crops/book-1/lesson-1.png")
lesson = db.get_lessons(book_id)[0]
assert lesson["preview_path"] == "data/book_crops/book-1/lesson-1.png"

db.set_lesson_preview_path(lesson_id, None)
assert db.get_lessons(book_id)[0]["preview_path"] is None
```

- [ ] **Step 3: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_userdb.py -q --basetemp=tmp/pytest-crops-data-red
```

Expected: FAIL vì schema version vẫn là 2, thiếu cột và thiếu phương thức.

- [ ] **Step 4: Cài migration và setter tối thiểu**

Trong `migrate.py`:

```python
SCHEMA_VERSION = 3

_BAC_3 = (
    "ALTER TABLE lesson ADD COLUMN preview_path TEXT",
)

def _len_bac_3(conn: sqlite3.Connection) -> None:
    for cau_lenh in _BAC_3:
        conn.execute(cau_lenh)

_CAC_BAC = {
    1: _len_bac_1,
    2: _len_bac_2,
    3: _len_bac_3,
}
```

Trong `UserDb`:

```python
def set_lesson_preview_path(
    self, lesson_id: int, preview_path: str | None
) -> None:
    with self._conn:
        self._conn.execute(
            "UPDATE lesson SET preview_path = ? WHERE id = ?",
            (preview_path, lesson_id),
        )
```

Đổi câu SELECT trong `get_lessons` thành:

```python
"SELECT id, index_no, title, page_start, page_end, confidence, preview_path "
```

- [ ] **Step 5: Chạy test data**

Run:

```powershell
python -m pytest tests/unit/test_userdb.py -q --basetemp=tmp/pytest-crops-data-green
```

Expected: toàn bộ test xanh.

---

### Task 2: Kho ảnh nguyên tử và đọc/xóa an toàn

**Files:**
- Modify: `hanzi_app/service/importer.py`
- Modify: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces: `save_lesson_preview(crop_root: Path, book_id: int, lesson_id: int, data: bytes) -> str`
- Produces: `load_lesson_preview(project_root: Path, preview_path: str | None) -> bytes`
- Produces: `delete_book_previews(crop_root: Path, book_id: int) -> None`

- [ ] **Step 1: Viết test đỏ cho lưu và đọc**

```python
relative = save_lesson_preview(tmp_path / "data/book_crops", 4, 9, PNG_BYTES)
assert relative == "data/book_crops/book-4/lesson-9.png"
assert load_lesson_preview(tmp_path, relative) == PNG_BYTES
assert not list((tmp_path / "data/book_crops/book-4").glob("*.tmp"))
```

PNG_BYTES phải được tạo từ `fitz` trong test để là PNG hợp lệ, không dùng bytes giả.

- [ ] **Step 2: Viết test đỏ cho đường dẫn mất/hỏng và xóa an toàn**

```python
with pytest.raises(ValueError, match="chưa có"):
    load_lesson_preview(tmp_path, None)
with pytest.raises(ValueError, match="không tồn tại"):
    load_lesson_preview(tmp_path, "data/book_crops/book-4/missing.png")
with pytest.raises(ValueError, match="không hợp lệ"):
    load_lesson_preview(tmp_path, bad_relative_path)

delete_book_previews(crop_root, 4)
assert not (crop_root / "book-4").exists()
assert (crop_root / "book-5").exists()
```

- [ ] **Step 3: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py -q --basetemp=tmp/pytest-crops-store-red
```

Expected: FAIL vì ba hàm chưa tồn tại.

- [ ] **Step 4: Cài kho ảnh tối thiểu**

Quy tắc triển khai:

- `save_lesson_preview` kiểm tra bytes bằng `fitz.Pixmap(data)`.
- Tạo đúng `crop_root/book-<id>`.
- Ghi `lesson-<id>.png.tmp`, sau đó `Path.replace()` sang `.png`.
- Trả đường dẫn POSIX tương đối `data/book_crops/...`.
- `load_lesson_preview` resolve đường dẫn, xác nhận nó nằm dưới `project_root/data/book_crops`, đọc bytes và kiểm tra PNG.
- `delete_book_previews` chỉ resolve `crop_root / f"book-{int(book_id)}"` và xác nhận parent đúng bằng `crop_root.resolve()` trước khi `shutil.rmtree`.

- [ ] **Step 5: Chạy test kho ảnh**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py -q --basetemp=tmp/pytest-crops-store-green
```

Expected: toàn bộ test xanh.

---

### Task 3: Giữ đúng ảnh đã dùng trong luồng OCR/Vision

**Files:**
- Modify: `hanzi_app/service/vocab.py`
- Modify: `hanzi_app/service/importer.py`
- Modify: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Changes: `VocabExtractor.extract_lesson(pdf, lesson, ai_client=None, preview_sink=None) -> list[VocabRow]`
- `preview_sink` nhận đúng một đối số `bytes` và được gọi tối đa một lần cho mỗi bài.
- Consumes: `save_lesson_preview(...)`, `UserDb.set_lesson_preview_path(...)`

- [ ] **Step 1: Viết test đỏ chứng minh bytes preview chính là ảnh gửi Vision**

```python
captured = []
rows = extractor.extract_lesson(
    pdf,
    lesson,
    ai_client=client,
    preview_sink=captured.append,
)
assert captured == [b"combined-lesson"]
client.extract_vocab_from_image.assert_called_once_with(captured[0])
```

- [ ] **Step 2: Viết test đỏ cho importer lưu ảnh trước khi lưu đường dẫn**

Fake `UserDb` ghi lại thứ tự gọi và xác nhận:

```python
assert events == [
    ("write_png", lesson_id),
    ("set_preview_path", lesson_id, expected_relative),
    ("replace_vocab", lesson_id),
]
```

- [ ] **Step 3: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py -q --basetemp=tmp/pytest-crops-flow-red
```

Expected: FAIL vì `extract_lesson` chưa nhận `preview_sink`.

- [ ] **Step 4: Cài callback preview và tái sử dụng ảnh**

Trong `extract_lesson`, tách việc render `located` thành helper cục bộ trả
`(images, combined)`. Khi `combined` hợp lệ:

```python
if preview_sink is not None:
    preview_sink(combined)
```

Chỉ gọi callback một lần. Tất cả nhánh Vision dùng lại `combined`; nhánh local
vẫn tạo `combined` để lưu preview nhưng không gọi AI khi client chưa cấu hình.

Trong `VocabImporterWorker`, callback ghi PNG theo `book_id`, `lesson["id"]`;
sau khi ghi thành công mới gọi `set_lesson_preview_path`, rồi lưu vocab.

Trong `VisionRepairWorker`, thêm `preview_ready = Signal(bytes)` và emit đúng ảnh
đã gửi Vision. Dialog chỉ thay file preview khi người dùng lưu kết quả bài.

- [ ] **Step 5: Chạy test luồng**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py tests/unit/test_review_dialog.py -q --basetemp=tmp/pytest-crops-flow-green
```

Expected: toàn bộ test xanh.

---

### Task 4: UI chỉ đọc PNG đã lưu

**Files:**
- Modify: `hanzi_app/ui/screen_books.py`
- Modify: `tests/unit/test_review_dialog.py`

**Interfaces:**
- Consumes: `load_lesson_preview(project_root: Path, preview_path: str | None) -> bytes`
- Normal click không dùng `PreviewWorker` hoặc `render_vocab_table_preview`.
- Explicit rebuild tiếp tục dùng `PreviewWorker`; kết quả được lưu bằng
  `save_lesson_preview(...)`.

- [ ] **Step 1: Viết test đỏ cho click đọc file, không gọi locator**

Tạo PNG hợp lệ trong `tmp_path/data/book_crops/...`, đặt `preview_path` cho bài,
monkeypatch `render_vocab_table_preview` để raise nếu bị gọi, sau đó:

```python
started = time.perf_counter()
dialog._show_row_source(0, 0)
assert time.perf_counter() - started < 0.1
assert dialog.preview.pixmap() is not None
assert not dialog.preview.pixmap().isNull()
```

- [ ] **Step 2: Viết test đỏ cho ảnh thiếu và hỏng**

```python
dialog._show_row_source(0, 0)
assert "Ảnh nguồn chưa có" in dialog.preview.text()
```

Lặp lại với `preview_path` trỏ tới file không phải PNG và xác nhận thông báo
“Ảnh nguồn không hợp lệ”.

- [ ] **Step 3: Viết test đỏ cho nút tạo lại riêng**

Khi ảnh thiếu, `btn_rebuild_preview` phải hiện. Bấm nút khởi động
`PreviewWorker`; khi worker trả PNG, test xác nhận file được ghi,
`preview_path` được cập nhật và pixmap hiện ra. Không tự khởi động worker chỉ vì
người dùng bấm một dòng.

- [ ] **Step 4: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -q --basetemp=tmp/pytest-crops-ui-red
```

Expected: FAIL vì UI còn chạy worker mở PDF.

- [ ] **Step 5: Cài đường đọc tức thì và rebuild tường minh**

`DialogReviewBook._show_row_source` lấy `current_lesson["preview_path"]`, gọi
`load_lesson_preview`, tạo `QPixmap` và scale `FastTransformation`. Xóa
`PreviewWorker` khỏi đường preview thông thường. Giữ worker và cơ chế chống kết
quả cũ ghi đè chỉ cho nút `Tạo lại ảnh nguồn`. Khi worker trả ảnh, lưu file trước,
cập nhật `preview_path`, rồi hiển thị. Thông báo thiếu/hỏng phải phân biệt rõ,
không fallback OCR ngầm.

- [ ] **Step 6: Chạy test UI**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -q --basetemp=tmp/pytest-crops-ui-green
```

Expected: toàn bộ test xanh.

---

### Task 5: Backfill có resume và không AI

**Files:**
- Modify: `hanzi_app/service/importer.py`
- Modify: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces: `backfill_book_previews(user_db: UserDb, book_id: int, crop_root: Path) -> dict[str, object]`
- Return shape: `{"created": int, "skipped": int, "failed": list[tuple[int, str]]}`

- [ ] **Step 1: Viết test đỏ cho tạo bù và resume**

Fake hai lesson, trong đó lesson đầu đã có PNG hợp lệ. Monkeypatch
`render_vocab_table_preview` cho lesson thứ hai và xác nhận:

```python
result = backfill_book_previews(db, book_id, crop_root)
assert result == {"created": 1, "skipped": 1, "failed": []}
assert render.call_count == 1
assert db.get_lessons(book_id)[1]["preview_path"]
```

- [ ] **Step 2: Viết test đỏ cho lỗi riêng từng bài**

Cho renderer raise ở một lesson và trả PNG ở lesson sau:

```python
assert result["created"] == 1
assert result["failed"] == [(lesson_no, "lý do")]
assert later_lesson["preview_path"] is not None
```

Test không tạo `AiClient` và không truyền API key.

- [ ] **Step 3: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py -q --basetemp=tmp/pytest-crops-backfill-red
```

Expected: FAIL vì hàm backfill chưa tồn tại.

- [ ] **Step 4: Cài backfill**

Hàm lấy `book` và `lessons` từ `user_db`; với mỗi lesson dương:

- Nếu `preview_path` đọc được thành PNG hợp lệ: tăng `skipped`.
- Nếu chưa có: gọi `render_vocab_table_preview` đúng một lần.
- Ghi bằng `save_lesson_preview`, sau đó cập nhật DB.
- Bắt lỗi theo từng lesson, thêm `(index_no, str(error))` và tiếp tục.
- Không khởi tạo `AiClient`.

- [ ] **Step 5: Chạy test backfill**

Run:

```powershell
python -m pytest tests/unit/test_universal_engine.py -q --basetemp=tmp/pytest-crops-backfill-green
```

Expected: toàn bộ test xanh.

---

### Task 6: Xóa ảnh cùng sách

**Files:**
- Modify: `hanzi_app/ui/screen_books.py`
- Modify: `tests/unit/test_review_dialog.py`

**Interfaces:**
- Consumes: `delete_book_previews(crop_root: Path, book_id: int) -> None`

- [ ] **Step 1: Viết test đỏ**

Tạo hai thư mục book crop, gọi luồng xóa sách cho book 1 và xác nhận database
không còn book 1, thư mục book 1 mất, thư mục book 2 còn nguyên.

- [ ] **Step 2: Chạy test và xác nhận đỏ**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -q --basetemp=tmp/pytest-crops-delete-red
```

Expected: FAIL vì UI chưa dọn crop.

- [ ] **Step 3: Cài xóa sau giao dịch**

Trong `_xoa_sach`, gọi `user_db.delete_book(book_id)` trước. Chỉ khi lệnh này
thành công mới gọi `delete_book_previews(project_root / "data/book_crops", book_id)`.
Lỗi dọn ảnh được báo bằng `QMessageBox.warning` nhưng không khôi phục book đã xóa.

- [ ] **Step 4: Chạy test xóa**

Run:

```powershell
python -m pytest tests/unit/test_review_dialog.py -q --basetemp=tmp/pytest-crops-delete-green
```

Expected: toàn bộ test xanh.

---

### Task 7: Tạo bù 30 ảnh Boya và verification

**Files:**
- Modify: `AGENTS.md`
- Create at runtime: `data/book_crops/book-1/lesson-<id>.png` cho 30 lesson
- Modify at runtime: `user.sqlite` qua migration bậc 3 và `preview_path`

**Interfaces:**
- Consumes: `backfill_book_previews(...)`

- [ ] **Step 1: Chạy toàn bộ unit trước khi đổi dữ liệu thật**

```powershell
python -m pytest tests/unit -q --basetemp=tmp/pytest-crops-final-unit
```

Expected: 0 failed.

- [ ] **Step 2: Sao lưu an toàn database trước migration**

Dùng `Copy-Item -LiteralPath user.sqlite -Destination output/user-before-crops.sqlite`
và xác nhận cả hai tệp tồn tại. Không ghi đè bản sao nếu đã tồn tại; thêm timestamp
vào tên tệp trong trường hợp đó.

- [ ] **Step 3: Chạy backfill Boya**

Chạy một đoạn Python gọi `UserDb("user.sqlite")` và
`backfill_book_previews(db, 1, Path("data/book_crops"))`. In JSON kết quả và yêu
cầu `failed == []`, `created + skipped == 30`.

- [ ] **Step 4: Kiểm tra dữ liệu và ảnh**

Đếm:

```python
assert len(lessons) == 30
assert all(lesson["preview_path"] for lesson in lessons)
assert len(list(Path("data/book_crops/book-1").glob("lesson-*.png"))) == 30
for lesson in lessons:
    fitz.Pixmap(load_lesson_preview(project_root, lesson["preview_path"]))
```

- [ ] **Step 5: QA bằng mắt Bài 5, 20 và 29**

Mở đúng ba PNG từ `preview_path`, xác nhận bảng từ mới là nội dung chính và ảnh
giải mã được. Nếu một bài sai crop, dừng và báo đúng bài; không đánh dấu hoàn tất.

- [ ] **Step 6: Chạy golden và toàn bộ unit lần cuối**

```powershell
python -m pytest tests/unit -q --basetemp=tmp/pytest-crops-verify-unit
python -m pytest tests/golden -q --basetemp=tmp/pytest-crops-verify-golden
```

Expected: 0 failed; hai golden Boya xanh.

- [ ] **Step 7: Cập nhật trạng thái**

Thêm phiên mới vào bảng `AGENTS.md` với số test thực tế, kết quả `30/30` ảnh và
QA Bài 5/20/29. Đổi dòng “Phiên tiếp theo phải làm” thành chờ người dùng nghiệm
thu preview đọc từ file.
