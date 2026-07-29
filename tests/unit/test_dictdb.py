"""Kiểm thử hai phương thức rổ đáp án nhiễu của data/dictdb.py, phiên 08a.

Chạy trên `dict.sqlite` THẬT ở gốc kho, mở chế độ chỉ đọc, khác với
test_lookup.py vốn dựng từ điển tí hon riêng. Lý do: hai phương thức này không
xếp hạng gì cả, chúng chỉ lọc và sắp theo thứ tự có sẵn, nên chạy trên dữ liệu
thật vừa đúng ý định vừa bắt được các chỗ dữ liệu chưa phủ. Phần tiếng Việt hiện
phủ 601 từ HSK 1-3 và 958 chữ.

Các con số kỳ vọng đọc thẳng từ tệp bằng một kết nối riêng chứ không chép cứng
vào test: khi bổ sung nghĩa tiếng Việt cho HSK 4-6 thì test vẫn đúng, mà vẫn
kiểm được đúng thứ cần kiểm.
"""

import sqlite3
from pathlib import Path

import pytest

from hanzi_app.data.dictdb import DictDb

DICT_PATH = Path(__file__).resolve().parents[2] / "dict.sqlite"


@pytest.fixture(scope="module")
def dd():
    d = DictDb(str(DICT_PATH))
    yield d
    d.close()


@pytest.fixture(scope="module")
def raw():
    """Kết nối riêng để đối chiếu, cũng chỉ đọc."""
    conn = sqlite3.connect(f"file:{DICT_PATH}?mode=ro", uri=True)
    yield conn
    conn.close()


def cap_hsk(raw: sqlite3.Connection, word: str) -> int | None:
    return raw.execute(
        "SELECT hsk_level FROM word WHERE word_simp = ?", (word,)
    ).fetchone()[0]


# ------------------------------------------------ 10, 11, 12, 13, 14: nghĩa
def test_10_candidate_meanings_dung_so_luong_va_bo_chinh_no(dd):
    ro = dd.candidate_meanings("认识", 1, 5)

    assert len(ro) == 5
    assert all(tu != "认识" for tu, _ in ro)


def test_11_moi_ung_vien_deu_co_nghia_tieng_viet(dd):
    ro = dd.candidate_meanings("认识", 1, 5)

    assert all(nghia is not None and nghia.strip() != "" for _, nghia in ro)


def test_12_goi_hai_lan_tra_ket_qua_giong_het_nhau(dd):
    # Ca quan trọng nhất: ORDER BY RANDOM() trong truy vấn sẽ làm test này đỏ.
    # Rổ phải xác định, việc bốc ngẫu nhiên là của tầng giao diện ở phiên 08c.
    assert dd.candidate_meanings("认识", 1, 5) == dd.candidate_meanings("认识", 1, 5)
    assert dd.candidate_meanings("认识", 1, 30) == dd.candidate_meanings("认识", 1, 30)


def test_13_loc_dung_cap_hsk_duoc_yeu_cau(dd, raw):
    ro = dd.candidate_meanings("认识", 1, 30)

    assert len(ro) == 30
    assert all(cap_hsk(raw, tu) == 1 for tu, _ in ro)


def test_13b_cap_khac_tra_ve_dung_cap_do(dd, raw):
    ro = dd.candidate_meanings("认识", 3, 20)

    assert len(ro) == 20
    assert all(cap_hsk(raw, tu) == 3 for tu, _ in ro)


def test_14_hsk_level_none_khong_loc_theo_cap_nhung_van_bo_exclude_word(dd, raw):
    tong_co_nghia = raw.execute(
        "SELECT COUNT(*) FROM word WHERE meaning_vi IS NOT NULL AND meaning_vi <> ''"
    ).fetchone()[0]

    ro = dd.candidate_meanings("认识", None, limit=tong_co_nghia)

    # Đúng một dòng bị bỏ, là chính exclude_word.
    assert len(ro) == tong_co_nghia - 1
    assert all(tu != "认识" for tu, _ in ro)
    # Và rổ trải qua nhiều hơn một cấp, nghĩa là không có bộ lọc cấp nào chạy lén.
    assert len({cap_hsk(raw, tu) for tu, _ in ro}) > 1


def test_14b_limit_mac_dinh_la_30(dd):
    assert len(dd.candidate_meanings("认识", 1)) == 30


def test_14c_cap_hsk_khong_co_du_lieu_tra_ro_rong(dd):
    # HSK 6 chưa được bổ sung nghĩa tiếng Việt. Rổ rỗng chứ không ném lỗi;
    # tầng giao diện tự xử khi không đủ đáp án nhiễu.
    assert dd.candidate_meanings("认识", 6, 5) == []


# ------------------------------------------------------------- 15: Hán-Việt
def test_15_candidate_hanviet_dung_so_luong_bo_chinh_no_va_am_khac_rong(dd):
    ro = dd.candidate_hanviet("认", 5)

    assert len(ro) == 5
    assert all(ch != "认" for ch, _ in ro)
    assert all(am is not None and am.strip() != "" for _, am in ro)


def test_15b_candidate_hanviet_goi_hai_lan_giong_het_nhau(dd):
    assert dd.candidate_hanviet("认", 5) == dd.candidate_hanviet("认", 5)
    assert dd.candidate_hanviet("认", 30) == dd.candidate_hanviet("认", 30)


def test_15c_candidate_hanviet_bo_dung_chu_bi_loai(dd):
    # 一 đứng đầu rổ theo thứ tự tần suất; loại nó ra thì phần còn lại dịch lên
    # một bậc chứ không phải xáo lại.
    day_du = dd.candidate_hanviet("认", 6)
    bo_dau = dd.candidate_hanviet(day_du[0][0], 5)

    assert bo_dau == day_du[1:]
