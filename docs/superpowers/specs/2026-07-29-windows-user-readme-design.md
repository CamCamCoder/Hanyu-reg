# Thiết kế README hướng dẫn người dùng Windows

## Mục tiêu

README giúp một người dùng Windows chưa biết cấu trúc mã nguồn có thể tải dự án,
cài phụ thuộc, mở ứng dụng, cấu hình Gemini và nhập giáo trình PDF mà không cần
đọc tài liệu dành cho lập trình viên.

## Đối tượng và phạm vi

- Đối tượng chính: người dùng ứng dụng trên Windows.
- Môi trường đã kiểm thử: Windows, Python 3.12.9.
- Không cung cấp hướng dẫn macOS hoặc Linux vì chưa được kiểm chứng.
- Không giải thích sâu kiến trúc, migration hoặc quy trình agent.

## Cấu trúc README

1. Tên ứng dụng và mô tả ngắn.
2. Các tính năng người dùng nhận được.
3. Yêu cầu hệ thống.
4. Cài đặt lần đầu bằng PowerShell hoặc Command Prompt.
5. Cách mở nhanh bằng `chay-app.bat`.
6. Cách tạo shortcut Desktop bằng `tao-shortcut.bat`.
7. Cách nhập Gemini API key trong màn hình Sách.
8. Cách nhập PDF, xác nhận ranh giới bài, duyệt bảng từ và thêm vào Ôn tập.
9. Các lỗi thường gặp và cách xử lý.
10. Lưu ý bảo mật và bản quyền.

## Lệnh cài đặt

README dùng đúng các lệnh:

```powershell
git clone https://github.com/CamCamCoder/Hanyu-reg.git
cd Hanyu-reg
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m hanzi_app.main
```

Nếu PowerShell chặn activation, người dùng có thể dùng Command Prompt:

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m hanzi_app.main
```

## Hướng dẫn nhập sách

Luồng được mô tả theo đúng giao diện:

1. Mở mục **Sách**.
2. Dán Gemini API key vào ô cấu hình.
3. Bấm **Nhập sách PDF** và chọn tệp.
4. Kiểm tra ranh giới từng bài trước khi OCR.
5. Chờ quá trình trích xuất hoàn tất.
6. Duyệt các dòng được gắn cờ và ảnh nguồn.
7. Bấm **Xác nhận toàn bộ**.
8. Thêm từ của bài vào **Ôn tập**.

README nói rõ API key chỉ được lưu trong `user.sqlite` cục bộ và tệp này đã nằm
trong `.gitignore`. Không ghi khóa thật vào tài liệu.

## Xử lý lỗi

- Không tìm thấy Python: cài Python 3.12 và chọn Add Python to PATH.
- App không mở: chạy `chay-app-go-loi.bat` để giữ cửa sổ lỗi.
- PowerShell không kích hoạt venv: dùng Command Prompt.
- Gemini trả 429: chờ quota hồi phục, tránh chạy lại nhiều lần liên tiếp.
- PDF xử lý lâu: giữ app mở và theo dõi trạng thái; quá trình OCR sách scan có
  thể mất nhiều thời gian.
- Ảnh nguồn chưa có: dùng tác vụ tạo lại ảnh sau khi tính năng lưu crop hoàn tất.

## An toàn

- Không commit hoặc chia sẻ `user.sqlite`, API key hay file `.env`.
- Không tải PDF giáo trình có bản quyền lên repository.
- Người dùng tự chịu trách nhiệm về quyền sử dụng tài liệu nhập vào ứng dụng.

## Tiêu chí nghiệm thu

- README hiển thị đúng tiếng Việt trên GitHub.
- Mọi đường dẫn và lệnh khớp với tệp thực tế trong repository.
- Người dùng Windows có thể cài và chạy mà không cần đọc tài liệu khác.
- Không chứa API key, dữ liệu người dùng hoặc tuyên bố hỗ trợ nền tảng chưa test.
- README ưu tiên hướng dẫn sử dụng, không biến thành tài liệu kiến trúc.
