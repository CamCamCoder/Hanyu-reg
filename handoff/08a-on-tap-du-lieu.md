# 08a — hoàn tác ôn tập và rổ đáp án nhiễu

Tầng dữ liệu cho hai việc của phiên 08b và 08c. Phiên duy nhất trong nhóm này kiểm
được bằng pytest, nên làm trước.

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Chỉ sửa hai tệp và một tệp test:
  hanzi_app/data/userdb.py      thêm ĐÚNG MỘT phương thức
  hanzi_app/data/dictdb.py      thêm ĐÚNG HAI phương thức
  tests/unit/test_userdb.py     thêm test
  tests/unit/test_dictdb.py     tạo mới nếu chưa có, hoặc thêm vào nếu đã có

Không sửa gì trong service/ hay ui/. Không đổi lược đồ, không thêm bậc migration.
Bảng đáp án bắt buộc ở cuối tệp handoff/08a-on-tap-du-lieu.md.

=== 1. UserDb.undo_review ===

    def undo_review(self, word: str, before: ReviewOutcome) -> None:
        """Hoàn tác lần tự đánh giá gần nhất của một từ.

        Ba việc, trong MỘT giao dịch:
          - khôi phục dòng progress về đúng trạng thái `before`
          - xoá dòng review_log MỚI NHẤT của từ đó, đúng một dòng
          - giảm review_count đi 1, không bao giờ xuống dưới 0
        """

Ba điểm dễ sai:

- Xoá ĐÚNG MỘT dòng review_log, dòng mới nhất của riêng từ đó. Không xoá theo
  word không thôi, làm vậy là xoá sạch lịch sử. SQLite không cho LIMIT trong
  DELETE ở bản mặc định, nên dùng
      DELETE FROM review_log WHERE id = (
          SELECT id FROM review_log WHERE word = ?
          ORDER BY reviewed_at DESC, id DESC LIMIT 1)
  Sắp theo reviewed_at rồi id, vì hai lần ôn trong cùng một giây có cùng dấu
  thời gian và khi đó chỉ id mới phân biệt được.

- review_count giảm 1 nhưng chặn dưới ở 0: MAX(review_count - 1, 0). Từ chưa
  từng ôn mà gọi undo thì vẫn phải khôi phục progress, không được ném lỗi và
  không được để review_count thành -1.

- ReviewOutcome KHÔNG chứa review_count, nên khôi phục progress bằng
  upsert_progress là đủ cho sáu trường kia; review_count phải sửa riêng bằng một
  câu UPDATE. Gọi upsert_progress bên trong cùng giao dịch được, vì transaction()
  đã cài bằng SAVEPOINT nên lồng nhau an toàn.

=== 2. DictDb.candidate_meanings ===

    def candidate_meanings(
        self, exclude_word: str, hsk_level: int | None, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài chọn nghĩa.

        Trả về [(word_simp, meaning_vi), ...]. Chỉ lấy dòng có meaning_vi khác
        rỗng, bỏ chính exclude_word. hsk_level khác None thì lọc đúng cấp đó;
        None thì lấy toàn bảng.
        """

=== 3. DictDb.candidate_hanviet ===

    def candidate_hanviet(
        self, exclude_char: str, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài chọn âm Hán-Việt.

        Trả về [(char, hanviet), ...]. Chỉ lấy dòng có hanviet khác rỗng, bỏ
        chính exclude_char.
        """

KHÔNG bốc ngẫu nhiên trong hai phương thức này. Trả về rổ theo thứ tự XÁC ĐỊNH,
sắp theo freq_rank rồi tới khoá chính, để test cho ra kết quả lặp lại được. Việc
bốc ngẫu nhiên là của tầng ui ở phiên 08c.

Lý do thiết kế như vậy, ghi luôn vào docstring: đáp án nhiễu lấy cùng cấp HSK mới
thành bài tập thật; bốc ngẫu nhiên toàn bộ 5001 từ thì người học loại trừ được
ngay bằng cảm giác độ khó chứ không cần biết nghĩa.

Test chạy trên dict.sqlite thật ở gốc kho, mở chế độ chỉ đọc. Dữ liệu tiếng Việt
hiện phủ 601 từ HSK 1-3 và 958 chữ, đủ để kiểm.

Viết test trước, chạy pytest, báo kết quả thật kèm tổng số test của cả kho.
```

---

## Bảng đáp án bắt buộc

| # | Hành vi | Kỳ vọng |
|---|---|---|
| 1 | `undo_review` sau một lần `apply_review` | `progress` khớp từng trường với `before` |
| 2 | Cùng ca trên | Số dòng `review_log` của từ đó giảm đúng 1 |
| 3 | Từ đã ôn 3 lần, gọi `undo_review` một lần | Còn đúng 2 dòng `review_log`, không phải 0 |
| 4 | Cùng ca trên | Dòng bị xoá là dòng **mới nhất**, hai dòng cũ còn nguyên |
| 5 | Hai từ đều có nhật ký, undo từ A | Nhật ký của từ B không đổi |
| 6 | `review_count` đang là 3, gọi `undo_review` | Thành 2 |
| 7 | `review_count` đang là 0, gọi `undo_review` | Vẫn 0, không âm, không ném lỗi |
| 8 | Từ chưa từng có dòng `review_log` | `progress` vẫn được khôi phục, không ném lỗi |
| 9 | `source_lw_id` đang khác `None` trước khi undo | Giữ nguyên sau khi undo |
| 10 | `candidate_meanings('认识', 1, 5)` | Đúng 5 phần tử, không phần tử nào là 认识 |
| 11 | Cùng ca trên | Mọi phần tử có `meaning_vi` khác rỗng |
| 12 | Cùng ca trên, gọi hai lần | Hai lần trả kết quả **giống hệt nhau**, không ngẫu nhiên |
| 13 | `candidate_meanings` với `hsk_level=1` | Mọi từ trả về đều thuộc HSK 1 |
| 14 | `candidate_meanings` với `hsk_level=None` | Không lọc theo cấp, vẫn bỏ `exclude_word` |
| 15 | `candidate_hanviet('认', 5)` | Đúng 5 phần tử, không có 认, mọi `hanviet` khác rỗng |

Ca 12 là ca quan trọng nhất và dễ bị bỏ qua: nếu ai đó nhét `ORDER BY RANDOM()`
vào truy vấn thì test này đỏ, và đó đúng là điều cần chặn.

---

## Vì sao hoàn tác chỉ trong phiên đang chạy

`review_log` hiện lưu `interval_before` và `ease_after`, nhưng không lưu
`ease_before`, `repetition_before`, `lapse_count_before`, `status_before` hay
`due_date_before`. Nên **không dựng lại được trạng thái cũ từ nhật ký**, và hoàn
tác sau khi tắt app sẽ cần migration bậc 3 thêm bốn cột.

Chưa làm vì chưa đáng: người dùng nhận ra bấm nhầm ngay lập tức. Màn hình Ôn tập ở
phiên 08b giữ một ngăn xếp `(word, before)` trong bộ nhớ và gọi `undo_review` với
`before` đó. Nếu sau này muốn hoàn tác xuyên phiên thì mở lại chỗ này.

## Sau khi xong

Cập nhật bảng tiến độ trong `CLAUDE.md`, rồi sang packet 08b.
