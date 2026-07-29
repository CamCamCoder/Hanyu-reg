# Cách chạy, đọc một lần rồi làm theo

## Bước 1. Dọn kho

Trong thư mục dự án, chỉ được có đúng những tệp sau:

    CLAUDE.md                    <- đổi tên từ tệp CLAUDE.md trong gói này
    dac-ta-ung-dung-v0.5.md      <- bản mới nhất
    dict.sqlite                  <- bản mới nhất, có word_fts
    build_dict.py
    handoff/01-pinyin.md ... 04-lookup.md

Xoá `dac-ta-ung-dung-v0.4 (1).md`, xoá `files.zip`, xoá mọi `dict.sqlite` cũ.
Để hai bản đặc tả cạnh nhau là agent sẽ đọc nhầm bản cũ.

## Bước 2. Bắt đầu phiên MỚI

Ngữ cảnh của phiên cũ vẫn còn nhớ chuyện lookup, nên nó sẽ kéo lệch. Gõ `/clear`,
hoặc mở hẳn một cửa sổ trò chuyện mới.

## Bước 3. Dán đúng đoạn này

    Đọc CLAUDE.md trước.
    Phiên này làm PHIÊN 01, module pinyin. Không làm gì khác.
    Đặc tả và bảng đáp án nằm trong handoff/01-pinyin.md, đọc tệp đó.
    Không lập kế hoạch cho toàn bộ ứng dụng, không tạo tệp ngoài hai tệp đã nêu.
    Viết test trước, chạy pytest, rồi báo kết quả.

## Bước 4. Kiểm tra nó đi đúng hướng

Dấu hiệu ĐÚNG:
- Việc đầu tiên nó làm là đọc `CLAUDE.md` và `handoff/01-pinyin.md`
- Nó tạo đúng hai tệp, không hơn
- Nó viết test trước rồi mới viết mã
- Nó chạy `pytest` và dán kết quả thật, không nói suông là "đã xong"

Dấu hiệu SAI, dừng ngay:
- Nó đề xuất cấu trúc thư mục cho cả ứng dụng
- Nó nhắc tới React, Vite, frontend, dashboard
- Nó hỏi khoá API
- Nó sửa test cho khớp mã thay vì sửa mã cho khớp test
- Nó tạo `models.py` hay `dictdb.py` trong phiên 01

## Bước 5. Xong phiên thì cập nhật bảng

Sửa cột Trạng thái của phiên 01 trong `CLAUDE.md` thành `xong`, đổi dòng
"Phiên tiếp theo phải làm" thành 02. Rồi `/clear` và lặp lại từ bước 3.

Đây là lý do bảng tiến độ tồn tại: agent không nhớ gì giữa các phiên, nhưng tệp
thì nhớ.

## Khi nó dừng lại và hỏi

Nếu agent dừng lại nói rằng bảng đáp án sai, hoặc thiếu tệp, hoặc dữ liệu không
khớp: **đó là hành vi đúng**, quy tắc 1 yêu cầu nó làm vậy. Đọc lý do nó đưa ra
rồi quyết định, đừng bảo nó cứ làm tiếp cho xong.
