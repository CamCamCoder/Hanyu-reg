"""Toàn bộ dataclass dùng chung, chép đúng theo mục 13.3 của đặc tả.

Tất cả đông cứng, không có phương thức nghiệp vụ. Tầng data không import bất cứ
thứ gì của Qt.
"""

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
# Lý do là quy tắc phân tầng ở mục 13.1: lookup và decomposer cùng nằm ở tầng
# service, mà phụ thuộc không được đi ngang giữa hai module cùng tầng. Cây chiết
# tự do Decomposer.tree() dựng, phần diễn giải do quy trình QT-05 sinh; tầng giao
# diện gọi cả ba rồi ghép lại thành màn hình ở mục 7.2. Nhét cây vào WordDetail
# sẽ buộc lookup phải import decomposer và phá vỡ phân tầng.


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
    is_group: bool = False    # True với nút nhóm lồng, xem ghi chú bên dưới


# Nút nhóm lồng. Chuỗi IDS '⿱木⿰木木' của chữ 森 sinh ra một nút trung gian ứng với
# '⿰木木', mà cụm đó không phải một chữ Hán. Nút loại này đặt char bằng chính chuỗi
# IDS con, meaning_vi và radical bằng None, và is_group bằng True. Giao diện BẮT
# BUỘC kiểm tra is_group trước khi vẽ: nút nhóm không được vẽ vào ô 田字格, vì ô đó
# chỉ dành cho một chữ đơn, vẽ chuỗi '⿰木木' vào đó sẽ trông như lỗi hiển thị.


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
    hanviet_src: str | None = None
    source_block_id: int | None = None


@dataclass(frozen=True)
class ReviewOutcome:
    ease: float
    interval_days: int
    repetition: int
    lapse_count: int
    status: str            # 'new' | 'learning' | 'known'
    due_date: date


@dataclass(frozen=True)
class TextSpan:
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    font_size: float
    is_ocr: bool = False


@dataclass(frozen=True)
class PageEvidence:
    pdf_page: int
    page_kind: str
    top_text: str
    bottom_text: str
    toc_text: str | None
    printed_page: int | None
    heading_lesson_no: int | None
    heading_title: str | None
    is_toc_candidate: bool
    layout_fingerprint: str | None = None


@dataclass(frozen=True)
class BoundaryEvidence:
    source: str
    page_index: int
    lesson_no: int | None
    title: str | None
    confidence: float
    detail: str


@dataclass(frozen=True)
class BoundaryIssue:
    code: str
    severity: str
    lesson_no: int | None
    page_index: int | None
    message: str


@dataclass(frozen=True)
class BoundaryReport:
    valid: bool
    issues: tuple[BoundaryIssue, ...]
    missing_lesson_nos: tuple[int, ...]


@dataclass(frozen=True)
class SplitResult:
    boundaries: tuple[LessonBoundary, ...]
    evidence: tuple[BoundaryEvidence, ...]
    report: BoundaryReport
    needs_review: bool


@dataclass(frozen=True)
class VocabBlock:
    id: int | None
    lesson_id: int | None
    block_no: int
    page_index: int
    bbox: tuple[float, float, float, float]
    crop_path: str | None
    expected_rows: int | None
    first_order: int | None
    last_order: int | None
    status: str = "pending"
    ai_attempts: int = 0


@dataclass(frozen=True)
class BlockCoverage:
    block_id: int | None
    expected_rows: int | None
    local_rows: int
    ai_rows: int
    final_rows: int
    missing_orders: tuple[int, ...]
    issues: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class ExtractionResult:
    rows: tuple[VocabRow, ...]
    coverage: tuple[BlockCoverage, ...]
    blocks: tuple[VocabBlock, ...]
    ai_attempts: int
    complete: bool
