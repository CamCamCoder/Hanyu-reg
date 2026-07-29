"""Kiểm thử service/lookup.py theo bảng đáp án ở mục 14.4 của đặc tả.

Chạy trên `mini_dict.sqlite` dựng bằng fixture, **không** chạy trên `dict.sqlite`
thật: `dict.sqlite` có 5001 từ với freq_rank sinh từ cấp HSK làm giá trị thay thế,
nên thứ tự trả về có thể tình cờ đúng vì lý do khác. Bảng từ của fixture nạp đúng
ba dòng của mục 14.4 và không dòng nào khác.

UserDb chưa được cài đặt ở phiên nào, nên tầng người dùng được thay bằng bản giả
lập ở dưới. Đúng theo mục 13.1: service nhận đối tượng tầng dưới qua tham số khởi
tạo nên thay được bằng bản giả lập.
"""

import ast
import dataclasses
import inspect
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import (
    CharInfo,
    ReviewOutcome,
    WordDetail,
    WordSource,
)
from hanzi_app.service import lookup as lookup_module
from hanzi_app.service.lookup import LookupService

DICT_PATH = Path(__file__).resolve().parents[2] / "dict.sqlite"

# Ký tự vùng dùng riêng, chắc chắn không có trong từ điển nào.
PUA = ""

# Lược đồ tối thiểu của dict.sqlite, chép từ mục 5.2, chỉ các bảng mà lookup dùng.
SCHEMA = """
CREATE TABLE char (
    char           TEXT PRIMARY KEY,
    codepoint      TEXT,
    pinyin         TEXT,
    pinyin_plain   TEXT,
    meaning_en     TEXT,
    meaning_vi     TEXT,
    hanviet        TEXT,
    radical_idx    INTEGER,
    radical_stroke INTEGER,
    total_strokes  INTEGER,
    trad_form      TEXT,
    ids            TEXT,
    hsk_level      INTEGER,
    freq_rank      INTEGER
);
CREATE TABLE char_reading (
    char         TEXT NOT NULL,
    pinyin       TEXT NOT NULL,
    pinyin_plain TEXT NOT NULL,
    is_primary   INTEGER DEFAULT 0,
    PRIMARY KEY (char, pinyin)
);
CREATE TABLE word (
    id             INTEGER PRIMARY KEY,
    word_simp      TEXT NOT NULL,
    word_trad      TEXT,
    pinyin_num     TEXT,
    pinyin_tone    TEXT,
    pinyin_plain   TEXT,
    pinyin_numeric TEXT,
    pos            TEXT,
    meaning_en     TEXT,
    meaning_vi     TEXT,
    hsk_level      INTEGER,
    freq_rank      INTEGER
);
CREATE VIRTUAL TABLE word_fts USING fts5(
    meaning_vi, meaning_en,
    content = 'word', content_rowid = 'id'
);
"""

# Đúng ba dòng của bảng ở mục 14.4. Cột pinyin và nghĩa lấy theo mockup mục 7.2.
WORDS_14_4 = [
    # id, giản, phồn, py_num, py_tone, py_plain, py_numeric, pos, en, vi, hsk, freq
    (1, "认识", "認識", "ren4 shi5", "rènshi", "renshi", "ren4shi5", "动",
     "recognize; know (a person)", "quen biết, làm quen", 1, 412),
    (2, "人事", "人事", "ren2 shi4", "rénshì", "renshi", "ren2shi4", "名",
     "personnel", "nhân sự, việc đời", 5, 2108),
    (3, "人士", "人士", "ren2 shi4", "rénshì", "renshi", "ren2shi4", "名",
     "person; public figure", "nhân sĩ, người có địa vị", 6, 2687),
]

# Chữ đơn của ba từ trên. Chỉ các cột mà CharInfo cần.
CHARS = [
    # char, pinyin, py_plain, en, vi, hanviet, radical, strokes, trad, ids
    ("认", "rèn", "ren", "to recognize", "nhận biết", "nhận", 149, 4, "認", "⿰讠人"),
    ("识", "shí", "shi", "to know", "nhận ra", "thức", 149, 7, "識", "⿰讠只"),
    ("人", "rén", "ren", "man; person", "người", "nhân", 9, 2, None, None),
    ("事", "shì", "shi", "matter; affair", "việc", "sự", 6, 8, None, None),
    ("士", "shì", "shi", "scholar", "người có học", "sĩ", 33, 3, None, None),
]

READINGS = [("认", "rèn", "ren", 1), ("识", "shí", "shi", 1), ("识", "zhì", "zhi", 0)]

# Điểm mong đợi, tính tay từ công thức mục 13.6:
# score = 100·w_khớp + 30·(7 − hsk)/6 + 20/log10(freq_rank + 10)
DIEM = {
    ("hanzi", "认识"): 137.6181,
    ("pinyin_tone", "认识"): 127.6181,
    ("pinyin_tone", "人事"): 106.0134,
    ("pinyin_tone", "人士"): 100.8294,
    ("pinyin_plain", "认识"): 112.6181,
    ("pinyin_plain", "人事"): 91.0134,
    ("pinyin_plain", "人士"): 85.8294,
    ("fuzzy", "认识"): 62.6181,
    ("fuzzy", "人事"): 41.0134,
    ("fuzzy", "人士"): 35.8294,
}


# ------------------------------------------------------------------- bản giả lập
class FakeUserDb:
    """Bản giả lập tối thiểu của UserDb: chỉ hai phương thức mà lookup gọi tới."""

    def __init__(self, progress=None, sources=None) -> None:
        self._progress = progress or {}
        self._sources = sources or {}

    def get_progress(self, word: str):
        return self._progress.get(word)

    def word_source(self, word: str):
        return self._sources.get(word)


NGUON_NHAN_THUC = WordSource(
    book_title="博雅汉语 I",
    lesson_no=3,
    lesson_title="你叫什么名字",
    page=31,
    pinyin_src="rènshi",
    hanviet_src="nhận thức",
    meaning_src="quen biết, làm quen",
)

TIEN_DO_NHAN_THUC = ReviewOutcome(
    ease=2.5,
    interval_days=6,
    repetition=2,
    lapse_count=0,
    status="learning",
    due_date=date(2025, 3, 1),
)


# ------------------------------------------------------------------------ fixtures
def _build(path: Path, words, chars=(), readings=()) -> None:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO word VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", words)
    con.executemany(
        "INSERT INTO char(char, pinyin, pinyin_plain, meaning_en, meaning_vi, "
        "hanviet, radical_idx, total_strokes, trad_form, ids) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        chars,
    )
    con.executemany("INSERT INTO char_reading VALUES (?,?,?,?)", readings)
    # Bảng ngoài nên chỉ mục toàn văn phải nạp tay sau khi bảng word đã có dữ liệu.
    con.execute(
        "INSERT INTO word_fts(rowid, meaning_vi, meaning_en) "
        "SELECT id, meaning_vi, meaning_en FROM word"
    )
    con.commit()
    con.close()


@pytest.fixture(scope="module")
def mini_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("dict") / "mini_dict.sqlite"
    _build(path, WORDS_14_4, CHARS, READINGS)
    db = DictDb(str(path))
    yield db
    db.close()


@pytest.fixture
def user_db():
    return FakeUserDb(
        progress={"认识": TIEN_DO_NHAN_THUC},
        sources={"认识": NGUON_NHAN_THUC},
    )


@pytest.fixture
def lk(mini_db, user_db):
    return LookupService(mini_db, user_db)


@pytest.fixture(scope="module")
def lk_khoa_kep(tmp_path_factory):
    """Từ điển hai dòng dựng riêng cho quy tắc khoá sắp xếp kép.

    Truy vấn 'ban' khớp nghĩa của 朋友 (điểm 50,0) và khớp gần với 八 (điểm 74,2).
    Khớp gần điểm cao hơn nhưng vẫn phải xếp sau, nên chỉ fixture này bắt được lỗi
    cộng dồn hai loại khớp vào cùng một điểm.
    """
    path = tmp_path_factory.mktemp("dict") / "khoa_kep.sqlite"
    _build(
        path,
        [
            (1, "八", "八", "ba1", "bā", "ba", "ba1", "数", "eight", "số tám", 1, 1),
            (2, "朋友", "朋友", "peng2 you5", "péngyou", "pengyou", "peng2you5",
             "名", "friend", "bạn bè", None, None),
        ],
    )
    db = DictDb(str(path))
    yield LookupService(db, FakeUserDb())
    db.close()


@pytest.fixture(scope="module")
def lk_that():
    """Từ điển thật, chỉ dùng cho các test không liên quan tới xếp hạng."""
    db = DictDb(str(DICT_PATH))
    yield LookupService(db, FakeUserDb())
    db.close()


# ------------------------------------------------------------------- tiện ích
def tu(hits):
    return [h.word.simplified for h in hits]


def cach_khop(hits):
    return {h.word.simplified: h.matched_by for h in hits}


# --------------------------------------------------- bảng 14.4: thứ tự xếp hạng
def test_bang_14_4_thu_tu_ba_tu(lk):
    assert tu(lk.search("renshi")) == ["认识", "人事", "人士"]


def test_bang_14_4_deu_la_khop_pinyin_phang(lk):
    hits = lk.search("renshi")
    assert [h.kind for h in hits] == ["word", "word", "word"]
    assert all(h.matched_by == "pinyin_plain" for h in hits)
    assert all(h.char is None for h in hits)


def test_bang_14_4_diem_dung_cong_thuc(lk):
    for hit in lk.search("renshi"):
        cho_doi = DIEM[("pinyin_plain", hit.word.simplified)]
        assert hit.score == pytest.approx(cho_doi, abs=1e-4)


def test_bang_14_4_diem_giam_dan(lk):
    diem = [h.score for h in lk.search("renshi")]
    assert diem == sorted(diem, reverse=True)
    assert len(set(diem)) == 3


def test_bang_14_4_hsk_thang_khi_tan_suat_chenh_it(lk):
    """人事 thắng 人士 chỉ nhờ cấp HSK chênh một bậc: bỏ thành phần HSK khỏi công
    thức là hai từ này đổi chỗ."""
    hits = {h.word.simplified: h for h in lk.search("renshi")}
    nhan_su, nhan_si = hits["人事"], hits["人士"]
    assert nhan_su.score > nhan_si.score
    assert nhan_su.word.hsk_level == 5 and nhan_si.word.hsk_level == 6


# --------------------------------------------------------- FR-01, FR-07: chữ Hán
def test_ca_bien_truy_van_chu_han(lk):
    hits = lk.search("认识")
    assert tu(hits)[0] == "认识"
    assert hits[0].matched_by == "hanzi"
    assert hits[0].kind == "word"
    assert hits[0].score == pytest.approx(DIEM[("hanzi", "认识")], abs=1e-4)


def test_khop_chu_han_khong_lay_tu_dong_am(lk):
    assert tu(lk.search("认识")) == ["认识"]


def test_khop_dang_phon_the(lk):
    assert tu(lk.search("認識")) == ["认识"]


def test_truy_van_mot_chu_cho_ket_qua_muc_chu(lk):
    """Không có mục từ nào là 认 trong fixture, nhưng chữ đơn vẫn tra được."""
    hits = lk.search("认")
    assert len(hits) == 1
    assert hits[0].kind == "char"
    assert hits[0].word is None
    assert isinstance(hits[0].char, CharInfo)
    assert hits[0].char.char == "认"
    assert hits[0].char.readings == ("rèn",)
    assert hits[0].matched_by == "hanzi"
    assert hits[0].score == pytest.approx(100.0, abs=1e-4)


def test_chu_khong_co_trong_tu_dien(lk):
    assert lk.search(PUA) == []
    assert lk.suggest(PUA) == []


# ---------------------------------------------- FR-02: pinyin có dấu thanh
def test_pinyin_co_dau_dung_thanh(lk):
    hits = lk.search("rènshi")
    assert cach_khop(hits)["认识"] == "pinyin_tone"
    assert hits[0].word.simplified == "认识"
    assert hits[0].score == pytest.approx(DIEM[("pinyin_tone", "认识")], abs=1e-4)


def test_pinyin_co_dau_tu_dong_am_chi_khop_muc_phang(lk):
    """'rènshi' khớp đúng dấu với 认识; 人事 và 人士 đọc 'rénshì' nên chỉ được tính
    ở mức pinyin phẳng, đúng thang trọng số 0,90 so với 0,75."""
    khop = cach_khop(lk.search("rènshi"))
    assert khop == {"认识": "pinyin_tone", "人事": "pinyin_plain", "人士": "pinyin_plain"}


def test_pinyin_co_dau_khac_thanh(lk):
    """'rénshì' đúng dấu cho 人事 và 人士. 认识 chỉ khớp mức phẳng nhưng vẫn hạng 1
    vì điểm cao hơn: mục 13.6 chỉ đẩy nhóm khớp gần xuống cuối, không đẩy nhóm
    khớp phẳng xuống dưới nhóm khớp có dấu."""
    hits = lk.search("rénshì")
    assert cach_khop(hits) == {
        "认识": "pinyin_plain",
        "人事": "pinyin_tone",
        "人士": "pinyin_tone",
    }
    assert tu(hits) == ["认识", "人事", "人士"]
    for hit in hits:
        assert hit.score == pytest.approx(
            DIEM[(hit.matched_by, hit.word.simplified)], abs=1e-4
        )


def test_pinyin_khong_dau_khong_bi_tinh_la_co_dau(lk):
    """'renshi' trùng y nguyên cột pinyin_tone của 认识 (từ này khinh thanh nên
    dạng có dấu không có dấu nào), nhưng người dùng không gõ dấu nào cả nên đây
    là khớp phẳng."""
    assert cach_khop(lk.search("renshi"))["认识"] == "pinyin_plain"


# --------------------------------------- FR-03: pinyin không dấu và pinyin số
def test_pinyin_so_du_khinh_thanh(lk):
    hits = lk.search("ren4shi5")
    assert tu(hits) == ["认识"]
    assert hits[0].matched_by == "pinyin_num"
    assert hits[0].score == pytest.approx(DIEM[("pinyin_plain", "认识")], abs=1e-4)


def test_pinyin_so_thieu_khinh_thanh(lk):
    """FR-03 nói rõ phải chấp nhận cả 'ren4shi' lẫn 'ren4shi5'."""
    assert tu(lk.search("ren4shi")) == ["认识"]
    assert lk.search("ren4shi")[0].matched_by == "pinyin_num"


def test_pinyin_so_co_khoang_trang(lk):
    assert tu(lk.search("ren4 shi5")) == ["认识"]


def test_pinyin_so_thanh_khac_cho_tu_khac(lk):
    """Người dùng đã nói rõ thanh nào thì không trả về toàn bộ từ đồng âm."""
    assert set(tu(lk.search("ren2shi4"))) == {"人事", "人士"}


# -------------------------------------------------------- FR-04: tìm theo nghĩa
@pytest.mark.skip(
    reason="Cột meaning_vi của bảng word trong dict.sqlite còn rỗng (0/5001 dòng) "
           "nên FR-04 theo nghĩa tiếng Việt chưa kiểm thử được trên dữ liệu thật. "
           "Đường đi qua word_fts được kiểm ở test_tim_theo_nghia_tieng_anh và "
           "test_khop_gan_xep_sau_khop_dung_du_diem_cao_hon."
)
def test_tim_theo_nghia_tieng_viet_tren_dict_that(lk_that):
    hits = lk_that.search("quen biết")
    assert "认识" in tu(hits)
    assert cach_khop(hits)["认识"] == "meaning"


def test_tim_theo_nghia_tieng_anh(lk_that):
    """Nửa tiếng Anh của FR-04 kiểm được ngay trên dict.sqlite thật."""
    hits = lk_that.search("know (a person)")
    assert tu(hits) == ["认识"]
    assert hits[0].matched_by == "meaning"
    assert hits[0].score == pytest.approx(50 + 30 * 1.0 + 20 / 1.9777, abs=0.1)


def test_dau_ngoac_trong_truy_van_khong_pha_cu_phap_fts(lk_that):
    """Chuỗi có ký tự đặc biệt của FTS5 phải không làm sqlite báo lỗi cú pháp."""
    for q in ['nhân "sự"', "a OR (b", "*", "^token", "-"]:
        assert isinstance(lk_that.search(q), list)


# ----------------------------------------- FR-08: khớp gần và khoá sắp xếp kép
def test_ca_bien_khong_khop_thi_search_tra_rong(lk):
    assert lk.search("renshix") == []


def test_ca_bien_suggest_tra_ve_renshi(lk):
    hits = lk.suggest("renshix")
    assert tu(hits) == ["认识", "人事", "人士"]
    assert all(h.matched_by == "fuzzy" for h in hits)
    for hit in hits:
        assert hit.score == pytest.approx(DIEM[("fuzzy", hit.word.simplified)], abs=1e-4)


def test_khop_gan_khong_bao_gio_lan_vao_search(lk):
    for q in ["renshi", "认识", "renshix", "rènshi", "ren4shi"]:
        assert all(h.matched_by != "fuzzy" for h in lk.search(q))


def test_suggest_van_uu_tien_khop_dung_khi_co(lk):
    hits = lk.suggest("renshi")
    assert all(h.matched_by == "pinyin_plain" for h in hits)


def test_khop_gan_xep_sau_khop_dung_du_diem_cao_hon(lk_khoa_kep):
    """Quy tắc khoá kép của mục 13.6: nhóm khớp đúng luôn ở trên."""
    hits = lk_khoa_kep.suggest("ban")
    assert tu(hits) == ["朋友", "八"]
    assert [h.matched_by for h in hits] == ["meaning", "fuzzy"]

    khop_dung, khop_gan = hits
    assert khop_dung.score == pytest.approx(50.0, abs=1e-4)
    assert khop_gan.score == pytest.approx(74.2051, abs=1e-4)
    assert khop_gan.score > khop_dung.score      # điểm cao hơn mà vẫn xếp sau


def test_search_o_fixture_khoa_kep_chi_tra_khop_dung(lk_khoa_kep):
    assert tu(lk_khoa_kep.search("ban")) == ["朋友"]


def test_khop_gan_khong_nhan_moi_thu(lk):
    """Truy vấn quá xa thì không được gợi ý bừa."""
    assert lk.suggest("xyzzyx") == []


# --------------------------------------------------------------------- limit
def test_search_ton_trong_limit(lk):
    assert len(lk.search("renshi", limit=2)) == 2
    assert tu(lk.search("renshi", limit=1)) == ["认识"]


def test_suggest_ton_trong_limit(lk):
    assert len(lk.suggest("renshix", limit=1)) == 1
    assert tu(lk.suggest("renshix", limit=1)) == ["认识"]


def test_truy_van_rong(lk):
    for q in ["", "   ", "\t"]:
        assert lk.search(q) == []
        assert lk.suggest(q) == []


def test_khoang_trang_hai_dau_bi_bo(lk):
    assert tu(lk.search("  renshi  ")) == ["认识", "人事", "人士"]


# ---------------------------------------------------------- FR-06: detail
def test_detail_gop_du_lieu_tu_dien_va_nguoi_dung(lk):
    ct = lk.detail("认识")

    assert isinstance(ct, WordDetail)
    assert ct.query == "认识"
    assert ct.word.simplified == "认识"
    assert ct.word.traditional == "認識"
    assert ct.word.pinyin_tone == "rènshi"
    assert ct.word.pos == "动"
    assert ct.word.hsk_level == 1
    assert ct.word.meaning_vi == "quen biết, làm quen"
    assert ct.source is NGUON_NHAN_THUC
    assert ct.status == "learning"


def test_detail_tung_chu_theo_dung_thu_tu(lk):
    ct = lk.detail("认识")
    assert tuple(c.char for c in ct.chars) == ("认", "识")
    assert ct.chars[0].hanviet == "nhận"
    assert ct.chars[1].readings == ("shí", "zhì")

    assert tuple(c.char for c in lk.detail("事人").chars) == ("事", "人")


def test_detail_khong_co_tien_do_va_nguon(lk):
    ct = lk.detail("人士")
    assert ct.word.simplified == "人士"
    assert ct.source is None
    assert ct.status is None


def test_detail_chu_don_khong_phai_muc_tu(lk):
    """FR-07 ngược lại: tra được ở mức chữ thì word bằng None, chars vẫn có."""
    ct = lk.detail("士")
    assert ct.word is None
    assert tuple(c.char for c in ct.chars) == ("士",)


def test_detail_khong_co_gi_trong_tu_dien(lk):
    ct = lk.detail(PUA)
    assert ct.word is None
    assert ct.chars == ()
    assert ct.source is None
    assert ct.status is None


def test_detail_bo_qua_chu_khong_co_trong_tu_dien(lk):
    assert tuple(c.char for c in lk.detail("认" + PUA + "识").chars) == ("认", "识")


# ------------------------------------------------- mục 13.1: quy tắc phân tầng
def test_word_detail_khong_chua_cay_chiet_tu():
    """WordDetail cố ý không có trường nào cho cây chiết tự hay phần diễn giải."""
    ten = tuple(f.name for f in dataclasses.fields(WordDetail))
    assert ten == ("query", "word", "chars", "source", "status")


def test_lookup_khong_import_ngang_va_khong_mo_co_so_du_lieu():
    """service không được import module cùng tầng, không được tự mở kết nối."""
    cay = ast.parse(inspect.getsource(lookup_module))
    da_import: set[str] = set()
    for node in ast.walk(cay):
        if isinstance(node, ast.Import):
            da_import.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            da_import.add(node.module or "")
            da_import.update(a.name for a in node.names)

    assert not any("decomposer" in m for m in da_import)
    assert "sqlite3" not in da_import
    assert not any(m.startswith("PySide6") for m in da_import)
