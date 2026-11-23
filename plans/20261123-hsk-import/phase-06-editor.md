---
phase: 6
title: "Duyệt vùng trên ảnh toàn trang"
status: completed
dependencies: [5]
---

# Duyệt vùng trên ảnh toàn trang

## Thực hiện

- [x] Qua service hiện có, tải ảnh nền cho trang đang chọn. Tại bước trước khi chốt từ, cho xác nhận, kéo khung, vẽ thêm, bỏ qua và hủy. Cho chuyển tới mọi trang của bài, kể cả trang chưa có ứng viên. Hủy trả về quyết định đã lưu.
- [x] Dùng page_index từ 0 và bbox OCR chuẩn 250 DPI theo get_page_crop_image_bytes. Quy đổi từ vùng ảnh thực đang vẽ, trừ lề và cuộn, tính lại theo zoom. Chặn khung rỗng và giới hạn trong biên trang. Mọi thao tác lưu đi qua service. Khi chuyển trang chỉ hiển thị kết quả của lần tải mới nhất.

## Điều kiện hoàn thành

- [x] Test Qt offscreen ở hai mức zoom, có lề ảnh và khi cuộn. Vẽ cùng vùng rồi so ảnh cắt với trang gốc, mở lại và đối chiếu bốn góc trong sai số tối đa một pixel OCR. Test thêm khung ở trang trống, hủy, xác nhận và chuyển bài nhanh.

Đã so ảnh PNG đã lưu với ảnh kết xuất trực tiếp từ cùng khung. Đã thử chuyển trang nhanh, cuộn, hai mức zoom, hủy và mở lại. [Biên bản](../journals/2026-11-23-boya-qa.md)
