# BÀN GIAO TRẠNG THÁI DỰ ÁN

Tệp này ghi lại những gì **không** nằm trong đặc tả: các quyết định đã chốt kèm lý
do, kết quả đo trên sách thật, việc còn nợ, và những lỗi đã mắc để khỏi lặp lại.
Đọc tệp này cộng với `dac-ta-ung-dung-v0.5.md` và `CLAUDE.md` là đủ để tiếp quản
dự án mà không cần lịch sử trò chuyện.

---

## 1. Đang ở đâu

| Phiên | Module | Trạng thái |
|---|---|---|
| 01 | pinyin | xong, 27 test xanh |
| 02 | scheduler | xong, 23 test xanh, tổng 50 |
| 03 | decomposer | xong, 30 test xanh (28 ban đầu + 2 của 03b) |
| 03b | bảo trì, thêm `DecompNode.is_group` | xong, tổng 120 |
| 04 | lookup | xong, 39 xanh 1 skip, tổng 120 |
| 05 | lát cắt giao diện Tra cứu | xong, nghiệm thu bằng mắt 8/8 mục, xem mục 7 |
| 06 | userdb | xong, 35 test xanh, tổng 154 |
| 06b | bảo trì, tách `repetition` khỏi `review_count` | xong, +7 test, tổng 161 |
| 07 | màn hình Ôn tập, kèm tách `ui/theme.py` | xong, +2 test, tổng 163 xanh 1 skip; nghiệm thu bằng mắt 7/7, xem mục 8 |

Môi trường thực tế: Windows, Python 3.12.9, PySide6 6.11.1, pytest 9.1.1. Đặc tả bản
đầu ghi Python 3.11, đã đổi trong `CLAUDE.md` thành 3.12 cho khớp máy.

`dict.sqlite` đã dựng xong bằng `build_dict.py`: 9534 chữ, 9802 âm đọc, 247 chữ đa
âm, 18803 dòng chiết tự, 5001 từ HSK, có bảng `word_fts`.

---

## 2. Quyết định đã chốt, không nằm trong đặc tả

**Nguồn dữ liệu.** Unihan và CC-CEDICT không tải trực tiếp được, nên dùng
makemeahanzi (dẫn xuất từ cả hai), OpenCC cho phồn thể, hskhsk.com cho từ HSK. 214
bộ Khang Hy sinh bằng mã từ khối Unicode U+2F00, không nhập tay.

**`char_reading` suy ngược từ bảng từ HSK.** makemeahanzi chỉ có 8 chữ đa âm, không
đủ. Cách làm: gióng âm tiết pinyin với chữ Hán trên 4732 từ, cộng 27 dòng chữ đơn
mà nguồn ghi nhiều âm ngăn bằng dấu phẩy. Kết quả 247 chữ đa âm.

**`freq_rank` là số ước lượng, không phải tần suất thật.** Sinh từ cấp HSK theo
công thức `(cấp - 1) * 1000 + thứ tự`. Muốn FR-05 có nghĩa thật thì phải nạp thêm
một bảng tần suất ngoài. Chừng nào chưa có, chỉ nên quảng cáo là xếp theo cấp HSK.

**`meaning_vi` đang rỗng hoàn toàn.** Không có nguồn mở nào cho nghĩa tiếng Việt.
Hai đường: gõ tay khoảng 1000 chữ HSK 1-3, hoặc lấy từ giáo trình. Đã chốt là
**không** đổ nghĩa từ giáo trình vào `dict.sqlite` vì tệp này đóng gói kèm sản phẩm,
làm vậy là phân phối lại bản dịch của nhà xuất bản. Nghĩa từ sách chỉ vào
`lesson_word.meaning_src` trong `user.sqlite`. Lý do đầy đủ ở mục 5.4.

**Còn 267 chữ thiếu bộ thủ, toàn phồn thể.** 0 chữ HSK bị thiếu. Chấp nhận được vì
mục 1.3 giới hạn ở giản thể.

**Nguồn HSK có lỗi gõ.** 严格 ghi `yang2e2` thay vì `yan2ge2`. Vài dòng lẻ, chưa xử lý.

**Cột `pos` rỗng toàn bộ 5001 dòng, `char.hanviet` rỗng toàn bộ 9534 dòng.** Phát
hiện khi soát dữ liệu trước phiên 05, không phải chỉ mỗi `meaning_vi` như bản trước
của tệp này ghi. Giao diện hiện trạng thái rỗng có nhãn, không bịa. Bảng `radical`
thì đủ cả 214 dòng `name_hv` và `meaning_vi`, nên dòng "bộ 讠 (ngôn — lời nói)" là
dữ liệu thật, dùng được.

**Màu cảnh báo `#9C7318` chỉ dùng cho viền, chấm và biểu tượng.** Đo được 4.02:1
trên nền cảnh báo và 4.30:1 trên nền thẻ, trượt ngưỡng chữ 4.5 nhưng dư ngưỡng phi
văn bản 3:1. Chữ trên dải cảnh báo dùng `#6B5310`, đạt 6.84:1. Bảng đo đầy đủ đã
thêm vào mục 6.1 của đặc tả. Màn hình Tra cứu không dùng màu này, nhưng màn hình
Sách và phần bóc tách thì có, nên phải theo ràng buộc từ phiên 06.

**Số trong mockup 7.2 và bảng 14.4 là số fixture, không phải số thật, và đúng như
vậy.** Mục 14.4 cố ý dựng `mini_dict.sqlite` ba dòng với thứ hạng 412 / 2108 / 2687
để tách bạch hai yếu tố xếp hạng. Trên `dict.sqlite` thật là 85 / 4984 / 5026 và
人士 nằm ở HSK 6 chứ không ngoài HSK; thứ tự trả về không đổi. **Đừng sửa số trong
14.4 cho khớp dữ liệu thật** — đã suýt làm một lần. Bản chép trong
`handoff/04-lookup.md` là bản rút gọn đánh mất ngữ cảnh đó; đọc 14.4 ở đặc tả gốc.

**Nút nhóm lồng, hai chi tiết chốt ở 03b.** `ids` của nút nhóm giữ bằng chính đoạn
IDS con, khớp test `test_sam_hai_tang_khong_phai_ba_la`. Nút nhóm bị cắt vì
`MAX_DEPTH` vẫn đặt `is_group = True` dù không có con; giao diện vẽ dấu ba chấm chứ
không vẽ cặp ngoặc rỗng.

**Nút "Thêm vào ôn tập" trên màn hình Tra cứu — lệch có ý thức với QT-04 bước 2.**
QT-04 bước 2 nói từ chỉ vào danh sách ôn tập qua một bài trong sách. Luồng nhập PDF
là phần lớn nhất còn lại của dự án, nên cài đúng đặc tả thì màn hình Ôn tập rỗng và
không dùng được cho tới khi xong cả giai đoạn B, tức là app không học được ngày nào
trong nhiều tuần. Phiên 07 thêm một nút trên trang chi tiết Tra cứu, tạo dòng
`progress` với `source_lw_id = NULL` và `scheduler.initial(hôm nay)`.

Lược đồ đã lường trước chứ không phải bị lách: chú thích cột `source_lw_id` trong
`migrate.py` bậc 1 ghi thẳng "từ thêm thẳng từ màn hình Tra cứu không đi qua quyển
sách nào", và ràng buộc là `ON DELETE SET NULL`. Không có bảng nào phải sửa.

Hệ quả duy nhất: mặt sau thẻ ôn tập lấy nghĩa từ `dict.sqlite` thay vì từ sách.
`review_card.nghia_cua()` vẫn ưu tiên `detail.source` trước, nên khi giai đoạn B
xong thì đường của QT-04 tự chạy đúng, không phải sửa lại thẻ. Đường thêm bằng nút
cũng không mất đi: một từ đã thêm tay rồi sau đó gặp trong sách vẫn được điền
`source_lw_id` nhờ COALESCE trong `upsert_progress`.

**Ba quyết định giao diện của phiên 05.** Nhãn dòng tóm lược đổi thành "XẾP THEO ĐỘ
KHỚP, HSK RỒI TẦN SUẤT" cho khớp công thức 13.6, nơi `w_khớp` đứng trước HSK. Dòng
bộ thủ ghi cả hai dạng `bộ 言 (讠)` vì từ điển không nói chữ dùng dạng chính hay dạng
giản lược. Bảng màu 6.1 và tên phông 6.2 tạm đặt trong `ui/widgets/tianzige.py` vì
phiên chỉ được tạo sáu tệp; xem món nợ ở mục 4.

---

## 3. Kết quả đo trên giáo trình thật

Sách dùng để đo: Boya sơ cấp I, 270 trang, bản photo từ máy RICOH MP 6503.

**Không có một ký tự văn bản nào.** Mọi trang là một ảnh, khoảng 485 DPI. Outline
nhúng chỉ có 1 mục, vô dụng. Nấc 1 và nấc 2 của thang tách bài đều chết.

**Sách tam ngữ Trung - Anh - Việt.** OCR bắt buộc dùng `chi_sim+vie`; với `chi_sim`
đơn thuần thì "giáo viên dạy" ra "gido vien day".

**Mẫu `第X课` tìm được đúng 0 kết quả** trên cả 270 dải trên, trên 26 trang OCR toàn
phần, và cả khi thử `--psm 11`. Tiêu đề bài in dạng đồ hoạ. Nấc 4 vô dụng với sách
quét.

**Nhưng cấu trúc lấy được bằng đặc trưng phi văn bản.** Tỷ lệ mực dải trên chia độ
dài văn bản OCR đọc được, ngưỡng 8 lần trung vị, cho ra 29 mốc với nhịp 6-8 trang
đều đặn: 36, 48, 54, 61, 67, 73, 81, 88, 96, 103, 110, 117, 124, 131, 138, 144,
151, 158, 166, 173, 179, 185, 192, 199, 207, 214, 220, 227, 234.

**Bảng 生词表 có bảy cột**, không phải bốn hay năm:
`STT | Chữ Hán | Pinyin | Từ loại | Âm Hán-Việt | Nghĩa Anh | Nghĩa Việt`.
Sách in sẵn âm Hán-Việt, nên `lesson_word` có thêm `hanviet_src`.

**Ngưỡng khe không tách được cột.** Khe trong cùng một cột có phân vị 90 là 78 px,
trong khi khe giữa hai cột chỉ 28-40 px. Phải dùng biểu đồ chiếu đứng toàn khối.

**Thời gian OCR đo được, một lõi CPU:**

| | |
|---|---|
| Đo mực dải trên, không OCR, 270 trang | 10 giây |
| OCR dải trên, 40 trang ứng viên | 35 giây |
| OCR toàn trang `chi_sim+vie` | 6,4 giây một trang |
| Luồng ba tầng, cả quyển | 7,2 phút |
| OCR toàn bộ 270 trang | 29 phút |

---

## 4. Việc còn nợ

**`VocabRow` lệch với bảng `lesson_word` theo CẢ HAI chiều.** Đã soát trên mã thật:
bảng có `hanviet_src` mà dataclass không có; dataclass có `review_reason` mà bảng
không có. Mục 3 của tệp này ghi rõ sách in sẵn âm Hán-Việt nên mới thêm cột đó, tức
là bảng được cập nhật còn dataclass thì quên. **Phải chốt trước phiên `vocab`**,
không thì tới đó mới phát hiện và lại mất một phiên bảo trì. Cùng loại lỗi với
`repetition` ở lỗi 9.

**Kho chưa có git.** Bảy phiên, hơn hai chục tệp mã, 154 test, không có đường lùi nếu
một phiên sau làm hỏng thứ đang chạy. `git init` cộng `.gitignore` cho `user.sqlite`,
`user.sqlite-shm`, `user.sqlite-wal`, `__pycache__`, `.pytest_cache`.


**`bounds_boya.json`** — 29 mốc ở trên mới là ứng viên. Phải mở PDF xác nhận từng
trang và ghi số bài. Khoảng 15 phút. Bắt buộc làm **trước** khi viết mã tách bài,
nếu không sẽ vô thức chỉnh thuật toán cho vừa đáp án và cả EV-01 lẫn EV-09 mất
nghĩa. Chặn `splitter` nấc 3 và chương đánh giá.

**`meaning_vi` và `hanviet`** cho từ điển. Không chặn gì, app chạy được với nghĩa
tiếng Anh. Để cuối.

**Packet 06 trở đi chưa viết.** Còn lại Ôn tập, Sách, Bản đồ bộ thủ, rồi `userdb`
đầy đủ, rồi `vocab` và `splitter`.

**~~Tách `ui/theme.py`~~ — TRẢ XONG ở phiên 07.** `PALETTE`, `FONT_DIR`,
`REQUESTED`, `load_fonts`, `han_font`, `mono_font`, `ui_font` đã chuyển sang
`hanzi_app/ui/theme.py`, `tianzige.py` chỉ còn lớp `TianZiGe`. Còn nợ nửa sau:
**QSS vẫn nằm trong `main.py`**, nên màu vẫn sống ở hai chỗ, chỉ khác là cả hai chỗ
giờ cùng đọc từ một `PALETTE`. Gom nốt QSS về `theme.py` khi có phiên đụng `main.py`
lần sau. Không chặn gì.

**Ba phông chưa đóng gói.** Mục 6.2 bắt buộc nhúng Noto Serif SC, IBM Plex Sans và
IBM Plex Mono rồi nạp bằng `QFontDatabase`. Hiện chưa có `resources/fonts/`, ứng
dụng in cảnh báo ra console rồi lùi về Segoe UI và Consolas. **Máy đang dùng tình cờ
có sẵn Noto Serif SC nên chữ Hán trông đúng; máy hội đồng chấm gần như chắc chắn
không có.** Đây là món nợ có hạn chót thật, phải trả trước buổi bảo vệ.

**`requirements.txt`.** Đã thêm ở gốc kho sau phiên 05. Trước đó kho không ghi phụ
thuộc nào, dựng lại trên máy khác là thiếu PySide6.

**Mục 5 của nghiệm thu phiên 05 mới đạt một nửa.** Tiêu chí là trang chi tiết hiện
"pinyin, từ loại, cấp HSK". Pinyin và HSK có thật; từ loại hiện "chưa có dữ liệu" vì
cột `pos` rỗng. Đạt về cấu trúc giao diện, chưa đạt về dữ liệu. **Đừng để dòng "8/8
đạt" trôi vào báo cáo đồ án** — hội đồng sẽ hỏi đúng chỗ đó.

**`pinyin.py` lệch với đặc tả.** Mục 13.5 nói `query_variants` phải sinh cả biến
thể có và không có số thanh nhẹ (`ren4shi` với `ren4shi5`), nhưng câu đó được thêm
vào đặc tả SAU khi phiên 01 đã chạy xong, nên `pinyin.py` chưa cài. Phiên 04 đã
tự xử lý bằng `_numeric_variants` ngay trong `lookup.py`. Cần một phiên bảo trì
ngắn dồn logic đó về đúng chỗ, hoặc chấp nhận và sửa mục 13.5 cho khớp thực tế.
Không gấp, chức năng vẫn chạy đúng.

**`radicals_vi.py` cần rà.** 214 dòng tên Hán-Việt và nghĩa, soạn tay, không có
nguồn mở. Vài bộ hiếm dễ nhầm.

**`spans_1col.json`** đã dựng từ trang PDF 42, 132 span có toạ độ. Dùng làm fixture
cho packet `vocab` khi viết tới.

---

## 5. Những lỗi đã mắc, để khỏi lặp lại

Năm lỗi đầu đều do bộ test hoặc do chạy thử phát hiện. Hai lỗi cuối thì khác: cả hai
chỉ lộ ra khi soát chéo tài liệu với dữ liệu thật, và bộ test sẽ không bao giờ bắt
được chúng. Đó là lý do phần soát trước phiên tồn tại.

1. **`to_plain` xoá nhầm U+0308.** Chuẩn hoá NFD rồi xoá mọi dấu kết hợp là cách
   trực giác nhất và nó sai: `nǚ` ra `nu` thay vì `nv`, hỏng tra cứu mọi âm có ü.
   Chỉ được xoá bốn dấu thanh U+0300, U+0301, U+0304, U+030C.

2. **Ca biên làm tròn không kiểm được gì.** Bộ số `interval=2, ease=1.75` cho tích
   3,7 mà 3,7 làm tròn kiểu nào cũng ra 4. Phải chọn bộ số cho tích rơi đúng vào
   một nửa **và** biểu diễn chính xác được bằng float. Bộ đúng: `ease=2.40`,
   `interval=1`, tích đúng bằng 2,5.

3. **Hai con số bị đảo trong packet 02.** Câu cảnh báo ghi ngược chiều so với bảng
   đáp án. May là quy tắc "test là chân lý" khiến agent theo bảng chứ không theo câu
   cảnh báo.

4. **Cột độ sâu cây ở 14.3 sai tám trên mười dòng.** Viết theo giả định thành phần
   là nút lá, trong khi dữ liệu phân tách cả bộ thủ xuống tận nét. Sinh ra ba quy
   tắc dừng ở mục 13.7.

5. **`word_fts` bị cắt mất khi trích lược đồ từ tài liệu.** Và `freq_rank` bản đầu
   để rỗng. Cả hai chỉ lộ ra khi agent đọc dữ liệu thật.

6. **`is_group` bị sót ở phiên 03 vì bản chép mục 13.3 trong `CLAUDE.md` cũ hơn đặc
   tả gốc.** Phiên 03 được bảo "toàn bộ dataclass ở mục 13.3" và nó đọc bản chép
   trong `CLAUDE.md`, bản đó thiếu trường. Không test nào đỏ, vì test 14.3 chỉ kiểm
   độ sâu cây chứ không kiểm cờ. Lỗi nằm im tới phiên 05 mới lộ, khi giao diện cần
   cờ đó để không vẽ chuỗi IDS vào ô 田字格. Phải chạy phiên bảo trì 03b để vá.
   Bài học: **mọi đoạn đặc tả chép sang `CLAUDE.md` là một bản sao sẽ trôi.** Đã thêm
   một khối cảnh báo ngay trên mục 13.3 trong `CLAUDE.md`; đối chiếu trước mỗi phiên
   đụng tới dataclass.

7. **Màu cảnh báo `#9C7318` trượt ngưỡng tương phản.** Mục 6.1 tự yêu cầu "kiểm bằng
   script tính tương phản, không ước lượng bằng mắt", và không ai chạy script đó cho
   tới sau phiên 05. Chạy rồi thì ra 4.02:1 và 4.30:1, dưới ngưỡng chữ 4.5. Đúng
   cùng loại lỗi với màu chữ mờ `#8E8A82` đã sửa ở bản 0.1, tức là câu cảnh báo có
   sẵn trong tài liệu vẫn không ngăn được việc lặp lại chính lỗi đó. Bảng đo đầy đủ
   giờ nằm trong mục 6.1, kèm hai cặp sát ngưỡng 4.68 và 4.66 cần chạy lại script
   nếu đổi màu.

8. **Bảng đáp án của packet 06 tự mâu thuẫn.** Hành vi số 4 bắt bật khoá ngoại, hành
   vi số 9 lại bảo chèn `source_lw_id = 7` khi bảng `lesson_word` còn rỗng. Hai điều
   đó không thể cùng đúng; ba test đầu đỏ vì chính test sai chứ không phải mã sai.
   Agent phát hiện, sửa test cho hợp lệ, và giữ lại `test_10b` khoá đúng hành vi khoá
   ngoại chặn id ảo. Lần thứ hai quy tắc "dừng lại và nói ra" cứu một packet viết ẩu.

9. **`ReviewOutcome.repetition` bị ánh xạ nhầm sang cột `review_count`.** Bảng
   `progress` ở mục 5.3 không có cột `repetition`, trong khi `ReviewOutcome` ở mục
   13.3 có trường đó, nên phiên 06 buộc phải chọn một cột và chọn sai. Hai con số
   khác nghĩa: `repetition` là bậc lặp đúng **liên tiếp**, `scheduler.py` dòng 52 đặt
   nó về 0 khi bấm Quên; `review_count` theo QT-04 bước 5 là **tổng** số lần ôn, chỉ
   tăng không giảm.

   Hỏng theo cả hai chiều. Đọc lên: `get_progress` trả tổng số lần ôn thay vì bậc lặp,
   nên `scheduler` trượt cả hai nhánh `repetition == 1` và `== 2` rồi rơi xuống
   `interval × ease`, giãn lịch cho đúng những từ người dùng đang quên. Ghi xuống:
   `upsert_progress` đặt `review_count = excluded.review_count` với giá trị buộc từ
   `outcome.repetition`, nên một lần quên xoá sạch tổng số lần ôn. Soát mã còn thấy
   `log_review` **không tăng `review_count`** chút nào, tức cột đó hiện chỉ đang làm
   nhiệm vụ của `repetition`.

   Không test nào bắt được vì cả hai module đều tự nhất quán; sai nằm ở chỗ nối.
   Sửa bằng phiên 06b, migration bậc 2 thêm cột `repetition`.

   Bài học: **lược đồ ở mục 5 và dataclass ở mục 13.3 viết ở hai thời điểm khác nhau
   và chưa bao giờ được đối chiếu chéo.** Lần thứ hai kiểu lỗi này xuất hiện, sau
   `is_group` ở lỗi 6. Trước mỗi phiên đụng tầng dữ liệu, đối chiếu từng trường của
   dataclass với từng cột của bảng tương ứng. Chỗ tiếp theo đã biết là lệch:
   `VocabRow` với `lesson_word`, xem mục 4.

Bài học chung: mọi bảng số trong mục 14 phải được kiểm bằng một cài đặt chạy được
trước khi đưa vào tài liệu. Bảng viết tay sai với tỷ lệ cao hơn nhiều so với cảm
giác lúc viết. Và một câu dặn trong tài liệu không thay được một script chạy thật:
lỗi 7 là câu dặn nằm ngay cạnh chỗ bị vi phạm.

---

## 6. Cách làm việc đang dùng

Mỗi module một phiên, không đưa cả tài liệu 2000 dòng cho agent. `CLAUDE.md` ở gốc
kho giữ bảng tiến độ, vì agent không nhớ gì giữa các phiên. Quy tắc quan trọng nhất
là **bộ test là chân lý, test đỏ nghĩa là mã sai, không được sửa test**, kèm câu
cho phép agent dừng lại phản đối nếu nó tin bảng sai. Câu đó đã cứu ba lần.

`/clear` khi và chỉ khi tệp đặc tả đổi giữa chừng, tức là khi nguồn sự thật trên đĩa
khác với thứ agent đã đọc.

Từ phiên 05 thêm một bước: **soát dữ liệu và soát chéo tài liệu trước khi dán
prompt.** Hai lỗi gần nhất, `is_group` và màu cảnh báo, đều không thể bắt bằng test.
Mở `dict.sqlite` đếm số dòng rỗng của các cột packet sắp dùng, và đối chiếu mọi khối
đặc tả chép trong `CLAUDE.md` với bản gốc.

---

## 7. Nghiệm thu phiên 05

Tám mục kiểm bằng mắt, không có pytest. Kết quả agent báo: 8/8 đạt. Đọc kèm hai lưu ý.

| # | Mục | Kết quả |
|---|---|---|
| 1 | Cửa sổ ≥1100x700, thanh trái 212 px, đủ bốn mục | đạt |
| 2 | `renshi` ra 认识, 人事, 人士 đúng thứ tự | đạt, kèm HSK1·#85, HSK5·#4984, HSK6·#5026 |
| 3 | `认识` ra 认识 đứng đầu | đạt, một kết quả |
| 4 | `renshix` không có kết quả nhưng gợi ý 认识 | đạt |
| 5 | Chi tiết hiện pinyin, từ loại, cấp HSK | **đạt một nửa**, từ loại rỗng vì cột `pos` rỗng |
| 6 | Hai ô 田字格 cho 认 và 识, viền nhấn chính, hai đường đứt | đạt |
| 7 | 识 hai tầng, 认 một tầng | đạt, 认 1 hàng 3 ô; 识 2 hàng 6 ô |
| 8 | Ba mục điều hướng còn lại không làm sập | đạt |

Kiểm thêm ngoài tám mục: 森 vẽ thành 森 = 木 + ( 木 + 木 ), chuỗi `⿰木木` không vào ô
田字格 nào; ca nút nhóm vừa `is_group` vừa `truncated` vẽ dấu ba chấm, không có ngoặc
rỗng. Ảnh chụp ở `scratchpad/01-cua-so.png` tới `04-nhom-bi-cat.png`.

Hai lưu ý về cách chấm. Mục 5 agent tự ghi "đạt"; đúng về cấu trúc giao diện nhưng
thiếu dữ liệu, nên ghi lại ở đây là đạt một nửa. Mục 6 và 7 là mục thị giác mà agent
tự chấm bằng ảnh nó tự chụp; người phải mở ảnh nhìn tận mắt, nếu không thì phiên
nghiệm thu bằng mắt duy nhất của dự án mất ý nghĩa.

---

## 8. Nghiệm thu phiên 07

Bảy mục kiểm bằng mắt. Kết quả agent báo: 7/7 đạt.

| # | Mục | Kết quả |
|---|---|---|
| 1 | pytest xanh, thêm test `progress_counts` | đạt, 163 passed 1 skipped, +2 test |
| 2 | Tra cứu y hệt trước khi tách theme | đạt, ô 田字格 vẫn viền đỏ gạch và hai đường đứt |
| 3 | Nút "Thêm vào ôn tập", bấm thì đổi thành nhãn | đạt |
| 4 | Mục 复 mở ra thẻ 认识, không phải chỗ trống | đạt |
| 5 | "Hiện đáp án" ra `rènshi` và nghĩa, cộng ba nút | đạt, nghĩa "quen biết, làm quen; nhận ra" |
| 6 | Bấm Nhớ ra tổng kết, vào lại thì hết thẻ | đạt |
| 7 | Chân thanh ghi "Đang theo dõi: 1" và "Đã thuộc: 0" | đạt, dòng Bộ thủ vẫn để nguyên |

Kiểm SQL sau một lần bấm Nhớ: `interval_days = 1`, `repetition = 1`,
`review_count = 1`, `status = 'learning'`. Bấm Quên thêm một lần: `repetition` về 0
còn `review_count` lên 2, đúng như 06b hứa. Đây là bằng chứng chạy thật đầu tiên cho
lỗi 9 ở mục 5.

Cách chấm giống phiên 05: agent tự dựng cửa sổ, bấm bằng mã, chụp bảy ảnh trong thư
mục scratchpad của phiên rồi tự đọc. Ảnh KHÔNG nằm trong kho, nên **người phải chạy
lại `python -m hanzi_app.main` và nhìn tận mắt**, nhất là mục 2 và mục 4. Trước khi
chạy nhớ là `user.sqlite` đã được trả về rỗng sau lượt nghiệm thu, nên mục 3 bắt đầu
lại từ đầu được.

Một chỗ cố tình để nguyên: chip "chưa ôn tập lần nào" trên trang chi tiết không đổi
ngay sau khi bấm thêm, phải tra lại mới thấy "trạng thái: new". Câu chữ vẫn đúng —
từ vừa thêm thật sự chưa ôn lần nào — nên không sửa để khỏi phình phạm vi phiên.
