"""Kiểm thử service/decomposer.py theo bảng đáp án ở mục 14.3 của đặc tả.

Chạy trên dict.sqlite thật, mở chỉ đọc. Ba ca biên bắt buộc (nút lá, chu trình,
chuỗi sâu quá 6 tầng) chạy trên một bản sao tạm có chèn thêm vài chữ giả; tệp gốc
không bị đụng tới.
"""

import shutil
import sqlite3
from pathlib import Path

import pytest

from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import DecompNode, Radical
from hanzi_app.service.decomposer import Decomposer

DICT_PATH = Path(__file__).resolve().parents[2] / "dict.sqlite"

# Mười hai toán tử mô tả cấu trúc chữ, không phải thành phần của chữ.
IDC = "⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻"

# Ký tự vùng dùng riêng, chắc chắn không có trong dict.sqlite.
PUA = ""


# ------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def dict_db():
    db = DictDb(str(DICT_PATH))
    yield db
    db.close()


@pytest.fixture(scope="module")
def decomp(dict_db):
    return Decomposer(dict_db)


@pytest.fixture(scope="module")
def fake_db(tmp_path_factory):
    """Bản sao tạm của dict.sqlite, chèn thêm chữ giả cho ca chu trình và ca sâu
    quá 6 tầng. Không sửa tệp gốc."""
    copy_path = tmp_path_factory.mktemp("dict") / "mini_dict.sqlite"
    shutil.copy(DICT_PATH, copy_path)

    con = sqlite3.connect(copy_path)
    # Hai chữ giả trỏ vòng vào nhau. 一 là bộ Khang Hy nên dừng ngay, chỉ còn
    # đúng một đường vòng để bẫy đệ quy.
    con.execute("INSERT INTO char(char, ids) VALUES ('㐀', '⿰㐁一')")
    con.execute("INSERT INTO char(char, ids) VALUES ('㐁', '⿰㐀一')")
    # Chuỗi tám tầng: 㐂 -> 㐃 -> ... -> 㐉. Không chữ nào là bộ Khang Hy.
    chain = "㐂㐃㐄㐅㐆㐇㐈㐉"
    for cur, nxt in zip(chain, chain[1:]):
        con.execute("INSERT INTO char(char, ids) VALUES (?, ?)", (cur, f"⿰{nxt}一"))
    con.execute("INSERT INTO char(char, ids) VALUES (?, NULL)", (chain[-1],))
    con.commit()
    con.close()

    db = DictDb(str(copy_path))
    yield db
    db.close()


@pytest.fixture(scope="module")
def fake_decomp(fake_db):
    return Decomposer(fake_db)


# -------------------------------------------------------------------- tiện ích
def depth_of(node: DecompNode) -> int:
    """Độ sâu cây: nút lá là 0."""
    if not node.children:
        return 0
    return 1 + max(depth_of(child) for child in node.children)


def components_of(ids: str | None) -> tuple[str, ...]:
    """Các thành phần trong chuỗi IDS, bỏ mười hai toán tử cấu trúc."""
    if ids is None:
        return ()
    return tuple(c for c in ids if c not in IDC)


def all_nodes(node: DecompNode):
    yield node
    for child in node.children:
        yield from all_nodes(child)


# ------------------------------------------------------ bảng 14.3: mười chữ
# (chữ, ids, thành phần, số hiệu bộ, glyph bộ, tổng nét, độ sâu cây)
BANG_14_3 = [
    ("认", "⿰讠人", "讠人", 149, "言", 4, 1),
    ("识", "⿰讠只", "讠只", 149, "言", 7, 2),
    ("谢", "⿰讠射", "讠射", 149, "言", 12, 2),
    ("好", "⿰女子", "女子", 38, "女", 6, 1),
    ("名", "⿸夕口", "夕口", 30, "口", 6, 1),
    ("字", "⿱宀子", "宀子", 39, "子", 6, 1),
    ("朋", "⿰月月", "月月", 74, "月", 8, 1),
    ("明", "⿰日月", "日月", 72, "日", 8, 1),
    ("森", "⿱木⿰木木", "木木木", 75, "木", 12, 2),
    # Chuỗi IDS của 一 trong dict.sqlite là NULL: nguồn không phân tách chữ này.
    # Bảng 14.3 ghi `一`, hai cách ghi cùng nghĩa "không phân tách được".
    ("一", None, "", 1, "一", 1, 0),
]


@pytest.mark.parametrize("ch, ids, thanh_phan, ridx, glyph, strokes, do_sau", BANG_14_3)
def test_bang_14_3(decomp, dict_db, ch, ids, thanh_phan, ridx, glyph, strokes, do_sau):
    node = decomp.tree(ch)

    assert node.char == ch
    assert node.ids == ids
    assert components_of(node.ids) == tuple(thanh_phan)
    assert depth_of(node) == do_sau

    bo = decomp.radical_of(ch)
    assert bo is not None
    assert (bo.idx, bo.glyph) == (ridx, glyph)
    assert node.radical == bo

    info = dict_db.get_char(ch)
    assert info is not None
    assert info.total_strokes == strokes


# ----------------------------------------------- quy tắc 1: giữ cấu trúc lồng
def test_sam_hai_tang_khong_phai_ba_la(decomp):
    """森 = ⿱木⿰木木 phải cho cây hai tầng, không phải một tầng ba lá."""
    node = decomp.tree("森")
    assert len(node.children) == 2

    trai, phai = node.children
    assert trai.char == "木"
    assert trai.children == ()          # bộ Khang Hy, dừng
    assert phai.ids == "⿰木木"
    assert tuple(c.char for c in phai.children) == ("木", "木")
    assert depth_of(node) == 2


def test_toan_tu_hai_toan_hang(decomp):
    node = decomp.tree("明")
    assert tuple(c.char for c in node.children) == ("日", "月")


def test_toan_tu_ba_toan_hang(decomp):
    """⿳ nhận ba toán hạng: 京 = ⿳亠口小."""
    node = decomp.tree("京")
    assert node.ids == "⿳亠口小"
    assert tuple(c.char for c in node.children) == ("亠", "口", "小")


def test_toan_tu_ba_toan_hang_co_nhom_long(decomp):
    """亮 = ⿳亠口⿱冖几: toán hạng thứ ba là một nhóm."""
    node = decomp.tree("亮")
    assert len(node.children) == 3
    assert node.children[2].ids == "⿱冖几"
    assert tuple(c.char for c in node.children[2].children) == ("冖", "几")
    assert depth_of(node) == 2


# ------------------------------------------------------ cờ is_group của nút nhóm
def test_is_group_dung_o_nut_nhom_long_cua_sam(decomp):
    """森 = ⿱木⿰木木: chỉ nút '⿰木木' là nút nhóm, các nút còn lại thì không."""
    node = decomp.tree("森")
    assert node.is_group is False

    trai, phai = node.children
    assert trai.is_group is False

    # Nút nhóm: char giữ nguyên đoạn IDS con, không có nghĩa và không có bộ.
    assert phai.is_group is True
    assert phai.char == "⿰木木"
    assert phai.meaning_vi is None
    assert phai.radical is None

    assert all(c.is_group is False for c in phai.children)
    assert [n.is_group for n in all_nodes(node)].count(True) == 1


def test_is_group_luon_false_khi_khong_co_nhom_long(decomp):
    """认 = ⿰讠人, mọi toán hạng đều là chữ đơn nên không sinh nút nhóm nào."""
    node = decomp.tree("认")
    assert all(n.is_group is False for n in all_nodes(node))


# --------------------------------------- quy tắc 2: bộ Khang Hy là nút lá
def test_quy_tac_2_bo_thu_la_nut_la_du_co_ids(decomp, dict_db):
    """日 có chuỗi IDS trong dữ liệu (⿴口一) nhưng là bộ 72 nên không đệ quy."""
    assert dict_db.get_char("日").ids is not None

    nhat = decomp.tree("明").children[0]
    assert nhat.char == "日"
    assert nhat.children == ()
    assert nhat.truncated is False


def test_quy_tac_2_thanh_phan_khong_phai_bo_thi_di_tiep(decomp):
    """只 không phải bộ Khang Hy nên còn tách tiếp một tầng: ⿱口八."""
    chi = decomp.tree("识").children[1]
    assert chi.char == "只"
    assert tuple(c.char for c in chi.children) == ("口", "八")
    assert all(c.children == () for c in chi.children)   # 口 và 八 đều là bộ


def test_quy_tac_2_xa_cung_dung_o_bo(decomp):
    """射 = ⿰身寸, cả 身 lẫn 寸 đều là bộ nên cây dừng ở tầng 2."""
    xa = decomp.tree("谢").children[1]
    assert xa.char == "射"
    assert tuple(c.char for c in xa.children) == ("身", "寸")
    assert depth_of(decomp.tree("谢")) == 2


def test_khong_chu_nao_tan_thanh_net(decomp):
    """Không nút lá nào của mười chữ trong bảng là nét rời như 丨 hay 丶."""
    for ch, *_ in BANG_14_3:
        for node in all_nodes(decomp.tree(ch)):
            if not node.children:
                assert node.char not in "丨丶乀乁"


# ---------------------------------------- ca biên 1: nút lá khác nút bị cắt
def test_ca_bien_nut_la_khong_phai_nut_bi_cat(decomp):
    node = decomp.tree("一")
    assert node.children == ()
    assert node.truncated is False


def test_chu_khong_co_trong_tu_dien_van_tra_ve_nut_la(decomp):
    node = decomp.tree(PUA)
    assert node.char == PUA
    assert node.ids is None
    assert node.children == ()
    assert node.truncated is False
    assert node.radical is None


# ------------------------------------------------------- ca biên 2: chu trình
def test_ca_bien_chu_trinh_khong_tran_ngan_xep(fake_decomp):
    """㐀 và 㐁 trỏ vòng vào nhau. Hàm phải kết thúc và đặt truncated = True."""
    node = fake_decomp.tree("㐀")

    quay_lai = [n for n in all_nodes(node) if n.char == "㐀" and n is not node]
    assert len(quay_lai) == 1
    assert quay_lai[0].truncated is True
    assert quay_lai[0].children == ()
    assert any(n.char == "㐁" for n in all_nodes(node))


def test_chu_tu_tro_vao_chinh_no(fake_decomp):
    """Nút gốc không bị đánh dấu cắt, chỉ nhánh gặp lại chữ cũ mới bị cắt."""
    node = fake_decomp.tree("㐀")
    assert node.truncated is False


# -------------------------------------------------- ca biên 3: sâu quá 6 tầng
def test_ca_bien_sau_qua_sau_tang(fake_decomp):
    """Chuỗi tám tầng phải dừng ở tầng 6 và giữ nguyên phần đã dựng."""
    node = fake_decomp.tree("㐂")

    assert depth_of(node) == Decomposer.MAX_DEPTH == 6

    # Đi dọc nhánh trái xuống tầng 6.
    cur, duong_di = node, [node]
    while cur.children:
        cur = cur.children[0]
        duong_di.append(cur)
    assert len(duong_di) == 7                    # tầng 0 tới tầng 6
    assert cur.char == "㐈"
    assert cur.truncated is True                 # bị cắt vì chạm MAX_DEPTH
    assert cur.children == ()
    assert cur.ids == "⿰㐉一"                    # phần đã dựng vẫn còn nguyên
    assert all(n.truncated is False for n in duong_di[:-1])


# ---------------------------------------------------------------- radical_of
def test_radical_of_tra_ve_du_thong_tin(decomp):
    bo = decomp.radical_of("认")
    assert isinstance(bo, Radical)
    assert bo.idx == 149
    assert bo.glyph == "言"
    assert bo.strokes == 7


def test_radical_of_chu_khong_co_tra_ve_none(decomp):
    assert decomp.radical_of(PUA) is None


# ------------------------------------------------- FR-15 và FR-34, mức cơ bản
def test_same_radical_learned_cung_bo_va_ton_trong_limit(decomp, dict_db):
    ket_qua = decomp.same_radical_learned("认", limit=5)
    assert len(ket_qua) <= 5
    assert "认" not in ket_qua
    for ch in ket_qua:
        assert dict_db.get_char(ch).radical_idx == 149


def test_same_radical_learned_chu_khong_co_bo(decomp):
    assert decomp.same_radical_learned(PUA) == []


def test_radical_map_du_214_bo(decomp):
    ban_do = decomp.radical_map()
    assert len(ban_do) == 214
    assert [bo.idx for bo, _ in ban_do] == list(range(1, 215))
    assert all(isinstance(bo, Radical) and isinstance(n, int) for bo, n in ban_do)

    dem = dict((bo.idx, n) for bo, n in ban_do)
    assert dem[149] > 0
    assert sum(dem.values()) <= 9534          # tổng không vượt số chữ trong bảng char
