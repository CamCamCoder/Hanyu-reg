# 05 — lát cắt giao diện Tra cứu

> **Phiên này ĐÃ CHẠY XONG.** Kết quả nghiệm thu ghi ở mục 7 của `BAN-GIAO.md`.
> Khối prompt dưới đây là bản đã vá, giữ lại làm mẫu cho các packet giao diện sau.
> Bốn điều rút ra: liệt kê đủ số tệp kể cả tệp ngoại lệ, nói rõ cột nào trong
> `dict.sqlite` đang rỗng, nói rõ số nào trong mockup là số minh hoạ, và cấm sửa
> ngược lại tài liệu để khớp màn hình.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Phiên này KHÁC bốn phiên trước: không có bảng đáp án, vì giao diện không kiểm được
bằng pytest. Tiêu chí xong nằm ở mục "Nghiệm thu" bên dưới, kiểm bằng mắt.

Cần tạo đúng sáu tệp:
  hanzi_app/main.py                    điểm vào, dựng đối tượng rồi bơm vào nhau
  hanzi_app/ui/main_window.py          cửa sổ chính, thanh điều hướng trái
  hanzi_app/ui/screen_lookup.py        màn hình Tra cứu
  hanzi_app/ui/widgets/tianzige.py     ô 田字格 vẽ một chữ
  hanzi_app/ui/widgets/decomp_tree.py  hàng chiết tự chữ = thành phần + thành phần
  hanzi_app/data/userdb.py             bản tối thiểu, xem ghi chú cuối prompt

Chỉ dựng MỘT màn hình Tra cứu. Ba màn hình còn lại của mục 7 để phiên sau; thanh
điều hướng vẫn có đủ bốn mục nhưng ba mục kia bấm vào chỉ hiện chỗ trống có chữ
"Chưa làm ở phiên này".

Sáu điểm rất dễ sai:

- Không sửa các tệp ĐÃ CÓ trong service/ hay data/. Tầng ui chỉ được GỌI xuống.
  Thiếu gì ở tầng dưới thì dừng lại báo, đừng tự thêm phương thức. Tệp userdb.py
  mới là ngoại lệ duy nhất được phép tạo trong data/.

- Nút nhóm lồng. DecompNode có cờ is_group; nút đó KHÔNG được vẽ vào ô 田字格 vì
  char của nó là chuỗi IDS như '⿰木木', vẽ vào ô sẽ trông như lỗi hiển thị. Nút
  nhóm chỉ vẽ dấu ngoặc gom các con của nó.

- Nút vừa is_group vừa truncated và không có con: vẽ dấu hiệu là còn nữa, ví dụ
  dấu ba chấm, KHÔNG vẽ cặp ngoặc rỗng, và vẫn không vẽ vào ô 田字格.

- Cột pos của bảng word rỗng toàn bộ 5001 dòng, cột hanviet của bảng char cũng
  rỗng toàn bộ 9534 dòng. Chỗ nào cần từ loại hoặc âm Hán-Việt thì hiện trạng thái
  rỗng có nhãn rõ ràng, KHÔNG bịa và KHÔNG lấy theo mockup. Mockup 7.2 vẽ sẵn chip
  [động từ] chỉ là hình minh hoạ. Tên và nghĩa bộ thủ thì có thật, lấy từ bảng
  radical, dùng bình thường.

- Phông chưa có trong kho. Mục 6.2 yêu cầu đóng gói ba phông và nạp bằng
  QFontDatabase. Chưa tải được thì dùng phông hệ thống và in một dòng cảnh báo ra
  console, KHÔNG được im lặng bỏ qua và cũng không tự đi tải về.

- meaning_vi trong dict.sqlite còn rỗng. Khối NGHĨA TỪ ĐIỂN hiện nghĩa tiếng Anh
  và ghi rõ nhãn là tiếng Anh, không để trống, không bịa.

Số HSK và số tần suất trong mockup 7.2 là số fixture của mục 14.4, không khớp
dict.sqlite thật. Số thật: 认识 HSK1 #85, 人事 HSK5 #4984, 人士 HSK6 #5026. Thứ tự
xếp hạng không đổi nên tiêu chí nghiệm thu giữ nguyên. Không sửa dữ liệu cho khớp
mockup, không sửa mục 14.4, và không báo là không đạt chỉ vì con số trên màn hình
khác hình vẽ.

Luồng phải chạy được đầu cuối: gõ renshi vào ô tìm kiếm, bấm Tìm, hiện danh sách
kết quả xếp hạng, bấm vào 认识, hiện trang chi tiết gồm khối thông tin từ, khối
chiết tự với ô 田字格, và khối nguồn nếu có. Ba khối còn lại của mockup 7.2, tức
là phần diễn giải và phần "bạn đã gặp bộ này ở đâu", để phiên sau.

Cấu trúc lắp ráp bắt buộc, theo mục 13.1: hanzi_app/main.py mở DictDb và UserDb,
dựng LookupService và Decomposer, rồi truyền vào MainWindow. Màn hình gọi
lookup.detail() để lấy thông tin từ và gọi decomposer.tree() cho từng chữ, rồi tự
ghép; lookup KHÔNG gọi sang decomposer.

UserDb chưa tồn tại. Dựng một bản tối thiểu ngay trong phiên này chỉ với hai
phương thức mà lookup.detail() cần là word_source và get_progress, cả hai trả về
None, kèm ghi chú rằng phiên userdb sẽ thay thế. Đây là ngoại lệ được phép.

Viết thẳng nội dung từng tệp, mỗi tệp một khối mã có ghi rõ đường dẫn. Xong thì
chạy `python -m hanzi_app.main`, tự đi hết tám mục nghiệm thu, và báo từng mục đạt
hay không đạt. Mục nào không đạt thì nói rõ mục đó chứ đừng báo là xong.
```

## Nghiệm thu

Không có pytest cho phiên này. Chạy `python main.py` rồi tự kiểm đủ tám mục:

1. Cửa sổ mở lên, tối thiểu 1100 x 700, thanh trái rộng 212 px, đủ bốn mục điều hướng.
2. Gõ `renshi` bấm Tìm, ra đúng thứ tự 认识, 人事, 人士.
3. Gõ `认识` ra 认识 ở vị trí đầu.
4. Gõ `renshix` không ra kết quả nào, nhưng hiện gợi ý 认识.
5. Bấm vào 认识, trang chi tiết hiện pinyin, từ loại, cấp HSK.
6. Khối chiết tự hiện hai ô 田字格 cho 认 và 识, mỗi ô có viền màu nhấn chính và
   hai đường đứt chia tư.
7. Chữ 识 hiện cây hai tầng (讠 và 只, rồi 只 tách tiếp), chữ 认 hiện một tầng.
8. Bấm ba mục điều hướng còn lại không làm ứng dụng sập.

Chụp màn hình trang chi tiết của 认识 rồi báo cáo. Mục nào không đạt thì nói rõ
mục đó chứ đừng báo là xong.

---

> Bốn mục dưới đây là **bản chép** từ `dac-ta-ung-dung-v0.5.md`. Bản chép trôi được,
> và đã trôi một lần với mục 13.3 (xem lỗi 6 trong `BAN-GIAO.md`). Đối chiếu với đặc
> tả gốc trước khi dùng lại cho packet sau.

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

`#9C7318` KHÔNG được dùng làm màu chữ: đo được 4.02:1 trên `#FBF7EC` và 4.30:1 trên
`#FFFFFF`, đều trượt ngưỡng 4.5. Chỉ dùng cho viền, chấm trạng thái và biểu tượng,
nơi ngưỡng là 3:1. Chữ trên dải cảnh báo dùng `#6B5310`, đạt 6.84:1. Bảng đo đầy đủ
ở mục 6.1 của đặc tả gốc.

Mọi cặp màu chữ trên nền phải đạt tỉ số tương phản từ 4.5:1 trở lên. Màu chữ mờ ở
bản 0.1 là `#8E8A82`, chỉ đạt khoảng 3.1:1 trên nền `#F5F4F0`, tức là không đạt,
mà đây lại đúng là màu dùng cho cỡ chữ nhỏ nhất; đã đổi thành `#716D66`, khoảng
5.0:1. Kiểm tra lại toàn bảng bằng một script tính tương phản, không ước lượng
bằng mắt.

---

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

---

### 7.1. Khung chung

Cửa sổ tối thiểu 1100 x 700. Thanh điều hướng bên trái rộng cố định 212 px.

---

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

Các con số HSK và thứ hạng trong hình lấy từ fixture của mục 14.4, không phải từ
`dict.sqlite` thật. Số thật: 认识 HSK1 #85, 人事 HSK5 #4984, 人士 HSK6 #5026, thứ tự
không đổi. Nghĩa tiếng Việt và chip từ loại trong hình là chỗ dành sẵn; `meaning_vi`
và `pos` đều rỗng, giao diện hiện trạng thái rỗng có nhãn.