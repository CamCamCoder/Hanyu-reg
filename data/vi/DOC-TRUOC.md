# Nghĩa tiếng Việt cho dict.sqlite

## Vì sao dữ liệu nằm ở đây chứ không nằm thẳng trong dict.sqlite

`build_dict.py` dựng lại `dict.sqlite` từ đầu mỗi lần chạy. Nó tạo hai cột
`meaning_vi` và `hanviet` nhưng không bao giờ đổ dữ liệu vào. Nếu bạn gõ nghĩa
thẳng vào database thì lần rebuild sau là mất sạch.

Nên nguồn sự thật là hai tệp CSV trong thư mục này. `dict.sqlite` chỉ là bản dựng ra.

## Nạp

    python tools/nap_nghia_vi.py

Chạy lại nhiều lần được, không nhân đôi dữ liệu. Sau mỗi lần chạy lại
`build_dict.py`, phải chạy lại lệnh trên.

Xem trước mà không ghi gì:

    python tools/nap_nghia_vi.py --kiem

## Định dạng

`nghia_tu.csv` — hai hoặc ba cột, phân cách bằng dấu `|`:

    word_simp|meaning_vi
    word_simp|meaning_vi|hsk_level

Cột thứ ba chỉ cần cho sáu từ xuất hiện ở hai cấp HSK với nghĩa khác nhau:
喂, 得, 等, 过, 还, 长. Ví dụ 喂 là "a lô" ở HSK 1 nhưng là "cho ăn" ở HSK 6.
Thiếu cột này thì một nghĩa đè lên cả hai bản ghi.

`nghia_chu.csv` — ba cột:

    char|hanviet|meaning_vi

## Chữ là bộ thủ thì không cần gõ

Bảng `radical` đã có sẵn `name_hv` và `meaning_vi` cho cả 214 bộ, kể cả dạng giản
lược. Kịch bản tự điền cho những chữ bản thân là bộ thủ (口, 木, 讠, 氵...) và chỉ
điền vào ô đang rỗng, không đè lên dòng bạn gõ tay trong CSV.

## Độ phủ hiện tại

| | Đã có | Tổng |
|---|---|---|
| `word.meaning_vi` | 601 | 5001 |
| `char.hanviet` | 958 | 9534 |

Toàn bộ HSK 1, 2 và 3: 601 từ. Cộng 716 chữ gõ tay và 242 chữ bộ thủ điền tự động.

**Mọi ô trong cây chiết tự của mọi từ HSK 1-3 đều có âm Hán-Việt và nghĩa** —
đã kiểm: 871 chữ cần phủ, 0 chữ còn thiếu.

## Còn thiếu

| Nội dung | Số lượng |
|---|---|
| Từ HSK 4 | 600 |
| Từ HSK 5 | 1300 |
| Từ HSK 6 | 2500 |
| Chữ thành phần của HSK 4-6 | ước 900 |

Đổ thêm lúc nào cũng được, không đụng tới mã. Chỉ cần nối thêm dòng vào hai tệp
CSV rồi chạy lại kịch bản nạp.

## Nguồn

Nghĩa tự soạn dựa trên cột `meaning_en` có sẵn trong `dict.sqlite`, cộng âm
Hán-Việt tra theo chữ. **Không lấy từ giáo trình.** Quyết định này đã chốt trong
`BAN-GIAO.md` mục 2: nghĩa lấy từ sách chỉ được vào `lesson_word.meaning_src`
của `user.sqlite`, vì `dict.sqlite` đóng gói kèm sản phẩm.
