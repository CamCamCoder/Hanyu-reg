# 06 — userdb

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Cần tạo đúng ba tệp:
  hanzi_app/data/migrate.py         kịch bản chuyển lược đồ theo schema_version
  hanzi_app/data/userdb.py          THAY THẾ bản tối thiểu của phiên 05
  tests/unit/test_userdb.py

Phiên 05 đã tạo một bản userdb.py giả với đúng hai phương thức word_source và
get_progress, cả hai trả None, kèm ghi chú rằng phiên userdb sẽ thay thế. Phiên này
viết lại hẳn tệp đó, không phải sửa thêm vào. Đây là ngoại lệ được phép, đã hẹn
trước trong packet 05.

Không sửa bất kỳ tệp nào khác. main.py hiện đang dựng UserDb với một tham số đường
dẫn; giữ nguyên chữ ký __init__(self, path: str) để nó không gãy.

Lược đồ đầy đủ ở mục 5.3 của dac-ta-ung-dung-v0.5.md, chín bảng cộng năm chỉ mục.
Chữ ký phương thức ở mục 13.4. Bảng hành vi bắt buộc ở cuối tệp này.

Năm điểm rất dễ sai:

- PRAGMA foreign_keys = ON phải bật NGAY sau khi mở kết nối, trên chính kết nối
  đó. SQLite mặc định TẮT khoá ngoại. Thiếu dòng này thì mọi ON DELETE CASCADE
  trong lược đồ chỉ là trang trí, xoá sách sẽ để lại bài học mồ côi, và không test
  nào báo đỏ trừ khi bạn viết test cho đúng chuyện đó. Kèm PRAGMA journal_mode =
  WAL để luồng nền nhập PDF ghi song song được với giao diện đọc.

- upsert_progress KHÔNG được ghi đè source_lw_id khi dòng đã tồn tại. QT-04 bước 2
  nói rõ: từ đã có trong progress thì giữ nguyên tiến độ cũ và không đổi
  source_lw_id, để mặt sau thẻ luôn hiện nghĩa của quyển sách mà người dùng gặp từ
  đó lần đầu. Dùng COALESCE trên cột cũ chứ đừng ghi thẳng giá trị mới.

- source_lw_id được phép NULL. Ứng dụng sẽ thêm từ vào ôn tập trực tiếp từ màn hình
  Tra cứu, không qua sách. Đừng đặt NOT NULL cho cột đó dù lược đồ gợi ý quan hệ
  với lesson_word.

- replace_lessons và replace_vocab là thay thế TRỌN GÓI trong MỘT giao dịch: xoá
  hết dòng cũ của book_id hoặc lesson_id đó rồi chèn dòng mới. Không phải chèn
  từng dòng, không phải upsert. Nhập lại một quyển phải không bao giờ để lại
  trạng thái nửa vời.

- migrate.upgrade() chạy bên trong UserDb.__init__ TRƯỚC khi hàm khởi tạo trả về.
  Bảng schema_version phải có ngay từ bản đầu tiên; thiếu nó thì lời hứa ở mục 4.3
  về nâng cấp từ điển và ứng dụng mà không mất dữ liệu học tập không thực hiện
  được. Bản này là version 1, nhưng hàm upgrade phải viết theo kiểu chạy tuần tự
  từng bậc để bản sau chỉ cần thêm một nhánh.

Không import bất cứ thứ gì của Qt vào data/. Không gọi sang service/.

Test dựng user.sqlite tạm trong tmp_path của pytest, không đụng tệp thật, không
dùng cơ sở dữ liệu trong bộ nhớ vì cần kiểm cả hành vi mở lại tệp.

Viết test trước, chạy pytest, rồi báo kết quả thật kèm tổng số test của cả kho.
```

---

## Bảng hành vi bắt buộc

Không có bảng số như các phiên trước, nhưng mười ba hành vi dưới đây là bắt buộc và
mỗi dòng phải có ít nhất một test. Đây là bảng đáp án của phiên này.

| # | Hành vi | Kỳ vọng |
|---|---|---|
| 1 | Mở `UserDb` trên đường dẫn chưa tồn tại | Tạo tệp, tạo đủ 9 bảng và 5 chỉ mục |
| 2 | Sau khi khởi tạo | `schema_version` có đúng 1 dòng, `version = 1` |
| 3 | Mở lại `UserDb` trên tệp đã có | Không tạo trùng bảng, `schema_version` vẫn đúng 1 dòng |
| 4 | `PRAGMA foreign_keys` sau khi mở | Trả về `1`, không phải `0` |
| 5 | Chèn `lesson` với `book_id` không tồn tại | Ném `sqlite3.IntegrityError` |
| 6 | Xoá một `book` đã có bài học | Các dòng `lesson` của nó biến mất theo, cascade thật |
| 7 | `find_book_by_hash` với hash chưa có | Trả `None`, không ném lỗi |
| 8 | `add_book` hai lần cùng `file_hash` | Lần hai ném `IntegrityError`, cột đó `UNIQUE` |
| 9 | `upsert_progress` lần đầu, `source_lw_id = 7` | Tạo dòng mới, `source_lw_id` bằng 7 |
| 10 | `upsert_progress` lần hai cùng từ, `source_lw_id = 99` | Tiến độ cập nhật, `source_lw_id` VẪN bằng 7 |
| 11 | `upsert_progress` với `source_lw_id = None` trên từ mới | Tạo dòng, `source_lw_id` là `NULL`, không ném lỗi |
| 12 | `due_words(hôm nay)` | Chỉ trả từ có `due_date <= hôm nay`, tôn trọng `limit` |
| 13 | `learned_chars()` với progress chứa `认识` và `你好` | Trả `{认, 识, 你, 好}`, tách theo chữ chứ không theo từ |

Ba hành vi nữa nên có test nhưng không bắt buộc nếu hết thời gian:

| # | Hành vi | Kỳ vọng |
|---|---|---|
| 14 | `replace_lessons` gọi lần hai với danh sách ngắn hơn | Số dòng bằng đúng danh sách mới, không còn dòng thừa |
| 15 | Ném lỗi giữa chừng trong `transaction()` | Toàn bộ thay đổi bị huỷ, không còn dòng nào nửa vời |
| 16 | `word_source` với từ xuất hiện ở hai sách | Trả lần gặp đầu tiên, không phải dòng ngẫu nhiên |

---

## Vì sao dòng 4 và 6 quan trọng hơn vẻ ngoài

Đây là hai dòng dễ bị bỏ qua nhất và cũng là hai dòng đắt nhất nếu sai.

SQLite tắt khoá ngoại theo mặc định, và nó **không báo lỗi** khi bạn khai báo
`REFERENCES` trong `CREATE TABLE` mà quên bật pragma. Lược đồ trông đúng, test chèn
dữ liệu hợp lệ vẫn xanh, và sai sót chỉ lộ ra nhiều tháng sau dưới dạng dữ liệu rác:
bài học trỏ tới quyển sách đã xoá, từ mới trỏ tới bài học không còn.

Pragma này còn đặt theo từng kết nối chứ không lưu vào tệp. Mở kết nối mới mà quên
bật là mất, nên nó phải nằm trong `__init__` chứ không phải trong kịch bản tạo bảng.

---

## Sau khi phiên này xong

Cập nhật bảng tiến độ trong `CLAUDE.md`, rồi sang phiên 07 là màn hình Ôn tập. Phiên
07 sẽ gộp luôn việc tách `ui/theme.py`, vì nó thuộc tầng giao diện.
