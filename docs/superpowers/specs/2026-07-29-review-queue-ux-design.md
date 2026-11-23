# Thiết kế hàng đợi duyệt từ cần xác nhận

Ngày: 2026-07-29  
Trạng thái: đã được người dùng duyệt trong hội thoại

## 1. Mục tiêu

Thay luồng mặc định của cửa sổ duyệt kết quả nhập sách bằng một bảng tổng hợp
toàn bộ các từ đang có `needs_review = 1`. Người dùng phải nhìn thấy ngay mỗi từ
thuộc bài nào, ở trang nào, xem được ảnh nguồn và xác nhận chọn lọc bằng một nút
lớn, dễ bấm.

Thay đổi này chỉ cải thiện luồng duyệt dữ liệu đã trích xuất. Nó không thay đổi
thuật toán chia bài, OCR, Vision, cấu trúc cơ sở dữ liệu hoặc dữ liệu của 30 bài
Boya đã nhập.

## 2. Phạm vi

### Trong phạm vi

- Thêm chế độ mặc định **Cần xác nhận** vào `DialogReviewBook`.
- Tổng hợp các dòng cần duyệt từ mọi bài trong sách.
- Hiển thị rõ bài, trang và toàn bộ bảy trường từ vựng đang có.
- Cho phép sửa trực tiếp nội dung dòng.
- Cho phép chọn từng dòng hoặc chọn tất cả các dòng đang hiển thị.
- Xác nhận chọn lọc và lưu các thay đổi theo đúng bài.
- Giữ chế độ duyệt theo từng bài hiện tại dưới phần **Tất cả các bài**.
- Tiếp tục tải ảnh nguồn ở luồng nền và chặn ảnh cũ ghi đè lựa chọn mới.
- Chỉ cho hoàn tất nhập sách khi không còn dòng cần xác nhận.

### Ngoài phạm vi

- Không thêm migration hoặc cột mới.
- Không gọi thêm AI.
- Không sửa thuật toán OCR, Vision, tách bài hay crop ảnh nguồn.
- Không tự động xác nhận bất kỳ dòng nào.
- Không thiết kế lại các màn hình Tra cứu, Ôn tập hoặc Bộ thủ.

## 3. Bố cục

Cửa sổ có hai chế độ:

1. **Cần xác nhận** — được chọn mặc định.
2. **Tất cả các bài** — giữ chức năng hiện có để sửa ranh giới, chạy Vision và
   xem toàn bộ từ của từng bài.

Chế độ **Cần xác nhận** gồm:

- Thanh tóm tắt: `N từ cần xác nhận · thuộc M bài`.
- Bộ lọc theo bài và ô tìm nhanh.
- Bảng tổng hợp ở nửa trên.
- Ảnh nguồn của dòng đang chọn ở nửa dưới.
- Thanh hành động cố định phía dưới.

Thứ tự cột của bảng:

1. Ô chọn.
2. Bài.
3. Trang.
4. STT.
5. Chữ Hán.
6. Pinyin.
7. Từ loại.
8. Hán–Việt.
9. Nghĩa Việt.

Cột Bài và Trang phải nằm gần đầu bảng để người dùng không cần cuộn ngang mới
biết nguồn của từ. Dòng đang chọn có trạng thái nổi bật; dòng đã tích có dấu
kiểm rõ ràng để ý nghĩa không phụ thuộc riêng vào màu sắc.

## 4. Luồng thao tác

### Mở cửa sổ

- Ứng dụng đọc tất cả bài của sách, lấy các dòng có `needs_review = 1` và tạo
  hàng đợi tổng hợp.
- Không ô chọn nào được tích sẵn.
- Nếu hàng đợi rỗng, hiển thị trạng thái đã duyệt xong và cho phép hoàn tất sách.

### Xem và sửa

- Khi chọn một dòng, ứng dụng hiển thị ảnh nguồn theo ranh giới của đúng bài và
  trang nguồn của từ.
- Ảnh được kết xuất ở luồng nền. Kết quả của yêu cầu cũ không được ghi đè ảnh
  của dòng đang chọn mới.
- Các ô dữ liệu từ vựng được sửa trực tiếp trong bảng.
- Sửa nội dung không đồng nghĩa với xác nhận; người dùng vẫn phải tích ô của
  dòng đó.

### Chọn dòng

- Người dùng có thể tích hoặc bỏ tích từng dòng.
- **Chọn tất cả đang hiển thị** chỉ tác động đến các dòng còn lại sau bộ lọc.
- **Bỏ chọn** bỏ toàn bộ lựa chọn hiện tại.
- Thay đổi bộ lọc không được tự chọn các dòng đang bị ẩn.

### Xác nhận

- Nút chính luôn nhìn thấy và mang nhãn
  `Xác nhận các dòng đã chọn (N)`.
- Nút bị vô hiệu hóa khi `N = 0`.
- Trước khi lưu, ứng dụng hỏi:
  `Xác nhận N từ thuộc M bài?`
- Sau khi đồng ý, ứng dụng lưu nội dung đã sửa và đặt `needs_review = 0` chỉ cho
  các dòng được chọn.
- Các dòng đã xác nhận biến khỏi hàng đợi; bộ đếm được cập nhật.
- Dòng không được chọn phải giữ nguyên nội dung và cờ `needs_review`.

### Hoàn tất

- Khi vẫn còn dòng cần xác nhận, thao tác hoàn tất sách bị chặn và hiển thị số
  dòng còn lại.
- Khi hàng đợi rỗng, nút chính chuyển thành **Hoàn tất nhập sách**.
- Hoàn tất đặt trạng thái sách thành `ready`.
- Nếu đóng cửa sổ giữa chừng, các lần xác nhận đã lưu vẫn được giữ; các dòng còn
  lại xuất hiện lại khi mở lần sau.

## 5. Dữ liệu và ranh giới tầng

Không đổi schema. `DialogReviewBook` dùng các phương thức hiện có để lấy sách,
bài và từ. Khi xác nhận nhiều dòng thuộc nhiều bài, giao diện nhóm thay đổi theo
`lesson_id`, dựng lại danh sách `VocabRow` đầy đủ của từng bài và gọi
`UserDb.replace_vocab_many()` để lưu toàn bộ nhóm trong một giao dịch nguyên tử.
Phương thức này được bổ sung sau code review nhằm ngăn trạng thái nửa thành công
nếu một bài ở giữa nhóm lưu lỗi.

Việc dựng lại một bài phải bảo toàn:

- Tất cả dòng không được chọn.
- Thứ tự từ.
- Các trường không được sửa.
- Cờ `needs_review` của dòng chưa xác nhận.

Không đưa Qt vào `data/`. Không cho `service/` tự mở cơ sở dữ liệu hoặc đọc PDF.

## 6. Xử lý lỗi

- Ảnh nguồn không mở được: hiển thị lỗi trong vùng ảnh; không tự xác nhận dòng.
- Dữ liệu sửa không hợp lệ, ví dụ chữ Hán rỗng: chặn xác nhận dòng đó và đưa
  tiêu điểm về ô lỗi.
- Không còn dòng sau khi bộ lọc áp dụng: hiển thị trạng thái rỗng nhưng không coi
  toàn bộ sách đã duyệt nếu hàng đợi tổng vẫn còn.
- Lưu thất bại: giữ nguyên hàng đợi và lựa chọn trên màn hình, báo lỗi rõ ràng;
  không hiển thị giả rằng thao tác đã thành công.

## 7. Kiểm thử và nghiệm thu

Viết test trước khi sửa mã sản phẩm.

Các test bắt buộc:

1. Tổng hợp đúng số từ, bài và trang.
2. Mặc định không dòng nào được tích.
3. Xác nhận một phần không làm mất hoặc xác nhận dòng khác.
4. Sửa một dòng rồi xác nhận lưu đúng nội dung.
5. Xác nhận các dòng thuộc nhiều bài giữ nguyên những dòng còn lại của từng bài.
6. Bộ lọc và **Chọn tất cả đang hiển thị** chỉ tác động đúng phạm vi.
7. Yêu cầu ảnh cũ không ghi đè ảnh của lựa chọn mới.
8. Không thể hoàn tất khi còn `needs_review = 1`.
9. Có thể hoàn tất và đặt sách thành `ready` khi hàng đợi rỗng.

Nghiệm thu trực quan trên dữ liệu Boya thật:

- Mở cửa sổ thấy ngay toàn bộ 17 dòng cần kiểm tra.
- Mỗi dòng chỉ rõ bài và trang.
- Chọn một dòng hiển thị đúng ảnh nguồn mà không khóa giao diện.
- Nút xác nhận luôn nhìn thấy, đủ lớn và hiển thị đúng số dòng đã chọn.
- Xác nhận thử một nhóm nhỏ, đóng và mở lại cửa sổ; chỉ các dòng chưa xác nhận
  còn xuất hiện.
- Chạy toàn bộ bộ test của dự án trước khi báo hoàn thành.
