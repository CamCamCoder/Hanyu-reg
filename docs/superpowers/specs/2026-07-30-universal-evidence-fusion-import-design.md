# Thiết kế Universal Evidence-Fusion Import

Ngày: 2026-07-30  
Trạng thái: đã được người dùng duyệt trong hội thoại

## 1. Bối cảnh và nguyên nhân gốc

Engine hiện tại đã đạt kết quả tốt trên Boya Sơ cấp 1 nhưng không đủ tổng quát.
Ca `新HSK1教程3.0.pdf` cho thấy hai lỗi độc lập:

1. PDF có 144 trang scan và 15 bài. Splitter gửi tóm lược OCR nhiễu cho AI,
   cắt ở 100 dòng đầu, chấp nhận mọi danh sách AI không rỗng và gắn cứng độ tin
   cậy `0.95`. Kết quả chỉ có các bài 1, 2, 3, 4, 8, 12, 13, 14 nhưng vẫn được
   coi là thành công.
2. Một bài HSK có nhiều khối `New Words` xen giữa bài khóa. Locator hiện tại
   tìm ở cấp trang, có nhiều false positive khi chữ `生词` chỉ xuất hiện trong
   nội dung, rồi dừng sau cụm đầu tiên. Vì vậy một bài có thể chỉ lấy 4–10 từ
   nhưng vẫn được coi là hoàn tất.

Màn xác nhận ranh giới hiện tại chỉ sửa được các dòng đã có, không thể thêm bài
bị AI bỏ sót. Validator chỉ chặn bài rỗng, không phát hiện bài thiếu hoặc khối từ
thiếu dòng.

## 2. Mục tiêu

Thiết kế lại luồng nhập PDF theo mô hình **Evidence Fusion**:

- Tách bài bằng nhiều nguồn bằng chứng thay vì tin một kết quả AI.
- Tự tiếp tục khi các nguồn đồng thuận; dừng để người dùng xác nhận khi mâu thuẫn.
- Tìm mọi khối từ mới trong toàn bộ bài, kể cả các khối không liền nhau.
- Dùng AI tối đa ba lượt có mục tiêu cho một bài khi validator chỉ ra phần thiếu.
- Không bao giờ báo thành công chỉ vì đầu ra không rỗng.
- Lưu checkpoint theo bài và khối để tiếp tục sau 429/lỗi mà không làm lại phần
  đã đạt.
- Không hardcode tên sách, tổng số trang hoặc ranh giới của Boya/HSK.

Phiên triển khai chỉ sửa engine và các màn xác nhận liên quan. Không sửa, xóa,
nhập lại hoặc ghi đè dữ liệu của quyển HSK đang có trong `user.sqlite`.

## 3. Ngoài phạm vi

- Không xây mô hình OCR mới.
- Không thêm PaddleOCR, OpenCV, NumPy hoặc phụ thuộc ngoài đặc tả.
- Không tạo preset ranh giới riêng cho HSK.
- Không tự động sửa nghĩa hoặc dịch lại toàn bộ từ đã được đọc đúng.
- Không thay đổi các màn Tra cứu, Ôn tập và Bộ thủ.
- Không cam kết mọi sách trên thế giới đều tự động 100%; khi không đủ bằng chứng,
  hành vi đúng là dừng với báo cáo cụ thể.

## 4. Định nghĩa thành công mới

Một bước chỉ được coi là thành công khi có bằng chứng về **độ đầy đủ**, không
chỉ về sự tồn tại:

- Split thành công: chuỗi bài hợp lệ, trang bắt đầu tăng dần, không chồng lấn và
  không có khoảng nhảy số bài chưa được giải thích.
- Locate thành công: mọi khối từ được phát hiện trong ranh giới bài đều có crop
  và manifest.
- Extract thành công: mọi khối trong manifest đã trả dữ liệu đạt coverage hoặc
  được người dùng xác nhận thủ công.
- Import thành công: mọi bài đạt; sách vẫn ở `incomplete` nếu một bài chưa đạt.

## 5. Kiến trúc tổng thể

Luồng gồm năm pha:

1. **Page Census** — khảo sát nhẹ toàn sách.
2. **Boundary Evidence Fusion** — tạo, hợp nhất và kiểm tra đề xuất ranh giới.
3. **Block Manifest** — tìm mọi vùng từ mới trong từng bài.
4. **Hybrid Extraction** — OCR local, AI có mục tiêu, validator coverage.
5. **Review and Resume** — duyệt, checkpoint và tiếp tục an toàn.

`service/` chỉ điều phối trên dữ liệu được adapter cung cấp. `adapter/pdfsource.py`
là nơi duy nhất đọc PDF/render ảnh; `adapter/aiclient.py` là nơi duy nhất gọi
mạng; `data/` không import Qt.

## 6. Pha 1: Page Census

### 6.1 Phân loại trang

Mỗi trang được phân loại:

- `native`: có lớp chữ đáng tin.
- `scan`: lớp chữ rỗng/rác và có ảnh trang.
- `mixed`: vừa có ảnh vừa có lớp chữ hữu ích.

Không dùng tổng CJK toàn sách để chọn một preset. Mỗi trang được quyết định riêng.

### 6.2 Khảo sát nhẹ

- OCR dải trên của mọi trang ở DPI thấp để tìm số bài/tiêu đề.
- OCR dải dưới khi cần ánh xạ số trang in.
- OCR toàn trang chỉ cho các trang ứng viên mục lục hoặc khi validator yêu cầu.
- Tạo thumbnail/contact sheet nhỏ cho AI phân xử, không ghép ảnh toàn sách ở DPI
  cao.

### 6.3 Phát hiện mục lục

Ưu tiên phần đầu sách và tìm các tín hiệu như `目录`, `Contents`, `Lesson`, `课`,
cột số bài và cột số trang. OCR mục lục giữ tọa độ để ghép đúng số bài, tiêu đề
và trang in theo từng hàng.

## 7. Pha 2: Boundary Evidence Fusion

### 7.1 Nguồn bằng chứng

Mỗi ứng viên ranh giới có thể nhận bằng chứng từ:

- Hàng mục lục.
- OCR dải đầu trang: `Lesson N`, `第N课`, số lớn và tiêu đề.
- Bố cục mở bài lặp lại: top-band có hash/hình thức gần các trang mở bài khác.
- Ánh xạ số trang in sang chỉ số PDF.
- AI đọc ảnh mục lục/contact sheet khi local không đủ chắc chắn.

AI là một nguồn bằng chứng, không phải nguồn chân lý duy nhất.

### 7.2 Hợp nhất

Các ứng viên gần cùng trang và cùng số bài được hợp nhất. Confidence được tính từ
nguồn thực tế; không gắn cứng `0.95`. Kết quả giữ danh sách nguồn và lý do.

### 7.3 Validator ranh giới

Bắt buộc kiểm tra:

- `index_no` dương, không trùng.
- Chuỗi số bài liên tục; khoảng thiếu chỉ hợp lệ khi được gắn rõ là review/phụ lục
  hoặc người dùng xác nhận.
- `page_start` tăng nghiêm ngặt.
- Không chồng lấn.
- `page_end` được suy ra từ bài kế tiếp và nằm trong PDF.
- Khoảng trang một bài quá lớn so với trung vị phải bị cảnh báo.
- Số bài từ mục lục và số trang mở bài không được mâu thuẫn âm thầm.

Nếu validator không đạt, importer chuyển `review_bounds`; không bắt đầu OCR từ.

### 7.4 AI cho pha split

- Tối đa hai lượt cho toàn sách.
- Lượt 1 đọc đúng ảnh mục lục/contact sheet và danh sách ứng viên local.
- Lượt 2 chỉ dùng khi validator nêu mâu thuẫn cụ thể.
- Không gửi 100 dòng OCR nhiễu rồi yêu cầu AI tự đoán toàn bộ.
- Mọi JSON AI phải qua cùng validator trước khi được dùng.

## 8. Màn xác nhận ranh giới

Màn hiện tại được bổ sung:

- Thêm bài.
- Xóa bài.
- Nhân bản dòng.
- Sắp xếp lại theo số bài/trang.
- Tô đỏ số bài thiếu/trùng và khoảng trang chồng lấn.
- Hiển thị nguồn bằng chứng và confidence.
- Nút `Đọc lại mục lục bằng AI` chỉ chạy một lượt có mục tiêu.
- Nút `Bắt đầu lấy từ` bị vô hiệu hóa khi validator chưa đạt.

Người dùng luôn có quyền sửa đề xuất trước pha OCR.

## 9. Pha 3: Block Manifest

### 9.1 Quét toàn bài

Locator quét từ `page_start` tới `page_end`, không `break` sau khối đầu tiên.
Một bài có thể có:

- Nhiều khối trên một trang.
- Nhiều khối ở các trang liên tiếp.
- Các khối không liền nhau, xen giữa hội thoại/ngữ pháp/bài tập.

### 9.2 Tín hiệu nhận diện khối

Một vùng chỉ trở thành ứng viên mạnh khi có ít nhất hai nhóm tín hiệu:

1. Tiêu đề: `生词`, `新词`, `词语表`, `New Words`, `Vocabulary`, `Từ mới`.
2. Dòng lặp: chữ Hán + pinyin + từ loại/nghĩa theo hàng.
3. Cấu trúc: STT liên tiếp, các baseline/cột lặp hoặc mật độ hàng cao.

Chỉ thấy chữ `生词` trong câu mô tả không đủ để coi trang/vùng là bảng từ.

### 9.3 Crop theo vùng

Mỗi block có bbox riêng, từ tiêu đề tới hàng cuối trước vùng kế tiếp. Không crop
cả trang nếu đã xác định được bbox. Crop được ghi atomically dưới:

`data/book_crops/book-<book_id>/lesson-<lesson_id>/block-<block_no>.png`

### 9.4 Manifest

Mỗi block lưu:

- Bài, số block, trang PDF và bbox.
- Crop path.
- Số dòng hình học dự kiến.
- Dải STT dự kiến nếu đọc được.
- Trạng thái: `pending`, `local_ok`, `ai_ok`, `manual`, `incomplete`.
- Số lượt AI đã dùng.

Manifest là checkpoint và là nguồn ảnh đối chiếu cho UI.

## 10. Pha 4: Hybrid Extraction

### 10.1 Local-first

Mỗi crop chạy OCR Trung và Latin rồi hợp nhất theo tọa độ. Parser dùng bố cục thực
tế của block, không giả định Boya luôn có bảy cột.

Các trường lõi:

- Chữ Hán.
- Pinyin nếu có.
- Từ loại nếu có.
- Nghĩa gốc trong sách nếu có.
- Trang và block nguồn.

Thiếu một cột tùy chọn không làm mất cả dòng.

### 10.2 AI có mục tiêu

Ngân sách tối đa ba lượt AI cho một bài:

1. Lượt đầu đọc các crop chưa đạt của bài.
2. Lượt hai đọc lại đúng block/dải STT còn thiếu ở DPI cao.
3. Lượt ba chỉ dùng khi validator vẫn xác định được một lỗi cụ thể.

Không retry cùng payload mà không có chẩn đoán mới. Không gửi cả bài nếu đã có
crop chặt.

### 10.3 Hợp nhất và khử trùng

Sắp theo `(page_index, block_no, row_position)`. Chỉ coi là trùng khi cùng chữ,
cùng pinyin và cùng block/vị trí nguồn. Một từ lặp lại ở block khác vẫn được giữ.

## 11. Coverage Validator

Mỗi block so sánh:

- Số hàng hình học dự kiến.
- Dải STT OCR được.
- Số dòng local.
- Số dòng AI.
- Số dòng cuối sau hợp nhất.

Các lỗi bắt buộc phát hiện:

- STT đứt đoạn.
- Một block phát hiện được nhưng trả 0 dòng.
- Block dự kiến 12 hàng nhưng chỉ có 4 dòng.
- Dòng trùng bất thường do OCR lặp.
- Chữ Hán/pinyin không hợp lệ theo validator hiện có.

Khi số hàng hình học không chắc chắn, cần hai nguồn độc lập đồng thuận hoặc người
dùng xác nhận. Bài chỉ đạt khi mọi block đạt.

## 12. Trạng thái, lỗi và resume

Trạng thái sách:

- `review_bounds`
- `extracting`
- `review`
- `incomplete`
- `ready`

`book.import_state` đang là TEXT không có CHECK constraint, nên không cần migration
chỉ để thêm `incomplete`.

Khi 429/lỗi:

- Giữ block đã đạt.
- Giữ crop và số lượt AI.
- Hiển thị lỗi dạng: `Bài 6 · block 2 · thiếu STT 8–12`.
- Resume từ block chưa đạt.
- Không gọi lại AI cho block `local_ok`, `ai_ok` hoặc `manual`.
- Hết ba lượt AI thì chuyển block/bài/sách sang `incomplete`.

Không ghi đè dữ liệu tốt bằng đầu ra ngắn hơn hoặc coverage thấp hơn.

## 13. Lưu trữ và migration

Thiết kế cần migration mới thay vì nhét checkpoint vào UI. Lược đồ hiện tại đang
ở bậc 2; phần này được triển khai nguyên tử trong **migration bậc 3**, không sửa
lại bậc 1 hoặc bậc 2 đã phát hành.

### 13.1 Bảng `import_block`

Migration tiếp theo tạo bảng thứ chín:

```sql
CREATE TABLE import_block (
    id             INTEGER PRIMARY KEY,
    lesson_id      INTEGER NOT NULL
                     REFERENCES lesson(id) ON DELETE CASCADE,
    block_no       INTEGER NOT NULL,
    page_index     INTEGER NOT NULL,
    bbox_json      TEXT NOT NULL,
    crop_path      TEXT,
    expected_rows  INTEGER,
    first_order    INTEGER,
    last_order     INTEGER,
    status         TEXT NOT NULL DEFAULT 'pending',
    ai_attempts    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (lesson_id, block_no)
);
```

Tạo chỉ mục trên `lesson_id`.

### 13.2 Liên kết từ với block

Thêm `lesson_word.source_block_id` nullable, FK tới `import_block(id)` với
`ON DELETE SET NULL`. `VocabRow` nhận trường mặc định
`source_block_id: int | None = None`.

Lược đồ cũ có `UNIQUE (lesson_id, word)`, mâu thuẫn với yêu cầu giữ một từ xuất
hiện thật ở hai block khác nhau. Migration bậc 3 dựng lại `lesson_word` mà không
có UNIQUE này, giữ nguyên toàn bộ `id`, dữ liệu và `progress.source_lw_id`, rồi
tạo chỉ mục không-unique `(lesson_id, word)`. Test migration phải chứng minh một
từ lặp ở hai block được lưu thành hai dòng và liên kết tiến độ cũ không bị mất.

### 13.3 Quan hệ với đặc tả crop cũ

Đặc tả `2026-07-29-persisted-vocab-crops-design.md` chưa được triển khai và bị
thiết kế này thay thế. Không thêm `lesson.preview_path`; preview được dựng từ các
crop `import_block`, vừa chính xác hơn vừa hỗ trợ nhiều khối.

## 14. API và ranh giới module

### 14.1 Hợp đồng dữ liệu

Các kiểu dưới đây là dataclass đông cứng trong `data/models.py`. Tên trường là hợp
đồng giữa adapter, service và UI; tầng dưới không truyền dict tự do:

- `PageEvidence`: `pdf_page`, `page_kind`, `top_text`, `bottom_text`,
  `toc_text`, `printed_page`, `heading_lesson_no`, `heading_title`,
  `is_toc_candidate`, `layout_fingerprint`. `toc_text` chỉ có dữ liệu với trang
  mục lục được OCR toàn trang; các trang khác dùng `None`.
  `layout_fingerprint` là hash của hình học OCR dải đầu trang sau khi lượng tử
  hóa, không chứa nội dung chữ và dùng để nhận bố cục mở bài lặp lại.
- `BoundaryEvidence`: `source`, `page_index`, `lesson_no`, `title`,
  `confidence`, `detail`.
- `BoundaryIssue`: `code`, `severity`, `lesson_no`, `page_index`, `message`.
- `BoundaryReport`: `valid`, `issues`, `missing_lesson_nos`.
- `SplitResult`: `boundaries`, `evidence`, `report`, `needs_review`.
- `VocabBlock`: `id`, `lesson_id`, `block_no`, `page_index`, `bbox`,
  `crop_path`, `expected_rows`, `first_order`, `last_order`, `status`,
  `ai_attempts`. `id` là `None` trước khi manifest được lưu.
- `BlockCoverage`: `block_id`, `expected_rows`, `local_rows`, `ai_rows`,
  `final_rows`, `missing_orders`, `issues`, `passed`.
- `ExtractionResult`: `rows`, `coverage`, `blocks`, `ai_attempts`, `complete`.

Các tập hợp trong dataclass dùng tuple. `bbox` dùng tọa độ PDF
`(x0, y0, x1, y1)`; khi lưu SQLite mới mã hóa thành `bbox_json`. `severity` chỉ
có `warning` hoặc `error`; còn bất kỳ `error` nào thì `valid=False`.

### 14.2 Interface

Các interface dự kiến:

- `PdfSource.page_census() -> list[PageEvidence]`
- `PdfSource.boundary_contact_sheet(evidence) -> bytes`
- `Splitter.propose(summaries, evidence, ai_client=None, evidence_image=None) -> SplitResult`
- `Splitter.validate(boundaries, evidence) -> BoundaryReport`
- `VocabExtractor.locate_blocks(pdf, lesson) -> list[VocabBlock]`
- `VocabExtractor.extract_blocks(pdf, blocks, ai_client=None) -> ExtractionResult`
- `AiClient.split_lessons_from_image(image_bytes, evidence_text, issue_context=None) -> list[dict]`
- `AiClient.extract_vocab_from_image(image_bytes, issue_context=None) -> list[dict]`
- `UserDb.replace_import_blocks(lesson_id, blocks) -> None`
- `UserDb.update_import_block(...) -> None`
- `UserDb.replace_vocab_block(block_id, rows) -> None`

Giữ wrapper `Splitter.split()` trong giai đoạn chuyển tiếp để test và người gọi
cũ không vỡ đột ngột; importer mới dùng `propose()`.

## 15. Kiểm thử

### 15.1 Unit

- Trang native, scan và mixed.
- OCR mục lục có cột lệch.
- AI trả thiếu bài, trùng bài, sai thứ tự, ngoài phạm vi.
- Mục lục và trang mở bài đồng thuận/mâu thuẫn.
- Nhiều block trên một trang và block không liền nhau.
- False positive khi `生词` chỉ nằm trong câu.
- STT đứt đoạn và expected row mismatch.
- Resume sau 429 không gọi lại block đã đạt.
- Giới hạn ba lượt AI/bài.

### 15.2 Fixture

Tạo fixture tổng hợp mô phỏng nhiều bố cục, không dùng tên Boya/HSK trong logic.
Không commit trang sách có bản quyền.

### 15.3 Integration thực tế

Các PDF thật là tài nguyên local tùy chọn:

- Boya: bảo toàn kết quả hiện có.
- HSK mới: engine độc lập phải đề xuất đủ 15 bài hoặc dừng với báo cáo chính xác
  số bài thiếu; không được trả 8 bài với confidence cao.

Metadata thủ công có thể lưu số bài/start page mong đợi; không lưu ảnh/PDF vào Git.

## 16. Tiêu chí nghiệm thu

1. Không còn nhánh Boya preset trong quyết định split mặc định.
2. HSK mới không thể đi tiếp với chuỗi 1, 2, 3, 4, 8, 12, 13, 14.
3. Màn ranh giới cho thêm/xóa/sắp xếp bài và chặn khoảng không hợp lệ.
4. Locator phát hiện tất cả block trong fixture nhiều khối.
5. Mỗi bài có coverage report theo block.
6. 429 dừng an toàn và resume đúng checkpoint.
7. Không vượt quá ba lượt AI cho một bài.
8. Dữ liệu HSK hiện có trong `user.sqlite` không bị thay đổi trong triển khai/QA.
9. Toàn bộ test cũ tiếp tục xanh.

## 17. Trình tự triển khai

Để giảm rủi ro, chia thành ba lát cắt nhưng cùng một thiết kế:

1. Boundary evidence + validator + màn sửa ranh giới.
2. Block manifest + locator đa khối + migration checkpoint.
3. Hybrid extraction + targeted AI + coverage/resume.

Mỗi lát cắt có TDD, QA riêng và chỉ sang lát tiếp theo khi lát trước xanh.
