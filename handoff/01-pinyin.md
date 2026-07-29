# 01 — pinyin

## Prompt để dán

```
Đọc kỹ QUY TẮC CHUNG trong CLAUDE.md ở gốc kho trước.

Cần tạo đúng hai tệp:
  hanzi_app/service/pinyin.py
  tests/unit/test_pinyin.py

Đặc tả module ở mục 13.5, bảng đáp án ở mục 14.2, cả hai kèm bên dưới.
Viết test TRƯỚC, đúng từng dòng của ba bảng trong mục 14.2, rồi mới viết mã.

Ba điểm rất dễ sai, chú ý:
- to_plain phải chỉ xoá bốn dấu thanh U+0300, U+0301, U+0304, U+030C và PHẢI GIỮ
  dấu tách âm U+0308. Xoá luôn U+0308 thì 'nǚ' ra 'nu' thay vì 'nv'. Cách an toàn:
  NFD, lọc bỏ đúng bốn mã trên, NFC lại, rồi mới đổi 'ü' thành 'v'.
- Quy tắc đặt dấu thanh: a và e luôn nhận dấu; trong 'ou' thì o nhận; còn lại
  nguyên âm cuối nhận. Thanh 5 và thanh 0 không đánh dấu.
- CC-CEDICT viết ü thành 'u:', ví dụ 'nu:3' phải ra 'nǚ'.

Module này thuần tuý, không chạm cơ sở dữ liệu, không chạm mạng, không chạm Qt.
```

---

### 13.5. Tiện ích pinyin

Module nhỏ nhất nhưng bị gọi nhiều nhất, và là nơi lỗi hay nấp.

```python
def to_plain(s: str) -> str: ...
    # 'rènshi' -> 'renshi';  bỏ dấu thanh, bỏ khoảng trắng và dấu nháy,
    # ü và u: và v đều quy về 'v'

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
    # 'lu' -> ['lu', 'lv'] vì người Việt quen gõ u thay cho ü.
```

`split_syllables` nhận `expect` là một quyết định thiết kế đáng nêu trong báo cáo.
Tách pinyin liền là bài toán nhập nhằng thật sự: chuỗi `xian` có thể là một âm tiết
`xian` hoặc hai âm tiết `xi` + `an`. Nhưng ở mọi chỗ ứng dụng cần tách, số chữ Hán
đã biết trước, và ràng buộc đó làm bài toán trở thành xác định trong hầu hết trường
hợp. Nhiều cách cài đặt bỏ qua thông tin này rồi đi giải bài toán khó hơn mức cần.

---

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
| `xi'an` | `xian` |

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