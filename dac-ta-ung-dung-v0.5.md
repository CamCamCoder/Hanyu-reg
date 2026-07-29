# ĐẶC TẢ ỨNG DỤNG
# Hệ thống học từ vựng tiếng Trung qua phân tích bộ thủ

Phiên bản: 0.5
Ngày: 27/07/2026
Trạng thái: Bản thảo phục vụ đồ án tốt nghiệp

Thay đổi so với 0.1: sửa các mâu thuẫn nội bộ giữa mục 2, 3, 5, 7, 9; bổ sung
bảng `char_reading`, các cột còn thiếu của bảng `word`, ràng buộc duy nhất và
bảng `schema_version`; định lượng các ngưỡng quyết định trong QT-02 và QT-03;
viết rõ ánh xạ ba mức đánh giá sang thang q của SM-2.

Thay đổi so với 0.2: bổ sung nấc 3 của thang tách bài, dùng mô hình ngôn ngữ đề
xuất ranh giới từ một bản tóm lược cấu trúc sách; thêm mục 2.6 gom toàn bộ chức
năng có gọi dịch vụ ngoài; thêm luồng OCR chọn lọc cho sách quét; sửa EV-03 và
thêm EV-09, EV-10.

Thay đổi so với 0.3: thêm mục 13 mô tả giao diện giữa các module và mục 14 mô tả bộ
kiểm thử tối thiểu kèm số liệu đáp án cố định.

Thay đổi so với 0.4: sửa theo kết quả đo trên một giáo trình quét thật (Boya sơ cấp
I, 270 trang, bản photo không có lớp văn bản). Thay bước tách cột bằng biểu đồ chiếu
đứng vì ngưỡng khe đã được chứng minh là không tách được; đổi mốc chia hàng sang cột
số thứ tự; chia OCR thành ba tầng với thời gian đo được; sửa NFR-04; thêm
`hanviet_src`; ghi nhận bảng từ mới có bảy cột và có sẵn cột âm Hán-Việt.

---

## 1. TỔNG QUAN

### 1.1. Mục tiêu

Xây dựng ứng dụng desktop hỗ trợ người Việt học từ vựng tiếng Trung, với hai đặc
điểm phân biệt so với các công cụ hiện có:

1. Tự động bóc tách giáo trình dạng PDF thành cơ sở dữ liệu từ vựng có cấu trúc
   theo từng bài học.
2. Giải thích từ mới thông qua phân tích bộ thủ và thành phần cấu tạo chữ, đồng
   thời liên kết chữ mới với các chữ người dùng đã học có cùng bộ.

### 1.2. Đối tượng người dùng

Người Việt học tiếng Trung ở trình độ sơ cấp đến trung cấp (HSK 1–4), đang theo
một giáo trình cụ thể (Boya, HSK Standard Course, Giáo trình Hán ngữ), có máy tính
cá nhân chạy Windows.

### 1.3. Phạm vi

Trong phạm vi:
- Chữ Hán giản thể
- Ba cách nhập liệu: bàn phím, tệp PDF một trang, tệp PDF cả quyển sách
- Tra cứu, phân tích chiết tự, quản lý từ vựng theo bài, ôn tập lặp lại ngắt quãng
- Hoạt động ngoại tuyến cho tra cứu, chiết tự, nhập PDF và ôn tập

Ngoài phạm vi phiên bản này:
- Nhận dạng chữ viết tay
- Chữ phồn thể như ngôn ngữ đích (chỉ dùng làm dữ liệu phụ trợ khi giải thích từ nguyên)
- Đồng bộ đám mây, tài khoản người dùng, phiên bản di động
- Luyện phát âm, nhận dạng giọng nói

### 1.4. Thuật ngữ

| Thuật ngữ | Giải nghĩa |
|---|---|
| Bộ thủ | Thành phần phân loại của chữ Hán, theo hệ 214 bộ Khang Hy |
| Chiết tự | Phân tách một chữ thành các thành phần cấu tạo |
| IDS | Ideographic Description Sequence, chuỗi mô tả cấu trúc chữ, ví dụ ⿰讠人 |
| 生词表 | Bảng từ mới, phần cố định trong mỗi bài của giáo trình tiếng Trung |
| SRS | Spaced Repetition System, hệ thống lặp lại ngắt quãng |
| Text layer | Lớp văn bản nhúng sẵn trong PDF, đọc được mà không cần OCR |

---

## 2. DANH SÁCH CHỨC NĂNG

Mức ưu tiên: **1** bắt buộc có để bảo vệ, **2** nên có, **3** có thì tốt.

### 2.1. Tra cứu

| Mã | Chức năng | Ưu tiên |
|---|---|---|
| FR-01 | Tìm kiếm bằng chữ Hán nhập trực tiếp | 1 |
| FR-02 | Tìm kiếm bằng pinyin có dấu thanh | 1 |
| FR-03 | Tìm kiếm bằng pinyin không dấu và pinyin số, chấp nhận cả `ren4shi` lẫn `ren4shi5` | 1 |
| FR-04 | Tìm kiếm bằng nghĩa tiếng Việt hoặc tiếng Anh | 2 |
| FR-05 | Xếp hạng kết quả đồng âm theo cấp HSK và tần suất | 1 |
| FR-06 | Hiển thị nghĩa, pinyin, từ loại, cấp HSK của từ | 1 |
| FR-07 | Tra cứu từ ghép, không chỉ chữ đơn | 1 |
| FR-08 | So khớp gần khi truy vấn không khớp chính xác, xếp sau nhóm khớp đúng | 2 |

### 2.2. Phân tích chiết tự

| Mã | Chức năng | Ưu tiên |
|---|---|---|
| FR-10 | Hiển thị bộ thủ, tên Hán-Việt, nghĩa và số nét của từng chữ | 1 |
| FR-11 | Hiển thị cây chiết tự đệ quy từ chuỗi IDS | 1 |
| FR-12 | Hiển thị nghĩa của từng thành phần cấu tạo | 1 |
| FR-13 | Sinh giải thích ngôn ngữ tự nhiên về cấu tạo chữ | 2 |
| FR-14 | Với chữ giản thể có từ nguyên mờ, đối chiếu dạng phồn thể | 2 |
| FR-15 | Liệt kê các chữ đã học có cùng bộ thủ | 2 |

### 2.3. Nhập liệu từ PDF

| Mã | Chức năng | Ưu tiên |
|---|---|---|
| FR-20 | Nhập PDF một trang, trích danh sách chữ Hán | 1 |
| FR-21 | Bóc tách bảng 生词表 thành các trường có cấu trúc | 1 |
| FR-22 | Nhập cả quyển sách, tự phát hiện ranh giới bài học | 1 |
| FR-23 | Cho phép người dùng xem lại và sửa ranh giới bài học | 1 |
| FR-24 | Định vị phần từ mới bên trong mỗi bài | 2 |
| FR-25 | Đánh dấu các dòng bóc tách không đáng tin để người dùng sửa | 1 |
| FR-26 | Xử lý PDF scan không có text layer bằng OCR | 1 |
| FR-27 | Chạy nền có thanh tiến độ khi nhập sách dài | 2 |
| FR-28 | Chữa các dòng bóc tách hỏng bằng mô hình ngôn ngữ, có kiểm chứng | 2 |
| FR-29 | Sửa, xoá sách và bài đã nhập; sửa, xoá dòng từ mới đã lưu | 1 |

### 2.4. Học và ôn tập

| Mã | Chức năng | Ưu tiên |
|---|---|---|
| FR-30 | Xem danh sách từ mới theo từng bài | 1 |
| FR-31 | Thêm từ hoặc cả bài vào danh sách ôn tập | 1 |
| FR-32 | Ôn tập dạng thẻ ghi nhớ với thuật toán SM-2 | 1 |
| FR-33 | Theo dõi trạng thái từng từ: mới, đang học, đã thuộc | 1 |
| FR-34 | Bản đồ 214 bộ thủ, đánh dấu bộ đã gặp và số lần gặp | 2 |
| FR-35 | Thống kê tiến độ theo sách và theo bài | 2 |
| FR-36 | Xuất từ vựng sang định dạng Anki | 3 |

### 2.5. Hệ thống

| Mã | Chức năng | Ưu tiên |
|---|---|---|
| FR-40 | Hoạt động đầy đủ chức năng tra cứu khi không có mạng | 1 |
| FR-41 | Người dùng tự nhập khoá API, lưu mã hoá cục bộ | 1 |
| FR-42 | Bộ nhớ đệm kết quả giải thích để không gọi lại API | 1 |
| FR-43 | Sao lưu và phục hồi dữ liệu học tập | 3 |

### 2.6. Chức năng có gọi dịch vụ ngoài

Khối mã FR-50 trở đi được dành riêng cho các chức năng có gửi dữ liệu ra khỏi máy
người dùng. Gom lại một chỗ để trả lời gọn một câu hỏi mà hội đồng chắc chắn hỏi:
ứng dụng gửi những gì đi đâu, và mất mạng thì hỏng cái gì.

| Mã | Chức năng | Dữ liệu gửi đi | Ưu tiên |
|---|---|---|---|
| FR-13 | Sinh giải thích ngôn ngữ tự nhiên về cấu tạo chữ | Dữ kiện chiết tự đã tra cứu cục bộ, không gửi nội dung sách | 2 |
| FR-28 | Chữa các dòng bóc tách hỏng | Văn bản thô của riêng những dòng hỏng | 2 |
| FR-50 | Đề xuất ranh giới bài từ bản tóm lược cấu trúc sách | Một bảng gồm số trang, số trang in, cỡ chữ và dòng tiêu đề của từng trang | 2 |
| FR-51 | Bóc tách bảng 生词表 từ ảnh trang bằng mô hình thị giác | Ảnh của riêng những trang chứa bảng từ mới | 3 |

Bốn chức năng này đều thoả ba điều kiện chung, và đây là ràng buộc thiết kế chứ
không phải khuyến nghị:
- Tắt được. Mỗi chức năng có một công tắc riêng trong màn hình Cài đặt, mặc định
  tắt cho FR-51 vì nó gửi ảnh nội dung sách đi.
- Có đường lui hoàn toàn cục bộ. Mất mạng, hết hạn mức hoặc người dùng tắt công
  tắc thì luồng vẫn chạy tới cùng bằng nấc thấp hơn, không có thao tác nào bị chặn.
- Có tầng kiểm chứng bằng mã nguồn. Kết quả không đạt kiểm chứng thì bị loại, và
  hệ thống hành xử đúng như khi không gọi gì cả.

---

## 3. QUY TRÌNH NGHIỆP VỤ

### QT-01. Tra cứu một từ

```
Người dùng                 Ứng dụng                      Dữ liệu
    │                         │                             │
    ├─ nhập "renshi" ────────►│                             │
    │                         ├─ khử dấu chuỗi tìm kiếm     │
    │                         ├─ truy vấn word + char ─────►│
    │                         │◄──── danh sách ứng viên ────┤
    │                         ├─ xếp hạng theo HSK, tần suất│
    │◄── danh sách kết quả ───┤                             │
    │                         │                             │
    ├─ chọn 认识 ─────────────►│                            │
    │                         ├─ tách thành 认, 识          │
    │                         ├─ tra IDS và thành phần ────►│
    │                         ├─ dựng cây chiết tự          │
    │                         ├─ kiểm tra explain_cache ───►│
    │                         │   nếu chưa có và có mạng:   │
    │                         │   gọi API, kiểm chứng, lưu  │
    │◄── trang chi tiết ──────┤                             │
```

Nhánh lỗi:
- Không tìm thấy kết quả: gợi ý các từ có pinyin gần giống, không trả về trang trắng.
- Không có mạng khi cần giải thích: hiển thị đầy đủ dữ liệu từ điển, ẩn khối giải
  thích kèm dòng ghi chú, không báo lỗi chặn thao tác.

### QT-02. Nhập cả quyển sách và tách bài

Bước 1. Người dùng chọn tệp PDF.

Bước 2. Hệ thống xác định loại PDF theo từng trang, không phân loại cả quyển:
- Với mỗi trang, gọi `page.get_text()` rồi đếm số ký tự thuộc khối CJK thu được.
  Dưới 20 ký tự thì coi trang đó là trang ảnh, cần OCR.
- Lấy mẫu 20 trang rải đều toàn sách. Dưới 10% số trang mẫu là trang ảnh thì xử
  lý như PDF số; trên 90% thì như PDF scan; ở khoảng giữa là sách hỗn hợp, mỗi
  trang được xử lý theo loại của chính nó.
- Không phân loại nhị phân cả quyển vì sách quét lại thường có bìa và mục lục
  đánh máy còn ruột là ảnh, và ngược lại PDF số vẫn có thể chèn vài trang chụp.
  Ngưỡng 20 ký tự nhằm loại trừ text layer rác do máy quét sinh ra.

Bước 3. Xác định ranh giới bài học, theo thang năm nấc, dừng ở nấc đầu tiên đạt.
Một nấc được coi là đạt khi thoả cả bốn điều kiện, nếu không thì chuyển xuống nấc
kế tiếp:
- Tìm được từ 5 mốc bài trở lên.
- Các khoảng trang tăng dần và không chồng lấn nhau.
- Không bài nào dài quá 3 lần độ dài trung vị của các bài.
- Tổng số trang thuộc các bài chiếm ít nhất 60% số trang của tệp.

| Nấc | Cách làm | Điều kiện áp dụng | Gọi mạng |
|---|---|---|---|
| 1 | Đọc outline nhúng bằng `doc.get_toc()` | PDF có mục lục nhúng | không |
| 2 | Phân tích trang mục lục in, hiệu chỉnh độ lệch số trang | Có trang mục lục đọc được | không |
| 3 | Mô hình ngôn ngữ đề xuất mốc từ bản tóm lược cấu trúc, xem QT-02b | Bật FR-50 và có mạng | có |
| 4 | Quét mẫu `第\s*[一二三四五六七八九十\d]+\s*课`, lọc theo cỡ chữ | Tiêu đề bài in rõ **và là PDF số** | không |
| 5 | Người dùng tự nhập khoảng trang cho từng bài | Luôn khả dụng | không |

Nấc đã dùng được ghi vào `book.split_method` để phục vụ đo đạc ở EV-01 và EV-09.

Nấc 4 chỉ có tác dụng với PDF số. Trên bản quét, đo thật cho kết quả bằng 0: quét
mẫu trên dải trên của cả 270 trang, rồi OCR toàn trang trên 26 trang lấy mẫu, rồi
thử lại với `--psm 11`, cả ba lần đều không tìm được một mốc nào. Nguyên nhân không
phải OCR kém — thân bài đọc rất sạch — mà là tiêu đề bài in dạng đồ hoạ trang trí,
nằm ngoài khả năng nhận dạng của công cụ OCR dòng văn bản. Vì vậy với sách quét,
nấc 3 không phải tuỳ chọn cho vui mà là phương án tự động duy nhất còn lại.

Nấc 3 đặt sau nấc 2 chứ không đặt đầu tiên, dù nó chính xác hơn trên sách khó.
Lý do: outline nhúng và mục lục in là dữ liệu do nhà xuất bản khai báo, đọc tức
thì, miễn phí và ngoại tuyến. Gọi API trước khi thử hai nguồn đó là trả tiền và
trả thời gian cho một việc đã có sẵn đáp án. Nấc 3 đặt trước nấc 4 vì trên sách
trình bày không đều, mô hình đọc được nhịp lặp của cả quyển, còn regex chỉ nhìn
được từng trang rời.

Quy tắc suy ra ranh giới sau khi đã có danh sách mốc bắt đầu:
- `page_end` của bài i là `page_start` của bài i+1 trừ 1.
- `page_end` của bài cuối lấy theo mốc bắt đầu của mục sau cùng trong outline
  hoặc mục lục, tức phần phụ lục, đáp án hoặc bảng từ vựng cuối sách, trừ 1.
  Không xác định được thì lấy trang cuối của tệp và đặt `confidence = 0.5`.
- Các mục có tiêu đề dạng 复习, 单元 hoặc Review được ghi nhận thành bản ghi
  `lesson` riêng với `index_no` âm, để không tính vào tiến độ nhưng cũng không bị
  gộp nhầm vào bài liền trước.
- `page_offset` chỉ được tính khi tìm được ít nhất hai cặp (số trang in, chỉ số
  trang PDF) cho ra cùng một hiệu số. Sách đánh số nhiều đoạn riêng biệt thì để
  `page_offset = NULL` và hiển thị chỉ số trang PDF cho người dùng.

Bước 4a. PDF số: đọc trực tiếp text và thuộc tính cỡ chữ qua `page.get_text("dict")`.

Bước 4b. Trang ảnh: kết xuất ở 300 DPI, chạy OCR, suy ra cỡ chữ từ chiều cao hộp
bao. Xử lý và giải phóng từng trang một, không giữ toàn bộ ảnh trong bộ nhớ. Chạy
trong luồng nền, hiển thị tiến độ theo trang, cho phép huỷ.

Bước 5. Chỉ đến đây mới kiểm tra sách có phải tiếng Trung hay không, vì trước khi
OCR thì trang ảnh luôn không có ký tự CJK nào. Quét 5 trang đã đọc được mà không
thấy ký tự CJK thì cảnh báo, vẫn cho người dùng tiếp tục.

Bước 6. Hiển thị bảng kết quả tách bài để người dùng xác nhận. Bước này bắt buộc,
không được bỏ qua kể cả khi nấc 1 đạt.

Bước 7. Lưu `book` và `lesson` trong một giao dịch, đặt `book.import_state =
'importing'`. Sách ở trạng thái này chưa hiện trong thư viện.

Bước 8. Chạy QT-03 cho từng bài. Bước này chạy hoàn toàn cục bộ, không gọi API.
Xong thì đặt `book.import_state = 'ready'` và ghi `imported_at`.

Bước 9. Việc chữa các dòng còn cờ `needs_review` bằng mô hình ngôn ngữ là một thao
tác riêng, do người dùng chủ động bấm ở màn hình Sách, có hiện trước số dòng và số
lần gọi API dự kiến. Tách ra như vậy để NFR-03 và NFR-04 đo được, và để toàn bộ
luồng nhập sách không phụ thuộc mạng.

### QT-02b. Nấc 3 — đề xuất ranh giới bằng mô hình ngôn ngữ

Ý tưởng: không đưa nội dung sách cho mô hình, mà đưa **hình dạng** của quyển sách.
Bài toán tách bài về bản chất là nhận ra một nhịp lặp trong dãy 248 trang. Con
người nhìn ra nhịp đó trong vài giây khi lướt qua sách; regex thì không, vì nó chỉ
nhìn được một trang tại một thời điểm. Mô hình ngôn ngữ nhìn được cả dãy cùng lúc,
và đó đúng là việc nó làm giỏi.

**Bước 1. Dựng bản tóm lược cấu trúc.** Với mỗi trang, trích ra vài trường rẻ tiền,
mỗi trang một dòng. Không đưa nội dung trang vào.

| Trường | Cách lấy |
|---|---|
| `id` | Số thứ tự dòng trong chính bản tóm lược này, đánh liên tục từ 1 |
| `pdf_page` | Chỉ số trang trong tệp, tính từ 0 |
| `folio` | Số trang in đọc được ở lề trên hoặc lề dưới, rỗng nếu không có |
| `max_size` | Cỡ chữ lớn nhất trên trang, làm tròn tới 0.5 |
| `head` | Dòng có cỡ chữ lớn nhất nằm trong 25% chiều cao phía trên trang, cắt còn 30 ký tự |
| `cjk` | Số ký tự CJK trên trang, làm tròn tới hàng chục |
| `ink_top` | Tỷ lệ điểm ảnh tối trong dải trên, đo ở 45 DPI, không cần OCR |
| `ratio` | `ink_top` chia độ dài văn bản OCR đọc được ở dải trên |

Hai trường cuối là bổ sung của bản 0.5 và là trường quan trọng nhất trong bảng.
Trang mở đầu bài có **nhiều mực nhưng ít chữ đọc được**, vì tiêu đề là đồ hoạ; nên
`ratio` của nó vọt lên gấp nhiều lần trung vị. Đo trên giáo trình thật, ngưỡng
`ratio > 8 lần trung vị` cho ra dãy mốc:

```
36 48 54 61 67 73 81 88 96 103 110 117 124 131 138 144
151 158 166 173 179 185 192 199 207 214 220 227 234

khoảng cách:  7 6 7 6 6 8 7 8 7 7 7 7 7 7 6 7 7 8 7 6 6 7 7 8 7 6 7 7
```

Nhịp 6 đến 8 trang, đều đặn suốt cả quyển, trong khi mẫu `第X课` tìm được đúng 0 kết
quả trên cùng quyển đó. Cấu trúc bài học tồn tại rất rõ, chỉ là nó không nằm trong
văn bản. Đây là lý do bản tóm lược không được chỉ chứa trường văn bản.

Ví dụ một đoạn bản tóm lược:

```
id   pdf_page  folio  max_size  head                cjk
...
45   44        10     10.5      语音练习            420
46   45        11     10.5      (rỗng)              380
47   46        12     22.0      第一课 你好         210
48   47        13     10.5      课文                450
...
62   61        27     10.5      练习                390
63   62        28     22.0      第二课 汉语很有意思  230
```

Cả quyển 248 trang cho ra khoảng 6 đến 7 nghìn token. Một lần gọi, vài giây, chi
phí không đáng kể kể cả với hạn mức miễn phí. So sánh: gửi toàn văn 248 trang là
khoảng 250 nghìn token, tức là gấp gần 40 lần, và với sách quét thì còn phải OCR
toàn bộ trước khi gửi.

**Bước 2. Gọi mô hình, yêu cầu chọn chứ không yêu cầu sinh.** Đây là điểm quan
trọng nhất của cả quy trình. Mô hình ngôn ngữ giữ chính xác một dãy số dài rất kém:
nó sẽ trả về danh sách số trang trông hoàn toàn hợp lý, tăng dần, cách đều, nhưng
lệch một hai trang ở vài chỗ. Loại sai này nguy hiểm hơn sai lộ liễu vì nó qua được
mọi kiểm tra hình thức. Cách chặn là không cho mô hình đánh máy dữ kiện, chỉ cho nó
quyền chọn: yêu cầu trả về `id` của dòng trong bản tóm lược, rồi mã nguồn tra ngược
ra `pdf_page`.

Lược đồ JSON bắt buộc:

```json
{
  "lessons": [
    {
      "anchor_id":   47,
      "lesson_no":   1,
      "title":       "你好",
      "kind":        "lesson",
      "confidence":  0.95
    }
  ],
  "back_matter_anchor_id": 231,
  "notes": "Sách có phần 复习 sau mỗi 4 bài."
}
```

- `anchor_id` bắt buộc là một `id` có thật trong bản tóm lược đã gửi. Đây là trường
  duy nhất quyết định vị trí, và nó không phải số do mô hình nghĩ ra.
- `kind` nhận `lesson` cho bài học thường, `review` cho các mục 复习, 单元 hoặc
  Review. Mục `review` được lưu với `index_no` âm theo đúng quy tắc ở Bước 3.
- `back_matter_anchor_id` là mốc bắt đầu của phần phụ lục, đáp án hoặc bảng từ vựng
  cuối sách. Trường này giải quyết bài toán `page_end` của bài cuối.
- Prompt nêu rõ: chỉ được chọn trong các `id` đã cho, không được suy đoán trang
  không có trong bảng, không chắc thì hạ `confidence` chứ không bỏ trống.

**Bước 3. Kiểm chứng bằng mã nguồn.** Khác với FR-13, ranh giới bài là thứ kiểm
chứng được hoàn toàn tự động, nên tầng này chặt hơn nhiều:

| # | Điều kiện | Xử lý khi vi phạm |
|---|---|---|
| 1 | Mọi `anchor_id` tồn tại trong bản tóm lược đã gửi | Loại phần tử đó |
| 2 | `pdf_page` tương ứng tăng nghiêm ngặt theo thứ tự trả về | Loại toàn bộ kết quả |
| 3 | `lesson_no` của các mục `kind = "lesson"` liên tiếp từ 1, không trùng, không nhảy | Loại toàn bộ kết quả |
| 4 | Trang được chọn phải chứa mẫu tiêu đề bài, hoặc phải có `max_size` lớn nhất trong khoảng 5 trang quanh nó | Hạ `confidence` xuống 0.4 |
| 5 | Khoảng cách giữa hai mốc liền nhau nằm trong [trung vị chia 3, trung vị nhân 3] | Hạ `confidence` xuống 0.4 |
| 6 | Số mốc từ 5 trở lên và tổng số trang thuộc các bài chiếm ít nhất 60% số trang tệp | Loại toàn bộ kết quả |

Quá hai lần hạ `confidence` thì coi như nấc 3 không đạt và rơi xuống nấc 4. Kết quả
bị loại toàn bộ cũng rơi xuống nấc 4. Không có trường hợp nào kết quả của mô hình
được ghi thẳng vào cơ sở dữ liệu mà không qua bảng xác nhận ở Bước 6 của QT-02.

**Bước 4. Quy đổi ra ranh giới.** Áp đúng bộ quy tắc đã nêu ở Bước 3 của QT-02:
`page_end` của bài i là `page_start` của bài i+1 trừ 1, còn `page_end` của bài cuối
lấy từ `back_matter_anchor_id` trừ 1.

**Bước 5. Luồng OCR ba tầng cho sách quét.** Bản 0.4 mô tả luồng này thành hai tầng
và ước lượng bằng cảm tính. Sau khi đo trên sách thật, luồng đúng là ba tầng, và
phần lớn công việc lọc lại nằm ở tầng rẻ nhất.

| Tầng | Làm gì | Phạm vi | Đo được |
|---|---|---|---|
| 0 | Đo `ink_top`, **không OCR một chữ nào** | cả 270 trang | **10 giây** |
| 1 | OCR dải trên, lấy `head` và `folio` | chỉ các trang ứng viên của tầng 0, khoảng 40 | **35 giây** |
| 2 | OCR toàn trang ở 200 DPI, `chi_sim+vie` | chỉ trang cần thật: mở đầu bài và bảng từ mới, khoảng 60 | **6,4 phút** |
| | **Tổng** | | **7,2 phút** |

So với OCR toàn bộ 270 trang: **29 phút**. Nhanh hơn bốn lần, và toàn bộ phần tiết
kiệm đến từ chỗ tầng 0 gần như miễn phí.

Bản 0.4 đặt tầng 1 chạy trên cả quyển. Đo lại cho thấy đó là lãng phí: OCR 270 dải
trên mất 234 giây trong khi chỉ cần OCR 40 dải, mất 35 giây. Sai lầm nằm ở thứ tự
tầng chứ không ở hiệu năng — đặc trưng rẻ nhất phải chạy trước và làm phần lớn việc
lọc.

Ngôn ngữ OCR bắt buộc là `chi_sim+vie`, không phải `chi_sim` đơn thuần. Giáo trình
dùng ở Việt Nam thường là bản tam ngữ; với `chi_sim` đơn thuần, chuỗi "giáo viên
dạy" bị nhận thành "gido vien day", mất toàn bộ dấu. Chế độ phân trang dùng `psm 6`;
đo trên cùng một trang, `psm 6` cho 132 span còn `psm 4` cho 123 và `psm 11` cho 107.

**Bước 6. Sách quá dài.** Bản tóm lược của sách trên 600 trang có thể vượt cửa sổ
ngữ cảnh thoải mái. Chia thành các lô 300 trang có chồng lấn 20 trang, gọi nhiều
lần, ghép kết quả rồi khử trùng lặp theo `pdf_page`. Mốc xuất hiện ở vùng chồng lấn
của hai lô mà không khớp nhau thì bỏ, để nấc 4 xử lý phần đó.

### QT-03. Bóc tách bảng từ mới

Áp dụng cho từng bài sau khi đã có khoảng trang.

Bước 1. Định vị phần từ mới: tìm tiêu đề `生词`, `生词表`, `New Words` trong khoảng
trang của bài. Không tìm thấy thì không được lấy toàn bộ bài đem đi bóc tách, vì
quét cả phần bài đọc bằng các mẫu ở Bước 3 sẽ sinh ra hàng trăm dòng rác. Thay vào
đó để trống danh sách từ mới, đặt cờ `needs_review` cho cả bài, và mở giao diện cho
người dùng khoanh vùng trang chứa bảng từ mới.

Bước 2. Tách cột bằng biểu đồ chiếu đứng, không bằng ngưỡng khe. Bản 0.4 ghi
"gom theo hoành độ thành cột", và cách hiểu tự nhiên của câu đó là so khoảng cách
giữa hai từ liền nhau với một ngưỡng. Đo trên bảng thật cho thấy cách đó **không thể
đúng**:

| | Đo được |
|---|---|
| Khe giữa hai từ **trong cùng một cột** | trung vị 9 px, phân vị 90 **78 px**, tối đa 116 px |
| Khe **giữa hai cột** | **28 đến 40 px** |

Khe trong cột rộng gấp đôi khe giữa cột, vì các cột nghĩa là văn bản xuống dòng chữ
thưa trong khi các cột lại xếp sát nhau. Không tồn tại ngưỡng cục bộ nào tách đúng.

Cách đúng là phép đo toàn cục: dựng **biểu đồ chiếu đứng** của toàn khối bảng, tức
là với mỗi hoành độ x đếm số span phủ lên nó, rồi tìm những dải x có giá trị **bằng
0 liên tục suốt chiều cao khối**. Mỗi dải như vậy là một khe cột. Trên bảng thật,
phép này tìm đúng năm khe rộng 28 đến 40 px.

Ngưỡng: dải rỗng rộng từ 20 px trở lên, sau khi đã chuẩn hoá ảnh về 200 DPI.

Một ngoại lệ phải xử lý riêng: khe giữa cột số thứ tự và cột chữ Hán hẹp hơn 12 px,
dưới ngưỡng phát hiện, nên biểu đồ chiếu gộp hai cột đó làm một. Tách tiếp cột trái
ngoài cùng bằng tiền tố toàn chữ số.

Bước 3. Chia hàng theo cột số thứ tự, rồi mới bóc tách trường.

Một dòng văn bản **không** tương ứng một mục từ. Ô nghĩa thường xuống dòng: trên
bảng thật, mục 来 có định nghĩa tiếng Anh chiếm bốn dòng. Mốc chia hàng phải là ô có
số trong cột số thứ tự; mọi dòng nằm giữa hai số liên tiếp thuộc về cùng một mục.

Bảng từ mới của giáo trình dùng ở Việt Nam có **bảy cột**, không phải bốn hay năm
như bản 0.4 giả định:

```
STT │ Chữ Hán │ Pinyin │ Từ loại │ Âm Hán-Việt │ Nghĩa Anh │ Nghĩa Việt
```

Cột Âm Hán-Việt là phát hiện đáng giá nhất: sách in sẵn 同学 là đồng học, 介绍 là
giới thiệu, 的 là đích. Trường `hanviet` mà bản 0.4 dự tính phải soạn thủ công thì
đã có nguồn ngay trong giáo trình, nên `lesson_word` được bổ sung cột `hanviet_src`.

Nhận dạng từng trường trong hàng:

| Trường | Cách nhận dạng |
|---|---|
| Số thứ tự | Chuỗi số ở đầu dòng, theo sau là dấu chấm hoặc khoảng trắng |
| Chữ Hán | Chuỗi ký tự liên tiếp trong khối Unicode CJK |
| Từ loại | Ký tự đơn trong ngoặc đơn: (名) (动) (形) (副) (量) (代) |
| Pinyin | Chuỗi Latin chứa ít nhất một trong các ký tự dấu thanh āáǎà… |
| Nghĩa | Phần còn lại của dòng |

Khi đã tách được cột bằng biểu đồ chiếu thì phần lớn các trường trên được xác định
bằng **vị trí cột** chứ không bằng biểu thức chính quy; các mẫu ở bảng trên chỉ dùng
để đối chiếu và để xử lý trang mà biểu đồ chiếu không tìm đủ khe.

Trường Nghĩa chỉ được lấy là phần còn lại của dòng khi đã tách được ít nhất hai
trong ba trường Chữ Hán, Pinyin, Từ loại. Dòng chỉ có chữ Hán mà không có pinyin
thì bỏ hẳn, vì gần như chắc chắn là câu trong bài đọc chứ không phải mục từ.

Bước 4. Kiểm chứng mọi dòng trước khi lưu:
- Từng chữ Hán phải tồn tại trong bảng `char`.
- Số âm tiết pinyin phải bằng số chữ Hán.
- Với mỗi chữ, âm tiết pinyin tương ứng phải khớp một dòng trong `char_reading`.
  So khớp thực hiện trên `pinyin_plain`, tức là bỏ thanh điệu trước khi so. Bắt
  buộc phải như vậy vì trong từ ghép rất nhiều âm tiết đọc khinh thanh: 识 shí đọc
  thành shi trong 认识, 字 zì thành zi trong 名字, 友 yǒu thành you trong 朋友,
  谢 xiè thành xie trong 谢谢. So khớp có kèm thanh điệu sẽ gắn cờ sai gần như
  toàn bộ bảng từ mới của mọi giáo trình.
- Không đạt một trong ba điều kiện: vẫn lưu, nhưng đặt `needs_review = 1`.

Bước 5. Lưu vào bảng `lesson_word` với `extract_by = 'regex'`.

Bước 6, tuỳ chọn, do người dùng chủ động kích hoạt. Gửi các dòng còn cờ
`needs_review` sang mô hình ngôn ngữ kèm lược đồ JSON bắt buộc, rồi chạy lại đúng
Bước 4 trên kết quả trả về. Đạt thì cập nhật dòng, đặt `extract_by = 'llm'` và
`needs_review = 0`; không đạt thì giữ nguyên dòng cũ. Đây là chức năng FR-28.

Bước 7, tuỳ chọn, mặc định tắt. Với bài mà Bước 3 hỏng quá nửa số dòng, gửi ảnh
trang chứa bảng 生词表 cho mô hình thị giác, yêu cầu trả về đúng lược đồ JSON của
`lesson_word`. Đây là chức năng FR-51.

Lý do có nhánh này: bảng 生词表 in hai cột là ca khó nhất của toàn bộ luồng nhập, và
là ca mà mô hình thị giác xử lý tốt hơn hẳn biểu thức chính quy, vì nó đọc được cấu
trúc bảng chứ không đọc theo dòng văn bản. Chi phí một ảnh cho mỗi bài, khoảng 15
lần gọi cho cả quyển.

Kết quả từ Bước 7 chạy qua đúng tầng kiểm chứng ở Bước 4, không có ngoại lệ, và
được lưu với `extract_by = 'vision'`. Mặc định tắt vì đây là chức năng duy nhất gửi
ảnh nội dung sách ra khỏi máy người dùng.

### QT-04. Học và ôn tập

Bước 1. Người dùng chọn một bài, xem danh sách từ mới.

Bước 2. Thêm từ lẻ hoặc cả bài vào danh sách ôn tập. Hệ thống tạo bản ghi `progress`
với `status = 'new'`, `interval_days = 0`, `ease = 2.5`, `due_date = hôm nay`, và
`source_lw_id` trỏ tới dòng `lesson_word` đã sinh ra nó. Từ đã có trong `progress`
thì giữ nguyên tiến độ cũ và không đổi `source_lw_id`, để mặt sau của thẻ luôn hiển
thị đúng nghĩa của quyển sách mà người dùng gặp từ đó lần đầu.

Bước 3. Vào màn hình ôn tập, hệ thống lấy các từ có `due_date <= hôm nay`.

Bước 4. Hiển thị mặt trước là chữ Hán. Người dùng tự nhớ rồi bấm hiện đáp án.

Bước 5. Người dùng tự đánh giá ở ba mức. SM-2 gốc dùng thang chất lượng q từ 0 đến
5, nên ba nút phải được ánh xạ tường minh trước khi áp công thức:

| Nút | q | Xử lý bậc lặp |
|---|---|---|
| Quên | 2 | `interval_days = 1`, `lapse_count += 1` |
| Khó | 3 | giữ nguyên bậc, `interval_days = làm tròn(interval_days × 1.2)` |
| Nhớ | 5 | lên bậc theo SM-2 |

Hệ số dễ cập nhật theo công thức gốc `ease = ease + (0.1 − (5−q)(0.08 + (5−q)·0.02))`,
chặn dưới ở 1.3. Bậc lặp khi bấm Nhớ: lần đúng thứ nhất `interval_days = 1`, lần thứ
hai `= 6`, từ lần thứ ba trở đi `= làm tròn(interval_days × ease)`. Mỗi lần đánh giá
ghi một dòng vào `review_log` và tăng `review_count`.

Bước 6. Chuyển trạng thái:
- `new` sang `learning` ngay ở lần ôn đầu tiên.
- `learning` sang `known` khi `interval_days >= 21`.
- `known` trở lại `learning` khi người dùng bấm Quên.

Từ ở trạng thái `known` vẫn tiếp tục được lên lịch ôn, chỉ khác ở chỗ được tính vào
thống kê. Hai con số dễ nhầm phải được gọi bằng hai tên khác nhau ở mọi màn hình:
"đang theo dõi" là số dòng trong `progress`, "đã thuộc" là số dòng có
`status = 'known'`.

### QT-05. Sinh giải thích chiết tự

Cùng với Bước 6 của QT-03, đây là một trong hai chỗ duy nhất phụ thuộc dịch vụ
ngoài. Cả hai được thiết kế để mô hình ngôn ngữ không bao giờ là nguồn dữ kiện, mà
chỉ là lớp diễn đạt hoặc lớp chữa lỗi có kiểm chứng.

```
1. Tra cứu cục bộ, thu thập:  bộ thủ và dạng chuẩn của bộ, nghĩa bộ, thành
                              phần, IDS, nghĩa từng thành phần, dạng phồn thể
2. Kiểm tra explain_cache. Khoá là chuỗi đang xét: chữ đơn khi tra một chữ,
   cả từ khi tra từ ghép. Bắt buộc như vậy vì phần diễn giải của từ ghép nói
   về quan hệ giữa các chữ, không quy về diễn giải của từng chữ rời.
   ├─ có: trả về ngay, không gọi mạng
   └─ không có, tiếp bước 3
3. Dựng prompt: đưa TOÀN BỘ dữ kiện ở bước 1 vào, yêu cầu chỉ diễn giải
   dựa trên dữ kiện đã cho, cấm bổ sung thông tin mới
4. Gọi API, yêu cầu trả JSON theo lược đồ cố định
5. Kiểm chứng: mọi chữ Hán xuất hiện trong kết quả phải nằm trong tập cho
   phép, gồm các chữ đã đưa vào ở bước 1, cộng dạng chuẩn của bộ thủ và
   dạng phồn thể của chúng. Có chữ ngoài tập thì gọi lại đúng một lần với
   chỉ dẫn nhắc lại ràng buộc; lần hai vẫn sai thì bỏ hẳn khối diễn giải,
   chỉ hiển thị phần chiết tự dạng bảng, không báo lỗi cho người dùng.
6. Lưu vào explain_cache, hiển thị kèm nhãn ghi rõ nguồn gốc
```

---

## 4. KIẾN TRÚC VÀ CÔNG NGHỆ

### 4.1. Sơ đồ phân lớp

```
┌─────────────────────────────────────────────────────────┐
│  LỚP GIAO DIỆN                                          │
│  PySide6 · cửa sổ chính, 4 màn hình, luồng nền          │
└────────────────────────┬────────────────────────────────┘
                                                          │
┌────────────────────────▼────────────────────────────────┐
│  LỚP NGHIỆP VỤ                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ lookup   │ │decomposer│ │ importer │ │ scheduler  │  │
│  │ tra cứu  │ │ chiết tự │ │ nhập PDF │ │ SM-2       │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└────────┬───────────────────────┬────────────────┬───────┘
         │                       │                        │
┌────────▼──────────┐  ┌─────────▼────────┐  ┌────▼───────┐
│  LỚP DỮ LIỆU      │  │  LỚP XỬ LÝ TÀI   │  │ LỚP DỊCH   │
│  SQLite           │  │  LIỆU            │  │ VỤ NGOÀI   │
│  dict.sqlite      │  │  PyMuPDF         │  │ Google AI  │
│  user.sqlite      │  │  PaddleOCR       │  │ Studio API │
└───────────────────┘  └──────────────────┘  └────────────┘
```

### 4.2. Công nghệ sử dụng

| Lớp | Công nghệ | Phiên bản | Lý do lựa chọn |
|---|---|---|---|
| Ngôn ngữ | Python | 3.12 | Toàn bộ thư viện xử lý ảnh và OCR đều là Python |
| Giao diện | PySide6 | 6.x | Cùng ngôn ngữ với lớp nghiệp vụ, không cần cầu nối |
| Đọc PDF | PyMuPDF | 1.24+ | Đọc được cả text layer và thuộc tính cỡ chữ |
| OCR | PaddleOCR | 3.x, PP-OCRv5 | Hỗ trợ chữ Hán giản thể, chữ viết dọc, chạy cục bộ |
| Cơ sở dữ liệu | SQLite | 3.x | Không cần máy chủ, một tệp, phù hợp app desktop |
| Dịch vụ ngoài | Google AI Studio API | Gemini | Ba việc: diễn đạt (FR-13), chữa dòng hỏng (FR-28), đề xuất ranh giới bài (FR-50). Mọi đầu ra đều qua kiểm chứng bằng mã nguồn |
| Nguồn từ điển | Unihan | UCD mới nhất | Bộ thủ, số nét, âm Hán-Việt, nghĩa gốc |
| Nguồn từ ghép | CC-CEDICT | bản mới nhất | Nghĩa của từ ghép, giấy phép CC-BY-SA |
| Nguồn chiết tự | cjkvi-ids, chaizi | — | Cây IDS và thành phần cấu tạo |
| Đóng gói | PyInstaller | 6.x | Xuất tệp thực thi Windows |

### 4.3. Lý do tách hai tệp cơ sở dữ liệu

`dict.sqlite` là dữ liệu tra cứu, đóng gói kèm sản phẩm, chỉ đọc, khoảng 85 MB.
`user.sqlite` là dữ liệu học tập của người dùng, tạo lúc chạy lần đầu, nhỏ.

Tách ra để: nâng cấp từ điển không làm mất dữ liệu học tập; sao lưu chỉ cần chép
một tệp nhỏ; và có thể mở `dict.sqlite` ở chế độ chỉ đọc, tránh hỏng dữ liệu.

---

## 5. CƠ SỞ DỮ LIỆU

### 5.1. Sơ đồ quan hệ

```
        dict.sqlite (chỉ đọc)              user.sqlite (đọc ghi)
   ┌──────────────────────────┐      ┌──────────────────────────────┐
   │                          │      │                              │
   │  radical                 │      │   book                       │
   │    idx (PK)              │      │     id (PK)                  │
   │      ▲                   │      │       │ 1                    │
   │      │ 1                 │      │       │                      │
   │      │                   │      │       ▼ N                    │
   │      │ N                 │      │   lesson                     │
   │  char ────────┐          │      │     id (PK)                  │
   │    char (PK)  │ 1        │      │     book_id (FK)             │
   │      ▲        │          │      │       │ 1                    │
   │      │ 1      ▼ N        │      │       ▼ N                    │
   │      │    char_part      │      │   lesson_word                │
   │      │      char (FK)    │      │     lesson_id (FK)           │
   │      │      part         │      │     word ─────────┐          │
   │      │                   │      │                   │          │
   │  word│                   │      │   progress ◄──────┘          │
   │    word_simp             │      │     word (PK)                │
   │                          │      │       │ 1                    │
   │                          │      │       ▼ N                    │
   │                          │      │   review_log                 │
   │                          │      │                              │
   │                          │      │   explain_cache              │
   │                          │      │   setting                    │
   └──────────────────────────┘      └──────────────────────────────┘

   Liên kết giữa hai tệp là liên kết logic qua giá trị chữ Hán,
   không phải khoá ngoại ràng buộc, vì SQLite không ràng buộc
   khoá ngoại xuyên tệp.
```

### 5.2. Định nghĩa bảng — dict.sqlite

```sql
-- Chữ đơn. Nguồn: Unihan, cjkvi-ids, chaizi.
CREATE TABLE char (
    char           TEXT PRIMARY KEY,  -- ký tự, ví dụ '认'
    codepoint      TEXT,              -- 'U+8BA4'
    pinyin         TEXT,              -- 'rèn', có dấu thanh
    pinyin_plain   TEXT,              -- 'ren', đã khử dấu, dùng để tìm kiếm
    meaning_en     TEXT,              -- nghĩa tiếng Anh từ Unihan
    meaning_vi     TEXT,              -- nghĩa tiếng Việt, bổ sung thủ công
    hanviet        TEXT,              -- âm Hán-Việt, ví dụ 'nhận'
    radical_idx    INTEGER,           -- số hiệu bộ thủ, 1..214
    radical_stroke INTEGER,           -- số nét còn lại ngoài bộ
    total_strokes  INTEGER,           -- tổng số nét
    trad_form      TEXT,              -- dạng phồn thể tương ứng, ví dụ '認'
    ids            TEXT,              -- chuỗi IDS, ví dụ '⿰讠人'
    hsk_level      INTEGER,           -- 1..6, NULL nếu ngoài danh sách HSK
    freq_rank      INTEGER            -- thứ hạng tần suất, càng nhỏ càng phổ biến
);

-- Toàn bộ âm đọc của một chữ. Phải là bảng riêng chứ không phải một cột, vì chữ
-- đa âm (了, 和, 长, 行, 得...) có nhiều âm hợp lệ. Quy trình kiểm chứng ở QT-03
-- bước 4 đối chiếu với bảng này chứ không đối chiếu với cột char.pinyin.
CREATE TABLE char_reading (
    char         TEXT NOT NULL,
    pinyin       TEXT NOT NULL,      -- 'rèn', có dấu thanh
    pinyin_plain TEXT NOT NULL,      -- 'ren', đã khử dấu và khử thanh
    is_primary   INTEGER DEFAULT 0,  -- 1 với âm đọc phổ biến nhất
    PRIMARY KEY (char, pinyin)
);

-- Thành phần cấu tạo. Một chữ có thể có nhiều cách chiết tự.
CREATE TABLE char_part (
    char     TEXT NOT NULL,               -- chữ được phân tách
    part     TEXT NOT NULL,               -- một thành phần
    variant  INTEGER NOT NULL DEFAULT 0,  -- 0 là cách chính, 1 trở đi là cách thay thế
    order_no INTEGER NOT NULL,            -- vị trí thành phần theo thứ tự đọc của chuỗi IDS
    PRIMARY KEY (char, variant, order_no)
);

-- Từ ghép. Nguồn: CC-CEDICT, bổ sung nghĩa tiếng Việt và từ loại thủ công.
-- Một dạng chữ có thể ứng với nhiều mục từ khác âm khác nghĩa, nên phải có id
-- riêng, không thể lấy word_simp làm khoá chính.
CREATE TABLE word (
    id             INTEGER PRIMARY KEY,
    word_simp      TEXT NOT NULL,   -- dạng giản thể, ví dụ '认识'
    word_trad      TEXT,            -- dạng phồn thể, ví dụ '認識'
    pinyin_num     TEXT,            -- nguyên bản CC-CEDICT, 'ren4 shi5'
    pinyin_tone    TEXT,            -- dạng có dấu để hiển thị và cho FR-02, 'rènshi'
    pinyin_plain   TEXT,            -- khử dấu, khử khoảng trắng, 'renshi', cho FR-03
    pinyin_numeric TEXT,            -- khử khoảng trắng, giữ số thanh, 'ren4shi5', cho FR-03
    pos            TEXT,            -- từ loại: 名, 动, 形... phục vụ FR-06
    meaning_en     TEXT,            -- các nghĩa nối bằng dấu chấm phẩy
    meaning_vi     TEXT,            -- nghĩa tiếng Việt, phục vụ FR-04 và FR-06
    hsk_level      INTEGER,
    freq_rank      INTEGER          -- thứ hạng tần suất của từ, phục vụ FR-05
);

-- 214 bộ thủ Khang Hy. Nhập thủ công.
CREATE TABLE radical (
    idx        INTEGER PRIMARY KEY,  -- 1..214
    glyph      TEXT,                 -- dạng chuẩn, ví dụ '言'
    glyph_alt  TEXT,                 -- dạng biến thể khi đứng trong chữ, '讠'
    name_hv    TEXT,                 -- tên Hán-Việt, 'ngôn'
    meaning_vi TEXT,                 -- 'lời nói'
    strokes    INTEGER               -- số nét của bộ
);

CREATE INDEX idx_char_pyplain  ON char(pinyin_plain);
CREATE INDEX idx_char_radical  ON char(radical_idx);
CREATE INDEX idx_reading_char  ON char_reading(char);
CREATE INDEX idx_reading_plain ON char_reading(pinyin_plain);
CREATE INDEX idx_part_char     ON char_part(char);
CREATE INDEX idx_part_part     ON char_part(part);
CREATE INDEX idx_word_simp     ON word(word_simp);
CREATE INDEX idx_word_pyplain  ON word(pinyin_plain);
CREATE INDEX idx_word_pynum    ON word(pinyin_numeric);
CREATE INDEX idx_word_freq     ON word(freq_rank);

-- Tìm kiếm theo nghĩa (FR-04) phải dùng chỉ mục toàn văn. Dùng LIKE '%...%' trên
-- vài chục nghìn dòng nghĩa sẽ không giữ được NFR-01 dưới 200 ms.
CREATE VIRTUAL TABLE word_fts USING fts5(
    meaning_vi, meaning_en,
    content = 'word', content_rowid = 'id'
);
```

### 5.3. Định nghĩa bảng — user.sqlite

```sql
-- Phiên bản lược đồ. Cần có ngay từ đầu, nếu không thì lời hứa "nâng cấp từ điển
-- và ứng dụng mà không mất dữ liệu học tập" ở mục 4.3 không thực hiện được.
CREATE TABLE schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);

-- Sách đã nhập.
CREATE TABLE book (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    file_path    TEXT NOT NULL,          -- đường dẫn tới PDF gốc trên máy người dùng
    file_hash    TEXT NOT NULL UNIQUE,   -- SHA-256, dùng để phát hiện nhập trùng
    page_count   INTEGER,
    page_offset  INTEGER,        -- độ lệch giữa số trang in và chỉ số trang PDF, có thể NULL
    is_scanned   INTEGER,        -- 0 là PDF số, 1 là PDF scan, 2 là hỗn hợp
    split_method TEXT,           -- 'outline' | 'toc' | 'llm' | 'heading' | 'manual'
    import_state TEXT NOT NULL,  -- 'importing' | 'ready'; chỉ 'ready' mới hiện trong thư viện
    imported_at  TEXT
);

-- Bài học trong sách.
CREATE TABLE lesson (
    id         INTEGER PRIMARY KEY,
    book_id    INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
    index_no   INTEGER NOT NULL,  -- số thứ tự bài
    title      TEXT,              -- tiêu đề gốc, ví dụ '你叫什么名字'
    page_start INTEGER NOT NULL,  -- chỉ số trang PDF, không phải số trang in
    page_end   INTEGER NOT NULL,
    confidence REAL,              -- độ tin cậy của việc tách tự động, 0..1
    UNIQUE (book_id, index_no)
);

-- Từ mới của từng bài, kèm dữ liệu lấy nguyên từ sách.
CREATE TABLE lesson_word (
    id           INTEGER PRIMARY KEY,
    lesson_id    INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
    order_no     INTEGER,   -- thứ tự trong bảng từ mới
    word         TEXT NOT NULL,
    pos          TEXT,      -- từ loại theo sách: 名, 动, 形...
    pinyin_src   TEXT,      -- pinyin in trong sách
    hanviet_src  TEXT,      -- âm Hán-Việt in trong sách, xem QT-03 bước 3
    meaning_src  TEXT,      -- nghĩa in trong sách, có thể khác từ điển
    source_page  INTEGER,
    extract_by   TEXT,      -- 'regex' | 'llm' | 'vision' | 'manual'
    needs_review INTEGER DEFAULT 0,
    UNIQUE (lesson_id, word)
);

-- Tiến độ học từng từ. Một dòng cho mỗi từ đang học.
CREATE TABLE progress (
    word          TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'new',  -- 'new' | 'learning' | 'known'
    ease          REAL DEFAULT 2.5,   -- hệ số dễ của SM-2
    interval_days INTEGER DEFAULT 0,
    due_date      TEXT,
    review_count  INTEGER DEFAULT 0,
    lapse_count   INTEGER DEFAULT 0,
    source_lw_id  INTEGER REFERENCES lesson_word(id) ON DELETE SET NULL,
                             -- dòng lesson_word dùng làm mặt sau của thẻ ôn tập;
                             -- cần có vì một từ xuất hiện ở nhiều sách với nghĩa khác nhau
    added_at      TEXT
);

-- Nhật ký ôn tập. Dùng để vẽ biểu đồ tiến độ và phân tích trong báo cáo.
CREATE TABLE review_log (
    id          INTEGER PRIMARY KEY,
    word        TEXT NOT NULL REFERENCES progress(word) ON DELETE CASCADE,
    reviewed_at TEXT NOT NULL,
    grade       INTEGER,   -- 0 quên, 1 khó, 2 nhớ, theo nút bấm
    q           INTEGER,   -- 2 | 3 | 5, giá trị sau ánh xạ sang thang SM-2, xem QT-04
    ease_after  REAL,
    interval_before INTEGER,
    interval_after  INTEGER
);

-- Bộ nhớ đệm giải thích, tránh gọi lại API và cho phép dùng ngoại tuyến.
CREATE TABLE explain_cache (
    key         TEXT PRIMARY KEY,  -- chữ đơn hoặc cả từ ghép, xem QT-05 bước 2
    payload     TEXT,      -- JSON kết quả đã kiểm chứng
    model       TEXT,      -- tên mô hình đã sinh ra nội dung này
    created_at  TEXT
);

-- Cấu hình. Khoá API lưu ở đây dưới dạng đã mã hoá.
CREATE TABLE setting (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX idx_lesson_book   ON lesson(book_id);
CREATE INDEX idx_lw_lesson     ON lesson_word(lesson_id);
CREATE INDEX idx_lw_word       ON lesson_word(word);
CREATE INDEX idx_progress_due  ON progress(due_date, status);
CREATE INDEX idx_log_word      ON review_log(word);
```

Hai điều bắt buộc khi mở kết nối, nếu thiếu thì các ràng buộc ở trên chỉ là trang trí:

```sql
PRAGMA foreign_keys = ON;   -- SQLite mặc định TẮT, ON DELETE CASCADE sẽ im lặng không chạy
PRAGMA journal_mode = WAL;  -- cho phép luồng nền nhập PDF ghi song song với giao diện đọc
```

Truy vấn nào cần dữ liệu của cả hai tệp, ví dụ FR-15 và FR-34, thì mở `user.sqlite`
rồi `ATTACH DATABASE 'dict.sqlite' AS d` và nối bảng qua giá trị chữ Hán.

### 5.4. Ghi chú thiết kế

**Vì sao `lesson_word` lưu `pinyin_src` và `meaning_src` riêng thay vì trỏ về từ
điển.** Giáo trình thường dịch nghĩa theo ngữ cảnh bài học, khác với nghĩa từ điển,
và đôi khi ghi pinyin theo cách đọc trong bài. Người học cần đúng bản của sách khi
ôn thi, nhưng vẫn cần nghĩa đầy đủ khi tra cứu. Lưu cả hai cho phép hiển thị song
song và đối chiếu, và cho phép sửa dữ liệu bóc tách sai mà không đụng vào từ điển.

**Vì sao `page_start` dùng chỉ số trang PDF chứ không dùng số trang in.** Số trang
in trên sách lệch so với chỉ số trang trong tệp do phần bìa và lời nói đầu. Lưu chỉ
số PDF để mở trang không cần tính toán, còn `book.page_offset` cho phép hiển thị số
trang in cho người dùng.

**Vì sao có cột `extract_by`.** Ghi lại phương pháp bóc tách từng dòng cho phép tính
tỷ lệ tự động hoá trong chương thực nghiệm, và giúp gỡ lỗi khi dữ liệu sai.

**Vì sao `progress` khoá theo từ chứ không theo `lesson_word.id`.** Một từ có thể
xuất hiện ở nhiều bài hoặc nhiều sách. Người dùng học nó một lần, không nên phải ôn
lại từ đầu khi gặp lại ở sách khác. Hệ quả là mặt sau của thẻ ôn tập mất chỗ bám,
nên phải có thêm `source_lw_id` trỏ tới lần gặp đầu tiên.

**Ranh giới giữa `lesson_word.meaning_src` và `dict.char.meaning_vi`.** Hai trường
này đều chứa nghĩa tiếng Việt nhưng không được lẫn nguồn với nhau. `meaning_src` lấy
từ chính quyển sách người dùng nhập, nằm trong `user.sqlite`, không rời khỏi máy họ.
`meaning_vi` nằm trong `dict.sqlite`, mà `dict.sqlite` được đóng gói kèm sản phẩm
theo mục 4.3, nên đổ bản dịch của nhà xuất bản vào đó là phân phối lại công sức
dịch thuật của họ. Ngoài vấn đề giấy phép còn hai lý do kỹ thuật: sách chỉ phủ
khoảng một nghìn từ trong khi tra cứu phủ hơn chín nghìn chữ, và nếu hai trường cùng
nguồn thì hai khối "nghĩa theo sách" với "nghĩa từ điển" ở màn hình Tra cứu sẽ in ra
y hệt nhau, làm tính năng đối chiếu tự triệt tiêu.

**Vì sao cần `char_reading` tách khỏi `char.pinyin`.** Không có bảng này thì bước
kiểm chứng của QT-03 chỉ so được với một âm duy nhất, và sẽ gắn cờ sai cho toàn bộ
chữ đa âm cũng như mọi âm tiết đọc khinh thanh trong từ ghép.

**Vì sao đếm "bộ thủ đã gặp" phải tính động chứ không lưu sẵn.** `progress` lưu từ,
còn bộ thủ gắn với chữ. Số liệu ở màn hình Bản đồ bộ thủ được tính bằng cách tách
mỗi từ trong `progress` thành các chữ rời, lấy tập hợp chữ đó, rồi nối sang
`d.char.radical_idx`. Đơn vị đếm là **số chữ khác nhau** đã gặp mang bộ đó, không
phải số từ; con số này phải được ghi rõ đơn vị trên giao diện.

---

## 6. BẢNG MÀU VÀ CHỮ

### 6.1. Bảng màu

| Vai trò | Mã hex | Dùng ở đâu |
|---|---|---|
| Nền ứng dụng | `#F5F4F0` | Nền cửa sổ chính |
| Nền thẻ | `#FFFFFF` | Thẻ nội dung, ô 田字格, bảng |
| Chữ chính | `#1B1A18` | Tiêu đề, nội dung chính, chữ Hán |
| Chữ phụ | `#605D57` | Nghĩa, mô tả, nhãn phụ |
| Chữ mờ | `#716D66` | Chú thích, siêu dữ liệu, trạng thái rỗng |
| Đường kẻ | `#E1DED6` | Viền thẻ, đường phân cách, viền bảng |
| Nhấn chính | `#A83A2C` | Nút chính, pinyin, viền ô 田字格, mục đang chọn |
| Nhấn chính khi rê | `#933327` | Trạng thái hover của nút chính |
| Nhấn phụ | `#3F7A68` | Trạng thái đã học, thanh tiến độ, dấu kiểm chứng |
| Nền nhấn phụ | `#F2F8F6` | Nền ô bộ thủ đã gặp, nhãn trạng thái |
| Viền nhấn phụ | `#BFD6CE` | Viền các thành phần dùng màu nhấn phụ |
| Cảnh báo | `#9C7318` | Trạng thái cần xem lại, dòng bóc tách không tin cậy |
| Nền cảnh báo | `#FBF7EC` | Nền dải thông báo cần xem lại |
| Chữ trên nền cảnh báo | `#6B5310` | Nội dung dải thông báo |

Nguyên tắc sử dụng: màu nhấn chính chỉ dùng cho hành động chính và điểm neo thị
giác, không dùng làm màu trang trí. Toàn bộ giao diện còn lại là thang xám ấm.
Ba màu trạng thái đỏ, xanh, vàng luôn đi kèm nhãn chữ, không bao giờ dùng màu đơn
độc để truyền đạt thông tin.

Mọi cặp màu **chữ** trên nền phải đạt tỉ số tương phản từ 4.5:1 trở lên. Thành phần
phi văn bản, tức viền, đường kẻ, chấm trạng thái và biểu tượng, chỉ cần 3:1 theo
WCAG 1.4.11, nên không áp ngưỡng 4.5 lên chúng.

Màu chữ mờ ở bản 0.1 là `#8E8A82`, chỉ đạt khoảng 3.1:1 trên nền `#F5F4F0`, tức là
không đạt, mà đây lại đúng là màu dùng cho cỡ chữ nhỏ nhất; đã đổi thành `#716D66`.

**Ràng buộc dùng màu cảnh báo.** `#9C7318` **không được dùng làm màu chữ**: đo được
4.02:1 trên nền cảnh báo `#FBF7EC` và 4.30:1 trên nền thẻ `#FFFFFF`, cả hai đều
trượt ngưỡng 4.5. Màu này chỉ dùng cho viền, chấm trạng thái và biểu tượng, nơi
ngưỡng là 3:1 và 4.02 thì dư. Chữ trên dải cảnh báo dùng `#6B5310`, đạt 6.84:1.
Ràng buộc này phát hiện sau phiên 05 bằng script tính tương phản, cùng loại lỗi với
màu chữ mờ ở trên, và là lý do câu "kiểm bằng script" bên dưới tồn tại.

Bảng đo thật, tính theo công thức tương phản WCAG 2.x:

| Cặp màu | Tỉ số | Kết luận |
|---|---|---|
| Chữ chính `#1B1A18` trên nền app `#F5F4F0` | 15.80:1 | đạt |
| Chữ chính `#1B1A18` trên nền thẻ `#FFFFFF` | 17.39:1 | đạt |
| Chữ phụ `#605D57` trên nền app | 5.96:1 | đạt |
| Chữ phụ `#605D57` trên nền thẻ | 6.56:1 | đạt |
| Chữ mờ `#716D66` trên nền app | 4.68:1 | đạt, sát ngưỡng |
| Chữ mờ `#716D66` trên nền thẻ | 5.15:1 | đạt |
| Nhấn chính `#A83A2C` trên nền app | 5.77:1 | đạt |
| Nhấn chính `#A83A2C` trên nền thẻ | 6.35:1 | đạt |
| Nhấn phụ `#3F7A68` trên nền nhấn phụ `#F2F8F6` | 4.66:1 | đạt, sát ngưỡng |
| Nhấn phụ `#3F7A68` trên nền thẻ | 5.01:1 | đạt |
| Cảnh báo `#9C7318` trên nền cảnh báo `#FBF7EC` | 4.02:1 | **không đạt cho chữ**, đạt cho viền |
| Cảnh báo `#9C7318` trên nền thẻ | 4.30:1 | **không đạt cho chữ**, đạt cho viền |
| Chữ trên nền cảnh báo `#6B5310` trên `#FBF7EC` | 6.84:1 | đạt |
| Đường kẻ `#E1DED6` trên nền thẻ | 1.34:1 | không áp ngưỡng, là đường kẻ |

Kiểm tra lại toàn bảng bằng một script tính tương phản, không ước lượng bằng mắt.
Hai cặp sát ngưỡng ở trên là 4.68 và 4.66; đổi bất kỳ màu nào trong bốn màu đó phải
chạy lại script chứ không được ước lượng là "vẫn còn dư".

### 6.2. Chữ

| Vai trò | Phông | Cỡ | Đậm |
|---|---|---|---|
| Chữ Hán cỡ lớn | Noto Serif SC | 88 px | 400 |
| Chữ Hán cỡ vừa | Noto Serif SC | 40 px | 400 |
| Chữ Hán trong dòng | Noto Serif SC | 19 px | 400 |
| Tiêu đề màn hình | IBM Plex Sans | 20 px | 600 |
| Tiêu đề mục | IBM Plex Sans | 13 px | 600 |
| Nội dung | IBM Plex Sans | 14 px | 400 |
| Pinyin | IBM Plex Mono | 12–16 px | 400 |
| Siêu dữ liệu, số liệu | IBM Plex Mono | 11 px | 400 |
| Nhãn mục nhỏ | IBM Plex Mono | 10.5 px, giãn chữ 0.06em, in hoa | 400 |

Chọn phông có chân cho chữ Hán vì giáo trình in bằng thể 宋体 có chân, người học
quen nhận dạng chữ ở dạng đó. Pinyin đặt bằng phông đơn cách để dấu thanh của các
dòng liền nhau thẳng hàng, dễ so sánh.

Ba phông này phải được đóng gói kèm sản phẩm và nạp bằng `QFontDatabase`, không
dựa vào phông có sẵn của hệ điều hành.

Cần kiểm tra ngay từ đầu rằng phông đơn cách chứa đủ các ký tự thanh ba và nguyên
âm ü có dấu: `ǎ ě ǐ ǒ ǔ ǚ ǜ` nằm ở khối Latin Extended-B từ U+01CE trở đi, và rất
nhiều phông đơn cách thiếu đúng nhóm này. Thiếu một ký tự là hệ điều hành thay
phông cho riêng ký tự đó, làm hỏng chính lý do chọn phông đơn cách. Không đủ thì
chuyển pinyin sang IBM Plex Sans và căn thẳng hàng bằng cách đặt bề rộng cột cố định.

---

## 7. PHÁC THẢO GIAO DIỆN

### 7.1. Khung chung

Cửa sổ tối thiểu 1100 x 700. Thanh điều hướng bên trái rộng cố định 212 px.

### 7.2. Màn hình Tra cứu

```
┌──────────────┬───────────────────────────────────────────────────────────┐
│ 部            │  Tra cứu                                                 │
│ Học từ qua   │  Gõ chữ Hán, pinyin có dấu hoặc không dấu, hoặc nghĩa     │
│ bộ thủ       │                                                           │
│ v0.2         │  ┌─────────────────────────────────────┬───────────┐      │
│              │  │ renshi                              │    Tìm    │      │
├──────────────┤  └─────────────────────────────────────┴───────────┘      │
│              │  认识 · rènshi · ren4shi5 · quen biết, làm quen           │
│ 查 Tra cứu ◄ │                                                           │
│ 书 Sách      │  3 KẾT QUẢ · XẾP THEO ĐỘ KHỚP, HSK RỒI TẦN SUẤT           │
│ 复 Ôn tập 12 │  ┌─────────────────────────────────────────────────────┐  │
│ 部 Bộ thủ    │  │ 认识  rènshi   quen biết, làm quen     HSK1 · #412 │◄  │
│              │  ├─────────────────────────────────────────────────────┤  │
│              │  │ 人事  rénshì   nhân sự, việc đời       HSK5 · #2108│   │
│              │  ├─────────────────────────────────────────────────────┤  │
│              │  │ 人士  rénshì   nhân sĩ, người có địa vị   — · #2687│   │
│              │  └─────────────────────────────────────────────────────┘  │
│              │                                                           │
├──────────────┤  ┌─────────────────────────────────────────────────────┐  │
│ Theo dõi 87  │  │ ┌────────┐┌────────┐  认识                          │  │
│ Bộ thủ 34/214│  │ │   认   ││   识   │  rènshi                        │  │
│ Ngoại tuyến  │  │ │        ││        │  [động từ][HSK 1][Đang học]    │  │
│              │  │ └────────┘└────────┘                                │  │
│              │  │                       NGHĨA THEO SÁCH               │  │
│              │  │                       quen biết, làm quen           │  │
│              │  │                       NGHĨA TỪ ĐIỂN                 │  │
│              │  │                       nhận biết, nhận ra            │  │
│              │  │                       NGUỒN                         │  │
│              │  │                       博雅汉语 I · Bài 3 · tr. 31    │ │
│              │  ├─────────────────────────────────────────────────────┤  │
│              │  │ CHIẾT TỰ                                            │  │
│              │  │ 认  rèn  bộ 讠 (ngôn — lời nói) · 4 nét             │  │
│              │  │  ┌────┐      ┌────┐      ┌────┐                     │  │
│              │  │  │ 认 │  =   │ 讠 │  +   │ 人 │                     │  │
│              │  │  └────┘      └────┘      └────┘                     │  │
│              │  │  chữ đủ    ngôn·lời nói  nhân·người                 │  │
│              │  │ ─────────────────────────────────────────────────── │  │
│              │  │ 识  shí  bộ 讠 (ngôn — lời nói) · 7 nét             │  │
│              │  │  ┌────┐      ┌────┐      ┌────┐                     │  │
│              │  │  │ 识 │  =   │ 讠 │  +   │ 只 │                     │  │
│              │  │  └────┘      └────┘      └────┘                     │  │
│              │  ├─────────────────────────────────────────────────────┤  │
│              │  │ VÌ SAO CHỮ NÀY VIẾT NHƯ VẬY                         │  │
│              │  │ Cả hai chữ đều mang bộ 讠, dạng giản lược của 言,   │  │
│              │  │ nghĩa là lời nói...                                 │  │
│              │  │ ● Đã đối chiếu bộ thủ và âm đọc với từ điển cục bộ  │  │
│              │  ├─────────────────────────────────────────────────────┤  │
│              │  │ BẠN ĐÃ GẶP BỘ 讠 Ở ĐÂU                              │  │
│              │  │  ┌──┐ ┌──┐ ┌──┐ ┌──┐                                │  │
│              │  │  │说│ │话│ │请│ │谢│                                │  │
│              │  │  └──┘ └──┘ └──┘ └──┘                                │  │
│              │  │  Bài 2 Bài 2 Bài 3 Bài 3                            │  │
│              │  └─────────────────────────────────────────────────────┘  │
└──────────────┴───────────────────────────────────────────────────────────┘
```

Ô vuông bao quanh mỗi chữ là ô 田字格, có viền màu nhấn chính và hai đường đứt
chia tư. Đây là yếu tố nhận diện của ứng dụng, dùng nhất quán ở mọi màn hình.

**Các con số trong mockup này lấy từ fixture của mục 14.4, không phải từ
`dict.sqlite` thật.** Cấp HSK và thứ hạng 412 / 2108 / 2687 là ba dòng dựng bằng
`pytest` fixture để tách bạch hai yếu tố xếp hạng. Trên dữ liệu thật, ba từ đó là
认识 HSK 1 thứ hạng 85, 人事 HSK 5 thứ hạng 4984, 人士 HSK 6 thứ hạng 5026; thứ tự
trả về không đổi. Giao diện hiện số thật, và lệch số so với hình vẽ ở đây **không**
phải là lỗi. Tương tự, `meaning_vi` và `pos` trong `dict.sqlite` còn rỗng hoàn
toàn, nên các nghĩa tiếng Việt và chip từ loại vẽ trong hình là chỗ dành sẵn, giao
diện phải hiện trạng thái rỗng có nhãn thay vì bịa.

Nhãn dòng tóm lược ghi "XẾP THEO ĐỘ KHỚP, HSK RỒI TẦN SUẤT" cho khớp công thức ở
mục 13.6, nơi trọng số khớp `w_khớp` đứng trước cả HSK lẫn tần suất.

Ba khối cuối của hình, tức NGHĨA THEO SÁCH, NGUỒN, VÌ SAO CHỮ NÀY VIẾT NHƯ VẬY và
BẠN ĐÃ GẶP BỘ NÀY Ở ĐÂU, phụ thuộc vào `user.sqlite` và quy trình QT-05 nên chỉ
hiện khi có dữ liệu. Hai khối đầu vẽ khi `WordDetail.source` khác `None`.

### 7.3. Màn hình Sách của tôi

```
┌──────────────┬───────────────────────────────────────────────────────────┐
│              │  Sách của tôi                                             │
│ 查 Tra cứu   │  Mỗi quyển được tách sẵn thành từng bài khi nhập          │
│ 书 Sách   ◄  │                                                           │
│ 复 Ôn tập    │  ┌─────────────────────────────────────────────────────┐  │
│ 部 Bộ thủ    │  │ ┌────┐ 博雅汉语 · 初级起步篇 I                       │ │
│              │  │ │博雅│ 15 bài · 248 trang · nhập 12/07/2026         │  │
│              │  │ │    │ Tách qua quét tiêu đề in · đã sửa tay 1 bài  │  │
│              │  │ └────┘ ████░░░░░░░░░░░░░░░░░░  17%    [Nhập sách]   │  │
│              │  └─────────────────────────────────────────────────────┘  │
│              │                                                           │
│              │  DANH SÁCH BÀI                                            │
│              │  ┌─────────────────────────────────────────────────────┐  │
│              │  │ Bài 1  你好                tr. 12–19    12/12 từ    │  │
│              │  │ Bài 2  汉语很有意思        tr. 20–29    15/15 từ    │  │
│              │  │ Bài 3  你叫什么名字        tr. 30–39     6/10 từ  ◄ │  │
│              │  │ Bài 4  我们都是学生        tr. 40–49     0/14 từ    │  │
│              │  │ Bài 5  现在几点            tr. 50–58     0/13 từ    │  │
│              │  └─────────────────────────────────────────────────────┘  │
│              │                                                           │
│              │  BÀI 3 · 10 TỪ MỚI · BÓC TÁCH TỪ TRANG 31–32              │
│              │  ┌───┬────────┬──────────┬──────────────────┬─────────┐   │
│              │  │ # │ Từ     │ Pinyin   │ Nghĩa theo sách  │Trạng thái│  │
│              │  ├───┼────────┼──────────┼──────────────────┼─────────┤   │
│              │  │ 1 │ 名字   │ míngzi   │ (名) tên, họ tên │ đã học  │   │
│              │  │ 2 │ 朋友   │ péngyou  │ (名) bạn bè      │ đã học  │   │
│              │  │ 3 │ 认识   │ rènshi   │ (动) quen biết   │ đang học│   │
│              │  │ … │        │          │                  │         │   │
│              │  │10 │ 谢谢   │ xièxie   │ (动) cảm ơn      │cần xem lại│ │
│              │  └───┴────────┴──────────┴──────────────────┴─────────┘   │
│              │  ┃ 1 dòng cần xem lại: pinyin của 谢谢 bị xuống dòng nên  │
│              │  ┃ regex không tách được. Bấm vào dòng để sửa tay.        │
│              │                                                           │
│              │  [Thêm cả bài vào ôn tập]  [Xuất bài này sang Anki]       │
└──────────────┴───────────────────────────────────────────────────────────┘
```

Thanh phần trăm là số từ đã đạt trạng thái "đã thuộc" chia cho tổng số từ mới đã
bóc tách được của quyển đó, ở đây là 33 trên 195. Con số "Theo dõi 87 từ" ở thanh
bên là số dòng trong `progress`, tính trên mọi quyển sách, nên hai số này không
bằng nhau và không được đặt cùng một nhãn.

### 7.4. Hộp thoại Nhập sách, bước xác nhận tách bài

Đây là màn hình quan trọng nhất về mặt kỹ thuật, hiện ra sau khi hệ thống chạy
xong thang năm nấc ở QT-02.

```
┌───────────────────────────────────────────────────────────────────┐
│  Xác nhận ranh giới bài học                                    ✕  │
├───────────────────────────────────────────────────────────────────┤
│  boya-1.pdf · 248 trang · PDF số, không cần OCR                   │
│  Đã tách được 15 bài bằng cách quét tiêu đề bài in trong sách.    │
│  Kiểm tra lại bên dưới rồi bấm Lưu. Bạn có thể sửa trực tiếp.     │
│                                                                   │
│  ┌────┬──────────────────────┬────────┬────────┬───────────────┐  │
│  │Bài │ Tiêu đề              │Trang từ│Trang đến│ Độ tin cậy   │  │
│  ├────┼──────────────────────┼────────┼────────┼───────────────┤  │
│  │ 1  │ 你好                 │  12    │  19    │ cao           │  │
│  │ 2  │ 汉语很有意思         │  20    │  29    │ cao           │  │
│  │ 3  │ 你叫什么名字         │  30    │  39    │ cao           │  │
│  │ 4  │ 我们都是学生         │  40    │  49    │ cao           │  │
│  │ 5  │ (cỡ chữ bất thường)  │  50    │  58    │ thấp       ⚠  │  │
│  │ …  │                      │        │        │               │  │
│  └────┴──────────────────────┴────────┴────────┴───────────────┘  │
│                                                                   │
│  ┃ 1 bài có độ tin cậy thấp. Mở trang 50 để kiểm tra tiêu đề.     │
│                                                                   │
│  [+ Thêm bài]  [Xoá bài đã chọn]  [Xem trang 50]                  │
│                                                                   │
│                          [Huỷ]   [Lưu 15 bài vào thư viện]        │
└───────────────────────────────────────────────────────────────────┘
```

### 7.5. Màn hình Ôn tập

```
┌──────────────┬───────────────────────────────────────────────────────────┐
│              │  Ôn tập                                                   │
│ 查 Tra cứu   │  12 từ đến hạn hôm nay                                    │
│ 书 Sách      │                                                           │
│ 复 Ôn tập ◄  │            ┌─────────────────────────────────┐            │
│ 部 Bộ thủ    │            │  TỪ NÀY ĐỌC VÀ NGHĨA LÀ GÌ      │            │
│              │            │                                 │            │
│              │            │      ┌──────┐  ┌──────┐         │            │
│              │            │      │  高  │  │  兴  │         │            │
│              │            │      └──────┘  └──────┘         │            │
│              │            │                                 │            │
│              │            │           gāoxìng               │            │
│              │            │        vui, vui mừng            │            │
│              │            │  高 bộ 高 (cao) · 兴 bộ 八      │            │
│              │            │                                 │            │
│              │            │  [Quên]   [Khó]   [ Nhớ ]       │            │
│              │            └─────────────────────────────────┘            │
│              │                                                           │
│              │              Còn 11 từ · Bài 3 · 博雅汉语 I               │
└──────────────┴───────────────────────────────────────────────────────────┘
```

Trước khi bấm hiện đáp án, vùng dưới ô 田字格 chỉ có một nút "Hiện đáp án".
Ba nút đánh giá xuất hiện sau đó.

### 7.6. Màn hình Bản đồ bộ thủ

```
┌──────────────┬───────────────────────────────────────────────────────────┐
│              │  Bản đồ bộ thủ                                            │
│ 查 Tra cứu   │  Bộ thủ nào bạn đã gặp qua các từ đã học                  │
│ 书 Sách      │                                                           │
│ 复 Ôn tập    │   34            讠            87                          │
│ 部 Bộ thủ ◄  │   đã gặp/214    nhiều nhất    từ đã học                   │
│              │                 11 từ                                     │
│              │                                                           │
│              │  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐       │
│              │  │  讠  │  亻  │  口  │  宀  │  女  │  子  │  月  │       │
│              │  │ ngôn │ nhân │ khẩu │ miên │  nữ  │  tử  │nguyệt│       │
│              │  │11 từ │ 9 từ │ 8 từ │ 5 từ │ 5 từ │ 4 từ │ 4 từ │       │
│              │  ├──────┼──────┼──────┼──────┼──────┼──────┼──────┤       │
│              │  │  又  │  门  │  囗  │  八  │  夕  │  心  │  木  │       │
│              │  │ hựu  │ môn  │  vi  │ bát  │ tịch │ tâm  │ mộc  │       │
│              │  │ 3 từ │ 3 từ │ 2 từ │ 2 từ │ 2 từ │ 2 từ │ 2 từ │       │
│              │  ├──────┼──────┼──────┼──────┼──────┼──────┼──────┤       │
│              │  │  土  │  山  │  火  │  金  │  田  │  目  │  耳  │       │
│              │  │ thổ  │ sơn  │ hoả  │ kim  │ điền │ mục  │ nhĩ  │       │
│              │  │chưa  │chưa  │chưa  │chưa  │chưa  │chưa  │chưa  │       │
│              │  └──────┴──────┴──────┴──────┴──────┴──────┴──────┘       │
└──────────────┴───────────────────────────────────────────────────────────┘
```

Ô bộ thủ đã gặp dùng nền `#F2F8F6`, viền `#BFD6CE`, chữ Hán màu `#3F7A68`.
Ô chưa gặp giảm độ mờ xuống 42%, nhưng vẫn phải giữ nhãn chữ "chưa" bên dưới, vì
độ mờ một mình không đủ để truyền đạt trạng thái.

Đơn vị đếm trong màn hình này là **số chữ khác nhau** mang bộ đó mà người dùng đã
gặp, không phải số từ. Cách tính đã nêu ở mục 5.4: tách mỗi từ trong `progress`
thành các chữ rời, lấy tập hợp, rồi nối sang `d.char.radical_idx`. Nhãn trên ô ghi
"11 chữ" chứ không ghi "11 từ".

---

## 8. XỬ LÝ TRẠNG THÁI BIÊN VÀ LỖI

| Tình huống | Hành vi của hệ thống |
|---|---|
| Tìm kiếm không có kết quả | Hiển thị gợi ý pinyin gần giống, kèm nút chuyển sang tra chữ đơn |
| Chữ không có dữ liệu chiết tự | Hiển thị bộ thủ và số nét, ghi rõ "chưa có dữ liệu cấu tạo" |
| Mất mạng khi cần giải thích | Ẩn khối giải thích, hiện dòng chú thích, mọi phần khác hoạt động bình thường |
| Khoá API sai hoặc hết hạn mức | Thông báo cụ thể lỗi nào, dẫn tới màn hình Cài đặt, không nói chung chung |
| PDF được bảo vệ bằng mật khẩu | Yêu cầu nhập mật khẩu, không im lặng bỏ qua |
| PDF không phải sách tiếng Trung | Cảnh báo sau khi quét 5 trang mà không thấy ký tự CJK, cho phép tiếp tục |
| Không tách được bài nào | Chuyển thẳng sang nấc 5, mở giao diện nhập tay với bảng trống |
| Không có mạng, hoặc người dùng tắt FR-50 | Bỏ qua nấc 3, chạy tiếp nấc 4 và 5, ghi rõ trong bảng xác nhận là đã tách bằng phương pháp nào |
| Mô hình trả về `anchor_id` không có thật | Loại phần tử đó; quá nhiều thì loại cả kết quả và rơi xuống nấc 4, không báo lỗi cho người dùng |
| Mô hình trả về thứ tự trang không tăng dần | Loại toàn bộ kết quả, rơi xuống nấc 4 |
| Sách trên 600 trang | Chia bản tóm lược thành lô 300 trang chồng lấn 20 trang, ghép kết quả, bỏ các mốc mâu thuẫn ở vùng chồng lấn |
| Hết hạn mức API giữa lúc nhập sách | Dừng gọi, giữ nguyên phần đã có, hoàn tất bằng nấc thấp hơn, báo một dòng ở cuối |
| Người dùng huỷ giữa chừng khi nhập sách | Xoá bản ghi `book` chưa hoàn tất, không để lại dữ liệu treo |
| OCR không đọc được một trang | Ghi nhận trang đó, tiếp tục các trang còn lại, báo cáo cuối cùng |
| Danh sách ôn tập rỗng | Hiển thị lời mời chọn một bài để bắt đầu, kèm nút chuyển sang màn hình Sách |
| Chưa nhập sách nào | Màn hình Sách hiển thị hướng dẫn nhập sách đầu tiên, không để trống |
| Nhập lại một quyển đã có | Đối chiếu `book.file_hash`, hỏi ghi đè hay bỏ qua, không tạo bản ghi thứ hai |
| Tệp PDF gốc bị xoá hoặc đổi chỗ | Sách vẫn mở được, mọi nút xem trang gốc chuyển sang trạng thái mờ kèm nút chỉ lại đường dẫn |
| Không tìm thấy bảng từ mới trong bài | Để trống danh sách, gắn cờ bài, mở giao diện khoanh vùng trang; không quét cả bài |
| Chữ đa âm hoặc âm tiết khinh thanh | So khớp kiểm chứng bỏ thanh điệu, không gắn cờ chỉ vì lệch thanh |
| Duyệt IDS gặp chu trình hoặc chữ không phân tách được | Dừng ở độ sâu 6, ghi nhớ tập chữ đã thăm, hiển thị phần cây đã dựng được |
| Mô hình ngôn ngữ trả kết quả không đạt kiểm chứng | Gọi lại đúng một lần, sau đó bỏ khối diễn giải, không hiện thông báo lỗi |
| Ứng dụng tắt đột ngột giữa lúc nhập sách | Lần mở sau phát hiện `import_state = 'importing'`, hỏi nhập tiếp hay xoá |

---

## 9. YÊU CẦU PHI CHỨC NĂNG

| Mã | Yêu cầu | Chỉ tiêu |
|---|---|---|
| NFR-01 | Thời gian phản hồi tra cứu | Dưới 200 ms cho truy vấn cục bộ |
| NFR-02 | Thời gian dựng cây chiết tự | Dưới 100 ms cho một từ hai chữ |
| NFR-03 | Thời gian nhập sách 250 trang, PDF số | Dưới 60 giây, không tính bước chữa dòng bằng mô hình ngôn ngữ |
| NFR-04 | Thời gian nhập sách 250 trang, PDF scan | Dưới 10 phút với luồng ba tầng ở QT-02b bước 5; dưới 35 phút nếu buộc phải OCR toàn bộ. Hai mốc này lấy từ số đo thật 7,2 và 29 phút trên một lõi CPU, cộng biên an toàn. Có thanh tiến độ và nút huỷ trong cả hai trường hợp |
| NFR-05 | Khởi động ứng dụng | Dưới 5 giây |
| NFR-06 | Dung lượng cài đặt | Dưới 500 MB sau cài, chưa gồm mô hình OCR; mô hình tải ở lần chạy đầu và có thể bỏ qua |
| NFR-07 | Hoạt động ngoại tuyến | Toàn bộ chức năng trừ FR-13 và FR-28; thiếu mạng chỉ làm mất hai chức năng đó, không chặn thao tác nào khác |
| NFR-08 | Bảo mật khoá API | Không nhúng trong bản build, lưu mã hoá trong `setting` |
| NFR-09 | Nền tảng | Windows 10 trở lên, 64-bit |
| NFR-10 | Không làm hỏng dữ liệu người dùng | Mọi thao tác ghi vào `user.sqlite` dùng giao dịch |
| NFR-11 | Ràng buộc toàn vẹn | Mọi kết nối bật `PRAGMA foreign_keys = ON` và `journal_mode = WAL` |
| NFR-12 | Nâng cấp phiên bản | Có kịch bản chuyển đổi lược đồ, đối chiếu bảng `schema_version`, kiểm thử nâng cấp từ bản trước |
| NFR-13 | Tương phản màu | Mọi cặp chữ trên nền đạt từ 4.5:1 trở lên, kiểm bằng script |

---

## 10. KẾ HOẠCH THỰC NGHIỆM

Phần này là cơ sở cho chương đánh giá của báo cáo. Cần chuẩn bị dữ liệu kiểm thử
từ sớm, không để tới tuần cuối.

| Mã | Hạng mục đo | Cách đo | Chỉ tiêu kỳ vọng |
|---|---|---|---|
| EV-01 | Độ chính xác tách bài | 5 giáo trình khác nhau, đối chiếu thủ công | Trên 90% số bài đúng cả hai mốc trang |
| EV-02 | Độ chính xác bóc tách bảng từ mới | 20 bảng 生词表, đối chiếu từng trường | Trên 85% dòng đúng hoàn toàn |
| EV-03 | Phân bố nguồn bóc tách | Đếm `extract_by` trong `lesson_word` | Báo cáo tỷ lệ regex, llm, vision, manual trên từng giáo trình. Không đặt ngưỡng cứng, vì tỷ lệ này phụ thuộc cách trình bày của sách chứ không phụ thuộc chất lượng cài đặt |
| EV-04 | Tỷ lệ loại bỏ khi kiểm chứng | Đếm kết quả API bị loại ở QT-05 bước 5 | Ghi nhận và phân tích nguyên nhân |
| EV-05 | Độ chính xác OCR | 30 trang scan, tính CER | CER dưới 5% |
| EV-06 | Tỷ lệ phủ chiết tự | Chạy decomposer trên 3000 chữ thông dụng | Trên 95% có cây IDS đầy đủ |
| EV-07 | Hiệu năng | Đo thời gian theo mục 9 | Đạt các chỉ tiêu NFR |
| EV-08 | Đánh giá người dùng | 15–20 người học, thang Likert 5 mức, 8 câu hỏi | Điểm trung bình trên 4.0 |
| EV-09 | So sánh ba phương pháp tách bài | Chạy độc lập nấc 2, nấc 3 và nấc 4 trên cùng 5 giáo trình, đối chiếu với đáp án thủ công | Báo cáo độ chính xác của từng nấc, kèm phân tích các ca nấc 3 sai. Đây là hạng mục trung tâm của chương đánh giá |
| EV-10 | Chi phí của luồng có gọi mạng | Đo số token, số lần gọi và thời gian cho mỗi quyển; đo riêng thời gian nhập sách quét có và không có OCR chọn lọc | Báo cáo số thực đo được, không đặt ngưỡng |

Bộ dữ liệu kiểm thử cần chuẩn bị: 5 giáo trình PDF khác nhau về nhà xuất bản và
cách trình bày, trong đó ít nhất 2 quyển là bản scan, ít nhất 1 quyển không có
mục lục nhúng, và ít nhất 1 quyển in bảng 生词表 hai cột.

EV-09 là hạng mục đáng đầu tư nhất trong toàn bộ mục này. "Ứng dụng có dùng mô hình
ngôn ngữ" là một câu; "trên tập 5 giáo trình, nấc 3 đạt 94% còn nấc 4 đạt 61%, và
đây là bốn ca nấc 3 sai cùng nguyên nhân" là một chương. Muốn có bảng đó thì đáp án
thủ công cho cả 5 quyển phải làm xong từ sớm, trước khi viết code tách bài, để tránh
việc vô tình chỉnh thuật toán cho vừa với đáp án.

---

## 11. RỦI RO VÀ PHƯƠNG ÁN

| Rủi ro | Mức | Phương án |
|---|---|---|
| PaddlePaddle không cài được trên máy phát triển | Cao | Thử cài ngay tuần đầu; dự phòng dùng Tesseract cho phần scan |
| Định dạng giáo trình quá đa dạng, regex không phủ hết | Cao | Nấc 4 nhập tay luôn có sẵn; báo cáo trung thực tỷ lệ phủ |
| Hạn mức API miễn phí không đủ khi demo | Trung bình | Bộ nhớ đệm bắt buộc; chuẩn bị sẵn dữ liệu đã đệm cho buổi bảo vệ |
| Không tìm được nguồn nghĩa tiếng Việt chất lượng | Trung bình | Giới hạn ở 1000 chữ HSK 1–3, rà thủ công, ghi rõ phạm vi |
| Dung lượng đóng gói quá lớn | Trung bình | Tải mô hình OCR ở lần chạy đầu thay vì nhúng sẵn, đúng như NFR-06 |
| Bảng từ mới in hai cột làm hỏng bóc tách | Cao | Tách cột theo toạ độ trước khi tách dòng, xem QT-03 bước 2; đo riêng trên giáo trình in hai cột |
| Kiểm chứng pinyin gắn cờ sai hàng loạt | Cao | Bắt buộc so khớp sau khi bỏ thanh điệu; có `char_reading` cho chữ đa âm; kiểm thử riêng trên các từ khinh thanh |
| Chậm tiến độ ở phần nhập PDF | Cao | Lát cắt tra cứu hoàn thành trước tuần 7 là mốc an toàn để bảo vệ |
| Luồng nhập PDF nay phụ thuộc mạng ở nấc 3 | Trung bình | Nấc 3 tắt được và luôn có nấc 4, nấc 5 chạy hoàn toàn cục bộ; không thao tác nào bị chặn khi mất mạng |
| Mô hình trả về số trang lệch một hai trang | Cao | Không cho mô hình sinh số trang, chỉ cho chọn `anchor_id` có sẵn; sáu điều kiện kiểm chứng ở QT-02b bước 3 |
| Vấn đề bản quyền giáo trình | Thấp | App không phân phối nội dung; demo dùng tài liệu hợp pháp; nêu rõ trong báo cáo |
| Gửi nội dung giáo trình sang dịch vụ bên thứ ba | Trung bình | Bản tóm lược của FR-50 chỉ chứa số trang, cỡ chữ và dòng tiêu đề, không chứa nội dung bài; FR-51 có gửi ảnh trang nên mặc định tắt và có cảnh báo tại chỗ; nêu rõ trong báo cáo và trong màn hình Cài đặt |

---

## 12. NGOÀI PHẠM VI, HƯỚNG PHÁT TRIỂN

Các hạng mục sau được xác định là có giá trị nhưng nằm ngoài phạm vi phiên bản
này, và sẽ được trình bày ở chương Hướng phát triển của báo cáo:

1. Nhận dạng chữ viết tay qua canvas, dùng mạng nơ-ron tích chập huấn luyện trên
   bộ dữ liệu CASIA-HWDB1.1. Đã khảo sát và xác định khả thi, hoãn do ưu tiên
   hoàn thiện luồng học từ vựng.
2. Hỗ trợ chữ phồn thể như ngôn ngữ đích, phục vụ người học Hán-Nôm.
3. Sinh câu ví dụ có kiểm chứng ngữ pháp.
4. Đồng bộ tiến độ học giữa nhiều máy.
5. Phiên bản di động.
6. Nhận dạng cấu trúc bảng trong PDF bằng mô hình phân tích bố cục tài liệu, thay
   cho phương pháp dựa trên biểu thức chính quy hiện tại.
7. Hiển thị thứ tự nét và cho phép tập viết theo nét. Cố ý để ngoài phạm vi vì cần
   thêm một nguồn dữ liệu riêng và một lớp vẽ động; nêu rõ ở đây để phân biệt với
   việc bỏ sót.

---

## 13. GIAO DIỆN GIỮA CÁC MODULE

Mục này tồn tại để trả lời một câu hỏi: hai người, hoặc một người và một tác nhân
sinh mã, có thể làm hai module khác nhau cùng lúc mà không phải hỏi nhau không.
Mọi thứ ở các mục trước mô tả ứng dụng làm gì; mục này mô tả mã nguồn được cắt ra
làm sao.

### 13.1. Nguyên tắc phân tầng

Bốn tầng, phụ thuộc chỉ đi xuống, không bao giờ đi lên hoặc đi ngang giữa hai module
cùng tầng:

```
ui/            →  chỉ gọi xuống service/, không được import trực tiếp data/
service/       →  lookup, decomposer, importer, scheduler
adapter/       →  pdfsource, aiclient, ocr
data/          →  dictdb, userdb, và các kiểu dữ liệu dùng chung
```

Ba hệ quả bắt buộc:
- `data/` không import bất cứ thứ gì của Qt. Nhờ vậy toàn bộ tầng dưới kiểm thử được
  mà không cần dựng ứng dụng đồ hoạ.
- `service/` không mở kết nối cơ sở dữ liệu và không đọc tệp PDF trực tiếp. Nó nhận
  các đối tượng tầng dưới qua tham số khởi tạo. Nhờ vậy kiểm thử thay được bằng bản
  giả lập.
- `adapter/` là chỗ duy nhất biết tới PyMuPDF, PaddleOCR và HTTP. Đổi thư viện OCR
  hay đổi nhà cung cấp mô hình chỉ sửa trong thư mục này.

### 13.2. Cây thư mục

```
hanzi_app/
    main.py                   điểm vào, dựng các đối tượng rồi bơm vào nhau
    data/
        models.py             toàn bộ dataclass dùng chung
        dictdb.py             truy cập dict.sqlite, chỉ đọc
        userdb.py             truy cập user.sqlite, đọc ghi, quản lý giao dịch
        migrate.py            kịch bản chuyển đổi lược đồ theo schema_version
    adapter/
        pdfsource.py          bọc PyMuPDF, che khác biệt giữa trang chữ và trang ảnh
        ocr.py                bọc PaddleOCR
        aiclient.py           gọi API, ép lược đồ JSON, không chứa logic nghiệp vụ
    service/
        pinyin.py             chuẩn hoá, tách âm tiết, đổi qua lại số và dấu
        lookup.py             FR-01 tới FR-08
        decomposer.py         FR-10 tới FR-15
        splitter.py           thang năm nấc của QT-02 và QT-02b
        vocab.py              QT-03
        importer.py           điều phối QT-02, chạy trong luồng nền
        scheduler.py          SM-2, QT-04
    ui/
        main_window.py
        screen_lookup.py      screen_books.py  screen_review.py  screen_radicals.py
        dialog_import.py
        widgets/              ô 田字格, cây chiết tự, thẻ ôn tập
    resources/
        fonts/  dict.sqlite  qss/
tests/
    unit/  golden/  fixtures/
```

### 13.3. Kiểu dữ liệu dùng chung

Đặt hết trong `data/models.py`. Tất cả là dataclass đông cứng, không có phương thức
nghiệp vụ. Lý do dùng dataclass thay vì dict: sai tên trường bị bắt lúc viết mã chứ
không phải lúc chạy, và đây là thứ giúp một tác nhân sinh mã đỡ tự bịa tên trường.

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class CharInfo:
    char: str
    pinyin: str            # âm đọc chính, có dấu
    readings: tuple[str, ...]   # toàn bộ âm đọc, có dấu, lấy từ char_reading
    hanviet: str | None
    meaning_vi: str | None
    meaning_en: str | None
    radical_idx: int | None
    total_strokes: int | None
    trad_form: str | None
    ids: str | None
    hsk_level: int | None
    freq_rank: int | None

@dataclass(frozen=True)
class WordInfo:
    id: int
    simplified: str
    traditional: str | None
    pinyin_tone: str       # 'rènshi'
    pos: str | None
    meaning_vi: str | None
    meaning_en: str | None
    hsk_level: int | None
    freq_rank: int | None

@dataclass(frozen=True)
class Radical:
    idx: int               # 1..214
    glyph: str             # '言'
    glyph_alt: str | None  # '讠', None nếu bộ không đổi hình khi đứng trong chữ
    name_hv: str           # 'ngôn'
    meaning_vi: str        # 'lời nói'
    strokes: int

@dataclass(frozen=True)
class WordSource:
    # Từ này xuất hiện ở đâu trong sách của người dùng. Lấy từ lesson_word,
    # lesson và book trong user.sqlite. None nếu từ chưa nằm trong quyển nào.
    book_title: str
    lesson_no: int
    lesson_title: str | None
    page: int | None
    pinyin_src: str | None
    hanviet_src: str | None
    meaning_src: str | None

@dataclass(frozen=True)
class WordDetail:
    query: str
    word: WordInfo | None            # None nếu chỉ tra được ở mức chữ đơn
    chars: tuple[CharInfo, ...]      # từng chữ của từ, theo đúng thứ tự
    source: WordSource | None
    status: str | None               # 'new' | 'learning' | 'known'; None nếu chưa ôn tập

# WordDetail CỐ Ý không chứa cây chiết tự và không chứa phần diễn giải của FR-13.
# Lý do là quy tắc phân tầng ở mục 13.1: lookup và decomposer cùng nằm ở tầng
# service, mà phụ thuộc không được đi ngang giữa hai module cùng tầng. Cây chiết
# tự do Decomposer.tree() dựng, phần diễn giải do quy trình QT-05 sinh; tầng giao
# diện gọi cả ba rồi ghép lại thành màn hình ở mục 7.2. Nhét cây vào WordDetail
# sẽ buộc lookup phải import decomposer và phá vỡ phân tầng.

@dataclass(frozen=True)
class SearchHit:
    kind: str              # 'word' | 'char'
    word: WordInfo | None
    char: CharInfo | None
    score: float           # điểm xếp hạng, càng lớn càng lên trên
    matched_by: str        # 'hanzi' | 'pinyin_tone' | 'pinyin_plain' | 'pinyin_num' | 'meaning' | 'fuzzy'

@dataclass(frozen=True)
class DecompNode:
    char: str
    ids: str | None
    meaning_vi: str | None
    radical: Radical | None
    children: tuple["DecompNode", ...]
    truncated: bool = False   # True nếu dừng vì chạm giới hạn độ sâu hoặc gặp chu trình
    is_group: bool = False    # True với nút nhóm lồng, xem ghi chú bên dưới

# Nút nhóm lồng. Chuỗi IDS '⿱木⿰木木' của chữ 森 sinh ra một nút trung gian ứng với
# '⿰木木', mà cụm đó không phải một chữ Hán. Nút loại này đặt char bằng chính chuỗi
# IDS con, meaning_vi và radical bằng None, và is_group bằng True. Giao diện BẮT
# BUỘC kiểm tra is_group trước khi vẽ: nút nhóm không được vẽ vào ô 田字格, vì ô đó
# chỉ dành cho một chữ đơn, vẽ chuỗi '⿰木木' vào đó sẽ trông như lỗi hiển thị.

@dataclass(frozen=True)
class PageSummary:
    id: int                # số thứ tự dòng trong bản tóm lược, đánh từ 1
    pdf_page: int          # chỉ số trang trong tệp, từ 0
    folio: str | None      # số trang in đọc được
    max_size: float
    head: str              # dòng lớn nhất ở phần trên trang, cắt còn 30 ký tự
    cjk: int

@dataclass(frozen=True)
class LessonBoundary:
    index_no: int          # âm với mục ôn tập, xem QT-02 bước 3
    title: str | None
    page_start: int
    page_end: int
    confidence: float      # 0..1
    kind: str              # 'lesson' | 'review'

@dataclass(frozen=True)
class VocabRow:
    order_no: int | None
    word: str
    pinyin_src: str | None
    pos: str | None
    meaning_src: str | None
    source_page: int
    extract_by: str        # 'regex' | 'llm' | 'vision' | 'manual'
    needs_review: bool
    review_reason: str | None   # lý do gắn cờ, hiện lên giao diện sửa tay

@dataclass(frozen=True)
class ReviewOutcome:
    ease: float
    interval_days: int
    repetition: int
    lapse_count: int
    status: str            # 'new' | 'learning' | 'known'
    due_date: date
```

### 13.4. Tầng dữ liệu

```python
class DictDb:
    def __init__(self, path: str) -> None: ...        # mở chế độ chỉ đọc
    def get_char(self, ch: str) -> CharInfo | None: ...
    def get_chars(self, chars: str) -> dict[str, CharInfo]: ...   # một truy vấn cho cả chuỗi
    def readings_of(self, ch: str) -> tuple[str, ...]: ...        # dạng plain, đã khử thanh
    def parts_of(self, ch: str, variant: int = 0) -> tuple[str, ...]: ...  # theo order_no
    def get_radical(self, idx: int) -> Radical | None: ...
    def all_radicals(self) -> list[Radical]: ...
    def find_words_by_hanzi(self, text: str) -> list[WordInfo]: ...
    def find_words_by_pinyin(self, plain: str, numeric: str | None) -> list[WordInfo]: ...
    def find_words_by_meaning(self, query: str, limit: int = 50) -> list[WordInfo]: ...
        # Qua word_fts. Chuỗi người dùng gõ PHẢI được bọc trong dấu nháy kép
        # thành một cụm trước khi đưa vào MATCH. Không bọc thì các ký tự có
        # nghĩa riêng trong cú pháp FTS5, gồm * ^ ( ) và từ khoá OR NOT NEAR,
        # sẽ làm câu truy vấn hỏng hoặc ném lỗi ngay khi người dùng gõ dấu sao.
    def chars_with_radical(self, radical_idx: int) -> list[str]: ...

class UserDb:
    def __init__(self, path: str) -> None: ...
    # mở kết nối bật foreign_keys và WAL, chạy migrate.upgrade() trước khi trả về

    def transaction(self): ...            # context manager, dùng cho mọi thao tác ghi

    def add_book(self, ...) -> int: ...
    def find_book_by_hash(self, file_hash: str) -> int | None: ...
    def set_import_state(self, book_id: int, state: str) -> None: ...
    def replace_lessons(self, book_id: int, bounds: list[LessonBoundary]) -> None: ...
    def replace_vocab(self, lesson_id: int, rows: list[VocabRow]) -> None: ...

    def word_source(self, word: str) -> WordSource | None: ...
        # Nối lesson_word, lesson và book để trả về lần gặp đầu tiên của từ này
        # trong sách của người dùng, phục vụ khối NGUỒN ở màn hình 7.2.
        # None nếu từ chưa xuất hiện trong quyển nào.
    def get_progress(self, word: str) -> ReviewOutcome | None: ...
    def upsert_progress(self, word: str, outcome: ReviewOutcome, source_lw_id: int | None) -> None: ...
    def due_words(self, on: date, limit: int = 100) -> list[str]: ...
    def log_review(self, word: str, grade: int, q: int, before: ReviewOutcome, after: ReviewOutcome) -> None: ...
    def learned_chars(self) -> set[str]: ...   # tách từng từ trong progress thành chữ rời

    def cache_get(self, key: str) -> dict | None: ...
    def cache_put(self, key: str, payload: dict, model: str) -> None: ...
```

`replace_lessons` và `replace_vocab` cố ý là thao tác thay thế trọn gói chứ không phải
chèn từng dòng. Nhập lại một quyển hoặc sửa ranh giới rồi lưu lại là ghi đè cả cụm,
làm trong một giao dịch, nên không bao giờ để lại trạng thái nửa vời.

### 13.5. Tiện ích pinyin

Module nhỏ nhất nhưng bị gọi nhiều nhất, và là nơi lỗi hay nấp.

```python
def to_plain(s: str) -> str: ...
    # 'rènshi' -> 'renshi';  'nǚ' -> 'nv'
    # Chỉ được xoá bốn dấu thanh U+0300, U+0301, U+0304, U+030C và PHẢI GIỮ
    # dấu tách âm U+0308. Chuẩn hoá NFD rồi xoá mọi dấu kết hợp là cách cài
    # đặt trực giác nhất và nó SAI: 'ǚ' tách thành u + tách âm + thanh, xoá
    # hết thì còn 'u', nên 'nǚ' ra 'nu' thay vì 'nv' và tra cứu mọi âm có ü
    # đều hỏng. Trình tự đúng: NFD, lọc bỏ đúng bốn mã trên, NFC lại, rồi mới
    # đổi 'ü' thành 'v'.

def num_to_tone(s: str) -> str: ...
    # 'ren4 shi5' -> 'rènshi';  'nu:3' -> 'nǚ';  thanh 5 và thanh 0 không đánh dấu

def tone_to_num(s: str) -> str: ...

def split_syllables(s: str, expect: int | None = None) -> list[str] | None: ...
    # Tách chuỗi pinyin liền thành các âm tiết.
    # Tham số expect là số âm tiết mong đợi, thường là số chữ Hán của từ.
    # Truyền expect vào thì hàm chỉ trả về cách tách có đúng số âm tiết đó,
    # nhờ vậy các ca nhập nhằng như 'xian' tự được giải quyết mà không cần
    # dấu nháy. Không có cách tách nào hợp lệ thì trả None.

def query_variants(q: str) -> list[str]: ...
    # Sinh các biến thể của chuỗi người dùng gõ, phục vụ FR-03.
    # 'lu' -> ['lu', 'lv'] vì người Việt quen gõ u thay cho ü. Chỉ sinh biến thể
    # sau l và n; sau j, q, x, y thì ü luôn viết là u nên không nhập nhằng.
    # Với pinyin số, phải sinh cả dạng có và không có số thanh nhẹ: người dùng
    # gõ 'ren4shi' còn cột pinyin_numeric lưu 'ren4shi5'. Không xử lý chỗ này thì
    # 89 trong 5001 từ HSK không bao giờ tìm được bằng pinyin số.
```

`split_syllables` nhận `expect` là một quyết định thiết kế đáng nêu trong báo cáo.
Tách pinyin liền là bài toán nhập nhằng thật sự: chuỗi `xian` có thể là một âm tiết
`xian` hoặc hai âm tiết `xi` + `an`. Nhưng ở mọi chỗ ứng dụng cần tách, số chữ Hán
đã biết trước, và ràng buộc đó làm bài toán trở thành xác định trong hầu hết trường
hợp. Nhiều cách cài đặt bỏ qua thông tin này rồi đi giải bài toán khó hơn mức cần.

### 13.6. lookup

```python
class LookupService:
    def __init__(self, dict_db: DictDb, user_db: UserDb) -> None: ...

    def search(self, query: str, limit: int = 30) -> list[SearchHit]: ...
    def detail(self, word: str) -> WordDetail: ...
        # Gộp dữ liệu từ điển với dữ liệu người dùng: thông tin từ, từng chữ,
        # nguồn trong sách nếu có, trạng thái ôn tập nếu có. Không gọi sang
        # decomposer, xem ghi chú ở mục 13.3.
    def suggest(self, query: str, limit: int = 5) -> list[SearchHit]: ...   # nhánh không có kết quả
```

Quy tắc xếp hạng của `search`, viết ra thành số vì FR-05 không kiểm chứng được nếu
chỉ nói "theo HSK và tần suất":

```
score = 100 · w_khớp + 30 · w_hsk + 20 · w_tần_suất

w_khớp:      1.00 khớp đúng chữ Hán
             0.90 khớp pinyin có dấu
             0.75 khớp pinyin không dấu hoặc pinyin số
             0.50 khớp nghĩa
             0.25 khớp gần (FR-08)

Mức 0.90 chỉ được tính khi chuỗi người dùng gõ THỰC SỰ có dấu thanh. Không kiểm
điều này thì truy vấn `renshi` sẽ khớp y nguyên cột `pinyin_tone` của những từ mà
mọi âm tiết đều đọc khinh thanh, và được nâng nhầm lên 0.90 dù người dùng không
gõ dấu nào.
w_hsk:       (7 − hsk_level) / 6, bằng 0 nếu ngoài danh sách HSK
w_tần_suất:  1 / log10(freq_rank + 10), bằng 0 nếu không có thứ hạng
```

Kết quả khớp gần luôn xếp sau toàn bộ nhóm khớp đúng, kể cả khi điểm cao hơn. Cài
đặt bằng cách sắp xếp theo khoá kép `(w_khớp >= 0.5, score)`.

Thuật toán khớp gần của FR-08, dùng trong `suggest` và không bao giờ dùng trong
`search`:

```
1. Sinh ứng viên: bỏ dần 1 rồi 2 ký tự cuối của truy vấn, mỗi lần tra khớp đúng
2. Lọc ứng viên: giữ lại những từ có difflib.SequenceMatcher.ratio() so với
   truy vấn gốc đạt từ 0.6 trở lên
3. Xếp hạng theo công thức trên với w_khớp = 0.25
```

Ngưỡng 0.6 lấy đúng mức cutoff mặc định của `difflib`. Có ngưỡng này thì truy vấn
rác như `xyzzyx` trả về rỗng thay vì gợi ý bừa một từ không liên quan.

### 13.7. decomposer

```python
class Decomposer:
    MAX_DEPTH = 6

    def __init__(self, dict_db: DictDb, user_db: UserDb) -> None: ...
        # Cần cả hai: tree() và radical_of() chỉ đọc từ điển, nhưng
        # same_radical_learned() và radical_map() phải lọc theo những chữ người
        # dùng đã học, mà dữ liệu đó nằm ở bảng progress trong user.sqlite.
        # Bản 0.5 lần đầu chỉ khai báo dict_db, khiến FR-15 và FR-34 không có
        # đường lấy dữ liệu và buộc phải đếm trên toàn bộ từ điển.

    def tree(self, ch: str) -> DecompNode: ...
        # Dựng cây chiết tự từ chuỗi IDS, theo ĐÚNG ba quy tắc dừng dưới đây.
        #
        # 1. Giữ nguyên cấu trúc lồng của chuỗi IDS. Toán tử ⿲ và ⿳ nhận ba
        #    toán hạng, mười toán tử còn lại nhận hai. Chuỗi '⿱木⿰木木' của chữ
        #    森 phải cho cây hai tầng, không phải một tầng ba lá.
        # 2. Chỉ đệ quy vào một thành phần khi thành phần đó KHÔNG phải là một
        #    trong 214 bộ Khang Hy. Bộ thủ là nút lá, kể cả khi dữ liệu có chuỗi
        #    IDS cho nó. Bắt buộc phải có quy tắc này: nguồn dữ liệu phân tách
        #    cả bộ thủ xuống tận nét (口 = ⿱冂一, 木 = ⿻十八, 十 = ⿻一丨), nên
        #    đệ quy không điều kiện sẽ làm mọi chữ tan thành nét. Kết quả đó vô
        #    dụng với người học và mâu thuẫn với chính mô hình của ứng dụng, vì
        #    màn hình Bản đồ bộ thủ coi 214 bộ là đơn vị nguyên tử.
        # 3. Mang theo tập chữ đã thăm trên đường đi; gặp lại một chữ đã có trên
        #    đường đi thì dừng nhánh đó và đặt truncated = True. Chạm MAX_DEPTH
        #    cũng đặt truncated = True.
        #
        # Chữ không phân tách được trả về nút lá, children rỗng, truncated = False.

    def radical_of(self, ch: str) -> Radical | None: ...
    def same_radical_learned(self, ch: str, limit: int = 12) -> list[str]: ...   # FR-15
    def radical_map(self) -> list[tuple[Radical, int]]: ...  # FR-34, đếm theo số chữ khác nhau
```

`truncated` phải là một trường trên nút chứ không phải một ngoại lệ. Giao diện cần
vẽ được phần cây đã dựng xong kèm dấu hiệu là còn nữa, chứ không phải bỏ trắng cả
khối vì một nhánh sâu.

### 13.8. Tầng bọc PDF và OCR

```python
@dataclass(frozen=True)
class TextSpan:
    text: str
    size: float
    x0: float; y0: float; x1: float; y1: float

class PdfSource:
    def __init__(self, path: str, ocr: "OcrEngine | None" = None) -> None: ...

    def page_count(self) -> int: ...
    def outline(self) -> list[tuple[int, str, int]]: ...     # cấp, tiêu đề, chỉ số trang
    def is_image_page(self, page: int) -> bool: ...          # dưới 20 ký tự CJK, xem QT-02 bước 2
    def classify(self) -> str: ...                           # 'digital' | 'scanned' | 'mixed'

    def spans(self, page: int, band: tuple[float, float] | None = None) -> list[TextSpan]: ...
        # Trả về các đoạn văn bản kèm cỡ chữ và toạ độ.
        # Trang ảnh thì tự chạy OCR và suy cỡ chữ từ chiều cao hộp bao,
        # nên tầng trên không cần biết trang đó là chữ hay ảnh.
        # band giới hạn theo tỷ lệ chiều cao trang, ví dụ (0.0, 0.25) cho dải trên.

    def render(self, page: int, dpi: int = 300) -> bytes: ...
```

`spans` che hoàn toàn khác biệt giữa trang chữ và trang ảnh. Đây là chỗ quyết định
`splitter` và `vocab` có kiểm thử được hay không: nhờ nó, hai module đó chỉ làm việc
với danh sách `TextSpan` và có thể chạy trên dữ liệu tự tạo, không cần PDF thật.

### 13.9. splitter

```python
class Splitter:
    def __init__(self, src: PdfSource, ai: "AiClient | None" = None) -> None: ...

    def summarize(self) -> list[PageSummary]: ...          # QT-02b bước 1
    def by_outline(self) -> list[LessonBoundary] | None: ...   # nấc 1
    def by_printed_toc(self) -> list[LessonBoundary] | None: ...   # nấc 2
    def by_ai(self, pages: list[PageSummary]) -> list[LessonBoundary] | None: ...   # nấc 3
    def by_heading_scan(self) -> list[LessonBoundary] | None: ...  # nấc 4

    def run(self, use_ai: bool) -> tuple[list[LessonBoundary], str]: ...
        # Chạy thang năm nấc, trả về kết quả kèm tên nấc đã dùng.
        # Không nấc nào đạt thì trả về danh sách rỗng và 'manual'.

    @staticmethod
    def accepts(bounds: list[LessonBoundary], page_count: int) -> bool: ...
        # Bốn điều kiện ở QT-02 bước 3. Hàm tĩnh, không phụ thuộc trạng thái,
        # nên kiểm thử được trực tiếp bằng dữ liệu dựng tay.
```

Mỗi nấc là một hàm riêng trả về cùng một kiểu và có thể gọi độc lập. Đây không phải
để cho đẹp: EV-09 yêu cầu chạy ba nấc riêng rẽ trên cùng một quyển rồi so kết quả,
và nếu thang nấc được viết thành một hàm dài thì phép đo đó không thực hiện được.

### 13.10. vocab

```python
class VocabExtractor:
    def __init__(self, src: PdfSource, dict_db: DictDb, ai: "AiClient | None" = None) -> None: ...

    def locate(self, b: LessonBoundary) -> tuple[int, int] | None: ...   # QT-03 bước 1
    def columns(self, spans: list[TextSpan]) -> list[list[TextSpan]]: ...   # QT-03 bước 2
    def parse_lines(self, column: list[TextSpan], page: int) -> list[VocabRow]: ...   # bước 3
    def validate(self, row: VocabRow) -> tuple[bool, str | None]: ...     # bước 4
    def extract(self, b: LessonBoundary) -> list[VocabRow]: ...           # bước 1 tới 5

    def repair_with_llm(self, rows: list[VocabRow]) -> list[VocabRow]: ...   # bước 6, FR-28
    def extract_with_vision(self, page: int) -> list[VocabRow]: ...          # bước 7, FR-51
```

`validate` trả về cả lý do chứ không chỉ đúng sai, và lý do đó đi thẳng vào
`VocabRow.review_reason` rồi hiện lên giao diện sửa tay. Người dùng thấy "pinyin có 3
âm tiết nhưng từ có 2 chữ" sẽ sửa được trong vài giây; thấy "cần xem lại" thì phải tự
đi tìm xem sai ở đâu.

### 13.11. importer và hợp đồng luồng nền

```python
class ImportProgress(NamedTuple):
    stage: str        # 'classify' | 'summarize' | 'split' | 'ocr' | 'vocab'
    current: int
    total: int
    message: str

class Importer(QObject):
    progress = Signal(ImportProgress)
    needs_confirm = Signal(list)      # list[LessonBoundary], chờ người dùng xác nhận
    finished = Signal(int)            # book_id
    failed = Signal(str)

    def __init__(self, src, splitter, vocab, user_db, use_ai: bool) -> None: ...
    def start(self) -> None: ...
    def confirm(self, bounds: list[LessonBoundary]) -> None: ...
    def cancel(self) -> None: ...
```

Ba ràng buộc, vi phạm là hỏng theo kiểu khó tìm:
- `Importer` chạy trong `QThread` riêng. Nó không được đụng vào bất cứ đối tượng đồ
  hoạ nào, chỉ phát tín hiệu.
- `UserDb` dùng trong luồng nền phải là kết nối riêng của luồng đó. SQLite không cho
  dùng chung một đối tượng kết nối giữa các luồng.
- `cancel` đặt cờ, và mọi vòng lặp dài phải kiểm cờ đó ở mỗi trang. Huỷ giữa chừng
  thì `book` giữ nguyên `import_state = 'importing'` để lần mở sau hỏi lại người dùng,
  đúng như dòng tương ứng ở mục 8.

### 13.12. scheduler

Module nhỏ nhất và là module duy nhất trong `service/` hoàn toàn thuần tuý: không
chạm cơ sở dữ liệu, không chạm mạng, không chạm đồng hồ hệ thống. Ngày hôm nay được
truyền vào chứ không tự lấy, để kiểm thử được lịch ôn mà không phải chờ qua đêm.

```python
GRADE_TO_Q = {0: 2, 1: 3, 2: 5}   # Quên, Khó, Nhớ

def apply_review(before: ReviewOutcome, grade: int, today: date) -> ReviewOutcome: ...
def initial(today: date) -> ReviewOutcome: ...
```

Thứ tự tính toán bên trong `apply_review`, viết ra vì đây là chỗ hai cách cài đặt hợp
lý cho ra hai kết quả khác nhau và không có cách nào đoán ra từ mô tả:

```
1. q = GRADE_TO_Q[grade]
2. ease = max(1.3, ease + (0.1 − (5−q)·(0.08 + (5−q)·0.02)))       cập nhật TRƯỚC
3. q == 2:  repetition = 0, interval = 1, lapse_count += 1
   q == 3:  repetition giữ nguyên, interval = round(interval × 1.2)
   q == 5:  repetition += 1
            repetition == 1 -> interval = 1
            repetition == 2 -> interval = 6
            repetition >= 3 -> interval = round(interval × ease)     dùng ease MỚI
4. làm tròn nửa lên, không dùng làm tròn nửa về số chẵn
5. interval tối thiểu là 1
6. due_date = today + interval
7. chuyển trạng thái theo QT-04 bước 6
```

### 13.13. aiclient

```python
class AiError(Exception): ...
class AiUnavailable(AiError): ...      # mất mạng, hết hạn mức, khoá sai
class AiInvalidOutput(AiError): ...    # trả về không đúng lược đồ

class AiClient:
    def __init__(self, api_key: str, model: str, timeout_s: int = 60) -> None: ...
    def complete_json(self, prompt: str, schema: dict, images: list[bytes] | None = None) -> dict: ...
```

Chỉ một phương thức, và nó không biết gì về bài học, bộ thủ hay từ vựng. Toàn bộ
prompt và toàn bộ kiểm chứng nằm ở module gọi nó. Nhờ vậy `splitter` và `vocab` kiểm
thử được bằng một `AiClient` giả trả về JSON dựng sẵn, kể cả JSON cố tình sai.

`AiUnavailable` không bao giờ được để nổi lên tới giao diện thành hộp thoại lỗi. Mọi
chỗ gọi đều bắt nó và đi tiếp bằng đường lui cục bộ, đúng như ràng buộc ở mục 2.6.

---

## 14. BỘ KIỂM THỬ TỐI THIỂU

Mục này là phần còn thiếu quan trọng nhất của bản 0.3. Đặc tả nói ứng dụng phải làm
gì, nhưng không có cách nào biết mã nguồn có làm đúng thế không. Các số liệu dưới đây
là đáp án cố định, tự tay kiểm, và phải viết xong trước khi viết mã của module tương
ứng. Viết sau thì gần như chắc chắn sẽ vô thức chép lại hành vi của mã, kể cả hành
vi sai.

Chạy bằng `pytest`. Mốc trước buổi bảo vệ: toàn bộ mục 14.2 tới 14.6 phải xanh.

### 14.1. Fixtures cần chuẩn bị

| Tên | Nội dung | Dùng cho |
|---|---|---|
| `mini_dict.sqlite` | Khoảng 300 chữ và 200 từ, đủ phủ mọi ca ở mục 14.2 tới 14.4 | Toàn bộ test tầng dưới |
| `spans_1col.json` | Danh sách `TextSpan` của một bảng 生词表 một cột, chép tay từ sách thật | vocab |
| `spans_2col.json` | Như trên nhưng bảng hai cột | vocab, ca khó nhất |
| `summary_boya.json` | Bản tóm lược 248 dòng của một giáo trình thật | splitter |
| `bounds_boya.json` | Đáp án ranh giới bài của chính quyển đó, đối chiếu thủ công | splitter, EV-01 |
| `ai_replies/` | Các JSON dựng sẵn, gồm cả bản hợp lệ và bản cố tình sai từng điều kiện | splitter, vocab |

Năm giáo trình PDF của EV-01 không nằm trong kho mã nguồn vì vấn đề bản quyền. Chỉ
có bản tóm lược và đáp án ranh giới, hai thứ này không chứa nội dung sách.

### 14.2. pinyin

Chuyển từ dạng số sang dạng dấu. Quy tắc đặt dấu: a và e luôn nhận dấu; trong `ou`
thì o nhận; còn lại nguyên âm cuối nhận. Thanh 5 và thanh 0 không đánh dấu.

| Vào | Ra mong đợi | Ca kiểm |
|---|---|---|
| `ren4 shi5` | `rènshi` | thanh nhẹ không dấu |
| `hao3` | `hǎo` | a ưu tiên |
| `gou3` | `gǒu` | ngoại lệ ou |
| `liu2` | `liú` | nguyên âm cuối |
| `nu:3` | `nǚ` | quy ước `u:` của CC-CEDICT |
| `er2` | `ér` | một nguyên âm |
| `peng2 you5` | `péngyou` | ghép hai âm tiết |

Chuẩn hoá về dạng phẳng:

| Vào | `to_plain` |
|---|---|
| `rènshi` | `renshi` |
| `nǚ` | `nv` |
| `lǜ` | `lv` |
| `ǖ` | `v` |
| `zhǎngdà` | `zhangda` |
| `xi'an` | `xian` |

Ba dòng có ü không phải cho đủ bộ. Cài đặt tham chiếu dùng để kiểm chứng chính bảng
này đã sai đúng ở đó, và chỉ lộ ra khi chạy bảng. Xem ghi chú ở mục 13.5.

Tách âm tiết, có ràng buộc số lượng:

| Vào | `expect` | Ra mong đợi |
|---|---|---|
| `renshi` | 2 | `['ren', 'shi']` |
| `xian` | 1 | `['xian']` |
| `xian` | 2 | `['xi', 'an']` |
| `xian` | 3 | `None` |
| `zhongguo` | 2 | `['zhong', 'guo']` |
| `qwerty` | 2 | `None` |

Ba dòng của `xian` là lý do hàm này nhận tham số `expect`. Không có ràng buộc thì
dòng thứ hai không có cách nào trả đúng.

### 14.3. Chiết tự

| Chữ | IDS | Thành phần | Bộ | Tổng nét | Độ sâu cây |
|---|---|---|---|---|---|
| 认 | `⿰讠人` | 讠, 人 | 149 言 | 4 | 1 |
| 识 | `⿰讠只` | 讠, 只 | 149 言 | 7 | 2 |
| 谢 | `⿰讠射` | 讠, 射 | 149 言 | 12 | 2 |
| 好 | `⿰女子` | 女, 子 | 38 女 | 6 | 1 |
| 名 | `⿸夕口` | 夕, 口 | 30 口 | 6 | 1 |
| 字 | `⿱宀子` | 宀, 子 | 39 子 | 6 | 1 |
| 朋 | `⿰月月` | 月, 月 | 74 月 | 8 | 1 |
| 明 | `⿰日月` | 日, 月 | 72 日 | 8 | 1 |
| 森 | `⿱木⿰木木` | 木, 木, 木 | 75 木 | 12 | 2 |
| 一 | `NULL` | không có | 1 一 | 1 | 0 |

Cột độ sâu được tính theo đúng ba quy tắc dừng ở mục 13.7. Hai chữ 识 và 谢 sâu 2
vì thành phần 只 và 射 không phải bộ Khang Hy nên còn đệ quy tiếp một tầng
(只 = ⿱口八, 射 = ⿰身寸), rồi dừng vì 口, 八, 身, 寸 đều là bộ. Chữ 森 sâu 2 do cấu
trúc lồng ngay trong chuỗi IDS `⿱木⿰木木`, không do đệ quy. Tám chữ còn lại sâu 1
vì mọi thành phần của chúng đều là bộ.

Bản 0.5 lần đầu ghi cả tám chữ đầu là độ sâu 1. Con số đó chỉ đúng nếu không đệ quy
vào thành phần nào cả, tức là mâu thuẫn với FR-11 và với mục 13.7.

Chữ 名 là ca cho thấy hai nguồn có thể mâu thuẫn: cjkvi-ids ghi `⿱夕口` còn
makemeahanzi ghi `⿸夕口`. Quy tắc chọn nguồn phải viết ra chứ không để người cài đặt
tự quyết: **cjkvi-ids là nguồn chuẩn cho IDS, makemeahanzi chỉ dùng bổ khuyết khi
cjkvi-ids không có chữ đó.** Bảng trên ghi theo nguồn thực tế đã nạp.

Ba ca biên bắt buộc:
- Chữ không phân tách được, ví dụ 一: trả về nút lá, `children` rỗng, `truncated`
  bằng False. Nút lá khác với nút bị cắt, và trộn hai thứ này là lỗi hay gặp.
  Trong `dict.sqlite`, chữ loại này có `ids` bằng NULL. Một số nguồn khác ghi
  `ids` bằng chính chữ đó; cài đặt phải coi cả hai dạng là không phân tách được.
- Chu trình: thêm vào `mini_dict.sqlite` hai chữ giả A và B với IDS trỏ lẫn nhau.
  Hàm phải kết thúc, không tràn ngăn xếp, và đặt `truncated` bằng True.
- Chuỗi sâu quá 6 tầng: dừng ở tầng 6, phần đã dựng vẫn trả về đầy đủ.

### 14.4. Xếp hạng tìm kiếm

Test này chạy trên `mini_dict.sqlite` dựng bằng `pytest` fixture, **không chạy trên
`dict.sqlite` thật**. Lý do: `dict.sqlite` có 5001 từ với `freq_rank` sinh từ cấp HSK
làm giá trị thay thế, nên thứ tự trả về có thể tình cờ đúng vì lý do khác với lý do
đang muốn kiểm. Fixture nạp đúng ba dòng dưới đây và không dòng nào khác:

| `word_simp` | `pinyin_plain` | `hsk_level` | `freq_rank` |
|---|---|---|---|
| 认识 | renshi | 1 | 412 |
| 人事 | renshi | 5 | 2108 |
| 人士 | renshi | 6 | 2687 |

Thứ tự trả về phải là 认识, 人事, 人士. Ba dòng này được chọn để tách bạch hai yếu tố
xếp hạng: 认识 thắng nhờ cả cấp HSK lẫn tần suất, còn 人事 thắng 人士 chỉ nhờ cấp HSK
chênh một bậc trong khi tần suất chênh không nhiều. Đổi trọng số trong công thức ở
mục 13.6 là thứ tự này đổi theo, nên test bắt được lỗi trọng số.

Lưu ý về dữ liệu thật: trong `dict.sqlite`, 人士 nằm ở HSK 6 chứ không phải ngoài
HSK, và `freq_rank` là số sinh từ cấp HSK chứ không phải thứ hạng tần suất thật.
Muốn `freq_rank` có nghĩa thì phải nạp thêm một bảng tần suất ngoài; chừng nào chưa
có, FR-05 chỉ nên quảng cáo là xếp theo cấp HSK.

Hai ca biên:
- Truy vấn `认识` phải cho 认识 hạng 1 với `matched_by` bằng `hanzi`.
- Truy vấn `renshix` không khớp gì; `search` trả rỗng còn `suggest` phải trả 认识.
  Kết quả khớp gần không bao giờ được lẫn vào `search`.

### 14.5. SM-2

Một chuỗi đánh giá liên tiếp trên cùng một từ, bắt đầu từ trạng thái mới. Đây là bảng
đáng giá nhất trong cả mục 14, vì SM-2 sai thì không ai phát hiện được bằng mắt: ứng
dụng vẫn chạy, thẻ vẫn hiện, chỉ có lịch ôn là vô nghĩa.

| Lần | Nút | q | `ease` sau | `repetition` | `interval` | `status` |
|---|---|---|---|---|---|---|
| 0 | — | — | 2.50 | 0 | 0 | new |
| 1 | Nhớ | 5 | 2.60 | 1 | 1 | learning |
| 2 | Nhớ | 5 | 2.70 | 2 | 6 | learning |
| 3 | Nhớ | 5 | 2.80 | 3 | 17 | learning |
| 4 | Nhớ | 5 | 2.90 | 4 | 49 | known |
| 5 | Khó | 3 | 2.76 | 4 | 59 | known |
| 6 | Quên | 2 | 2.44 | 0 | 1 | learning |
| 7 | Nhớ | 5 | 2.54 | 1 | 1 | learning |
| 8 | Nhớ | 5 | 2.64 | 2 | 6 | learning |

Kiểm lại vài dòng bằng tay: lần 3 lấy 6 nhân 2.80 bằng 16.8, làm tròn thành 17, tức
là dùng `ease` đã cập nhật chứ không dùng 2.70. Lần 5 lấy 59 từ 49 nhân 1.2 bằng
58.8. Lần 6 đưa `lapse_count` lên 1 và `repetition` về 0.

Bốn ca biên:

| Ca | Vào | Ra mong đợi |
|---|---|---|
| Chặn dưới hệ số dễ | `ease = 1.40`, bấm Quên | `ease = 1.30`, không phải 1.08 |
| Làm tròn nửa lên | `interval = 1`, `ease = 2.40`, `repetition = 3`, bấm Nhớ | `interval = 3`, không phải 2 |
| Ngày đến hạn | `today = 2026-07-27`, `interval = 6` | `due_date = 2026-08-02` |
| Khoảng tối thiểu | `interval = 0`, bấm Khó | `interval = 1`, không phải 0 |

Ca làm tròn có mặt ở đây vì hàm `round` của Python làm tròn nửa về số chẵn, nên
`round(3.5)` trả về 4 nhưng `round(2.5)` trả về 2. Cài đặt phải tự làm tròn, không
dùng thẳng hàm dựng sẵn.

Bộ số của ca này phải chọn rất cẩn thận, và bản 0.5 lần đầu chọn sai. Ca cũ dùng
`interval = 2`, `ease = 1.75`: sau khi cập nhật ease thành 1.85 thì tích là 3.7, mà
3.7 làm tròn kiểu nào cũng ra 4, nên ca đó **không phân biệt được hai cách làm
tròn** — nó chỉ bắt được lỗi cắt cụt bằng `int()`. Muốn phân biệt thì tích phải rơi
đúng vào một nửa và phải biểu diễn chính xác được bằng số thực nhị phân. Bộ số hiện
tại thoả cả hai: `2.40 + 0.1` cho ra đúng `2.5`, nhân với `interval = 1` ra đúng
`2.5`, chỗ mà `round` dựng sẵn trả về 2 còn `ROUND_HALF_UP` trả về 3.

So sánh số thực bằng `pytest.approx` với sai số 1e-9, đừng so bằng dấu bằng.

### 14.6. Kiểm chứng bảng từ mới

Đây là tầng bảo vệ toàn bộ dữ liệu học tập, và là chỗ bản 0.1 sai nặng nhất. Nhóm ca
đầu tiên phải đạt, vì nếu không thì mọi bảng từ mới của mọi giáo trình đều bị gắn cờ.

| Từ | Pinyin | Kết quả | Vì sao |
|---|---|---|---|
| 认识 | `rènshi` | đạt | 识 đọc khinh thanh, so khớp sau khi bỏ thanh |
| 名字 | `míngzi` | đạt | 字 khinh thanh |
| 朋友 | `péngyou` | đạt | 友 khinh thanh |
| 谢谢 | `xièxie` | đạt | chữ lặp, âm tiết sau khinh thanh |
| 好了 | `hǎo le` | đạt | 了 đa âm, khớp âm `le` |
| 长大 | `zhǎng dà` | đạt | 长 đa âm, khớp âm thứ hai chứ không phải âm chính |

Nhóm phải bị gắn cờ:

| Từ | Pinyin | `review_reason` mong đợi |
|---|---|---|
| 认识 | `rènshishi` | số âm tiết không khớp số chữ |
| 认识 | `rènqí` | âm tiết `qi` không thuộc âm đọc của 识 |
| 认X识 | `rènshi` | có ký tự không phải chữ Hán |
| 龘 | `dá` | chữ không có trong bảng char |

Ca 长大 quan trọng riêng: nếu cài đặt chỉ so với `char.pinyin` thì nó sẽ đối chiếu
`zhǎng` với âm chính `cháng` và gắn cờ sai. Đây chính là ca chứng minh vì sao phải có
bảng `char_reading`.

### 14.7. Kiểm chứng đề xuất của mô hình

Sáu điều kiện ở QT-02b bước 3, mỗi điều kiện một tệp JSON dựng sẵn trong `ai_replies/`:

| Tệp | Nội dung | Kết quả mong đợi |
|---|---|---|
| `ok.json` | 15 mốc hợp lệ | nhận, `split_method = 'llm'` |
| `bad_anchor.json` | một `anchor_id` bằng 9999, không có thật | loại riêng phần tử đó, 14 mốc còn lại vẫn nhận |
| `bad_order.json` | trang không tăng dần | loại toàn bộ, rơi xuống nấc 4 |
| `bad_numbering.json` | `lesson_no` nhảy từ 3 sang 5 | loại toàn bộ |
| `bad_gap.json` | một bài dài gấp 8 lần trung vị | `confidence` hạ xuống 0.4, vẫn nhận |
| `too_few.json` | chỉ 3 mốc | loại toàn bộ |
| `malformed.json` | không phải JSON hợp lệ | ném `AiInvalidOutput`, rơi xuống nấc 4 |

Thêm hai test về đường lui, quan trọng ngang các test trên:
- `AiClient` giả ném `AiUnavailable`: `Splitter.run(use_ai=True)` phải trả về kết quả
  của nấc 4, không ném ngoại lệ ra ngoài.
- `Splitter.run(use_ai=False)`: `by_ai` không được gọi lần nào. Kiểm bằng cách đếm số
  lần gọi trên đối tượng giả.

### 14.8. Tách cột và bóc tách dòng

Chạy trên `spans_2col.json`, là ca mà bản 0.1 làm sai:
- `columns` phải trả về đúng 2 cột.
- Tổng số dòng bóc tách được bằng tổng số mục từ thật, không phải một nửa.
- Không dòng nào có `meaning_src` chứa chữ Hán của mục từ kế bên. Đây là dấu hiệu
  đặc trưng của lỗi trộn cột, và là thứ cần kiểm trực tiếp chứ không suy ra từ số
  lượng dòng.

Trên `spans_1col.json`: `columns` trả về đúng 1 cột, không được cắt nhầm thành 2.

### 14.9. Test golden trên sách thật

Chạy `Splitter` trên `summary_boya.json`, đối chiếu với `bounds_boya.json`. Một bài
tính là đúng khi khớp cả hai mốc trang. Ngưỡng để test xanh là 90%, đúng theo EV-01.

Test này chạy chậm và cần fixture lớn nên tách thành nhóm riêng, đánh dấu
`@pytest.mark.golden`, không chạy trong vòng lặp sửa mã hằng ngày.

Đây cũng chính là dữ liệu của EV-09. Viết một lần, dùng cho cả kiểm thử lẫn chương
đánh giá, và nhờ vậy con số trong báo cáo là con số sinh ra từ mã chạy được chứ
không phải con số gõ tay vào bảng.

### 14.10. Thứ tự làm

Không viết cả mục 14 một lượt. Mỗi nhóm test viết ngay trước module tương ứng:

| Thứ tự | Viết test | Rồi viết mã |
|---|---|---|
| 1 | 14.2 | `service/pinyin.py` |
| 2 | 14.5 | `service/scheduler.py` |
| 3 | 14.3 | `service/decomposer.py` |
| 4 | 14.4 | `service/lookup.py` |
| 5 | 14.6 | `vocab.validate` |
| 6 | 14.8 | `vocab.columns`, `vocab.parse_lines` |
| 7 | 14.7 | `splitter.by_ai` và tầng kiểm chứng |
| 8 | 14.9 | phần còn lại của `splitter` |

Hai module đầu là lựa chọn có chủ ý: cả hai đều thuần tuý, không chạm cơ sở dữ liệu,
không chạm PDF, không chạm mạng. Chúng cho ra kết quả xanh trong ngày đầu tiên và
dựng sẵn thói quen chạy `pytest` trước khi bắt đầu phần khó.

---

## PHỤ LỤC A. NGUỒN DỮ LIỆU VÀ GIẤY PHÉP

| Nguồn | Nội dung | Giấy phép | Ghi chú |
|---|---|---|---|
| makemeahanzi | Chữ, IDS, thành phần, âm đọc, nghĩa Anh | LGPL và Arphic Public License | Nguồn chính của bảng `char`; dẫn xuất từ Unihan và CC-CEDICT |
| OpenCC | Ánh xạ giản thể sang phồn thể | Apache 2.0 | Dùng cả để suy dạng giản thể của bộ thủ |
| hskhsk.com | Danh sách từ HSK 1-6 kèm pinyin và nghĩa | Xem trang nguồn | Nguồn của bảng `word`, và là nguồn suy `char_reading` |
| Khối Unicode U+2F00, U+2E80 | 214 bộ Khang Hy và các biến thể | Unicode License | Sinh bằng mã, không nhập tay |
| Unihan Database | Bộ thủ, số nét, pinyin, nghĩa | Unicode License | Nguồn gián tiếp qua makemeahanzi |
| CC-CEDICT | Từ điển từ ghép Hán-Anh | CC BY-SA 4.0 | Nguồn gián tiếp; bắt buộc ghi nhận và chia sẻ tương tự |
| cjkvi-ids | Chuỗi IDS mô tả cấu trúc chữ | Xem repo | Kiểm tra lại trước khi nộp |
| kfcd/chaizi | Thành phần cấu tạo chữ | Xem repo | Kiểm tra lại trước khi nộp |
| PaddleOCR | Mô hình OCR | Apache 2.0 | Cho phép dùng tự do |
| PySide6 | Khung giao diện | LGPL v3 | Phải đóng gói bằng PyInstaller ở chế độ `--onedir` để giữ thư viện thành tệp riêng; bản `--onefile` gộp tất cả vào một exe là vùng xám với LGPL |

Ghi lại phiên bản và ngày tải của từng nguồn. Danh sách này phải xuất hiện trong
phần Tài liệu tham khảo của báo cáo.
