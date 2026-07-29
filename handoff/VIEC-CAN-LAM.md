# Việc cần làm — Ôn tập và nhập sách

Viết sau phiên 05, khi mục tiêu đã đổi từ "đồ án" sang "app dùng được hàng ngày".
Thứ tự dưới đây tối ưu cho mục tiêu đó, không phải cho việc trình bày báo cáo.

---

## Chỗ tắc phải quyết trước khi viết dòng mã nào

**QT-04 bước 2 nói từ vào danh sách ôn tập bằng cách chọn một bài trong sách.**
Mà nhập sách thì chưa làm, và nó là phần lớn nhất còn lại của dự án. Nghĩa là nếu
làm Ôn tập đúng như đặc tả, xong xuôi rồi mở lên sẽ thấy **màn hình rỗng, không có
từ nào để ôn**, và phải chờ xong toàn bộ luồng PDF mới dùng được.

Lược đồ cho phép lách: `progress.source_lw_id` là `NULL` được, ràng buộc ghi rõ
`ON DELETE SET NULL`. Nên một dòng `progress` không bắt buộc phải sinh ra từ
`lesson_word`.

**Quyết định đề nghị:** thêm nút "Thêm vào ôn tập" ngay trên màn hình Tra cứu, tạo
dòng `progress` với `source_lw_id = NULL`. Mặt sau thẻ khi đó lấy nghĩa từ
`dict.sqlite` thay vì từ sách. Ba dòng mã, và nó là khác biệt giữa app dùng được
ngay hôm nay với app phải chờ thêm nhiều tuần.

Việc này nằm ngoài đặc tả nên phải ghi vào `BAN-GIAO.md` mục 2 là quyết định có ý
thức, đừng để lẫn thành lỗi.

---

## Giai đoạn A — Ôn tập

### A0. Tách `ui/theme.py` — ĐÃ CHUYỂN SANG PHIÊN 07

Bảng màu 6.1 và tên phông 6.2 đang nằm trong `ui/widgets/tianzige.py`, QSS nằm
trong `main.py`. Giai đoạn này thêm hai màn hình nữa, để nguyên là chúng phải
import màu từ một module widget.

Không gộp vào A1 như bản đầu của tệp này: `theme.py` ở tầng `ui/` còn A1 ở tầng
`data/`, gộp vào là vi phạm quy tắc phân tầng mục 13.1. Đã đưa vào phần 1 của
packet 07, xem `handoff/07-on-tap.md`.

Soát trên mã thật: bốn tệp đang import từ `tianzige` là `main.py`, `main_window.py`,
`screen_lookup.py`, `decomp_tree.py`.

### A1. Phiên `userdb` — XONG, 35 test xanh, tổng 154

Kèm phiên bảo trì **06b chưa làm**: tách `repetition` khỏi `review_count`, xem
`handoff/06b-repetition.md`. **Chặn phiên 07.**

Nội dung gốc của A1 giữ lại bên dưới để tham khảo.

Tệp cần tạo:

    hanzi_app/data/migrate.py
    hanzi_app/data/userdb.py          (THAY THẾ bản tối thiểu của phiên 05)
    tests/unit/test_userdb.py
    hanzi_app/ui/theme.py             (A0, gộp vào đây)

Lược đồ ở mục 5.3, chín bảng. Chữ ký phương thức ở mục 13.4.

Bốn điểm dễ sai, ghi thẳng vào prompt:

- `PRAGMA foreign_keys = ON` và `PRAGMA journal_mode = WAL` phải bật ngay khi mở
  kết nối. SQLite mặc định TẮT khoá ngoại, thiếu dòng này thì mọi `ON DELETE
  CASCADE` trong lược đồ chỉ là trang trí và sẽ im lặng không chạy.
- `userdb.py` của phiên 05 là bản giả hai phương thức trả `None`. Phiên này thay
  hẳn, không phải sửa thêm. Đây là ngoại lệ được phép, ghi rõ trong prompt kẻo
  agent từ chối vì quy tắc "không sửa tệp phiên trước".
- `migrate.upgrade()` chạy trong `UserDb.__init__` trước khi trả về. Bảng
  `schema_version` phải có ngay từ bản đầu, nếu không thì lời hứa ở mục 4.3 về
  nâng cấp mà không mất dữ liệu học tập không thực hiện được.
- `replace_lessons` và `replace_vocab` là thay thế trọn gói trong một giao dịch,
  không phải chèn từng dòng.

Test chạy trên `user.sqlite` tạm trong `tmp_path`, không đụng tệp thật.

### A2. Phiên màn hình Ôn tập

Tệp cần tạo:

    hanzi_app/ui/screen_review.py
    hanzi_app/ui/widgets/review_card.py

Cộng sửa `screen_lookup.py` để thêm nút "Thêm vào ôn tập", và sửa `main.py` để
bơm `Scheduler` vào.

Luồng ở QT-04 bước 3 tới 6. Ba nút Quên / Khó / Nhớ ánh xạ sang q = 2 / 3 / 5.
Bộ `Scheduler` đã xong từ phiên 02, 23 test xanh — **không được viết lại công thức
SM-2 trong tầng giao diện**, chỉ gọi xuống.

Hai con số phải gọi bằng hai tên khác nhau ở mọi chỗ, theo QT-04 bước 6:
"đang theo dõi" là số dòng trong `progress`, "đã thuộc" là số dòng có
`status = 'known'`. Chân thanh điều hướng hiện đang ghi "chưa có dữ liệu", nối vào
đây là hết.

Sau phiên này app đã dùng học hàng ngày được, chưa cần sách.

---

## Giai đoạn B — Nhập sách PDF

Phần lớn nhất và rủi ro nhất của cả dự án. Đừng bắt đầu viết mã trước khi xong B0.

### B0. Xác nhận `bounds_boya.json` — 15 phút, VIỆC CỦA NGƯỜI, không giao agent

`BAN-GIAO.md` mục 4 đã ghi và vẫn còn nguyên: 29 mốc trang tìm được bằng tỷ lệ mực
mới chỉ là **ứng viên**. Phải mở PDF, xác nhận từng trang, ghi số bài thật.

    36, 48, 54, 61, 67, 73, 81, 88, 96, 103, 110, 117, 124, 131, 138,
    144, 151, 158, 166, 173, 179, 185, 192, 199, 207, 214, 220, 227, 234

Bắt buộc làm **trước** khi viết `splitter`. Nếu không sẽ vô thức chỉnh thuật toán
cho vừa đáp án, và cả EV-01 lẫn EV-09 mất nghĩa.

**Đây là việc nên làm song song khi đang chờ, vì nó chặn toàn bộ giai đoạn B và chỉ
người có tệp PDF mới làm được.**

Định dạng đề nghị:

```json
{
  "book": "Boya sơ cấp I",
  "page_count": 270,
  "lessons": [
    {"index_no": 1, "page_start": 36, "title": "…", "kind": "lesson"},
    {"index_no": 2, "page_start": 48, "title": "…", "kind": "lesson"}
  ]
}
```

`kind` là `review` với các bài ôn tập; QT-02 bước 3 dùng `index_no` âm cho mục ôn tập.

### B1. Phiên `pdfsource` + `ocr`

    hanzi_app/adapter/pdfsource.py
    hanzi_app/adapter/ocr.py
    tests/unit/test_pdfsource.py

Chữ ký ở mục 13.8. Điểm cốt lõi: `spans()` che hoàn toàn khác biệt giữa trang chữ
và trang ảnh, tự chạy OCR khi cần. Nhờ vậy `splitter` và `vocab` chỉ làm việc với
danh sách `TextSpan` và kiểm thử được bằng dữ liệu tự tạo, không cần PDF thật.

Cần cài PyMuPDF, đã để sẵn dạng chú thích trong `requirements.txt`.

Đặc tả ghi PaddleOCR nhưng số đo trong `BAN-GIAO` mục 3 là của Tesseract với
`chi_sim+vie`. Chốt lấy một cái rồi sửa tài liệu cho khớp.

### B2. Phiên `splitter`

    hanzi_app/service/splitter.py
    tests/unit/test_splitter.py

Thang năm nấc ở QT-02. Với sách của bạn:

| Nấc | Cách | Trạng thái đo thật |
|---|---|---|
| 1 | outline nhúng | chết, outline chỉ có 1 mục |
| 2 | mục lục in | chết, không có ký tự văn bản nào |
| 3 | mô hình ngôn ngữ | **phương án tự động duy nhất còn lại** |
| 4 | regex `第X课` | chết, 0 kết quả trên cả 270 trang |
| 5 | nhập tay | luôn dùng được |

`Splitter.accepts()` là hàm tĩnh với bốn điều kiện ở QT-02 bước 3 — kiểm thử được
trực tiếp bằng dữ liệu dựng tay, viết test cho nó trước.

Nấc 3 gọi API, cần khoá. Đây là phiên đầu tiên trong cả dự án cần khoá API.

### B3. Phiên `vocab`

    hanzi_app/service/vocab.py
    tests/unit/test_vocab.py

QT-03. Hai điều đã đo được và phải đưa vào prompt:

- Bảng 生词表 có **bảy cột**, không phải bốn hay năm:
  `STT | Chữ Hán | Pinyin | Từ loại | Âm Hán-Việt | Nghĩa Anh | Nghĩa Việt`
- **Ngưỡng khe không tách được cột.** Khe trong cùng một cột có phân vị 90 là 78 px,
  khe giữa hai cột chỉ 28–40 px. Phải dùng biểu đồ chiếu đứng toàn khối.

Fixture đã có sẵn: `spans_1col.json`, dựng từ trang PDF 42, 132 span có toạ độ.

### B4. Phiên `importer` + màn hình Sách

    hanzi_app/service/importer.py
    hanzi_app/ui/screen_books.py
    hanzi_app/ui/dialog_import.py

Chạy trong luồng nền. Số đo thời gian ở `BAN-GIAO` mục 3: luồng ba tầng cả quyển
mất 7,2 phút, nên bắt buộc có thanh tiến trình và nút huỷ.

---

## Thứ tự đề nghị

| | Việc | Ai làm | Chặn gì |
|---|---|---|---|
| ~~x~~ | ~~A1 `userdb`~~ | XONG, 154 test | — |
| 1 | **06b tách `repetition`** | phiên agent, ngắn | 07 |
| 2 | **07 Ôn tập + `theme.py`** | phiên agent | — |
| 2b | `git init` + `.gitignore` | người, 5 phút | không gì, nên làm ngay |
| 3 | B0 xác nhận `bounds_boya.json` | người, 15 phút | cả giai đoạn B |
| 4 | B1 `pdfsource` + `ocr` | phiên agent | B2, B3 |
| 5 | B2 `splitter` | phiên agent | B4 |
| 6 | B3 `vocab` | phiên agent | B4 |
| 7 | B4 `importer` + màn hình Sách | phiên agent | — |

Xong bước 2 là app dùng học hàng ngày được. Bước 4 trở đi là để nhập giáo trình thật.

B0 và `git init` là việc tay, làm xen kẽ lúc chờ phiên agent chạy.

---

## Món nợ song song, không chặn gì

- **Đóng gói ba phông.** Máy đang dùng tình cờ có Noto Serif SC, máy khác thì không.
- **Bỏ `skip`** ở `test_tim_theo_nghia_tieng_viet_tren_dict_that`, giờ đã có dữ liệu
  tiếng Việt thật. Đây là dòng `1 skipped` duy nhất còn lại.

- **Chốt `VocabRow` với bảng `lesson_word`** trước phiên B3. Đã soát mã và xác nhận
  lệch cả hai chiều: bảng có `hanviet_src` mà dataclass không có, dataclass có
  `review_reason` mà bảng không có.
- **Nghĩa tiếng Việt HSK 4-6**, 4400 từ còn lại. Chỉ nối thêm dòng vào CSV.
- **Gộp CC-CEDICT**, 114.181 từ thay cho 4.995 từ HSK. Cần quyết định về giấy phép
  CC BY-SA 4.0 trước. Đây là thứ làm app tra được 你好, 您好, 晚安, 手, 眼, 头 —
  toàn bộ từ vựng đời thường không nằm trong đề thi HSK.
