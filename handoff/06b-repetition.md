# 06b — bảo trì, tách `repetition` khỏi `review_count`

Phải chạy **trước** phiên 07, vì màn hình Ôn tập gọi thẳng vào đường này.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Đây là phiên bảo trì ngắn, KHÔNG phải phiên 07. Chỉ sửa hai tệp:
  hanzi_app/data/migrate.py
  hanzi_app/data/userdb.py
Được phép thêm test mới vào tests/unit/test_userdb.py.

VẤN ĐỀ. Phiên 06 ánh xạ ReviewOutcome.repetition sang cột progress.review_count vì
bảng progress ở mục 5.3 không có cột repetition. Ánh xạ đó sai, hai con số khác
nghĩa:

  repetition   = bậc lặp đúng LIÊN TIẾP. scheduler.py dòng 52 đặt về 0 khi bấm
                 Quên, dòng 58 tăng 1 khi bấm Nhớ.
  review_count = TỔNG số lần ôn. QT-04 bước 5: mỗi lần đánh giá ghi một dòng vào
                 review_log VÀ tăng review_count. Chỉ tăng, không bao giờ giảm.

Ba chỗ sai cụ thể trong mã hiện tại:

  1. get_progress trả repetition=row["review_count"], kèm chú thích "cùng một con
     số" — giả định đó sai.
  2. upsert_progress đặt review_count = excluded.review_count với giá trị buộc từ
     outcome.repetition, nên một lần bấm Quên xoá sạch tổng số lần ôn.
  3. log_review KHÔNG tăng review_count chút nào, trái với QT-04 bước 5.

Hậu quả khi màn hình Ôn tập chạy: sau một lần quên, scheduler nhận repetition bằng
tổng số lần ôn nên trượt cả hai nhánh `repetition == 1` và `== 2`, rơi thẳng xuống
interval × ease, giãn lịch cho đúng những từ người dùng đang quên.

CẦN LÀM.

1. Thêm bậc 2 vào _CAC_BAC trong migrate.py, giữ đúng kiểu chạy tuần tự và giao
   dịch riêng từng bậc đã có:
       ALTER TABLE progress ADD COLUMN repetition INTEGER NOT NULL DEFAULT 0
   Bậc 2 phải chạy được trên user.sqlite ĐANG TỒN TẠI ở gốc kho, tệp đó đã tạo
   bằng lược đồ bậc 1 và có dữ liệu. Không dựng lại bảng từ đầu, không làm mất dữ
   liệu. Giữ nguyên quy ước schema_version đúng một dòng.

2. get_progress đọc repetition từ cột mới.

3. upsert_progress ghi repetition vào cột mới, KHÔNG đụng review_count. Giữ nguyên
   COALESCE cho source_lw_id, chỗ đó đang đúng.

4. log_review tăng review_count đúng 1 mỗi lần gọi, trong cùng giao dịch với dòng
   review_log.

Test bắt buộc thêm:

  a. Mở UserDb trên tệp đã có ở bậc 1 với sẵn một dòng progress: nâng lên bậc 2
     thành công, dòng cũ vẫn còn, cột repetition mới bằng 0.
  b. upsert_progress với repetition=3 rồi get_progress: trả về đúng 3.
  c. Đã có review_count=5, gọi upsert_progress với repetition=0: review_count VẪN
     bằng 5.
  d. Gọi log_review ba lần trên cùng một từ: review_count bằng 3.
  e. schema_version sau khi nâng cấp: đúng một dòng, version = 2.

Chạy pytest tests/unit -q và báo kết quả thật. Trước phiên này: 154 passed,
1 skipped.
```

---

## Bằng chứng, để khỏi tra lại

`findstr /n "repetition" hanzi_app\service\scheduler.py`:

```
33:        repetition=0,
48:    repetition = before.repetition
52:        repetition = 0
58:        repetition += 1
59:        if repetition == 1:
61:        elif repetition == 2:
79:        repetition=repetition,
```

Dòng 52 reset về 0 ở nhánh Quên, dòng 58 tăng 1 ở nhánh Nhớ. Test tương ứng:
`test_scheduler.py` dòng 105 `assert out.repetition == 0`, dòng 121
`assert out.repetition == 3` sau khi vào `repetition=2`.

Tức `repetition` reset khi quên, đúng SM-2 gốc. `review_count` thì không bao giờ
giảm. Hai con số tách nhau ngay lần bấm Quên đầu tiên.

## Sau khi xong

`CLAUDE.md` dòng 06b thành `xong`, phiên tiếp theo là 07.
