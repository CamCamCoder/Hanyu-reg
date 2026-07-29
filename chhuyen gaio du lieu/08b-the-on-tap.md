# 08b — thẻ ôn tập: cây chiết tự, âm Hán-Việt, hoàn tác, phím tắt

Chạy **sau** 08a, vì nút Hoàn tác gọi `UserDb.undo_review`.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Phiên giao diện, không có bảng đáp án bằng pytest. Tiêu chí xong ở mục "Nghiệm
thu" cuối tệp handoff/08b-the-on-tap.md, kiểm bằng mắt.

Không tạo tệp mới. Sửa đúng bốn tệp:
  hanzi_app/ui/widgets/review_card.py   cây chiết tự, âm Hán-Việt, phím tắt
  hanzi_app/ui/screen_review.py         sửa _clear, nút Hoàn tác, bơm decomposer
  hanzi_app/ui/main_window.py           truyền decomposer xuống ScreenReview
  hanzi_app/main.py                     truyền decomposer vào MainWindow nếu chưa

KHÔNG sửa gì trong data/ hay service/. Tầng ui chỉ được GỌI xuống.

=== VIỆC 0. Sửa _clear trong screen_review.py, làm trước tiên ===

Hàm _clear hiện dùng widget.setParent(None). Trong Qt, cắt cha biến widget thành
CỬA SỔ CẤP CAO NHẤT và Windows cấp cho nó một HWND thật, nên mỗi lần sang thẻ mới
sẽ có một cửa sổ chớp lên rồi tắt. Đây là lỗi đã sửa ở screen_lookup.py, còn sót
lại đúng tệp này.

Thay hai dòng:
        if widget is not None:
            widget.setParent(None)
bằng:
        if widget is not None:
            widget.hide()
            widget.deleteLater()

Quy tắc chung cho mọi mã ui từ giờ: KHÔNG BAO GIỜ gọi setParent(None) lên widget
đang hiện, và KHÔNG BAO GIỜ gọi setVisible(True) lên widget chưa gắn vào cây
widget. Cả hai đều tạo cửa sổ thật trên Windows.

=== VIỆC 1. Cây chiết tự ở mặt sau thẻ ===

Đây là việc quan trọng nhất của phiên. Mặt sau thẻ hiện chỉ có pinyin và nghĩa,
tức đúng bằng một app flashcard bất kỳ. Nhưng kho đã có sẵn cây chiết tự, âm
Hán-Việt cho 958 chữ, và 214 bộ thủ kèm nghĩa tiếng Việt. Widget DecompTree đã
viết xong từ phiên 05 và đang không được dùng ở màn hình quan trọng nhất.

ReviewCard.__init__ nhận thêm tham số decomposer:

    def __init__(self, word: str, detail, decomposer, parent=None) -> None:

Trong _dung_mat_sau, sau khối nghĩa, thêm một khối chiết tự:

  - Với MỖI chữ trong detail.chars, gọi decomposer.tree(ch) rồi dựng DecompTree.
    Chữ ký đã có: DecompTree(node, parent=None).
  - Đặt dưới nhãn mục _section("Chiết tự").
  - Từ nhiều chữ thì xếp các cây theo chiều dọc, có đường kẻ mảnh ngăn giữa,
    giống cách screen_lookup.py đang làm ở khối CHIẾT TỰ.

Gọi decomposer.tree() ngay trong _dung_mat_sau là chấp nhận được: mặt sau chỉ
dựng một lần cho mỗi thẻ, và ScreenReview đã dựng thẻ theo từng từ chứ không
dựng trước cả danh sách.

=== VIỆC 2. Âm Hán-Việt ===

Với người Việt đây là công cụ nhớ chữ mạnh nhất và cột char.hanviet giờ đã có dữ
liệu thật cho 958 chữ. Thêm ngay dưới dòng pinyin ở mặt sau:

    认识  ·  rènshi  ·  nhận thức

Ghép hanviet của từng chữ trong detail.chars, nối bằng dấu cách. Chữ nào thiếu
hanviet thì bỏ qua chữ đó; nếu KHÔNG chữ nào có hanviet thì bỏ luôn cả dòng,
đừng hiện dòng rỗng và đừng hiện "chưa có dữ liệu" ở đây.

Dùng mono_font để thẳng hàng với pinyin, màu PALETTE["ink2"].

=== VIỆC 3. Nút Hoàn tác ===

Bấm nhầm một nút đánh giá hiện không sửa được, mà một cú bấm nhầm "Nhớ" vào từ
đang quên sẽ đẩy lịch lên 6 ngày rồi từ đó biến mất khỏi danh sách hôm nay.

ScreenReview giữ một ngăn xếp trong bộ nhớ:

    self._lich_su: list[tuple[str, ReviewOutcome]] = []

Trong _cham, sau khi đọc before và TRƯỚC khi ghi, đẩy (word, before) vào ngăn xếp.

Thêm nút "Hoàn tác" ở dòng tóm lược phía trên thân màn hình. Nút chỉ hiện khi
ngăn xếp khác rỗng — dùng cách dựng có điều kiện, ĐỪNG dựng rồi setVisible(True),
xem quy tắc ở việc 0.

Bấm Hoàn tác:
    word, before = self._lich_su.pop()
    self._user.undo_review(word, before)
    self._vi_tri = max(self._vi_tri - 1, 0)
    self._da_on = max(self._da_on - 1, 0)
    self.progress_changed.emit()
    self._ve()

Phải hoàn tác được cả khi đang ở thẻ tổng kết, vì đó chính là lúc người ta nhận
ra vừa bấm nhầm thẻ cuối.

Ngăn xếp CỐ Ý chỉ sống trong phiên đang chạy. review_log không lưu ease_before,
repetition_before, status_before hay due_date_before nên không dựng lại được
trạng thái cũ từ nhật ký; hoàn tác xuyên phiên sẽ cần migration bậc 3. Không làm
ở phiên này. Ghi chú lý do đó vào docstring.

reload() phải xoá ngăn xếp, vì nó bắt đầu một phiên ôn mới.

=== VIỆC 4. Phím tắt ===

App này dùng mỗi ngày, chuột hoá ra chậm. Trên ReviewCard:

    Space hoặc Enter   lật thẻ, tương đương nút "Hiện đáp án"
    1 / 2 / 3          Quên / Khó / Nhớ, chỉ ăn SAU khi đã lật

Cài bằng QShortcut gắn vào chính ReviewCard với ngữ cảnh
Qt.ShortcutContext.WindowShortcut. Trước khi lật thì ba phím số không làm gì cả,
đừng cho chấm điểm khi chưa thấy đáp án.

Thêm một dòng gợi ý nhỏ dưới hàng nút, cỡ chữ mono 11, màu muted:
    "Phím tắt: cách để lật, 1 quên · 2 khó · 3 nhớ"

=== ĐIỂM DỄ SAI ===

- ScreenReview.__init__ hiện là (lookup, user_db, scheduler). Thêm decomposer vào
  cuối để không phá thứ tự cũ. Sửa luôn chỗ dựng nó trong main_window.py, và nếu
  MainWindow chưa nhận decomposer thì sửa cả main.py.
- ReviewCard không được import decomposer hay tự dựng nó. Nhận qua tham số.
- Đừng gọi decomposer.tree() cho cả danh sách due_words lúc mở màn hình. Chỉ gọi
  lúc dựng mặt sau của đúng thẻ đang xét.
- Giữ nguyên tín hiệu graded và cách _cham đang chạy. Phiên này thêm chứ không
  đổi luồng chấm điểm.

Xong thì chạy `pytest tests/unit -q` xác nhận không test nào đỏ, rồi chạy
`python -m hanzi_app.main` và tự đi hết tám mục nghiệm thu, báo từng mục.
```

---

## Nghiệm thu

1. `pytest tests/unit -q` vẫn xanh, không test nào đỏ.
2. Vào Ôn tập, bấm qua ba bốn thẻ liên tiếp: **không còn cửa sổ nào chớp lên**.
   Kiểm chắc bằng `python tools/chan_doan_cua_so.py`, chỉ được có dòng `[1] MainWindow`.
3. Lật một thẻ có từ 认识: mặt sau hiện `rènshi`, dòng Hán-Việt `nhận thức`, nghĩa
   `quen biết, làm quen; nhận ra`.
4. Cùng thẻ đó: khối CHIẾT TỰ hiện hai cây, 认 một tầng và 识 hai tầng, mỗi ô có
   viền đỏ gạch và hai đường đứt.
5. Bấm phím cách để lật, rồi bấm phím 3: thẻ chuyển sang từ kế tiếp.
6. Nút Hoàn tác hiện ra sau lần chấm đầu tiên. Bấm vào: quay lại đúng thẻ vừa rồi,
   và số ở chân thanh điều hướng trở lại như trước.
7. Chấm hết thẻ để ra màn tổng kết, rồi bấm Hoàn tác: quay lại được thẻ cuối.
8. Kiểm bằng SQL sau khi chấm một lần rồi hoàn tác:
   ```sql
   SELECT word, repetition, review_count, interval_days FROM progress;
   SELECT COUNT(*) FROM review_log;
   ```
   Cả ba số trong `progress` phải bằng đúng giá trị trước khi chấm, và số dòng
   `review_log` phải trở lại như cũ.

Mục 8 là mục quan trọng nhất: nó chứng minh `undo_review` của phiên 08a chạy đúng
ngoài đời chứ không chỉ trong test.

## Sau khi xong

Cập nhật `CLAUDE.md`. Ghi vào `BAN-GIAO.md` mục 5 lỗi thứ mười: `setVisible(True)`
trên widget chưa có cha, và `setParent(None)` trên widget đang hiện, đều tạo cửa sổ
thật trên Windows. Đây là lỗi đầu tiên mà cả pytest lẫn nghiệm thu bằng mắt đều
không bắt được — chỉ lộ ra khi dùng thật. Thêm hai điều đó vào phần "điểm dễ sai"
của mọi packet `ui/` từ giờ.

Rồi sang packet 08c, bốn kiểu bài tập.
