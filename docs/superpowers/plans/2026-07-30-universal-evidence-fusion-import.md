# Universal Evidence-Fusion Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay luồng nhập PDF đang tin một kết quả AI bằng engine Evidence Fusion có kiểm tra đủ bài, tìm nhiều block từ mới, checkpoint theo block và dừng an toàn khi dữ liệu chưa đủ.

**Architecture:** `PdfSource` khảo sát trang và tạo ảnh bằng chứng; `Splitter` hợp nhất mục lục, tiêu đề, số trang và AI rồi trả báo cáo validator; `VocabExtractor` tạo manifest block và coverage report. `VocabImporterWorker` là nơi duy nhất điều phối checkpoint vào `UserDb`; UI chỉ hiển thị/sửa kết quả service trả về.

**Tech Stack:** Python 3.12.9, PySide6 6.11.1, PyMuPDF, SQLite, Windows OCR, pytest 9.1.1.

## Global Constraints

- Không thêm thư viện ngoài thư viện chuẩn, PySide6, PyMuPDF và pytest.
- `data/` không import Qt; `service/` không tự mở SQLite và không đọc PDF trực tiếp; `adapter/` là nơi duy nhất biết PyMuPDF, OCR và HTTP.
- Không hardcode tên sách, số trang, ranh giới Boya hoặc HSK trong nhánh quyết định mặc định.
- AI split tối đa hai request cho một quyển; AI từ vựng tối đa ba request cho một bài.
- HTTP 429 phải dừng và giữ checkpoint, không retry mù trong cùng một lần chạy.
- Không sửa, xóa, nhập lại hoặc ghi đè quyển HSK hiện có trong `user.sqlite`; QA thật chỉ đọc PDF và dùng DB tạm.
- Mỗi task đi theo RED → GREEN → REFACTOR, chạy test đích trước khi chạy regression liên quan.
- Không sửa/nới test cũ để làm mã xanh; cuối phiên cập nhật `AGENTS.md`.

---

## File Map

- `hanzi_app/data/models.py`: hợp đồng dữ liệu Evidence Fusion và liên kết từ với block.
- `hanzi_app/adapter/pdfsource.py`: page census, OCR theo dải và contact sheet.
- `hanzi_app/adapter/aiclient.py`: hai prompt ảnh có ngữ cảnh lỗi; không chứa validator.
- `hanzi_app/service/splitter.py`: tạo bằng chứng, hợp nhất ứng viên và kiểm tra ranh giới.
- `hanzi_app/service/vocab.py`: locator đa block, extraction và coverage.
- `hanzi_app/data/migrate.py`: migration bậc 3.
- `hanzi_app/data/userdb.py`: CRUD manifest/checkpoint và từ theo block.
- `hanzi_app/service/importer.py`: điều phối hai pha, giới hạn AI, resume và preview crop.
- `hanzi_app/ui/dialog_import.py`: CRUD ranh giới và hiển thị lỗi/bằng chứng.
- `hanzi_app/ui/screen_books.py`: trạng thái `incomplete`, resume và preview crop đã lưu.
- `tests/unit/test_pdfsource.py`, `test_splitter.py`, `test_aiclient.py`, `test_userdb.py`, `test_vocab.py`, `test_universal_engine.py`, `test_review_dialog.py`: TDD và regression.
- `tests/golden/test_boya_vocab_golden.py`: bảo toàn golden Boya.
- `AGENTS.md`: trạng thái B7m và bằng chứng nghiệm thu.

### Task 1: Hợp đồng dữ liệu và Page Census

**Files:**
- Modify: `hanzi_app/data/models.py`
- Modify: `hanzi_app/adapter/pdfsource.py`
- Test: `tests/unit/test_pdfsource.py`

**Interfaces:**
- Produces: `PageEvidence`, `BoundaryEvidence`, `BoundaryIssue`, `BoundaryReport`, `SplitResult`, `VocabBlock`, `BlockCoverage`, `ExtractionResult`.
- Produces: `PdfSource.page_census() -> list[PageEvidence]`.
- Produces: `PdfSource.boundary_contact_sheet(evidence: list[PageEvidence]) -> bytes`.

- [ ] **Step 1: Write failing census and contact-sheet tests**

```python
def test_page_census_classifies_pages_and_reads_toc(monkeypatch, temp_pdf_path):
    with PdfSource(temp_pdf_path) as pdf:
        monkeypatch.setattr(
            pdf,
            "_band_text",
            lambda page, band: {
                (0, "top"): "Contents",
                (0, "bottom"): "1",
                (1, "top"): "Lesson 1 Hello",
                (1, "bottom"): "5",
            }[(page, band)],
        )
        monkeypatch.setattr(pdf, "_full_ocr_text", lambda page: "Lesson 1 005")
        evidence = pdf.page_census()

    assert evidence[0].is_toc_candidate is True
    assert evidence[0].toc_text == "Lesson 1 005"
    assert evidence[1].heading_lesson_no == 1
    assert evidence[1].printed_page == 5
    assert evidence[0].page_kind in {"native", "scan", "mixed"}


def test_boundary_contact_sheet_is_bounded(temp_pdf_path):
    with PdfSource(temp_pdf_path) as pdf:
        evidence = [
            PageEvidence(0, "native", "Contents", "1", "Lesson 1 005",
                         1, None, None, True),
            PageEvidence(1, "native", "Lesson 1", "5", None,
                         5, 1, "Lesson 1", False),
        ]
        image = pdf.boundary_contact_sheet(evidence)
    pix = fitz.Pixmap(image)
    assert pix.width <= 1200
    assert pix.height > 0
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `pytest tests/unit/test_pdfsource.py -k "page_census or boundary_contact" -v`

Expected: collection fails because `PageEvidence` and the two `PdfSource` methods do not exist.

- [ ] **Step 3: Add frozen dataclasses and minimal census**

Add exact frozen dataclasses to `data/models.py`:

```python
@dataclass(frozen=True)
class PageEvidence:
    pdf_page: int
    page_kind: str
    top_text: str
    bottom_text: str
    toc_text: str | None
    printed_page: int | None
    heading_lesson_no: int | None
    heading_title: str | None
    is_toc_candidate: bool
    layout_fingerprint: str | None = None


@dataclass(frozen=True)
class BoundaryEvidence:
    source: str
    page_index: int
    lesson_no: int | None
    title: str | None
    confidence: float
    detail: str


@dataclass(frozen=True)
class BoundaryIssue:
    code: str
    severity: str
    lesson_no: int | None
    page_index: int | None
    message: str


@dataclass(frozen=True)
class BoundaryReport:
    valid: bool
    issues: tuple[BoundaryIssue, ...]
    missing_lesson_nos: tuple[int, ...]


@dataclass(frozen=True)
class SplitResult:
    boundaries: tuple[LessonBoundary, ...]
    evidence: tuple[BoundaryEvidence, ...]
    report: BoundaryReport
    needs_review: bool


@dataclass(frozen=True)
class VocabBlock:
    id: int | None
    lesson_id: int | None
    block_no: int
    page_index: int
    bbox: tuple[float, float, float, float]
    crop_path: str | None
    expected_rows: int | None
    first_order: int | None
    last_order: int | None
    status: str = "pending"
    ai_attempts: int = 0


@dataclass(frozen=True)
class BlockCoverage:
    block_id: int | None
    expected_rows: int | None
    local_rows: int
    ai_rows: int
    final_rows: int
    missing_orders: tuple[int, ...]
    issues: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class ExtractionResult:
    rows: tuple[VocabRow, ...]
    coverage: tuple[BlockCoverage, ...]
    blocks: tuple[VocabBlock, ...]
    ai_attempts: int
    complete: bool
```

Append `source_block_id: int | None = None` to `VocabRow`. In `PdfSource`, implement `_band_text()` by rendering top/bottom 22% at 110 DPI and passing bytes to `OcrAdapter.ocr_png_bytes`; implement `_full_ocr_text()` at 140 DPI only for explicit TOC pages and up to three adjacent continuation pages. Classify each page from useful native text and `page.get_images(full=True)`, parse folio with `r"\b(\d{1,4})\b"`, and parse lesson headings with the existing Chinese/English/Vietnamese forms. Build `layout_fingerprint` by quantizing top-band OCR boxes into a 12×4 occupancy grid and hashing that grid, so text changes do not change the layout signature. Build the contact sheet with PyMuPDF in a four-column grid and cap output width at 1200 px.

Extend the first test with a counter around `_full_ocr_text()` and assert it is
called only for the TOC page/adjacent continuation pages, never for every page.

- [ ] **Step 4: Run target and existing PDF tests**

Run: `pytest tests/unit/test_pdfsource.py -v`

Expected: all tests in `test_pdfsource.py` pass.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/data/models.py hanzi_app/adapter/pdfsource.py tests/unit/test_pdfsource.py
git commit -m "feat: add lightweight PDF page census"
```

### Task 2: Local Boundary Evidence and Structural Validator

**Files:**
- Modify: `hanzi_app/service/splitter.py`
- Test: `tests/unit/test_splitter.py`
- Test: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Consumes: `PageEvidence`, `BoundaryEvidence`.
- Produces: `Splitter.validate(boundaries, evidence, total_pages) -> BoundaryReport`.
- Produces: `Splitter.propose(summaries, evidence, ai_client=None, evidence_image=None) -> SplitResult`.
- Preserves: `Splitter.split(summaries, ai_client=None) -> list[LessonBoundary]` compatibility wrapper.

- [ ] **Step 1: Write failing validator and fusion tests**

```python
def test_boundary_validator_rejects_missing_lessons_and_overlap():
    boundaries = [
        LessonBoundary(1, "Bài 1", 15, 25, 0.7, "lesson"),
        LessonBoundary(3, "Bài 3", 24, 35, 0.7, "lesson"),
    ]
    report = Splitter().validate(boundaries, (), total_pages=144)
    assert report.valid is False
    assert report.missing_lesson_nos == (2,)
    assert {issue.code for issue in report.issues} >= {
        "missing_lesson", "overlap"
    }


def test_local_toc_and_heading_fuse_into_complete_boundaries():
    evidence = [
        PageEvidence(0, "scan", "Contents", "i",
                     "1 One 001\n2 Two 005\n3 Three 010",
                     None, None, None, True),
        PageEvidence(15, "scan", "Lesson 1 One", "1", None,
                     1, 1, "Lesson 1 One", False),
        PageEvidence(19, "scan", "Lesson 2 Two", "5", None,
                     5, 2, "Lesson 2 Two", False),
        PageEvidence(24, "scan", "Lesson 3 Three", "10", None,
                     10, 3, "Lesson 3 Three", False),
    ]
    result = Splitter().propose([], evidence)
    assert [b.index_no for b in result.boundaries] == [1, 2, 3]
    assert [b.page_start for b in result.boundaries] == [15, 19, 24]
    assert result.report.valid is True
    assert all(b.confidence < 1.0 for b in result.boundaries)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/unit/test_splitter.py tests/unit/test_universal_engine.py -k "boundary_validator or local_toc" -v`

Expected: FAIL because `validate()` and `propose()` are absent.

- [ ] **Step 3: Implement local evidence, merge and validation**

Use these issue codes exactly:

```python
ERROR_CODES = {
    "duplicate_lesson",
    "missing_lesson",
    "start_not_increasing",
    "overlap",
    "page_out_of_range",
    "toc_heading_conflict",
}
```

Parse TOC rows from `PageEvidence.toc_text`, infer a page offset only when at least two `(printed_page, pdf_page)` pairs agree, and create heading evidence from `heading_lesson_no`. Merge candidates by lesson number; prefer a page supported by two sources, otherwise retain the single-source page with confidence at most `0.65`. Set page ends from the next accepted start. `validate()` must reject duplicates, positive-number gaps, non-increasing starts, overlaps and pages outside `[0, total_pages - 1]`.

Pages with the same non-null `layout_fingerprint` as at least two confirmed
lesson-open pages contribute `source="layout"` evidence, but never invent a
lesson number by themselves; they only strengthen an existing numbered
candidate on that page.

Remove the Boya preset branch from `split()`; keep `split_by_boya1_preset()` only as a non-default compatibility helper until the old preset test is replaced by the new fusion test. Make `split()` call `propose()` and return `[]` when `report.valid` is false.

- [ ] **Step 4: Run splitter regression**

Run: `pytest tests/unit/test_splitter.py tests/unit/test_universal_engine.py -v`

Expected: all tests pass; no test asserts that the default `split()` chooses a Boya preset.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/service/splitter.py tests/unit/test_splitter.py tests/unit/test_universal_engine.py
git commit -m "feat: validate fused lesson boundaries"
```

### Task 3: Targeted AI Split and Phase-One Worker

**Files:**
- Modify: `hanzi_app/adapter/aiclient.py`
- Modify: `hanzi_app/service/splitter.py`
- Modify: `hanzi_app/service/importer.py`
- Test: `tests/unit/test_aiclient.py`
- Test: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces: `AiClient.split_lessons_from_image(image_bytes, evidence_text, issue_context=None) -> list[dict]`.
- Changes: `BookImporterWorker.boundaries_ready = Signal(int, str, object)` where object is `SplitResult`.
- Produces: `BookImporterWorker._store_boundaries_or_raise(db, book_id, result) -> None`.
- Enforces: zero AI calls when local evidence is valid; at most two when invalid/conflicting.

- [ ] **Step 1: Write failing request-budget and worker tests**

```python
def test_splitter_calls_ai_only_for_invalid_local_result():
    client = MagicMock()
    client.is_configured.return_value = True
    client.split_lessons_from_image.return_value = [
        {"index_no": 1, "title": "一", "page_start": 10},
        {"index_no": 2, "title": "二", "page_start": 20},
    ]
    evidence = [
        PageEvidence(10, "scan", "Lesson 1", "1", None,
                     1, 1, "Lesson 1", False)
    ]
    result = Splitter().propose(
        [], evidence, ai_client=client, evidence_image=b"sheet"
    )
    assert result.report.valid is True
    assert client.split_lessons_from_image.call_count <= 2


def test_book_worker_does_not_persist_invalid_boundaries(tmp_path):
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "split-invalid", 40)
    issue = BoundaryIssue(
        "missing_lesson", "error", 2, None, "Thiếu bài 2"
    )
    fake_result = SplitResult(
        (), (), BoundaryReport(False, (issue,), (2,)), True
    )
    worker = BookImporterWorker("book.pdf", db.path)

    with pytest.raises(RuntimeError, match="Thiếu bài 2"):
        worker._store_boundaries_or_raise(db, book_id, fake_result)
    assert db.get_lessons(book_id) == []
    db.close()
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_aiclient.py tests/unit/test_universal_engine.py -k "splitter_calls_ai or does_not_persist_invalid" -v`

Expected: FAIL because the image split method and result-bearing signal do not exist.

- [ ] **Step 3: Implement targeted image split**

Add an image prompt that includes local candidates and validator issues. `_call_llm_vision()` remains the only HTTP path. In `Splitter.propose()`:

```python
if local.report.valid and _has_two_source_support(local):
    return local
if not ai_client or not ai_client.is_configured() or not evidence_image:
    return local

raw = ai_client.split_lessons_from_image(
    evidence_image, _format_evidence(evidence)
)
merged = _merge_ai_candidates(local, raw, total_pages)
if merged.report.valid:
    return merged

raw_retry = ai_client.split_lessons_from_image(
    evidence_image,
    _format_evidence(evidence),
    issue_context=_format_issues(merged.report),
)
return _merge_ai_candidates(merged, raw_retry, total_pages)
```

Update `BookImporterWorker.run()` to call `page_census()`, build the contact sheet, call `propose()`, and only call `replace_lessons()` for a nonempty structurally valid result. Emit the `SplitResult` so the dialog can display evidence.
`_store_boundaries_or_raise()` joins all error messages with `"; "`, raises
`RuntimeError` before any DB write when invalid, and otherwise calls
`replace_lessons(book_id, list(result.boundaries))`.

- [ ] **Step 4: Run adapter, splitter and worker tests**

Run: `pytest tests/unit/test_aiclient.py tests/unit/test_splitter.py tests/unit/test_universal_engine.py -v`

Expected: all pass; tests assert `call_count <= 2`.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/adapter/aiclient.py hanzi_app/service/splitter.py hanzi_app/service/importer.py tests/unit/test_aiclient.py tests/unit/test_universal_engine.py
git commit -m "feat: target AI at unresolved lesson boundaries"
```

### Task 4: Boundary Dialog CRUD and Validation UX

**Files:**
- Modify: `hanzi_app/ui/dialog_import.py`
- Test: `tests/unit/test_review_dialog.py`

**Interfaces:**
- Changes: `DialogReviewBoundaries(user_db, book_id, page_count, split_result=None, parent=None)`.
- Consumes: `Splitter.validate()` and `SplitResult.evidence`.
- Produces: add, duplicate, delete and sort actions; confirmation disabled while errors remain.

- [ ] **Step 1: Write failing offscreen UI tests**

```python
def test_boundary_dialog_can_add_sort_and_blocks_missing_lesson(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "bounds-crud", 40)
    db.replace_lessons(book_id, [
        LessonBoundary(1, "Một", 0, 9, 0.7, "lesson"),
        LessonBoundary(3, "Ba", 20, 29, 0.7, "lesson"),
    ])
    dialog = DialogReviewBoundaries(db, book_id, 40)
    assert dialog.btn_confirm.isEnabled() is False

    dialog._add_row()
    row = dialog.table.rowCount() - 1
    for column, text in ((0, "2"), (1, "Hai"), (2, "11"), (3, "20")):
        dialog.table.item(row, column).setText(text)
    dialog._sort_rows()

    assert [int(dialog.table.item(r, 0).text())
            for r in range(dialog.table.rowCount())] == [1, 2, 3]
    assert dialog.btn_confirm.isEnabled() is True
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
    assert "mục lục" in dialog.table.item(0, 5).text().lower()
    dialog.deleteLater()
    app.processEvents()
    db.close()
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_review_dialog.py -k "boundary_dialog_can or shows_evidence" -v`

Expected: FAIL because the buttons, sixth evidence column and live validation do not exist.

- [ ] **Step 3: Implement the boundary editor**

Make lesson number editable. Add buttons named `btn_add`, `btn_duplicate`, `btn_delete`, `btn_sort`, and expose `btn_confirm`. Add an error summary label above the table. On every cell change, parse rows, call `Splitter.validate(bounds, evidence, page_count)`, color cells referenced by issues, and disable `btn_confirm` if `report.valid` is false. Use these Vietnamese messages:

```python
ISSUE_TEXT = {
    "duplicate_lesson": "Trùng số bài",
    "missing_lesson": "Thiếu bài",
    "start_not_increasing": "Trang đầu chưa tăng",
    "overlap": "Khoảng trang chồng nhau",
    "page_out_of_range": "Trang nằm ngoài PDF",
    "toc_heading_conflict": "Mục lục và trang mở bài mâu thuẫn",
}
```

Pass `SplitResult` from `DialogImport._on_boundaries_ready()` into the dialog. If the user defers, keep `review_bounds`; no OCR begins.

- [ ] **Step 4: Run UI and splitter regression**

Run: `pytest tests/unit/test_review_dialog.py tests/unit/test_splitter.py -v`

Expected: all pass in Qt offscreen mode.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/ui/dialog_import.py tests/unit/test_review_dialog.py
git commit -m "feat: make lesson boundary review repairable"
```

### Task 5: Migration 3 and Persistent Block Manifest

**Files:**
- Modify: `hanzi_app/data/migrate.py`
- Modify: `hanzi_app/data/userdb.py`
- Test: `tests/unit/test_userdb.py`

**Interfaces:**
- Produces: schema version 3, table `import_block`, nullable `lesson_word.source_block_id`.
- Produces: `replace_import_blocks`, `get_import_blocks`, `update_import_block`, `replace_vocab_block`.
- Produces: `book_import_complete(book_id) -> bool`.
- Preserves: every old `lesson_word.id` and `progress.source_lw_id`.

- [ ] **Step 1: Write failing migration and CRUD tests**

```python
def create_version_2_database_with_source_word(tmp_path):
    path = tmp_path / "v2.sqlite"
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate._len_bac_1(conn)
    migrate._ghi_version(conn, 1)
    migrate._len_bac_2(conn)
    migrate._ghi_version(conn, 2)
    conn.execute(
        "INSERT INTO book(id,title,file_path,file_hash,import_state) "
        "VALUES(1,'Sách cũ','old.pdf','old-hash','ready')"
    )
    conn.execute(
        "INSERT INTO lesson(id,book_id,index_no,page_start,page_end) "
        "VALUES(1,1,1,0,9)"
    )
    conn.execute(
        "INSERT INTO lesson_word(id,lesson_id,order_no,word) "
        "VALUES(7,1,1,'你好')"
    )
    conn.execute(
        "INSERT INTO progress(word,status,source_lw_id) "
        "VALUES('你好','new',7)"
    )
    conn.close()
    return path


def test_migration_3_preserves_progress_source_and_allows_repeated_word(tmp_path):
    path = create_version_2_database_with_source_word(tmp_path)
    db = UserDb(str(path))
    lesson_id = db.get_lessons(1)[0]["id"]
    blocks = db.replace_import_blocks(lesson_id, [
        VocabBlock(None, lesson_id, 1, 3, (0, 10, 100, 200),
                   "a.png", 1, 1, 1),
        VocabBlock(None, lesson_id, 2, 5, (0, 10, 100, 200),
                   "b.png", 1, 2, 2),
    ])
    db.replace_vocab_block(blocks[0]["id"], [vocab("你好", 1)])
    db.replace_vocab_block(blocks[1]["id"], [vocab("你好", 2)])

    assert migrate.current_version(db._conn) == 3
    assert len(db.get_lesson_words(lesson_id)) == 2
    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word='你好'"
    ).fetchone()[0] is not None


def test_replace_import_blocks_is_atomic(db):
    book_id = them_sach(db, "Sách manifest", "manifest-atomic")
    db.replace_lessons(book_id, [bound(1, 0, 9)])
    lesson_id = db.get_lessons(book_id)[0]["id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_import_blocks(lesson_id, [
            VocabBlock(None, lesson_id, 1, 3, (0, 0, 100, 200),
                       None, 2, 1, 2),
            VocabBlock(None, lesson_id, 1, 4, (0, 0, 100, 200),
                       None, 2, 3, 4),
        ])
    assert db.get_import_blocks(lesson_id) == []


def test_book_import_complete_requires_a_passed_block_for_every_lesson(db):
    book_id = them_sach(db, "Sách đủ bài", "manifest-complete")
    db.replace_lessons(book_id, [bound(1, 0, 4), bound(2, 5, 9)])
    first, second = db.get_lessons(book_id)
    db.replace_import_blocks(first["id"], [
        VocabBlock(None, first["id"], 1, 1, (0, 0, 100, 200),
                   "one.png", 1, 1, 1, "local_ok")
    ])
    assert db.book_import_complete(book_id) is False
    db.replace_import_blocks(second["id"], [
        VocabBlock(None, second["id"], 1, 6, (0, 0, 100, 200),
                   "two.png", 1, 1, 1, "manual")
    ])
    assert db.book_import_complete(book_id) is True
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_userdb.py -k "migration_3 or replace_import_blocks" -v`

Expected: FAIL at schema version 2 and missing methods.

- [ ] **Step 3: Implement atomic migration and CRUD**

Set `SCHEMA_VERSION = 3`. `_len_bac_3()` must:

1. Create `import_block`.
2. Create a temporary mapping of `(word, source_lw_id)` for non-null progress links.
3. Create `lesson_word_new` with the old columns plus `source_block_id`, no unique word constraint.
4. Copy rows with unchanged IDs.
5. Drop old `lesson_word`, rename the new table, recreate `idx_lw_lesson`, `idx_lw_word`, and `idx_lw_lesson_word`.
6. Restore `progress.source_lw_id` from the temporary mapping.
7. Run `PRAGMA foreign_key_check` in the migration test and require an empty result.

Use exact UserDb signatures:

```python
def replace_import_blocks(
    self, lesson_id: int, blocks: list[VocabBlock]
) -> list[dict]

def get_import_blocks(self, lesson_id: int) -> list[dict]

def update_import_block(
    self, block_id: int, *, status: str,
    ai_attempts: int, crop_path: str | None
) -> None

def replace_vocab_block(
    self, block_id: int, rows: list[VocabRow]
) -> None

def book_import_complete(self, book_id: int) -> bool
```

`replace_vocab_block()` resolves `lesson_id` from `import_block`, deletes only rows with the same `source_block_id`, and inserts all rows with that block ID. `book_import_complete()` returns true only when every positive lesson has at least one manifest block and every block status is `local_ok`, `ai_ok` or `manual`.

- [ ] **Step 4: Run all UserDb tests**

Run: `pytest tests/unit/test_userdb.py -v`

Expected: all pass; schema-version assertions expect exactly one row containing `3`.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/data/migrate.py hanzi_app/data/userdb.py tests/unit/test_userdb.py
git commit -m "feat: persist vocabulary block checkpoints"
```

### Task 6: Multi-Block Locator and Atomic Crop Storage

**Files:**
- Modify: `hanzi_app/service/vocab.py`
- Modify: `hanzi_app/service/importer.py`
- Test: `tests/unit/test_vocab.py`
- Test: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces: `VocabExtractor.locate_blocks(pdf, lesson) -> list[VocabBlock]`.
- Produces: `render_block_crop(pdf, block, dpi=250) -> bytes`.
- Produces: `_write_crop_atomic(root, book_id, lesson_id, block_no, data) -> str` in importer.

- [ ] **Step 1: Write failing locator tests with synthetic spans**

```python
def _span(text, x, y, width=50, height=14):
    return TextSpan(
        text, (x, y, x + width, y + height), float(height), True
    )


def _vocab_region(title, orders, y0):
    spans = [_span(title, 20, y0, 100, 18)]
    for offset, order in enumerate(orders, start=1):
        y = y0 + 30 * offset
        spans.extend([
            _span(str(order), 20, y, 20),
            _span(f"词{order}", 80, y, 45),
            _span("cí", 160, y, 45),
        ])
    return spans


def test_locator_finds_disjoint_blocks_and_ignores_prose(monkeypatch):
    pages = {
        0: [_span("Trong bài này 生词 nghĩa là từ mới", 20, 100, 300)],
        1: _vocab_region("New Words", (1, 2, 3), 100),
        2: [_span("A: 你好", 20, 100), _span("B: 你好", 20, 140)],
        3: _vocab_region("生词", (4, 5), 300),
    }
    pdf = MagicMock()
    pdf.page_count.return_value = 4
    pdf.spans.side_effect = lambda page: pages[page]
    lesson = LessonBoundary(1, "Bài 1", 0, 3, 1.0, "lesson")
    blocks = VocabExtractor().locate_blocks(pdf, lesson)

    assert [(b.block_no, b.page_index) for b in blocks] == [(1, 1), (2, 3)]
    assert [b.expected_rows for b in blocks] == [3, 2]
    assert blocks[0].bbox[1] < blocks[0].bbox[3]


def test_crop_writer_is_atomic_and_uses_block_path(tmp_path):
    path = _write_crop_atomic(tmp_path, 4, 9, 2, b"png")
    assert Path(path).read_bytes() == b"png"
    assert Path(path).as_posix().endswith("book-4/lesson-9/block-2.png")
    assert not list(tmp_path.rglob("*.tmp"))
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -k "locator_finds or crop_writer" -v`

Expected: FAIL because locator and crop writer do not exist.

- [ ] **Step 3: Implement two-of-three block detection**

Scan every page from `page_start` through `page_end`; never break after the first block. A region is accepted when at least two signal groups are true:

```python
signals = {
    "heading": has_vocab_heading(region_spans),
    "rows": repeated_hanzi_pinyin_rows(region_spans) >= 2,
    "structure": sequential_orders(region_spans) >= 2 or aligned_columns(region_spans),
}
accepted = sum(signals.values()) >= 2
```

Split multiple headings on one page into separate y-ranges. Derive `expected_rows`, `first_order`, and `last_order` from geometric row/order evidence. `render_block_crop()` uses the block bbox and `PdfSource.get_page_crop_image_bytes()`. `_write_crop_atomic()` creates the target directory, writes a sibling `.tmp`, then calls `Path.replace()`.

- [ ] **Step 4: Run vocab and worker regression**

Run: `pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v`

Expected: all pass; the prose-only `生词` page yields no block.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/service/vocab.py hanzi_app/service/importer.py tests/unit/test_vocab.py tests/unit/test_universal_engine.py
git commit -m "feat: locate every vocabulary block in a lesson"
```

### Task 7: Block Extraction and Coverage Validator

**Files:**
- Modify: `hanzi_app/service/vocab.py`
- Test: `tests/unit/test_vocab.py`
- Test: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Produces: `validate_block_coverage(block, local_rows, ai_rows, final_rows) -> BlockCoverage`.
- Produces: `extract_blocks(pdf, blocks, ai_client=None) -> ExtractionResult`.
- Preserves repeated words when their `source_block_id` differs.

- [ ] **Step 1: Write failing coverage and merge tests**

```python
def _block_row(word, order_no, block_id):
    return VocabRow(
        order_no, word, "cí", None, None, 1,
        "regex", False, None, source_block_id=block_id
    )


def test_coverage_rejects_four_of_twelve_rows():
    block = VocabBlock(7, 2, 1, 10, (0, 0, 100, 200),
                       "crop.png", 12, 1, 12)
    rows = [_block_row(f"词{i}", i, 7) for i in range(1, 5)]
    report = VocabExtractor().validate_block_coverage(block, rows, [], rows)
    assert report.passed is False
    assert report.missing_orders == tuple(range(5, 13))
    assert "expected_row_mismatch" in report.issues


def test_merge_keeps_same_word_from_different_blocks():
    first = _block_row("行", 1, 11)
    second = _block_row("行", 9, 12)
    result = VocabExtractor().merge_block_rows([first], [second])
    assert [(r.word, r.source_block_id) for r in result] == [
        ("行", 11), ("行", 12)
    ]


def test_three_column_block_keeps_word_when_meaning_is_absent():
    spans = [
        _span("STT", 10, 50), _span("Chữ Hán", 80, 50),
        _span("Pinyin", 180, 50),
        _span("1", 10, 100), _span("你好", 80, 100),
        _span("nǐhǎo", 180, 100),
    ]
    rows = VocabExtractor().extract_table_spans(spans, source_page=1)
    assert len(rows) == 1
    assert rows[0].word == "你好"
    assert rows[0].meaning_src is None
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_vocab.py -k "coverage_rejects or different_blocks" -v`

Expected: FAIL because coverage and source-aware merge are missing.

- [ ] **Step 3: Implement local block extraction and exact coverage**

For each block, crop spans to its bbox, run bilingual OCR merge and refactor the
row parser to infer 2–7 column centers from repeated x positions. Chữ Hán is the
only mandatory content column; pinyin, part of speech, Hán-Việt and meaning are
optional and missing cells remain `None`. Then attach
`source_block_id=block.id`. Sort final rows by
`(source_page, source_block_id, order_no)`. Deduplicate only the exact key:

```python
key = (
    row.word,
    row.pinyin_src,
    row.source_block_id,
    row.order_no,
)
```

Coverage fails for zero rows, missing STT inside a known range, final count below `ceil(expected_rows * 0.8)`, or abnormal exact duplicates. If `expected_rows is None`, pass only when two independent sources have the same nonzero row count; without AI, mark `needs_review` and keep `passed=False`.

- [ ] **Step 4: Run all extraction tests**

Run: `pytest tests/unit/test_vocab.py tests/unit/test_universal_engine.py -v`

Expected: all pass; a nonempty four-row result for a 12-row block is incomplete.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/service/vocab.py tests/unit/test_vocab.py tests/unit/test_universal_engine.py
git commit -m "feat: validate vocabulary coverage per block"
```

### Task 8: Targeted AI Budget, Checkpoint and Resume

**Files:**
- Modify: `hanzi_app/adapter/aiclient.py`
- Modify: `hanzi_app/service/vocab.py`
- Modify: `hanzi_app/service/importer.py`
- Modify: `hanzi_app/data/userdb.py`
- Test: `tests/unit/test_aiclient.py`
- Test: `tests/unit/test_universal_engine.py`

**Interfaces:**
- Changes: `AiClient.extract_vocab_from_image(image_bytes, issue_context=None)`.
- Enforces: maximum three AI requests summed across all blocks of one lesson.
- Produces: block states `pending`, `local_ok`, `ai_ok`, `manual`, `incomplete`.
- Produces: book state `incomplete` when any lesson/block lacks coverage.
- Produces: `VocabImporterWorker._load_or_create_blocks(db, pdf, extractor, lesson, boundary) -> list[VocabBlock]`.
- Produces: `VocabImporterWorker._checkpoint_result(db, result) -> None`.
- Produces: `VocabImporterWorker._format_incomplete(lesson, coverage) -> str`.

- [ ] **Step 1: Write failing budget, 429 and resume tests**

```python
def test_vocab_ai_budget_is_three_per_lesson(monkeypatch):
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"crop"
    blocks = [
        VocabBlock(i + 1, 2, i + 1, i, (0, 0, 100, 200),
                   f"block-{i + 1}.png", 2, i * 2 + 1, i * 2 + 2)
        for i in range(4)
    ]
    extractor = VocabExtractor()
    monkeypatch.setattr(extractor, "_extract_local_block", lambda *_args: [])
    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.return_value = []
    result = extractor.extract_blocks(pdf, blocks, ai_client=client)
    assert result.complete is False
    assert result.ai_attempts == 3
    assert client.extract_vocab_from_image.call_count == 3


def test_429_result_carries_consumed_attempt(monkeypatch):
    block = VocabBlock(
        9, 2, 1, 4, (0, 0, 100, 200),
        "block.png", 2, 1, 2
    )
    extractor = VocabExtractor()
    monkeypatch.setattr(extractor, "_extract_local_block", lambda *_args: [])
    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.side_effect = AiRateLimitError()

    result = extractor.extract_blocks(MagicMock(), [block], client)

    assert result.complete is False
    assert result.ai_attempts == 1
    assert result.blocks[0].ai_attempts == 1
    assert result.blocks[0].status == "incomplete"


def test_429_keeps_completed_block_and_resume_skips_it(tmp_path, monkeypatch):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Sách thử", "book.pdf", "resume-429", 20)
    db.replace_lessons(
        book_id, [LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")]
    )
    lesson_id = db.get_lessons(book_id)[0]["id"]
    blocks = db.replace_import_blocks(lesson_id, [
        VocabBlock(None, lesson_id, 1, 1, (0, 0, 100, 200),
                   "done.png", 1, 1, 1),
        VocabBlock(None, lesson_id, 2, 3, (0, 0, 100, 200),
                   "pending.png", 2, 2, 3),
    ])
    db.replace_vocab_block(
        blocks[0]["id"],
        [VocabRow(1, "你好", "nǐhǎo", None, None, 2,
                  "regex", False, None)]
    )
    db.update_import_block(
        blocks[0]["id"], status="local_ok", ai_attempts=0,
        crop_path=blocks[0]["crop_path"]
    )
    db.close()

    class FakePdfSource:
        def __init__(self, _path):
            self.path = _path
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False

    class FakeExtractor:
        def __init__(self, _dict_db):
            self.dict_db = _dict_db
        def extract_blocks(self, _pdf, pending, ai_client=None):
            assert [block.block_no for block in pending] == [2]
            try:
                ai_client.extract_vocab_from_image(b"pending")
            except AiRateLimitError:
                updated = replace(
                    pending[0], status="incomplete", ai_attempts=1
                )
                coverage = BlockCoverage(
                    pending[0].id, 2, 0, 0, 0, (2, 3),
                    ("rate_limited",), False
                )
                return ExtractionResult(
                    (), (coverage,), (updated,), 1, False
                )

    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.side_effect = AiRateLimitError()
    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "VocabExtractor", FakeExtractor)
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)
    worker.ai_client = client
    worker.run()

    reopened = UserDb(db_path)
    assert reopened.get_import_blocks(lesson_id)[0]["status"] == "local_ok"
    assert reopened.get_import_blocks(lesson_id)[1]["ai_attempts"] == 1
    assert reopened.get_lesson_words(lesson_id)[0]["word"] == "你好"
    assert reopened.get_book(book_id)["import_state"] == "incomplete"
    assert client.extract_vocab_from_image.call_count == 1
    reopened.close()
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_aiclient.py tests/unit/test_universal_engine.py -k "budget_is_three or 429_keeps" -v`

Expected: FAIL because retry currently happens inside each image call and worker has no block checkpoint.

- [ ] **Step 3: Move retry policy into the orchestrator**

Make `extract_by_llm_image()` issue exactly one HTTP request. Add validator context such as `"Block 2: thiếu STT 8–12; chỉ chép các dòng này"` to the prompt. `extract_blocks()` consumes one attempt for each actual request and stops at three total for the lesson. On `AiRateLimitError`, propagate immediately without sleeping or another request.

Refactor `VocabImporterWorker.run()`:

```python
for lesson in lessons:
    blocks = self._load_or_create_blocks(
        thread_db, pdf, extractor, lesson, boundary
    )

    pending = [b for b in blocks if b.status not in
               {"local_ok", "ai_ok", "manual"}]
    result = extractor.extract_blocks(pdf, pending, self.ai_client)
    self._checkpoint_result(thread_db, result)
    if not result.complete:
        thread_db.set_import_state(self.book_id, "incomplete")
        raise RuntimeError(self._format_incomplete(lesson, result.coverage))
```

Only after every lesson is complete set the book to `review`. Never skip a lesson merely because it has any rows; skip only blocks in a completed checkpoint state.
`_load_or_create_blocks()` converts DB dicts to `VocabBlock`, and on the first
run locates blocks, writes each crop atomically, persists the manifest, then
returns the persisted rows as dataclasses. `_checkpoint_result()` calls
`replace_vocab_block()` before marking that block `local_ok`/`ai_ok`; incomplete
coverage is marked `incomplete`. `_format_incomplete()` returns
`"Bài <n> · block <n> · <issue>"` for the first failing block.
The remaining AI budget is `max(0, 3 - sum(block.ai_attempts for block in
blocks))`, so resume cannot reset the limit. `_checkpoint_result()` stores
attempt counts/status from `result.blocks`; it replaces partial rows only when
their count is not lower than the rows already stored for that block. The final
transition to `review` uses `book_import_complete()`, not merely “all existing
manifest rows passed”.

- [ ] **Step 4: Run AI, worker and DB regression**

Run: `pytest tests/unit/test_aiclient.py tests/unit/test_userdb.py tests/unit/test_universal_engine.py -v`

Expected: all pass; 429 produces one request in that run and preserves prior rows.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/adapter/aiclient.py hanzi_app/service/vocab.py hanzi_app/service/importer.py hanzi_app/data/userdb.py tests/unit/test_aiclient.py tests/unit/test_universal_engine.py
git commit -m "feat: resume incomplete imports from block checkpoints"
```

### Task 9: Incomplete-State UX and Persisted Source Preview

**Files:**
- Modify: `hanzi_app/service/importer.py`
- Modify: `hanzi_app/ui/dialog_import.py`
- Modify: `hanzi_app/ui/screen_books.py`
- Modify: `hanzi_app/data/userdb.py`
- Test: `tests/unit/test_review_dialog.py`

**Interfaces:**
- Produces: `UserDb.get_word_source_crop(lesson_word_id) -> str | None`.
- Changes: `PreviewWorker(pdf_path, page_start=None, page_end=None, crop_paths=(), dpi=125, parent=None)`.
- Produces: `PreviewWorker` support for persisted crop paths with legacy PDF fallback.
- Produces: resume actions for `review_bounds` and `incomplete`.
- Produces: `DialogReviewBook._confirm_current_block_manual() -> None`.

- [ ] **Step 1: Write failing UI state and preview tests**

```python
def test_books_screen_labels_incomplete_and_offers_resume(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    db.set_import_state(book_id, "incomplete")
    screen = ScreenBooks(db)
    screen.load_books()
    assert "chưa đủ dữ liệu" in screen.list_books.item(0).text()
    screen._hien_bai_hoc_cua_sach(book_id, "Sách kiểm thử")
    assert screen.btn_resume_import.isVisible()
    screen.deleteLater()
    app.processEvents()
    db.close()


def test_review_preview_prefers_saved_block_crop(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db, book_id = _make_review_queue_book(tmp_path)
    lesson = db.get_lessons(book_id)[0]
    crop = str(tmp_path / "block-1.png")
    block = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 4, (0, 0, 100, 200),
                   crop, 3, 1, 3)
    ])[0]
    first_word = db.get_lesson_words(lesson["id"])[0]
    with db.transaction() as conn:
        conn.execute(
            "UPDATE lesson_word SET source_block_id=? WHERE id=?",
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
    assert dialog.user_db.get_word_source_crop(first_word["id"]) == crop
    dialog.deleteLater()
    app.processEvents()
    db.close()


def test_manual_block_confirmation_unblocks_book(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book(
        "Sách thủ công", str(tmp_path / "book.pdf"), "manual-block", 10
    )
    db.replace_lessons(
        book_id, [LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")]
    )
    lesson = db.get_lessons(book_id)[0]
    block = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 4, (0, 0, 100, 200),
                   "block.png", 3, 1, 3, "incomplete", 3)
    ])[0]
    db.replace_vocab_block(block["id"], [
        VocabRow(1, "你好", "nǐhǎo", None, None, 5,
                 "manual", False, None)
    ])
    db.set_import_state(book_id, "incomplete")
    dialog = DialogReviewBook(db, db.get_book(book_id))
    dialog.current_lesson = lesson
    dialog.current_block_id = block["id"]
    dialog._confirm_current_block_manual()

    assert db.get_import_blocks(lesson["id"])[0]["status"] == "manual"
    assert db.get_book(book_id)["import_state"] == "review"
    dialog.deleteLater()
    app.processEvents()
    db.close()
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest tests/unit/test_review_dialog.py -k "labels_incomplete or prefers_saved" -v`

Expected: FAIL because state suffix, resume button and crop lookup are missing.

- [ ] **Step 3: Implement resume and preview behavior**

Add list suffixes:

```python
STATE_SUFFIX = {
    "review_bounds": "  ·  chờ duyệt ranh giới",
    "extracting": "  ·  đang lấy từ mới",
    "incomplete": "  ·  chưa đủ dữ liệu",
    "review": "  ·  cần duyệt từ mới",
}
```

For `review_bounds`, show “Phân tích lại và sửa ranh giới”; this starts phase one again from the book’s saved PDF path and opens `DialogReviewBoundaries`. For `incomplete`, show “Tiếp tục lấy phần còn thiếu”; this starts `VocabImporterWorker` and resumes pending blocks. Disable both buttons while a worker is running.

Also allow opening `DialogReviewBook` for an `incomplete` book. Show the failing
block crop, its partial rows and a button “Xác nhận block thủ công”. The handler
saves edited rows with `replace_vocab_block()`, marks the block `manual`, and
changes the book to `review` only when every manifest block is in
`local_ok`, `ai_ok` or `manual`; otherwise it remains `incomplete`.

`get_word_source_crop()` joins `lesson_word.source_block_id` to `import_block.crop_path`. Preview loads this PNG in the background. If the row is legacy and has no block link, retain `render_vocab_table_preview()` as fallback.

- [ ] **Step 4: Run all review UI tests**

Run: `pytest tests/unit/test_review_dialog.py -v`

Expected: all pass; preview workers remain non-blocking and stale workers cannot overwrite a newer selection.

- [ ] **Step 5: Commit**

```bash
git add hanzi_app/service/importer.py hanzi_app/ui/dialog_import.py hanzi_app/ui/screen_books.py hanzi_app/data/userdb.py tests/unit/test_review_dialog.py
git commit -m "feat: expose incomplete import recovery"
```

### Task 10: Cross-Book Verification, Regression and Project State

**Files:**
- Modify: `tests/unit/test_universal_engine.py`
- Modify: `tests/golden/test_boya_vocab_golden.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Verifies: generic synthetic book, Boya golden, real HSK discovery without writing the live DB.
- Records: phase B7m test totals and next manual acceptance step.

- [ ] **Step 1: Add final generic regression tests**

```python
def test_generic_import_never_accepts_sparse_lesson_sequence():
    numbers = (1, 2, 3, 4, 8, 12, 13, 14)
    boundaries = [
        LessonBoundary(number, f"Bài {number}", index * 10,
                       index * 10 + 9, 0.6, "lesson")
        for index, number in enumerate(numbers)
    ]
    report = Splitter().validate(boundaries, (), total_pages=144)
    assert report.valid is False
    assert report.missing_lesson_nos == (5, 6, 7, 9, 10, 11)


def test_generic_multi_block_book_is_complete_only_after_every_block(monkeypatch):
    row_counts = (5, 4, 6, 3, 2, 7)
    blocks = [
        VocabBlock(index, 1, index, index, (0, 0, 100, 200),
                   f"block-{index}.png", count, 1, count)
        for index, count in enumerate(row_counts, start=1)
    ]
    extractor = VocabExtractor()
    monkeypatch.setattr(
        extractor,
        "_extract_local_block",
        lambda _pdf, block: [
            VocabRow(order, f"词{block.id}-{order}", "cí", None, None,
                     block.page_index + 1, "regex", False, None,
                     source_block_id=block.id)
            for order in range(1, block.expected_rows + 1)
        ],
    )
    result = extractor.extract_blocks(MagicMock(), blocks)
    assert result.complete is True
    assert sum(c.final_rows for c in result.coverage) == 27
```

The synthetic rows do not include copied textbook images or book-specific presets.

- [ ] **Step 2: Run focused RED/GREEN and all unit tests**

Run: `pytest tests/unit/test_universal_engine.py -k "sparse_lesson or multi_block_book" -v`

Expected before final glue: at least one test fails. Complete only the missing glue in the files already changed by Tasks 1–9, then rerun until both pass.

Run: `pytest tests/unit -v`

Expected: all unit tests pass with only the pre-existing skip.

- [ ] **Step 3: Run Boya golden and real HSK discovery read-only**

Run: `pytest tests/golden/test_boya_vocab_golden.py -v`

Expected: both Boya golden lessons pass without using the default preset branch.

For the local HSK PDF, run discovery directly against the PDF and serialize only the returned boundary report to stdout; do not instantiate `UserDb`:

```powershell
python -c "from hanzi_app.adapter.pdfsource import PdfSource; from hanzi_app.service.splitter import Splitter; p=r'C:\Users\Admin\Downloads\新HSK1教程3.0.pdf'; pdf=PdfSource(p); e=pdf.page_census(); r=Splitter().propose([],e,evidence_image=pdf.boundary_contact_sheet(e)); print([b.index_no for b in r.boundaries]); print(r.report); pdf.close()"
```

Expected: either `[1, 2, ..., 15]` with `valid=True`, or `valid=False` with exact missing/conflicting lessons. It must never return the sparse sequence as valid/high-confidence.

- [ ] **Step 4: Prove the live HSK rows were untouched and run full suite**

Before and after QA, query the live DB read-only and compare the exact tuple result:

```powershell
python -c "import sqlite3; p=r'D:\Hanyu recognize\data\user.sqlite'; c=sqlite3.connect('file:'+p.replace('\\','/')+'?mode=ro',uri=True); print(c.execute(\"SELECT b.id,b.import_state,l.index_no,l.page_start,l.page_end,COUNT(lw.id) FROM book b JOIN lesson l ON l.book_id=b.id LEFT JOIN lesson_word lw ON lw.lesson_id=l.id WHERE b.title='新HSK1教程3.0' GROUP BY b.id,l.id ORDER BY l.index_no\").fetchall())"
```

The two outputs must be byte-for-byte identical.

Run: `pytest -v`

Expected: all tests pass with only the pre-existing skip and no product failure warning.

- [ ] **Step 5: Update AGENTS.md and commit**

Add phase `B7m | Universal Evidence Fusion Import` with exact test totals from the preceding commands. Set the next phase to manual acceptance on one non-Boya PDF, including boundary review, incomplete resume and source preview.

```bash
git add tests/unit/test_universal_engine.py tests/golden/test_boya_vocab_golden.py AGENTS.md
git commit -m "test: verify universal evidence fusion import"
```

## Completion Gate

Before claiming completion, invoke `superpowers:verification-before-completion` and verify:

1. `git diff --check` is clean.
2. `pytest tests/unit -v` passes.
3. `pytest tests/golden/test_boya_vocab_golden.py -v` passes.
4. `pytest -v` passes.
5. HSK read-only boundary discovery returns 15 continuous lessons or an explicit invalid report.
6. The before/after live HSK DB snapshots are identical.
7. No API call count exceeds two per book split or three per lesson extraction.
8. `AGENTS.md` contains the actual, not estimated, test totals.
