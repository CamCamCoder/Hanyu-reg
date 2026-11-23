---
phase: 2
title: "Lập đáp án và đo A/B"
status: completed
dependencies: [1]
---

# Lập đáp án và đo A/B

## Thực hiện

- [x] Lập danh sách bài và tất cả vùng bảng từ PDF gốc trước khi nhìn đầu ra. Ghi mã sách/bài, trang PDF từ 1 và phần bảng qua trang. Đối chiếu từ đầu/cuối và phần sát bảng bằng hình PDF khi nghiệm thu. Một bảng qua hai trang dùng chung mã bảng. Đánh dấu bài đối chứng của mỗi sách trước khi chỉnh thuật toán.
- [x] Chụp một bộ span OCR cục bộ theo từng trang và dùng lại ở cả hai lượt. Mỗi lượt dùng DB mới, vô hiệu hóa client AI. A chạy đường phân bài của ứng dụng; nếu buộc duyệt thì ghi xung đột và lựa chọn. B dùng đúng ranh giới đáp án, giữ nguyên phần định vị và trích từ.

## Điều kiện hoàn thành

- [x] Xuất hai bảng số liệu theo từng sách. Ghép vùng một-một theo trang và nội dung trước khi so bài. Ghi vùng sót/thừa, sai bài, mất hàng/lấn hội thoại và số trang phải duyệt trên tổng số trang. Đối chiếu cả bảng nhiều vùng. Mỗi lỗi truy được về một trang. Thiếu đúng PDF thì chưa công bố số liệu.

Đáp án trang được lập độc lập từ PDF. Các từ hai đầu bảng được bổ sung khi kiểm ảnh cắt. Không có bộ tọa độ từng điểm ảnh gán nhãn độc lập trước khi sửa. [Biên bản](../journals/2026-11-23-boya-qa.md)
