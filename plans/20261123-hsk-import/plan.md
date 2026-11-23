---
title: "QA hàng đợi HSK và nhập bảng từ mới Boya 1–2"
description: "Đo riêng lỗi phân bài và lỗi định vị, duyệt khung trên PDF và bảo toàn kết quả khi nhập tiếp."
status: completed
priority: P2
created: 2026-11-23
tags: [ocr, desktop, sqlite]
---

# QA hàng đợi HSK và nhập bảng từ mới Boya 1–2

Ngày 23/11, người dùng chuyển phép đo và nghiệm thu sang Boya sơ cấp 1 (270 trang) và 2 (226 trang), chỉ tính bảng chính “Từ mới / New Words and Expressions” trong mỗi bài. Các chỉ dẫn HSK bên dưới áp dụng cho QA hàng đợi đã nhập. Với các phiên đo trên PDF, dùng hai cuốn Boya. Đáp án trang PDF đánh từ 1 ở [bảng tham chiếu](../../tests/golden/boya_table_pages.csv). Dành riêng các bài 4, 8, 12, 16, 20, 24 và 28 nếu có của mỗi sách để đối chứng.

Người nhập sách có thể để app nhận bảng rõ và tự sửa khung ở trang khó trước khi đưa từ vào học. Thực hiện tuần tự, chia các thay đổi khác module thành phiên riêng và cập nhật AGENTS.md cuối từng phiên đã hoàn thành. Kế hoạch dùng Python/PySide6, SQLite và OCR cục bộ. Mọi lần kiểm tra dùng hồ sơ thử. Phạm vi nghiệm thu là hai sách đã thống nhất.

[Bản brainstorm](../../docs/superpowers/plans/2026-11-23-hsk-review-and-table-detection.md) · [Trạng thái dự án](../../AGENTS.md)

## Các phiên

- [x] 1. [QA hàng đợi và nhận diện PDF](phase-01-qa.md)
- [x] 2. [Lập đáp án và đo A/B](phase-02-baseline.md)
- [x] 3. [Sửa lỗi phân bài đã tái hiện](phase-03-boundaries.md)
- [x] 4. [Chọn đúng bảng trong từng bài](phase-04-regions.md)
- [x] 5. [Lưu quyết định duyệt và tiếp tục nhập](phase-05-persistence.md)
- [x] 6. [Duyệt vùng trên ảnh toàn trang](phase-06-editor.md)
- [x] 7. [Nghiệm thu trên hai sách](phase-07-acceptance.md)

Kết quả nghiệm thu định vị trên 55 bài và 109 trang bảng, cùng các giới hạn của OCR, được ghi trong [biên bản đối chiếu](../journals/2026-11-23-boya-qa.md). Chưa đặt mục tiêu giảm số trang duyệt chữ vì bộ cũ bỏ sót 88 trang bảng ngay cả khi được cấp đúng ranh giới bài.
