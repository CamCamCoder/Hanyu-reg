# Command Debug Log Design

## Goal

Cho phép người dùng tái hiện lỗi ứng dụng mà không cần chụp ảnh. Khi chạy
`chay-app-go-loi.bat`, mọi mốc xử lý quan trọng và traceback liên quan được ghi
vào `debug-latest.log` ở gốc repo. Sau khi lỗi xuất hiện, người dùng chỉ cần báo
"xong" để agent đọc log trực tiếp trên cùng máy.

## Scope

- Giữ `chay-app.bat` và luồng chạy bình thường không đổi.
- `chay-app-go-loi.bat` bật biến môi trường debug, làm mới log mỗi lần chạy,
  chạy Python unbuffered với `faulthandler`, ghi cả stdout và stderr vào log,
  rồi giữ cửa sổ CMD để hiện mã thoát và đường dẫn log.
- Điểm khởi động cấu hình logging UTF-8 khi debug được bật, gồm thời gian,
  level, thread và logger name.
- Ghi traceback cho exception Python chưa bắt, exception của thread Python và
  thông báo Qt nghiêm trọng.
- Các worker import đang bắt exception để phát Qt signal phải gọi
  `logger.exception(...)` trước khi phát signal, nếu không traceback sẽ mất.
- Dialog import ghi các mốc progress, hoàn tất và lỗi đã nhận từ worker.

## Data And Privacy

Log được phép chứa tên sách, book/lesson/block id, phần trăm tiến trình, loại
engine, exception và traceback. Không ghi API key, nội dung request AI, raw OCR
toàn trang hoặc dữ liệu SQLite. `debug-latest.log` là file sinh lúc chạy và không
được commit.

## Error Handling

- Nếu app lỗi trước khi logging Python được cấu hình, chuyển hướng stdout/stderr
  của batch vẫn giữ được traceback khởi động.
- Nếu app đóng bình thường hoặc lỗi, batch luôn ghi mã thoát cuối log và hiện vị
  trí log trong CMD.
- Logging tuyệt đối không được làm worker thất bại thêm; chỉ dùng thư viện chuẩn
  và các lời gọi logging không phát sinh nghiệp vụ mới.

## Files

- `chay-app-go-loi.bat`: launcher debug và thu log.
- `hanzi_app/main.py`: cấu hình debug logging và global exception hooks.
- `hanzi_app/service/importer.py`: traceback tại các worker boundary.
- `hanzi_app/ui/dialog_import.py`: log progress/result người dùng nhìn thấy.
- `.gitignore`: bỏ qua `debug-latest.log`.
- Unit tests tập trung vào cấu hình debug và việc worker giữ traceback; không mở
  PDF/SQLite thật và không gọi AI.

## Acceptance

1. Chạy debug tạo mới `debug-latest.log` UTF-8 và ghi rõ phiên bắt đầu.
2. Lỗi import đã được worker bắt vẫn có exception type và traceback trong log.
3. Log cho biết mốc progress cuối cùng trước lỗi và thông điệp UI nhận được.
4. Không xuất hiện API key trong log.
5. Chạy app bình thường không tạo log debug.
6. Toàn bộ unit test xanh; nghiệm thu thật chỉ cần người dùng chạy debug một lần
   và báo "xong".
