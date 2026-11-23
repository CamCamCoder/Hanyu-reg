---
phase: 5
title: "Lưu quyết định duyệt và tiếp tục nhập"
status: completed
dependencies: [4]
---

# Lưu quyết định duyệt và tiếp tục nhập

## Thực hiện

- [x] Trong phiên dữ liệu dùng import_block.id làm định danh. Phân biệt quyết định vùng (chờ duyệt, chấp nhận, bỏ qua) với trạng thái trích từ. Nếu thêm trường, dùng bậc migration mới và kiểm hồ sơ cũ; các block manual cũ vẫn giữ nguyên. Lưu vùng bỏ qua để lần chạy tiếp không tạo lại.
- [x] Phiên importer chỉ xử lý vùng rõ hoặc đã xác nhận. Khi sửa khung, giữ id, vô hiệu crop và hàng tự động gắn source_block_id trong giao dịch. Giữ sửa tay, báo dòng cần đối chiếu nếu vùng nguồn đã đổi. Tạo crop mới trước khi chuyển tham chiếu; lỗi giữa chừng phải chạy lại được. Kiểm tra phiên bản khung trước khi nhận kết quả worker cũ.

## Điều kiện hoàn thành

- [x] Chạy `python -m pytest tests/unit/test_userdb.py tests/unit/test_universal_engine.py -q`. Kiểm retry, đóng/mở, kết quả worker đến muộn, bỏ qua tất cả vùng, sửa một trong hai bảng cùng trang. Không nhân đôi từ, không dùng crop cũ, không xóa dữ liệu vùng bên cạnh; chỉ tái trích vùng bị đổi.

Đã kiểm migration 3 lên 4, giao dịch khi lưu khung, worker đến muộn, hai khung trên cùng trang và trường hợp bỏ qua mọi vùng. [Biên bản](../journals/2026-11-23-boya-qa.md)
