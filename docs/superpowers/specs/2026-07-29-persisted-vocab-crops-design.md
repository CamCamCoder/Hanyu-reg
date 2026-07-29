# Thiết kế lưu ảnh bảng từ mới theo từng bài

## Mục tiêu

Ảnh bảng từ mới đã được tạo để OCR/Vision phải được lưu lại theo từng bài. Màn
hình duyệt chỉ đọc ảnh đã lưu, không mở lại PDF, không OCR và không chạy lại bộ
định vị bảng khi người dùng bấm vào một dòng.

Quyển Boya hiện có phải được tạo bù ảnh cho đủ 30 bài.

## Phạm vi

- Lưu một ảnh PNG đã ghép cho mỗi bài học có bảng từ mới.
- Ghi đường dẫn ảnh vào dữ liệu bài học bằng một bậc migration mới.
- Lưu ảnh mới ngay trong luồng nhập PDF và luồng chạy lại Vision.
- Tạo bù ảnh cho các bài của sách đã nhập trước tính năng này.
- Đọc ảnh đã lưu để hiển thị trong dialog duyệt.
- Xóa ảnh liên quan khi xóa sách.

Không thay đổi thuật toán trích xuất từ, không gọi thêm AI và không lưu ảnh vào
SQLite dưới dạng BLOB.

## Lưu trữ

Ảnh nằm trong thư mục dữ liệu của ứng dụng:

```text
data/book_crops/book-<book_id>/lesson-<lesson_id>.png
```

Bảng `lesson` nhận thêm cột nullable `preview_path`. Việc bổ sung dùng một bậc
migration mới; không chỉnh sửa bậc migration đã phát hành. Đường dẫn được lưu
dạng tương đối so với thư mục gốc ứng dụng để dự án vẫn di chuyển được trên máy.

Ảnh được ghi theo kiểu nguyên tử: ghi ra tệp tạm cùng thư mục, sau đó thay tên
thành tệp đích. Nếu ghi lỗi, dữ liệu từ vựng vẫn được giữ nhưng bài tiếp tục ở
trạng thái cần tạo ảnh nguồn.

## Trách nhiệm theo tầng

- `adapter/pdfsource.py` chỉ render, crop và ghép bytes ảnh từ PDF.
- `service/importer.py` điều phối tạo ảnh, ghi tệp, tạo bù và dọn thư mục ảnh.
- `data/migrate.py` thêm cột; `data/userdb.py` chỉ đọc/ghi `preview_path`, không
  thao tác filesystem.
- `ui/screen_books.py` yêu cầu service đọc ảnh đã lưu và hiển thị kết quả.

Như vậy tầng dữ liệu không phụ thuộc Qt hoặc filesystem ảnh, còn UI không đọc
PDF trực tiếp.

## Luồng nhập mới

1. Bộ trích xuất định vị và tạo các crop bảng của bài.
2. Các crop được ghép/co chiều rộng như ảnh đã gửi cho Vision.
3. Ảnh PNG ghép được lưu vào đường dẫn của bài.
4. Kết quả từ vựng được lưu như hiện tại.
5. Màn duyệt đọc trực tiếp PNG đã lưu.

Ảnh dùng để đối chiếu phải là đúng ảnh đầu vào đã ghép trước khi gửi AI, không
được tạo lại bằng một thuật toán khác sau đó.

## Luồng chạy lại Vision

Khi người dùng chạy Vision cho một bài, ảnh đầu vào mới thay thế ảnh nguồn cũ
chỉ sau khi ảnh mới đã được tạo thành công. Kết quả từ Vision vẫn chỉ được lưu
sau bước duyệt hiện có.

## Tạo bù cho Boya hiện tại

Một thao tác tạo bù duyệt 30 bài đã có:

1. Đọc ranh giới bài và PDF gốc.
2. Định vị, crop và ghép bảng một lần cho mỗi bài.
3. Lưu PNG và cập nhật `preview_path`.
4. Bỏ qua bài đã có ảnh PNG hợp lệ để có thể chạy tiếp sau khi bị gián đoạn.
5. Báo số bài thành công, thất bại và lý do cụ thể.

Hoàn thành khi có 30 đường dẫn, 30 tệp tồn tại và cả 30 ảnh giải mã được. Không
gọi Gemini trong quá trình tạo bù.

## Hiển thị và xử lý lỗi

- Khi chọn dòng, UI đọc PNG đã lưu và hiển thị ngay.
- UI không gọi `render_vocab_table_preview` trong đường bấm thông thường.
- Nếu `preview_path` rỗng, tệp mất hoặc PNG hỏng, UI báo rõ ảnh nguồn chưa có và
  cho phép tạo lại ở tác vụ riêng; không tự OCR ngầm.
- Kết quả của bài cũ không được ghi đè preview của bài mới.

## Xóa và tính nhất quán

Khi xóa sách, tầng service xóa thư mục `book-<book_id>` sau khi giao dịch xóa dữ
liệu thành công. Chỉ được xóa đúng thư mục con đã xác thực nằm trong
`data/book_crops`;
không dùng đường dẫn lấy trực tiếp từ dữ liệu người dùng làm đích xóa đệ quy.

Nếu database trỏ tới ảnh không tồn tại, đây là trạng thái có thể phục hồi bằng
tạo bù, không làm hỏng sách hoặc từ vựng.

## Kiểm thử và nghiệm thu

- Migration mới giữ nguyên dữ liệu cũ và thêm `preview_path`.
- Lưu ảnh nguyên tử và đọc lại đúng bytes.
- Luồng nhập lưu đúng ảnh đã dùng để trích xuất.
- Dialog dùng ảnh đã lưu và không gọi OCR/locator.
- Ảnh mất/hỏng trả thông báo rõ ràng.
- Chuyển bài nhanh không cho kết quả cũ ghi đè.
- Xóa sách chỉ xóa đúng thư mục ảnh của sách đó.
- Tạo bù có thể resume và không gọi AI.
- Toàn bộ unit test và hai golden Boya vẫn xanh.
- Kiểm tra thực tế Boya đạt 30/30 ảnh PNG hợp lệ; mở ngẫu nhiên ít nhất Bài 5,
  Bài 20 và Bài 29 để đối chiếu bằng mắt.
