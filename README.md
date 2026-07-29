# Hanyu Recognize

Ứng dụng desktop học từ vựng tiếng Trung dành cho người Việt. Hanyu Recognize
giúp bạn tra cứu chữ Hán, xem pinyin và âm Hán–Việt, học bộ thủ, nhập từ mới từ
giáo trình PDF và ôn tập ngay trong một ứng dụng.

> Ứng dụng hiện được kiểm thử trên **Windows** với **Python 3.12.9**.

## Tính năng chính

- Tra cứu chữ Hán và từ ghép theo chữ, pinyin hoặc nghĩa.
- Xem pinyin, nghĩa Việt, âm Hán–Việt và cây chiết tự.
- Học 214 bộ thủ Khang Hy.
- Nhập giáo trình PDF có chữ hoặc ảnh scan.
- Tự tách bài và trích xuất bảng từ mới.
- Duyệt, sửa dữ liệu OCR trước khi đưa vào học.
- Ôn tập bằng thẻ nhớ và các bài tập pinyin, nghĩa, Hán–Việt, bộ thủ.

## Yêu cầu

- Windows 10 hoặc Windows 11.
- Python 3.12, khuyến nghị đúng bản 3.12.9.
- Git nếu tải dự án bằng lệnh `git clone`.
- Kết nối Internet và Gemini API key nếu sử dụng Smart Import/Vision.

Bạn có thể tải Python tại [python.org](https://www.python.org/downloads/).
Trong lúc cài, nhớ chọn **Add Python to PATH**.

## Cài đặt lần đầu

### Cách 1: PowerShell

Mở PowerShell và chạy:

```powershell
git clone https://github.com/CamCamCoder/Hanyu-reg.git
cd Hanyu-reg
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m hanzi_app.main
```

Từ những lần sau, mở PowerShell tại thư mục dự án:

```powershell
.\.venv\Scripts\Activate.ps1
python -m hanzi_app.main
```

### Cách 2: Command Prompt

Nếu PowerShell không cho kích hoạt môi trường ảo, mở Command Prompt:

```bat
git clone https://github.com/CamCamCoder/Hanyu-reg.git
cd Hanyu-reg
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m hanzi_app.main
```

## Mở app bằng một cú bấm

Repository có sẵn:

- `chay-app.bat`: mở ứng dụng.
- `chay-app-go-loi.bat`: mở ứng dụng và giữ cửa sổ lỗi để chẩn đoán.
- `tao-shortcut.bat`: tạo shortcut **Học từ qua bộ thủ** trên Desktop.

Các file `.bat` sử dụng Python mặc định trên Windows. Nếu bạn muốn dùng chúng,
hãy cài dependencies cho Python mặc định:

```powershell
py -3.12 -m pip install -r requirements.txt
```

Sau đó:

1. Bấm đúp `tao-shortcut.bat` một lần.
2. Kiểm tra thông báo kết thúc có mã `0`.
3. Mở shortcut **Học từ qua bộ thủ** trên Desktop.

Nếu không muốn cài packages vào Python mặc định, hãy tiếp tục chạy app bằng
môi trường `.venv` như phần cài đặt ở trên.

## Cấu hình Gemini API key

API key không bắt buộc cho các chức năng tra cứu và ôn tập. Tuy nhiên, bạn nên
có key để Smart Import/Vision đọc bảng từ mới trong PDF scan chính xác hơn.

1. Tạo API key trong [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Mở ứng dụng và chọn mục **Sách**.
3. Dán key vào ô **Cấu hình AI Smart Import**.
4. Chuyển sang ô khác để ứng dụng lưu key.

Key được lưu trong `user.sqlite` trên máy của bạn. Tệp này đã được Git bỏ qua,
nhưng bạn vẫn không nên gửi nó hoặc chụp màn hình có lộ key cho người khác.

## Nhập giáo trình PDF

Ứng dụng nhận PDF có lớp chữ, PDF scan ảnh hoặc tài liệu kết hợp hai loại.

1. Mở mục **Sách**.
2. Nhập Gemini API key nếu muốn sử dụng Smart Import/Vision.
3. Bấm **+ Nhập sách PDF...** và chọn giáo trình.
4. Chờ ứng dụng phân tích và đề xuất ranh giới các bài.
5. Kiểm tra trang bắt đầu, trang kết thúc của từng bài rồi xác nhận để OCR.
6. Chờ quá trình trích xuất bảng từ mới hoàn tất.
7. Trong màn duyệt, kiểm tra các dòng màu vàng, sửa từ sai và đối chiếu ảnh nguồn.
8. Khi không còn dòng cần kiểm tra, bấm **Xác nhận toàn bộ**.
9. Mở bài mong muốn và bấm **Thêm vào Ôn tập**.

PDF scan dài có thể cần nhiều thời gian. Hãy giữ ứng dụng mở và theo dõi thông
báo tiến trình. Không bấm nhập lại liên tục khi tác vụ vẫn đang chạy.

## Sử dụng các màn hình

- **Tra cứu:** nhập chữ Hán, pinyin hoặc nghĩa để xem thông tin từ.
- **Sách:** nhập PDF, duyệt bài và chọn từ cần học.
- **Ôn tập:** học các từ đã thêm bằng thẻ nhớ và bài tập.
- **Bộ thủ:** xem và học danh sách 214 bộ thủ Khang Hy.

Dữ liệu học tập, sách đã nhập và API key nằm trong `user.sqlite`. Hãy sao lưu
tệp này nếu chuyển ứng dụng sang máy khác.

## Xử lý lỗi thường gặp

### Windows báo không tìm thấy Python

Cài Python 3.12 và chọn **Add Python to PATH**, sau đó mở cửa sổ dòng lệnh mới:

```powershell
python --version
```

Kết quả cần bắt đầu bằng `Python 3.12`.

### PowerShell chặn kích hoạt `.venv`

Dùng Command Prompt và chạy:

```bat
.venv\Scripts\activate.bat
```

Bạn cũng có thể chạy trực tiếp mà không kích hoạt:

```powershell
.\.venv\Scripts\python.exe -m hanzi_app.main
```

### App không mở hoặc tự tắt

Bấm đúp `chay-app-go-loi.bat`, đọc dòng lỗi cuối cùng trong cửa sổ màu đen và
kiểm tra lại bước cài dependencies.

### Gemini báo `429 Too Many Requests`

Đây là giới hạn quota hoặc số request trong một khoảng thời gian. Hãy:

- Dừng thao tác nhập lại liên tục.
- Chờ quota hồi phục rồi tiếp tục.
- Kiểm tra mục **Usage** và **Rate Limit** trong Google AI Studio.
- Tận dụng khả năng tiếp tục của luồng nhập thay vì quét lại từ đầu.

### Nhập PDF đứng lâu

Sách scan phải OCR nhiều trang nên có thể chậm. Nếu phần trăm không đổi quá lâu,
đóng ứng dụng, mở lại và kiểm tra sách đã nhập trước khi chạy tiếp. Dữ liệu các
bài hoàn tất trước đó được giữ lại.

### Không thấy ảnh nguồn

Đảm bảo file PDF gốc vẫn nằm ở đường dẫn đã dùng khi nhập. Nếu PDF đã bị đổi tên,
di chuyển hoặc xóa, ứng dụng sẽ không thể tạo lại ảnh nguồn.

## Bảo mật và bản quyền

- Không commit hoặc chia sẻ `user.sqlite`, API key hay tệp `.env`.
- Không đưa giáo trình PDF có bản quyền lên GitHub.
- Chỉ nhập tài liệu mà bạn có quyền sử dụng.
- Repository không chứa PDF Boya hoặc API key mẫu.

## Cập nhật phiên bản mới

Nếu thư mục không có thay đổi cá nhân:

```powershell
git pull
python -m pip install -r requirements.txt
```

Ứng dụng tự nâng cấp cấu trúc `user.sqlite` khi cần. Dù vậy, nên sao lưu
`user.sqlite` trước khi cập nhật phiên bản lớn.
