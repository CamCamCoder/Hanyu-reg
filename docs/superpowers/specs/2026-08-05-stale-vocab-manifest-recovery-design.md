# Stale Vocabulary Manifest Recovery Design

## Problem

Log thật dừng tại `Bài 3 · block 1 · thiếu STT 0`. Truy vấn chỉ đọc cho thấy
manifest Bài 3 có block `first_order=0`, phạm vi không khớp `expected_rows`, và
một block lưu nhiều dòng trùng STT. Locator hiện coi cả dãy hợp lệ khi chỉ một
cặp số liên tiếp, chấp nhận số 0, rồi resume tái dùng metadata đã lưu.

## Locator Rules

- Chỉ số nguyên từ 1 trở lên mới là ứng viên STT.
- Một dãy có STT chỉ khi có ít nhất hai số khác nhau và mọi cặp kề nhau đều
  tăng đúng 1.
- Chỉ lưu `first_order` và `last_order` cho dãy đạt quy tắc trên.
- `expected_rows` lấy từ dãy STT nghiêm ngặt; nếu không có thì chỉ lấy từ bằng
  chứng hàng/cột đủ mạnh như hiện tại.

## Stale Manifest Detection

Một block tự động là cũ/hỏng khi có một trong các dấu hiệu:

- `first_order` hoặc `last_order` nhỏ hơn 1;
- chỉ một trong hai đầu phạm vi có giá trị;
- đầu cuối đảo ngược;
- có đủ đầu cuối và `expected_rows` nhưng độ dài phạm vi không khớp.

Block trạng thái `manual` luôn được giữ nguyên và không tham gia tự sửa.

## Safe Recovery

Khi resume gặp block cũ/hỏng, locator chạy lại trong đúng ranh giới bài. Mỗi
block lỗi chỉ được ghép với một block mới trên cùng trang khi đó là cặp có IoU
lớn nhất, duy nhất và đạt tối thiểu 0.5. Nếu không ghép chắc chắn, importer giữ
dữ liệu hiện tại, đánh dấu bài `incomplete` và báo manifest cần duyệt; không xóa
hay đoán metadata.

Với cặp ghép an toàn, một transaction sẽ:

- giữ nguyên `import_block.id` và `ai_attempts`;
- cập nhật trang, bbox, crop, `expected_rows`, `first_order`, `last_order`;
- đặt trạng thái về `pending`;
- xóa riêng các `lesson_word` tự động gắn với block lỗi;
- không đụng block hợp lệ hoặc block `manual`.

Crop mới được ghi nguyên tử trước khi transaction cập nhật đường dẫn. Tổng
`ai_attempts` của bài không giảm, nên recovery không làm mới ngân sách AI.

## Coverage Rules

- Nhiều dòng có cùng `order_no` khác `None` trong một block sinh
  `duplicate_orders` và là lỗi chặn.
- `expected_row_mismatch` là lỗi chặn cho cả thiếu lẫn thừa dòng.
- Khử trùng exact key hiện tại vẫn giữ nguyên; hệ thống không tự chọn một trong
  hai từ khác nhau cùng STT.

## Scope And Safety

- Sửa `service/vocab.py`, `service/importer.py`, `data/userdb.py` và unit test
  liên quan.
- TDD chỉ dùng spans/PDF adapter/SQLite tạm; không ghi `user.sqlite`, không mở
  PDF thật và không gọi AI.
- Không xóa sách, không chạy Vision toàn sách, không reset AI budget.
- Sau toàn bộ review và test, người dùng chỉ nghiệm thu lại Bài 3 bằng nút tiếp
  tục; chưa mở rộng toàn sách trước khi Bài 3 qua.

## Acceptance

1. Số 0 và dãy chỉ có một cặp liên tiếp không tạo phạm vi STT.
2. Manifest lỗi được sửa tại chỗ khi ghép bbox chắc chắn.
3. Dòng tự động lỗi bị xóa, block thủ công và AI attempts được giữ.
4. Ghép không chắc chắn không làm mất dữ liệu.
5. STT trùng và số dòng thừa/thiếu đều chặn coverage.
6. Toàn unit test xanh và reviewer độc lập phê duyệt trước nghiệm thu Bài 3.
