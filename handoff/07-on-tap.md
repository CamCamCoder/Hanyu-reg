# 07 — màn hình Ôn tập, kèm tách `ui/theme.py`

Chạy **sau** phiên 06b. Nếu 06b chưa xong thì dừng lại, lịch ôn sẽ sai ngay từ lần
bấm Quên đầu tiên.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Phiên này giống phiên 05: không có bảng đáp án vì giao diện không kiểm được bằng
pytest. Tiêu chí xong ở mục "Nghiệm thu" cuối tệp handoff/07-on-tap.md, kiểm bằng
mắt.

Cần tạo đúng ba tệp:
  hanzi_app/ui/theme.py                bảng màu 6.1 và phông 6.2, chuyển từ tianzige
  hanzi_app/ui/screen_review.py        màn hình Ôn tập
  hanzi_app/ui/widgets/review_card.py  thẻ ôn tập, mặt trước và mặt sau

Và sửa đúng sáu tệp đã có, không sửa tệp nào khác:
  hanzi_app/data/userdb.py             THÊM ĐÚNG MỘT phương thức, xem phần 4
  hanzi_app/ui/widgets/tianzige.py     bỏ PALETTE và phần phông, import từ theme
  hanzi_app/ui/widgets/decomp_tree.py  đổi lệnh import
  hanzi_app/ui/main_window.py          đổi import, gắn màn hình Ôn tập vào ô số 2,
                                       nối hai số ở chân thanh điều hướng
  hanzi_app/ui/screen_lookup.py        đổi import, thêm nút "Thêm vào ôn tập"
  hanzi_app/main.py                    đổi import, bơm thêm UserDb và scheduler

Việc sửa sáu tệp trên là ngoại lệ được phép của phiên này, đã hẹn trước.
Ngoài đúng một phương thức nêu ở phần 4, KHÔNG sửa gì khác trong data/, và không
sửa gì trong service/. Tầng ui chỉ được GỌI xuống.

=== PHẦN 1. Tách theme.py, làm trước ===

PALETTE và phần nạp phông đang nằm trong hanzi_app/ui/widgets/tianzige.py, còn QSS
nằm trong hanzi_app/main.py. Bốn tệp đang import từ tianzige:

  main.py          PALETTE, load_fonts
  main_window.py   PALETTE, han_font, mono_font, ui_font
  screen_lookup.py (nhiều tên)
  decomp_tree.py   (nhiều tên)

Chuyển sang hanzi_app/ui/theme.py: PALETTE, FONT_DIR, REQUESTED, load_fonts,
han_font, mono_font, ui_font. Chuyển NGUYÊN VĂN, không đổi giá trị màu, không đổi
tên khoá, không đổi cỡ chữ. tianzige.py giữ lại đúng lớp TianZiGe và import những
gì nó cần từ theme.

Lý do tách: sau phiên này có ba màn hình dùng chung bảng màu, để nguyên thì hai màn
hình mới phải import màu từ một module widget, sai tầng.

Chạy pytest sau bước này TRƯỚC khi viết tiếp. Không test nào được đỏ.

=== PHẦN 2. Nút "Thêm vào ôn tập" trên màn hình Tra cứu ===

QT-04 bước 2 nói từ vào danh sách ôn tập bằng cách chọn một bài trong sách. Nhưng
luồng nhập sách chưa làm, nên nếu chỉ cài đúng đặc tả thì màn hình Ôn tập sẽ rỗng
và không dùng được cho tới khi xong toàn bộ luồng PDF.

Lược đồ đã lường trước: cột progress.source_lw_id CỐ Ý cho phép NULL, chú thích
ngay trong migrate.py ghi rõ "từ thêm thẳng từ màn hình Tra cứu không đi qua quyển
sách nào".

Thêm vào ScreenLookup._word_card, ngay sau hàng chip: một QPushButton "Thêm vào ôn
tập". Bấm vào thì gọi

    scheduler.initial(date.today())          -> ReviewOutcome
    user_db.upsert_progress(word, outcome, None)

rồi đổi nút thành nhãn tĩnh "đã có trong danh sách ôn tập". Nếu detail.status khác
None thì hiện nhãn đó ngay từ đầu, không hiện nút.

Đây là lệch có ý thức với QT-04, ghi vào BAN-GIAO.md mục 2 sau khi xong.

=== PHẦN 3. Màn hình Ôn tập ===

Luồng ở QT-04 bước 3 tới 6:

  1. user_db.due_words(date.today()) lấy danh sách từ tới hạn.
  2. Danh sách rỗng thì hiện trạng thái rỗng tử tế: "Hôm nay không có từ nào tới
     hạn ôn" cộng số từ đang theo dõi. KHÔNG để trắng màn hình.
  3. Mặt trước thẻ chỉ có chữ Hán cỡ lớn, dùng ô 田字格 cho từ một chữ, chữ trơn cỡ
     88px cho từ nhiều chữ. Một nút "Hiện đáp án".
  4. Mặt sau thêm pinyin, nghĩa tiếng Việt nếu có, nghĩa tiếng Anh nếu không, và ba
     nút Quên / Khó / Nhớ.
  5. Bấm một trong ba nút thì:
         before = user_db.get_progress(word)
         after  = scheduler.apply_review(before, grade, date.today())
         user_db.upsert_progress(word, after, None)
         user_db.log_review(word, grade, scheduler.GRADE_TO_Q[grade], before, after)
     rồi sang thẻ tiếp theo.
  6. Hết thẻ thì hiện tổng kết: đã ôn bao nhiêu từ trong phiên này.

Ánh xạ nút sang grade LẤY TỪ scheduler.GRADE_TO_Q, đã có sẵn {0: 2, 1: 3, 2: 5}
tương ứng Quên, Khó, Nhớ. TUYỆT ĐỐI không viết lại công thức SM-2 trong tầng giao
diện; Scheduler đã xong từ phiên 02 với 23 test xanh, chỉ gọi xuống.

Lấy nghĩa cho mặt sau bằng lookup.detail(word). Nếu detail.source khác None thì ưu
tiên nghĩa của sách, đúng tinh thần QT-04 bước 2; hiện tại luôn None nên trên thực
tế sẽ lấy nghĩa từ điển.

=== PHẦN 4. Hai số ở chân thanh điều hướng ===

main_window.py hiện ghi "Theo dõi: chưa có dữ liệu" và "Bộ thủ: chưa có dữ liệu".
Nối vào dữ liệu thật.

QT-04 bước 6 bắt buộc gọi hai con số bằng hai tên khác nhau ở MỌI màn hình:
  "đang theo dõi" = số dòng trong progress
  "đã thuộc"      = số dòng có status = 'known'
Đừng trộn hai số này, và đừng đặt tên chung chung như "số từ".

UserDb hiện KHÔNG có phương thức nào đếm hai số đó. due_words lọc theo due_date nên
không dùng được, learned_chars trả tập chữ chứ không phải số từ. Vì vậy phiên này
được phép thêm ĐÚNG MỘT phương thức vào hanzi_app/data/userdb.py, không hơn:

    def progress_counts(self) -> tuple[int, int]:
        """(đang theo dõi, đã thuộc) — số dòng progress, và số dòng status='known'.

        Hai con số của QT-04 bước 6. Đếm ở tầng data bằng một truy vấn, vì tầng ui
        không được phép mở kết nối cơ sở dữ liệu theo mục 13.1.
        """

Một truy vấn duy nhất, dùng SUM(status = 'known') cạnh COUNT(*), đừng chạy hai lần.
Thêm test cho nó vào tests/unit/test_userdb.py: kho rỗng trả (0, 0); sau khi chèn ba
dòng trong đó một dòng 'known' thì trả (3, 1).

Số bộ thủ thì KHÁC: nó cần đối chiếu learned_chars() với dict.sqlite, tức là bắc cầu
hai cơ sở dữ liệu. Việc đó KHÔNG thuộc phiên này. Để nguyên "Bộ thủ: chưa có dữ
liệu", nó không nằm trong tiêu chí nghiệm thu.

=== ĐIỂM DỄ SAI ===

- main.py hiện gọi MainWindow(lookup, decomposer). Cần thêm user_db và scheduler.
  Giữ thứ tự tham số cũ ở đầu để đọc diff dễ.
- user_db đã được dựng sẵn trong main.py rồi, đừng mở kết nối thứ hai. Mục 13.1 cấm
  tầng ui tự mở cơ sở dữ liệu.
- scheduler là module hàm chứ không phải lớp: initial(today), apply_review(before,
  grade, today), GRADE_TO_Q. Import module rồi gọi, đừng khởi tạo đối tượng.
- due_words trả danh sách chuỗi, không phải đối tượng. Muốn có nghĩa thì gọi tiếp
  lookup.detail().
- Đừng gọi lookup.detail() cho cả danh sách ngay lúc mở màn hình. Gọi từng thẻ khi
  tới lượt, nếu không mở màn hình với 100 từ tới hạn sẽ khựng.

Viết thẳng nội dung từng tệp, mỗi tệp một khối mã có ghi rõ đường dẫn. Với năm tệp
sửa thì chỉ ghi phần thay đổi kèm đủ ngữ cảnh để dán vào, đừng in lại cả tệp.

Xong thì chạy `pytest tests/unit -q` xác nhận không có test cũ nào đỏ, rồi chạy
`python -m hanzi_app.main` và tự đi hết bảy mục nghiệm thu, báo từng mục đạt hay
không đạt.
```

---

## Nghiệm thu

Không có pytest cho phần giao diện. Chạy `python -m hanzi_app.main` rồi kiểm bảy mục:

1. `pytest tests/unit -q` vẫn xanh và tăng thêm ít nhất 1 test của
   `progress_counts`, không test nào đỏ vì việc tách `theme.py`. Trước phiên này:
   161 passed, 1 skipped.
2. Màn hình Tra cứu trông y hệt trước khi tách theme: cùng màu, cùng phông, ô 田字格
   vẫn viền đỏ gạch với hai đường đứt.
3. Tra `认识`, trang chi tiết có nút "Thêm vào ôn tập". Bấm một lần thì nút đổi
   thành nhãn "đã có trong danh sách ôn tập".
4. Bấm mục 复 Ôn tập trên thanh trái: hiện thẻ với chữ 认识, không phải chỗ trống
   "Chưa làm ở phiên này".
5. Bấm "Hiện đáp án": hiện `rènshi` và nghĩa `quen biết, làm quen; nhận ra`, cộng ba
   nút Quên / Khó / Nhớ.
6. Bấm Nhớ: hết thẻ, hiện tổng kết. Quay lại Tra cứu rồi vào lại Ôn tập thì không
   còn thẻ nào tới hạn hôm nay.
7. Chân thanh điều hướng hiện "Đang theo dõi: 1" và "Đã thuộc: 0" chứ không phải
   "chưa có dữ liệu". Dòng "Bộ thủ" vẫn được phép để nguyên.

Kiểm thêm bằng SQL sau khi bấm Nhớ một lần, để chắc phiên 06b đã đúng:

```sql
SELECT word, status, interval_days, repetition, review_count FROM progress;
```

Kỳ vọng: `interval_days = 1`, `repetition = 1`, `review_count = 1`, `status =
'learning'`. Nếu `repetition` và `review_count` bằng nhau ở mọi lần thì chưa chắc
sai, nhưng bấm Quên một lần rồi xem lại: `repetition` phải về 0 còn `review_count`
phải tăng lên 2.

---

## Sau khi xong

Cập nhật bảng tiến độ trong `CLAUDE.md`. Ghi vào `BAN-GIAO.md` mục 2 quyết định
thêm nút "Thêm vào ôn tập" là lệch có ý thức với QT-04 bước 2, kèm lý do.

Xong phiên này là app dùng học hàng ngày được, chưa cần nhập sách.
