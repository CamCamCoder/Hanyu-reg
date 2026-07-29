# AGENTS.md — đọc trước khi làm bất cứ việc gì

## TRẠNG THÁI DỰ ÁN

Dự án được chia thành các phiên độc lập, làm **đúng theo thứ tự**. Bảng này là
nguồn sự thật duy nhất về việc đang ở đâu. Sau khi hoàn thành một phiên, cập nhật
cột Trạng thái rồi mới sang phiên sau.

| Phiên | Module | Tệp sinh ra | Trạng thái |
|---|---|---|---|
| 01 | pinyin | `service/pinyin.py`, `tests/unit/test_pinyin.py` | xong, 27 test xanh |
| 02 | scheduler | `service/scheduler.py`, `tests/unit/test_scheduler.py` | xong, 23 test xanh |
| 03 | decomposer | `data/models.py`, `data/dictdb.py`, `service/decomposer.py`, `tests/unit/test_decomposer.py` | xong, 30 test xanh, tổng 80 |
| 04 | lookup | `service/lookup.py`, `tests/unit/test_lookup.py` | xong, 39 xanh 1 skip, tổng 120 |
| 05 | lát cắt giao diện Tra cứu | `main.py`, `ui/main_window.py`, `ui/screen_lookup.py`, `ui/widgets/tianzige.py`, `ui/widgets/decomp_tree.py`, `data/userdb.py` (bản tối thiểu) | xong, nghiệm thu bằng mắt 8 mục; mục 5 đạt về cấu trúc nhưng cột `pos` rỗng nên chưa có dữ liệu từ loại |
| 06 | userdb | `data/migrate.py`, `data/userdb.py`, `tests/unit/test_userdb.py` | xong, 35 test xanh, tổng 154 xanh 1 skip |
| 06b | bảo trì, tách `repetition` khỏi `review_count` | `data/migrate.py`, `data/userdb.py` | xong, +7 test, tổng 161 xanh 1 skip |
| 07 | màn hình Ôn tập, kèm tách `ui/theme.py` | `ui/theme.py`, `ui/screen_review.py`, `ui/widgets/review_card.py` | xong, +2 test `progress_counts`, tổng 163 xanh 1 skip; nghiệm thu bằng mắt 7/7 mục |
| 08a | hoàn tác ôn tập + rổ đáp án nhiễu | `data/userdb.py`, `data/dictdb.py`, `tests/unit/test_dictdb.py` | xong, +20 test (9 userdb, 11 dictdb), tổng 183 xanh 1 skip |
| 08b | cải thiện thẻ ôn tập | cây chiết tự mặt sau, âm Hán-Việt, nút Hoàn tác, phím tắt | xong |
| 08c | bài tập trắc nghiệm | `ui/widgets/bai_tap.py`, chọn nghĩa và chọn âm Hán-Việt | xong |
| 08d | bài tập gõ pinyin + ghép bộ thủ | `ui/widgets/bai_tap.py` (thêm `GoPinyin`, `GhepBoThu`), `ui/screen_review.py` | xong, 183 test xanh 1 skip |
| B1 | pdfsource & ocr | `adapter/pdfsource.py`, `adapter/ocr.py`, `tests/unit/test_pdfsource.py` | xong, +5 test xanh |
| B2 | splitter | `service/splitter.py`, `tests/unit/test_splitter.py` | xong, +3 test xanh |
| B3 | vocab | `service/vocab.py`, `tests/unit/test_vocab.py` | xong, +1 test xanh |
| B4 | giao diện Sách & nhập PDF | `ui/screen_books.py`, `ui/dialog_import.py`, `service/importer.py` | xong, nghiệm thu 4/4 màn hình |
| B5 | Smart Import AI (LLM API + Hybrid) | `adapter/aiclient.py`, `tests/unit/test_aiclient.py` | xong, +2 test xanh |
| B6 | Universal 2-Layer Hybrid Engine | `service/splitter.py`, `service/vocab.py`, `service/importer.py`, `ui/screen_books.py`, `tests/unit/test_universal_engine.py` | xong, +3 test xanh, tổng 197 test xanh 1 skip |
| B7a | prototype nhập Boya local-first | fallback Windows OCR, mốc 30 bài đã đối chiếu, locator bảng, parser 7 cột, lưu âm Hán-Việt, validator sơ bộ | xong prototype; +3 test, tổng 202 xanh 1 skip; thử thật Bài 5 và 29 còn nhiễu ở pinyin/nghĩa nên chưa đạt nghiệm thu dữ liệu |
| B7b | OCR song ngữ + Vision crop-only + golden Boya | hợp nhất OCR Trung–Anh, biên cột theo bảng thật, validator `char_reading`, bơm `DictDb` vào importer, golden Bài 5/29 | xong; +2 unit test, tổng 204 xanh 1 skip; 2 golden xanh; Bài 5 recall 70%/precision 93,3%, Bài 29 recall 86,4%/precision 100% |
| B7c | duyệt kết quả nhập sách | trạng thái `review`, dialog sửa ranh giới và bảng 7 cột, tô dòng lỗi, preview crop nguồn, chặn Ôn tập trước xác nhận | xong; +1 test Qt offscreen, tổng 205 xanh 1 skip; QA render đạt |
| B7d | xác nhận ranh giới trước OCR + Vision chọn lọc | tách worker phân bài/OCR, dialog xác nhận khoảng trang, trạng thái `review_bounds`/`extracting`, chạy lại Vision crop-only cho một bài và chỉ lưu sau duyệt | xong; +1 test Qt offscreen, tổng 206 xanh 1 skip; 2 golden Boya Bài 5/29 xanh; QA render đạt |
| B7e | nghiệm thu Vision crop-only trên Boya thật | chạy API key đã lưu trên đúng crop bảng từ mới Bài 5 và Bài 29, đo theo golden độc lập | xong; Bài 5 đúng 20/20 (recall 100%, precision 100%, 1 dòng được gắn cờ duyệt); Bài 29 đúng 22/22 (recall 100%, precision 100%, 0 dòng gắn cờ); không cần nới validator |
| B7f | dừng an toàn khi AI lỗi + tiếp tục bài đã nhập + thử A/B | phân biệt HTTP 429, không coi 0 từ là thành công, giữ bài đã có khi chạy lại; so local với Vision ghép trang trên golden Bài 5/29 | xong; +3 test, tổng 209 xanh 1 skip; local recall 70%/86,4%, Vision một request mỗi bài đạt 100%/100%; ghép nhiều bài thành một raster không khả thi do giới hạn kích thước/bộ nhớ |
| B7g | Vision một request mỗi bài + hoàn tất Boya | ghép/co crop cùng bài xuống tối đa 1200 px; Flash-Lite; khử trùng/null; fallback từng trang khi độ bao phủ thấp; resume và dừng an toàn | xong; tổng 216 xanh 1 skip, 2 golden xanh; 30/30 bài, 722 từ, 17 dòng gắn cờ, không bài rỗng/trùng/thứ tự lỗi/chuỗi `None`; Bài 5 đúng 20/20 và Bài 29 đúng 22/22 |
| B7h | sửa preview ảnh nguồn | bỏ heuristic nửa trên/nửa dưới và `source_page - 1`; tái định vị, crop và ghép toàn bộ bảng theo ranh giới bài, cache 64 preview | xong; +1 test, tổng 217 xanh 1 skip, 2 golden xanh; QA Bài 5 và 15 hiển thị đủ bảng nhiều trang |
| B7i | sửa preview làm treo giao diện | `PreviewWorker` kết xuất crop ở luồng nền, trạng thái đang tải, giải mã ảnh có kiểm tra và scale nhanh | xong; +1 test, tổng 218 xanh 1 skip, 2 golden xanh; QA thật Bài 5 trả thao tác sau 0,9 ms, ảnh hiện sau 6,12 giây |
| B7j | sửa locator preview Bài 20 | nhận tiêu đề `生词` bị tách thành nhiều span ở đầu trang, không bắt buộc hậu tố `表` | xong; +1 test, tổng 219 xanh 1 skip, 2 golden xanh; QA dialog thật Bài 20 hiển thị pixmap sau 12,65 giây, không khóa UI |
| B7k | chặn preview cũ ghi đè bài mới | vô hiệu hóa worker khi chuyển bài, chỉ worker mới nhất được cập nhật preview, giữ và dọn các thread cũ an toàn | xong; +1 test, tổng 220 xanh 1 skip, 2 golden xanh |

**Phiên tiếp theo phải làm: chờ người dùng nghiệm thu lại preview Bài 20 sau lỗi
worker cũ ghi đè, rồi duyệt 17 dòng được validator gắn cờ; chỉ sửa tiếp khi có lỗi
cụ thể hoặc yêu cầu tự động hóa khâu duyệt.**

Phiên 08a thêm đúng ba phương thức: `UserDb.undo_review`, `DictDb.candidate_meanings`
và `DictDb.candidate_hanviet`, không đổi lược đồ, không thêm bậc migration. Hoàn tác
chỉ chạy trong phiên đang mở vì `review_log` không lưu đủ trạng thái cũ; người gọi
phải giữ cặp `(word, before)` trong bộ nhớ. Hai phương thức rổ đáp án nhiễu trả về
thứ tự XÁC ĐỊNH, việc bốc ngẫu nhiên thuộc tầng giao diện ở phiên 08c.
`tests/unit/test_dictdb.py` là tệp test đầu tiên chạy trên `dict.sqlite` thật.

Trước B1 còn hai việc tay chặn giai đoạn B, xem `handoff/VIEC-CAN-LAM.md`: xác nhận
`bounds_boya.json` và `git init`. Cả hai là việc của người, không giao phiên agent.

Phiên 07 sửa sáu tệp đã có, đúng như packet hẹn trước: `data/userdb.py` thêm đúng
một phương thức `progress_counts()`, còn `ui/widgets/tianzige.py`,
`ui/widgets/decomp_tree.py`, `ui/main_window.py`, `ui/screen_lookup.py` và `main.py`
đổi lệnh import theo việc tách `theme.py`. `MainWindow` và `ScreenLookup` nhận thêm
hai tham số `user_db` và `scheduler` ở cuối danh sách tham số.

Phiên bảo trì **06b**: bảng `progress` ở mục 5.3 thiếu cột `repetition` trong khi
`ReviewOutcome` ở mục 13.3 có trường đó, nên phiên 06 buộc phải ánh xạ nó sang cột
`review_count`. Hai con số khác nghĩa và ánh xạ đó sai. Xem lỗi 9 trong `BAN-GIAO.md`.
**Phải chạy trước phiên 07**, vì màn hình Ôn tập gọi thẳng vào đường này.

Phiên 06 ghi nhận một chỗ lệch giữa packet và đặc tả: packet nói user.sqlite có
"chín bảng", mục 5.3 của đặc tả chỉ định nghĩa **tám** (`schema_version`, `book`,
`lesson`, `lesson_word`, `progress`, `review_log`, `explain_cache`, `setting`).
Đã cài theo đặc tả, tám bảng cộng đúng năm chỉ mục. Nếu bản sau cần bảng thứ chín
thì thêm một bậc mới vào `migrate._CAC_BAC`, đừng sửa bậc 1.

Phiên bảo trì **03b**, chạy sau 04: thêm `DecompNode.is_group` vào `models.py` và cho
`decomposer.tree()` đặt cờ đó, cộng 2 test. Đây không phải một phiên trong dãy, không
đánh số lại; nó giải thích vì sao phiên 03 nhảy từ 28 lên 30 test và tổng nhảy từ 117
lên 120.

Nếu người dùng yêu cầu một phiên mà phiên trước nó chưa xong, hãy dừng lại và nói
rõ phiên nào còn thiếu, đừng tự tạo bù các tệp của phiên trước.

Cập nhật bảng này là **việc bắt buộc cuối mỗi phiên** và không tính là vi phạm quy
tắc "không sửa tệp khác": đổi trạng thái phiên vừa xong, đổi dòng "Phiên tiếp theo
phải làm". Đây là bộ nhớ duy nhất nối các phiên với nhau.

## TỆP HẠ TẦNG ĐƯỢC PHÉP TẠO

Ngoài các tệp liệt kê trong packet, được phép tạo thêm hai tệp sau nếu chưa có, và
chỉ hai tệp này:

- `conftest.py` ở gốc kho, nội dung tối thiểu để `pytest` tìm thấy gói `hanzi_app`.
  Có tệp này rồi thì **không** chèn `sys.path` vào từng tệp test nữa.
- `pytest.ini` hoặc `pyproject.toml` tối thiểu, nếu cần khai báo đường dẫn test.
- `data/models.py` chứa các dataclass ở mục 13.3. Tệp này thuộc phiên 03. Phiên nào
  cần một dataclass trước khi nó ra đời thì khai báo tạm ngay trong module của mình
  kèm ghi chú, rồi phiên 03 gom về một chỗ và sửa lại lệnh import.

## KHÔNG LÀM NHỮNG VIỆC SAU

- Không lập kế hoạch kiến trúc cho toàn bộ ứng dụng. Kiến trúc đã chốt ở mục 13
  của đặc tả; việc của mỗi phiên là cài đặt đúng một module.
- Không tạo thư mục `frontend/`, không dùng React, Vue, Vite hay bất kỳ công nghệ
  web nào. Giao diện là PySide6, ứng dụng desktop.
- Không gộp `dict.sqlite` với `user.sqlite` thành một tệp. Hai tệp tách nhau có lý
  do ở mục 4.3 của đặc tả.
- Không tạo "chế độ giả lập" sinh dữ liệu mẫu trông như thật cho phần diễn giải.
  Toàn bộ luận điểm của đồ án là đầu ra của mô hình luôn phải qua kiểm chứng.
- Không hỏi khoá API. Chưa phiên nào trong bốn phiên trên cần gọi mạng.

## Bối cảnh

Ứng dụng desktop học từ vựng tiếng Trung cho người Việt. Python 3.12, PySide6,
SQLite, chạy trên Windows. Đây là đồ án tốt nghiệp, nên mã phải đọc được và giải
thích được, không tối ưu quá mức.

Môi trường thực tế đang chạy: Python 3.12.9 trên Windows, PySide6 6.11.1, pytest
9.1.1. Bản đặc tả đầu ghi Python 3.11; đã đổi thành 3.12 cho khớp máy đang dùng vì
toàn bộ 120 test xanh trên bản này. Nếu nơi bảo vệ đồ án bắt buộc 3.11 thì đổi lại
ở đây trước, rồi mới chạy phiên tiếp theo. Phụ thuộc ghi ở `requirements.txt` gốc kho.

## Năm quy tắc không được vi phạm

1. **Bộ test là chân lý.** Các bảng số trong đặc tả đã được kiểm chứng độc lập
   bằng một cài đặt riêng. Test đỏ nghĩa là mã sai. Không sửa test, không nới điều
   kiện, không thêm `pytest.approx` rộng hơn mức đặc tả cho phép, không đánh dấu
   `xfail`. Nếu bạn tin rằng test sai, hãy dừng lại và nói ra lý do, đừng tự sửa.

2. **Một phiên một module.** Chỉ tạo đúng các tệp được liệt kê ở mục "Cần tạo".
   Không tạo module khác, không viết sẵn tệp cho bước sau, không dựng khung ứng
   dụng, không thêm `__main__`, không thêm giao diện dòng lệnh.

3. **Không tự thêm tính năng.** Không thêm tham số, không thêm phương thức, không
   thêm xử lý ngoại lệ ngoài phần đặc tả nêu. Thiếu thông tin thì hỏi, đừng đoán.

4. **Phân tầng.** `data/` không được import bất cứ thứ gì của Qt. `service/` không
   được tự mở kết nối cơ sở dữ liệu và không đọc tệp PDF trực tiếp, mà nhận các
   đối tượng tầng dưới qua tham số khởi tạo.

5. **Chỉ dùng thư viện đã có trong đặc tả.** Thư viện chuẩn của Python, cộng
   PySide6, PyMuPDF, pytest. Không thêm phụ thuộc mới nếu không được yêu cầu.

## Xong là khi nào

`pytest tests/unit/<tên tệp test>.py -v` xanh toàn bộ, và không có tệp nào khác
trong kho bị sửa.

## Định dạng trả lời mong muốn

Viết thẳng nội dung từng tệp, mỗi tệp một khối mã có ghi rõ đường dẫn. Không tóm
tắt lại đặc tả, không giải thích dài dòng trước khi viết mã. Sau khi viết xong,
liệt kê ngắn gọn những chỗ bạn phải tự quyết vì đặc tả chưa nói rõ.

---

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

> **Đây là bản CHÉP từ `dac-ta-ung-dung-v0.5.md` và nó đã trôi một lần.** Phiên 03
> sót `DecompNode.is_group` đúng vì đọc bản chép cũ ở đây thay vì đặc tả gốc, phải
> chạy phiên bảo trì 03b để vá. Trước mỗi phiên đụng tới dataclass, đối chiếu khối
> này với mục 13.3 của đặc tả gốc; lệch thì sửa ở đây trước rồi mới bắt đầu phiên.
> Bản này đã đồng bộ tới hết phiên 05.

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
    glyph_alt: str | None  # '讠'
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
# Lookup và decomposer cùng nằm ở tầng service, mà mục 13.1 cấm phụ thuộc đi ngang
# giữa hai module cùng tầng. Cây do Decomposer.tree() dựng, tầng giao diện gọi cả
# hai rồi ghép.

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
    is_group: bool = False    # True với nút nhóm lồng

# Nút nhóm lồng. Chuỗi IDS '⿱木⿰木木' của chữ 森 sinh một nút trung gian ứng với
# '⿰木木', mà cụm đó không phải một chữ Hán. Nút loại này đặt char VÀ ids bằng chính
# đoạn IDS con, meaning_vi và radical bằng None, is_group bằng True. Nút nhóm bị cắt
# vì MAX_DEPTH vẫn giữ is_group bằng True dù không có con. Giao diện BẮT BUỘC kiểm
# tra is_group trước khi vẽ: nút nhóm không được vẽ vào ô 田字格, vì char của nó là
# chuỗi IDS chứ không phải chữ.

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
