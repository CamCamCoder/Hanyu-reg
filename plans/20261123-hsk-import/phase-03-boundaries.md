---
phase: 3
title: "Sửa lỗi phân bài đã tái hiện"
status: completed
dependencies: [2]
---

# Sửa lỗi phân bài đã tái hiện

## Thực hiện

- [x] Từ lượt A/B lấy ca A sai nhưng B đúng, truy lại mục lục, trang in, chỉ số trang PDF và tiêu đề. Trong phiên splitter thêm test tái hiện, rồi sửa quy tắc chịu trách nhiệm. Nếu không thấy lỗi phân bài, ghi kết quả chứng minh và bỏ qua thay đổi thuật toán.
- [x] Ở phiên dialog ranh giới, cho xem cả hai trang ứng viên khi mục lục xung đột với tiêu đề. Chỉ chạy OCR theo ranh giới người dùng đã chọn; lưu được lựa chọn khi tiếp tục nhập.

## Điều kiện hoàn thành

- [x] Chạy `python -m pytest tests/unit/test_splitter.py -q` và test Qt cho đường xác nhận. Kiểm đầu/cuối bài, không chồng trang, không lệch một trang giữa nhãn hiển thị và adapter. Chạy lại A với cùng OCR.

Có 55/55 ranh giới khớp cả đầu và cuối bài. Test Qt xác nhận lựa chọn trang khi mục lục và tiêu đề mâu thuẫn. [Biên bản](../journals/2026-11-23-boya-qa.md)
