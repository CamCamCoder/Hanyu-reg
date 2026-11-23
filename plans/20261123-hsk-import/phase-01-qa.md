---
phase: 1
title: "QA hàng đợi và nhận diện PDF"
status: completed
dependencies: []
---

# QA hàng đợi và nhận diện PDF

QA Qt offscreen với bản sao SQLite. Lọc HSK1 các bài 2/3/5/6/8/10/11 trả lần lượt 10/28/30/22/20/22/24 dòng, HSK2 Bài 17 trả 3 dòng. Sửa và xác nhận một dòng rồi mở lại giảm hàng đợi 229 → 228 và 114 → 113. Phát hiện mất 22 và 2 liên kết nguồn khi xác nhận; đã sửa và lặp lại thao tác, giữ đủ liên kết. HSK2 Bài 17 hiển thị được ảnh đã lưu ở dòng có crop; dòng thiếu crop báo thiếu PDF. Ảnh toàn trang HSK chưa đối chiếu, phạm vi đo đã chuyển sang Boya theo yêu cầu. SQLite thật giữ cùng SHA-256 trước và sau QA.

## Thực hiện

- [x] Trên bản sao SQLite nhất quán (SQLite backup), kiểm tra hàng đợi HSK1 id 4, Bài 2/3/5/6/8/10/11 và HSK2 id 5, Bài 17. Lọc, sửa một dòng, chuyển bài khi preview đang tải, xác nhận có chọn lọc rồi mở lại. Đối chiếu số dòng còn chờ và ảnh đúng bài. Dòng đã bị sửa trong hồ sơ chỉ là bằng chứng QA thao tác.
- [x] Đối chiếu mã băm. Người dùng đã đổi phép đo sang Boya 1 và 2. Chưa đối chiếu toàn trang từ PDF HSK cũ.

## Điều kiện hoàn thành

- [x] Biên bản ghi bài, trang, hành động, kết quả và mục chưa kiểm. Chạy `python -m pytest tests/unit/test_review_dialog.py -q` với Qt offscreen. Bàn giao phiên QA theo AGENTS.md trước khi sửa module.

Phần kiểm thao tác HSK đã hoàn thành trên bản sao. Người dùng thay bộ PDF nghiệm thu bằng hai cuốn Boya. [Biên bản](../journals/2026-11-23-boya-qa.md)
