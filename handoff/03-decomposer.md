# 03 — decomposer

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Cần tạo đúng bốn tệp:
  hanzi_app/data/models.py        (toàn bộ dataclass ở mục 13.3)
  hanzi_app/data/dictdb.py        (chỉ các phương thức decomposer cần)
  hanzi_app/service/decomposer.py
  tests/unit/test_decomposer.py

Phiên 02 đã khai báo tạm ReviewOutcome ngay trong service/scheduler.py vì
data/models.py chưa tồn tại. Phiên này gom nó về models.py rồi sửa scheduler.py
thành một lệnh import. Đây là ngoại lệ duy nhất được phép chạm vào tệp của phiên
trước; sửa xong phải chạy lại toàn bộ tests/unit và báo cáo tổng số test xanh.

Đặc tả ở mục 13.7, bảng đáp án ở mục 14.3. Tệp dict.sqlite đã có sẵn, lược đồ
đúng như mục 5.2. Mở ở chế độ chỉ đọc.

Ba điểm rất dễ sai:
- Quy tắc dừng đệ quy. Nguồn dữ liệu phân tách cả bộ thủ xuống tận nét, nên đệ quy
  không điều kiện sẽ làm mọi chữ tan thành nét. Bộ Khang Hy là nút lá, kể cả khi
  bảng char có chuỗi IDS cho nó. Đồng thời phải giữ cấu trúc lồng của chuỗi IDS:
  toán tử ⿲ và ⿳ nhận ba toán hạng, mười toán tử còn lại nhận hai. Đọc kỹ ba quy
  tắc trong phần chú thích của tree() ở mục 13.7 bên dưới.
- Nút lá KHÁC nút bị cắt. Chữ không phân tách được, ví dụ 一, trả về nút lá với
  children rỗng và truncated bằng False. Chỉ đặt truncated bằng True khi dừng vì
  chạm giới hạn độ sâu hoặc vì phát hiện chu trình.
- Bắt buộc mang theo tập chữ đã thăm trên đường đi. Dữ liệu IDS có trường hợp chữ
  trỏ vòng về chính nó; thiếu tập này thì tràn ngăn xếp.

Với ca kiểm tra chu trình, hãy tự chèn hai bản ghi chữ giả vào một bản sao tạm của
dict.sqlite trong fixture, đừng sửa tệp gốc.
```

---

### 13.7. decomposer

```python
class Decomposer:
    MAX_DEPTH = 6

    def __init__(self, dict_db: DictDb) -> None: ...

    def tree(self, ch: str) -> DecompNode: ...
        # Dựng cây chiết tự đệ quy từ chuỗi IDS.
        # Bắt buộc mang theo tập chữ đã thăm trên đường đi; gặp lại một chữ
        # đã có trên đường đi thì dừng nhánh đó và đặt truncated = True.
        # Chạm MAX_DEPTH cũng đặt truncated = True.
        # Chữ không phân tách được trả về nút lá, children rỗng, truncated = False.

    def radical_of(self, ch: str) -> Radical | None: ...
    def same_radical_learned(self, ch: str, limit: int = 12) -> list[str]: ...   # FR-15
    def radical_map(self) -> list[tuple[Radical, int]]: ...  # FR-34, đếm theo số chữ khác nhau
```

`truncated` phải là một trường trên nút chứ không phải một ngoại lệ. Giao diện cần
vẽ được phần cây đã dựng xong kèm dấu hiệu là còn nữa, chứ không phải bỏ trắng cả
khối vì một nhánh sâu.

---

### 14.3. Chiết tự

| Chữ | IDS | Thành phần | Bộ | Tổng nét | Độ sâu cây |
|---|---|---|---|---|---|
| 认 | `⿰讠人` | 讠, 人 | 149 言 | 4 | 1 |
| 识 | `⿰讠只` | 讠, 只 | 149 言 | 7 | 1 |
| 谢 | `⿰讠射` | 讠, 射 | 149 言 | 12 | 1 |
| 好 | `⿰女子` | 女, 子 | 38 女 | 6 | 1 |
| 名 | `⿱夕口` | 夕, 口 | 30 口 | 6 | 1 |
| 字 | `⿱宀子` | 宀, 子 | 39 子 | 6 | 1 |
| 朋 | `⿰月月` | 月, 月 | 74 月 | 8 | 1 |
| 明 | `⿰日月` | 日, 月 | 72 日 | 8 | 1 |
| 森 | `⿱木⿰木木` | 木, 木, 木 | 75 木 | 12 | 2 |
| 一 | `一` | không có | 1 一 | 1 | 0 |

Ba ca biên bắt buộc:
- Chữ không phân tách được, ví dụ 一: trả về nút lá, `children` rỗng, `truncated`
  bằng False. Nút lá khác với nút bị cắt, và trộn hai thứ này là lỗi hay gặp.
- Chu trình: thêm vào `mini_dict.sqlite` hai chữ giả A và B với IDS trỏ lẫn nhau.
  Hàm phải kết thúc, không tràn ngăn xếp, và đặt `truncated` bằng True.
- Chuỗi sâu quá 6 tầng: dừng ở tầng 6, phần đã dựng vẫn trả về đầy đủ.