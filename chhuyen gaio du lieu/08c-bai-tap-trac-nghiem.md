# 08c — khung bài tập và hai kiểu trắc nghiệm

Chạy **sau** 08a và 08b. Cần `DictDb.candidate_meanings` và
`DictDb.candidate_hanviet` của 08a.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Phiên giao diện, không có bảng đáp án bằng pytest. Tiêu chí xong ở mục "Nghiệm
thu" cuối tệp handoff/08c-bai-tap-trac-nghiem.md.

Tạo đúng một tệp:
  hanzi_app/ui/widgets/bai_tap.py    lớp nền BaiTap + lớp ChonMotDap

Sửa đúng một tệp:
  hanzi_app/ui/screen_review.py      thêm bộ chọn chế độ, dựng bài tập

KHÔNG sửa gì trong data/ hay service/. KHÔNG sửa review_card.py.

QUY TẮC GIAO DIỆN BẮT BUỘC, đã mắc lỗi này hai lần rồi:
  - Không bao giờ gọi setParent(None) lên widget đang hiện.
  - Không bao giờ gọi setVisible(True) lên widget chưa gắn vào cây widget.
Cả hai đều biến widget thành cửa sổ cấp cao nhất và Windows cấp cho nó một HWND
thật, gây ra một cửa sổ chớp lên rồi tắt. Cần ẩn thì dựng có điều kiện, hoặc chỉ
gọi setVisible(False).

=== 1. Ánh xạ điểm, chốt trước khi viết ===

SM-2 chấm theo ba mức tự đánh giá, còn bài tập thì chấm đúng/sai máy móc. Ánh xạ
BẮT BUỘC như sau, không được tự đổi:

    đúng ngay lần thử đầu      -> grade 2  (Nhớ)
    đúng ở lần thử thứ hai     -> grade 1  (Khó)
    sai cả hai lần             -> grade 0  (Quên)

Mỗi câu cho đúng HAI lần thử. Sai lần một thì báo sai, giữ nguyên câu hỏi, cho
chọn lại. Sai lần hai thì hiện đáp án đúng rồi mới sang câu sau.

Lý do có lần thử thứ hai: trắc nghiệm bốn lựa chọn mà chỉ cho một lần thì đoán
bừa trúng 25%, đủ để làm hỏng lịch ôn. Loại được một đáp án rồi mới đoán thì tỷ
lệ đó không còn phản ánh việc nhớ hay không.

=== 2. Lớp nền BaiTap ===

    class BaiTap(QFrame):
        """Lớp nền cho mọi kiểu bài tập. Không biết gì về SM-2 và cơ sở dữ liệu.

        Lớp con dựng phần thân câu hỏi và gọi _cham(dung: bool) khi người dùng
        trả lời. Lớp nền lo đếm số lần thử, ánh xạ sang grade, hiện đáp án đúng,
        rồi phát answered.
        """
        answered = Signal(int)     # grade 0/1/2, đúng khoá của scheduler.GRADE_TO_Q

        def __init__(self, word: str, parent=None) -> None: ...
        def _cham(self, dung: bool) -> None: ...   # lớp con gọi
        def _hien_dap_an(self, text: str) -> None: ...  # lớp con cài
        def _khoa(self) -> None: ...   # lớp con cài: khoá không cho trả lời nữa

Lớp nền giữ self._lan_thu, bắt đầu bằng 0. _cham xử lý:
    dung và _lan_thu == 0   -> phát answered(2)
    dung và _lan_thu == 1   -> phát answered(1)
    sai và _lan_thu == 0    -> _lan_thu = 1, hiện "Chưa đúng, thử lại", KHÔNG phát
    sai và _lan_thu == 1    -> _hien_dap_an, _khoa, phát answered(0)

Đặt toàn bộ logic đếm ở lớp nền. Lớp con chỉ báo đúng hay sai.

=== 3. ChonMotDap: trắc nghiệm bốn lựa chọn ===

    class ChonMotDap(BaiTap):
        def __init__(self, word: str, cau_hoi: str, dap_an: str,
                     nhieu: list[str], parent=None) -> None: ...

  - cau_hoi hiện to ở trên, dùng han_font nếu là chữ Hán.
  - Bốn nút xếp dọc, mỗi nút một đáp án, đã trộn sẵn.
  - Bấm đúng: nút xanh theo PALETTE["accent2"], khoá cả bốn nút.
  - Bấm sai lần một: nút đó xám đi và bị vô hiệu, ba nút kia còn bấm được.
  - Bấm sai lần hai: nút đúng sáng lên màu accent2, khoá hết.

Trộn đáp án bằng random.shuffle NGAY TRONG WIDGET NÀY. Tầng data cố ý trả về rổ
theo thứ tự xác định để kiểm thử được; việc bốc ngẫu nhiên là của tầng ui.

=== 4. Hai nguồn câu hỏi ===

Cả hai đều dùng ChonMotDap, chỉ khác dữ liệu đưa vào.

KIỂU A — chọn nghĩa:
    cau_hoi = từ đang xét, ví dụ 认识
    dap_an  = nghĩa tiếng Việt nếu có, không thì tiếng Anh
    nhieu   = 3 nghĩa lấy từ dict_db.candidate_meanings(word, hsk_level, 30),
              trộn rồi bốc 3

KIỂU B — chọn âm Hán-Việt:
    Chỉ dùng khi từ có ĐÚNG MỘT chữ, hoặc lấy chữ đầu của từ nhiều chữ.
    cau_hoi = chữ Hán đó
    dap_an  = char.hanviet
    nhieu   = 3 âm lấy từ dict_db.candidate_hanviet(ch, 30), trộn rồi bốc 3

Ba điều bắt buộc khi dựng đáp án nhiễu:
  - Loại bỏ mọi đáp án nhiễu TRÙNG với đáp án đúng. Từ đồng nghĩa có thật trong
    dữ liệu, và một câu hỏi có hai đáp án đúng thì không chấm được.
  - Không đủ 3 đáp án nhiễu thì gọi lại candidate_meanings với hsk_level=None.
    Vẫn không đủ thì BỎ QUA kiểu bài đó cho từ này, rơi về thẻ lật.
  - Kiểu B chỉ dùng được khi chữ có hanviet. Cột đó phủ 958 chữ, không phải tất
    cả 9534, nên phải kiểm trước.

=== 5. Bộ chọn chế độ trong screen_review.py ===

Thêm một hàng nút chọn chế độ ngay dưới dòng tóm lược, hai lựa chọn:

    Thẻ lật        dựng ReviewCard như hiện tại
    Trắc nghiệm    dựng ChonMotDap

Mặc định là Thẻ lật. Chế độ giữ trong self._che_do, đổi chế độ thì vẽ lại thẻ
hiện tại chứ không nhảy sang từ khác và không đụng tới tiến độ.

Ở chế độ Trắc nghiệm, với mỗi từ chọn ngẫu nhiên giữa kiểu A và kiểu B trong số
những kiểu dùng được cho từ đó. Không kiểu nào dùng được thì rơi về ReviewCard,
và ghi một dòng nhỏ màu muted: "Từ này chưa đủ dữ liệu cho bài tập".

Tín hiệu answered nối vào đúng self._cham đang có. KHÔNG viết lại luồng chấm
điểm: _cham đã đọc before, gọi scheduler, ghi tiến độ, ghi nhật ký, đẩy ngăn xếp
hoàn tác. Bài tập chỉ thay phần hỏi, không thay phần chấm.

Nút Hoàn tác của phiên 08b phải chạy được y hệt ở chế độ Trắc nghiệm.

=== 6. Điểm dễ sai ===

- ScreenReview hiện chưa nhận dict_db. Kiểu A và B cần nó để lấy rổ đáp án nhiễu.
  Thêm dict_db vào cuối danh sách tham số của ScreenReview, sửa chỗ dựng nó trong
  main_window.py, và main.py nếu cần. Đây là ngoại lệ được phép của phiên này.
- Đừng gọi candidate_meanings cho cả danh sách due_words lúc mở màn hình. Gọi
  đúng lúc dựng câu hỏi của từ đang xét.
- BaiTap không được import scheduler hay UserDb. Nó chỉ phát grade.
- Phím tắt 1/2/3/4 chọn đáp án tương ứng, cùng cách cài như 08b.

Xong thì chạy `pytest tests/unit -q` xác nhận không test nào đỏ, rồi chạy
`python -m hanzi_app.main` và đi hết bảy mục nghiệm thu, báo từng mục.
```

---

## Nghiệm thu

1. `pytest tests/unit -q` vẫn xanh.
2. Vào Ôn tập, có hàng chọn chế độ. Mặc định Thẻ lật, hoạt động y như trước.
3. Chuyển sang Trắc nghiệm: hiện câu hỏi với đúng bốn lựa chọn, không lựa chọn nào
   trùng nhau.
4. Chọn đúng ngay lần đầu: nút sáng xanh, sang từ kế tiếp. Kiểm SQL, `repetition`
   phải tăng đúng như khi bấm "Nhớ" ở chế độ thẻ lật.
5. Chọn sai lần một: nút đó xám và không bấm được nữa, ba nút kia vẫn bấm được,
   **chưa** sang từ mới. Chọn đúng ở lần hai: chấm như "Khó".
6. Chọn sai cả hai lần: đáp án đúng sáng lên, rồi mới sang từ mới, chấm như "Quên".
7. Bấm Hoàn tác sau một câu trắc nghiệm: quay lại đúng từ đó, số liệu trong
   `progress` trở lại như trước.
8. Bấm qua lại năm sáu câu: không cửa sổ nào chớp lên. Kiểm bằng
   `python tools/chan_doan_cua_so.py`.

Mục 4 và 6 là hai mục quan trọng nhất: chúng chứng minh bài tập đi đúng vào cùng
một đường chấm điểm với thẻ lật, chứ không phải một nhánh riêng.

---

## Còn lại cho 08d

Hai kiểu tương tác khác, mỗi cái một kiểu nhập liệu riêng nên tách phiên:

**Gõ pinyin.** Ô nhập chữ, chấm bằng `pinyin.to_plain` nên nhận cả `rènshi`,
`renshi` và `RenShi`. Người gõ dạng số như `ren4shi5` thì thử thêm
`to_plain(num_to_tone(...))`. Sau khi trả lời luôn hiện dạng có dấu để người học
thấy thanh điệu đúng, kể cả khi họ gõ không dấu.

**Ghép bộ thủ.** Hiện chữ, đưa ra 5–6 mảnh gồm các thành phần thật của nó cộng
vài mảnh nhiễu, người học chọn đúng tập thành phần. Lấy từ `decomposer.tree()` và
bảng `radical`. Đây là kiểu bài không app học tiếng Trung nào khác có, vì nó dựa
vào `char.ids` cộng 214 bộ thủ có nghĩa tiếng Việt mà anh tự dựng.
