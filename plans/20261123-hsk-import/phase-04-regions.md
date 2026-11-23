---
phase: 4
title: "Chọn đúng bảng trong từng bài"
status: completed
dependencies: [3]
---

# Chọn đúng bảng trong từng bài

## Thực hiện

- [x] Dùng lỗi còn ở lượt B để thêm test trong test_vocab.py. Với mỗi ca thêm một mẫu đối nghịch, chẳng hạn bảng một hàng dưới tiêu đề mờ và hội thoại đánh số. Bảo toàn bảng song song, bảng tiếp trang và khung manual cũ.
- [x] Trong service/vocab.py giữ thông tin trang, khung và lý do cần duyệt cho vùng mơ hồ. Tự lấy vùng có cấu trúc bảng rõ; cắt trước hội thoại, loại bảng tham chiếu rõ ràng. Không mã hóa riêng số bài/trang. Giữ ngưỡng hiện hành trừ khi có mẫu chứng minh cần đổi.

## Điều kiện hoàn thành

- [x] Chạy `python -m pytest tests/unit/test_vocab.py -q`. So lượt B trước/sau trên cùng OCR. Mỗi nhóm sửa phải giảm lỗi mục tiêu và giữ được các bảng đã đúng trên tập đối chứng.

Đúng 109/109 trang bảng, gồm 25 trang trong các bài đối chứng. Số liệu theo sách và kiểm tra mép bảng ở biên bản. [Biên bản](../journals/2026-11-23-boya-qa.md)
