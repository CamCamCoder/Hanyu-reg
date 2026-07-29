# 04 — lookup

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Cần tạo đúng hai tệp:
  hanzi_app/service/lookup.py
  tests/unit/test_lookup.py

Cộng thêm: bổ sung WordSource và WordDetail vào hanzi_app/data/models.py đã có.

Đặc tả ở mục 13.6, bảng đáp án ở mục 14.4. Dùng lại dictdb.py đã viết ở phiên
trước, chỉ bổ sung phương thức còn thiếu, không viết lại tệp đó từ đầu.

WordDetail và WordSource đã được định nghĩa ở mục 13.3, kèm bên dưới. Chúng thuộc
data/models.py; tệp đó đã tồn tại từ phiên 03 nên chỉ cần thêm hai dataclass vào,
không tạo lại. Việc sửa models.py là ngoại lệ được phép của phiên này.

WordDetail cố ý KHÔNG chứa cây chiết tự: lookup và decomposer cùng ở tầng service,
mà mục 13.1 cấm phụ thuộc đi ngang giữa hai module cùng tầng. Tầng giao diện sẽ gọi
cả hai rồi ghép.

Ba điểm rất dễ sai:
- Kết quả khớp gần LUÔN xếp sau toàn bộ nhóm khớp đúng, kể cả khi điểm số cao hơn.
  Cài bằng khoá sắp xếp kép, không cộng dồn vào cùng một điểm.
- search và suggest là hai hàm khác nhau. Không có kết quả khớp đúng thì search
  trả về danh sách rỗng, không được tự động rơi sang khớp gần.

CHÚ Ý: dict.sqlite đã được dựng lại sau phiên 03, bảng radical giờ có đủ name_hv,
meaning_vi và glyph_alt cho cả 214 bộ. Nếu bạn đã đọc dữ liệu bảng đó ở phiên
trước thì đọc lại.

CHÚ Ý: cột meaning_vi của bảng word và bảng char trong dict.sqlite vẫn còn rỗng, nên FR-04 tìm theo nghĩa
tiếng Việt chưa kiểm thử được. Cứ cài đặt đường đi qua bảng word_fts cho đủ, và
đánh dấu test tương ứng bằng pytest.mark.skip kèm lý do rõ ràng.
```

---

### 13.6. lookup

```python
class LookupService:
    def __init__(self, dict_db: DictDb, user_db: UserDb) -> None: ...

    def search(self, query: str, limit: int = 30) -> list[SearchHit]: ...
    def detail(self, word: str) -> WordDetail: ...
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
w_hsk:       (7 − hsk_level) / 6, bằng 0 nếu ngoài danh sách HSK
w_tần_suất:  1 / log10(freq_rank + 10), bằng 0 nếu không có thứ hạng
```

Kết quả khớp gần luôn xếp sau toàn bộ nhóm khớp đúng, kể cả khi điểm cao hơn. Cài
đặt bằng cách sắp xếp theo khoá kép `(w_khớp >= 0.5, score)`.

---

### 14.4. Xếp hạng tìm kiếm

Với truy vấn `renshi` trên `mini_dict.sqlite`, thứ tự trả về phải đúng như mockup ở
mục 7.2:

| Hạng | Từ | Vì sao ở vị trí này |
|---|---|---|
| 1 | 认识 | cùng khớp pinyin phẳng như hai từ dưới, nhưng HSK 1 và tần suất cao nhất |
| 2 | 人事 | HSK 5, tần suất 2108 |
| 3 | 人士 | ngoài HSK, tần suất 2687 |

Hai ca biên:
- Truy vấn `认识` phải cho 认识 hạng 1 với `matched_by` bằng `hanzi`.
- Truy vấn `renshix` không khớp gì; `search` trả rỗng còn `suggest` phải trả 认识.
  Kết quả khớp gần không bao giờ được lẫn vào `search`.