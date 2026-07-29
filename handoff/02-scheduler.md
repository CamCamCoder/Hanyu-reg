# 02 — scheduler

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Cần tạo đúng hai tệp:
  hanzi_app/service/scheduler.py
  tests/unit/test_scheduler.py

Đặc tả ở mục 13.12, quy trình nghiệp vụ ở QT-04, bảng đáp án ở mục 14.5.
Viết test TRƯỚC, gồm cả chuỗi 8 lần đánh giá lẫn bốn ca biên, rồi mới viết mã.

Bảng 8 dòng ở mục 14.5 đã được kiểm chứng bằng một cài đặt độc lập. Nếu mã của
bạn ra số khác, mã sai.

Ba điểm rất dễ sai:
- Cập nhật ease TRƯỚC rồi mới dùng ease MỚI để tính interval. Lần 3 phải ra 17
  (6 x 2.80 = 16.8), dùng ease cũ sẽ ra 16 (6 x 2.70 = 16.2) và cả bảng lệch theo.
- Làm tròn nửa LÊN. Hàm round dựng sẵn của Python làm tròn nửa về số chẵn nên
  round(2.5) trả về 2. Phải tự cài, ví dụ bằng decimal.ROUND_HALF_UP.
- Ngày hôm nay được truyền vào qua tham số today, tuyệt đối không gọi date.today()
  bên trong module.

Module này thuần tuý: không chạm cơ sở dữ liệu, không chạm mạng, không chạm Qt,
không chạm đồng hồ hệ thống. So sánh số thực bằng pytest.approx sai số 1e-9.
```

---

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

---

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

---

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
| Làm tròn nửa lên | `interval = 2`, `ease = 1.75`, bấm Nhớ ở bậc 3 | `interval = 4`, không phải 3 |
| Ngày đến hạn | `today = 2026-07-27`, `interval = 6` | `due_date = 2026-08-02` |
| Khoảng tối thiểu | `interval = 0`, bấm Khó | `interval = 1`, không phải 0 |

Ca làm tròn có mặt ở đây vì hàm `round` của Python làm tròn nửa về số chẵn, nên
`round(3.5)` trả về 4 nhưng `round(2.5)` trả về 2. Cài đặt phải tự làm tròn, không
dùng thẳng hàm dựng sẵn.

So sánh số thực bằng `pytest.approx` với sai số 1e-9, đừng so bằng dấu bằng.