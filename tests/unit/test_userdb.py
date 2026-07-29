"""Kiểm thử data/migrate.py và data/userdb.py theo bảng hành vi của phiên 06.

Mỗi dòng trong bảng hành vi có ít nhất một test, đánh số trong tên hàm để đối
chiếu. Toàn bộ test dựng tệp thật trong ``tmp_path`` chứ không dùng cơ sở dữ
liệu trong bộ nhớ, vì hành vi số 3 là mở lại một tệp đã có.
"""

import sqlite3
from datetime import date, timedelta

import pytest

from hanzi_app.data import migrate
from hanzi_app.data.migrate import SCHEMA_VERSION
from hanzi_app.data.models import LessonBoundary, ReviewOutcome, VocabRow
from hanzi_app.data.userdb import UserDb
from hanzi_app.service.scheduler import apply_review

# Tám bảng của mục 5.3. Packet phiên 06 ghi "chín bảng"; đặc tả gốc chỉ định
# nghĩa tám. Xem phần ghi chú cuối phiên.
BANG_5_3 = {
    "schema_version",
    "book",
    "lesson",
    "lesson_word",
    "progress",
    "review_log",
    "explain_cache",
    "setting",
}

CHI_MUC_5_3 = {
    "idx_lesson_book",
    "idx_lw_lesson",
    "idx_lw_word",
    "idx_progress_due",
    "idx_log_word",
}

HOM_NAY = date(2026, 7, 27)


# ------------------------------------------------------------------ tiện ích
@pytest.fixture
def duong_dan(tmp_path):
    return str(tmp_path / "user.sqlite")


@pytest.fixture
def db(duong_dan):
    """Một UserDb mở trên tệp tạm, đóng lại sau mỗi test."""
    u = UserDb(duong_dan)
    yield u
    u.close()


def doc_ten(duong_dan: str, loai: str) -> set[str]:
    """Tên bảng hoặc tên chỉ mục trong tệp, đọc bằng một kết nối riêng.

    Kết nối riêng để chắc chắn dữ liệu đã nằm trong tệp chứ không phải chỉ nằm
    trong bộ nhớ của kết nối đang mở. Bỏ các đối tượng sqlite_* do SQLite tự
    sinh, ví dụ chỉ mục ngầm của ràng buộc UNIQUE.
    """
    conn = sqlite3.connect(duong_dan)
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ?", (loai,)
            )
            if not row[0].startswith("sqlite_")
        }
    finally:
        conn.close()


def doc_schema_version(duong_dan: str) -> list[tuple]:
    conn = sqlite3.connect(duong_dan)
    try:
        return list(conn.execute("SELECT version, applied_at FROM schema_version"))
    finally:
        conn.close()


def outcome(
    due: date,
    *,
    status: str = "new",
    ease: float = 2.5,
    interval_days: int = 0,
    repetition: int = 0,
    lapse_count: int = 0,
) -> ReviewOutcome:
    return ReviewOutcome(
        ease=ease,
        interval_days=interval_days,
        repetition=repetition,
        lapse_count=lapse_count,
        status=status,
        due_date=due,
    )


def bound(index_no: int, page_start: int, page_end: int, **kw) -> LessonBoundary:
    return LessonBoundary(
        index_no=index_no,
        title=kw.get("title", f"Bài {index_no}"),
        page_start=page_start,
        page_end=page_end,
        confidence=kw.get("confidence", 0.9),
        kind=kw.get("kind", "lesson"),
    )


def vocab(word: str, order_no: int = 1, **kw) -> VocabRow:
    return VocabRow(
        order_no=order_no,
        word=word,
        pinyin_src=kw.get("pinyin_src", "rènshi"),
        pos=kw.get("pos", "动"),
        meaning_src=kw.get("meaning_src", "quen biết"),
        source_page=kw.get("source_page", 12),
        extract_by=kw.get("extract_by", "regex"),
        needs_review=kw.get("needs_review", False),
        review_reason=kw.get("review_reason", None),
    )


def them_sach(db: UserDb, title: str, file_hash: str) -> int:
    return db.add_book(
        title=title,
        file_path=f"C:/sach/{file_hash}.pdf",
        file_hash=file_hash,
        page_count=200,
    )


@pytest.fixture
def hai_lw(db):
    """Hai dòng lesson_word THẬT ở hai quyển khác nhau, trả về id của chúng.

    progress.source_lw_id là khoá ngoại trỏ tới lesson_word, mà khoá ngoại đang
    bật, nên các test upsert phải dùng id có thật chứ không bịa số.
    """
    ids = []
    for i, (ten, bam) in enumerate([("Quyển A", "hash-a"), ("Quyển B", "hash-b")]):
        book_id = them_sach(db, ten, bam)
        db.replace_lessons(book_id, [bound(1, 0, 9)])
        lesson_id = db._conn.execute(
            "SELECT id FROM lesson WHERE book_id = ?", (book_id,)
        ).fetchone()[0]
        db.replace_vocab(lesson_id, [vocab("认识", meaning_src=f"nghĩa quyển {i}")])
        ids.append(
            db._conn.execute(
                "SELECT id FROM lesson_word WHERE lesson_id = ?", (lesson_id,)
            ).fetchone()[0]
        )
    return tuple(ids)


# ----------------------------------------------------- 1: dựng lược đồ đầy đủ
def test_01_mo_tren_duong_dan_chua_ton_tai_tao_du_bang_va_chi_muc(duong_dan, tmp_path):
    assert not (tmp_path / "user.sqlite").exists()

    u = UserDb(duong_dan)
    u.close()

    assert (tmp_path / "user.sqlite").exists()
    assert doc_ten(duong_dan, "table") == BANG_5_3
    assert doc_ten(duong_dan, "index") == CHI_MUC_5_3


# ------------------------------------------------ 2: schema_version đúng 1 dòng
def test_02_schema_version_co_dung_mot_dong_version_hien_tai(db, duong_dan):
    # Phiên 06 viết `== 1 ==` vì lúc đó lược đồ mới có một bậc. Phiên bảo trì
    # 06b thêm bậc 2, nên con số chốt ở đây đổi theo; bảng vẫn phải đúng một dòng.
    dong = doc_schema_version(duong_dan)
    assert len(dong) == 1
    assert dong[0][0] == 2 == SCHEMA_VERSION
    assert dong[0][1]          # applied_at không rỗng


# ------------------------------------------------------- 3: mở lại tệp đã có
def test_03_mo_lai_khong_tao_trung_bang(duong_dan):
    UserDb(duong_dan).close()
    bang_lan_dau = doc_ten(duong_dan, "table")

    u = UserDb(duong_dan)      # lần hai trên đúng tệp đó
    u.close()

    assert doc_ten(duong_dan, "table") == bang_lan_dau == BANG_5_3
    assert doc_ten(duong_dan, "index") == CHI_MUC_5_3
    assert len(doc_schema_version(duong_dan)) == 1


def test_03b_mo_lai_giu_nguyen_du_lieu(duong_dan):
    u = UserDb(duong_dan)
    book_id = them_sach(u, "Giáo trình Hán ngữ 1", "hash-a")
    u.close()

    u2 = UserDb(duong_dan)
    try:
        assert u2.find_book_by_hash("hash-a") == book_id
    finally:
        u2.close()


# --------------------------------------------------------- 4: pragma khoá ngoại
def test_04_pragma_foreign_keys_bang_1(db):
    # Pragma đặt theo từng kết nối chứ không lưu vào tệp, nên phải kiểm trên
    # đúng kết nối mà UserDb đang dùng.
    assert db._conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_04b_journal_mode_la_wal(db):
    assert db._conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


# --------------------------------------------- 5: khoá ngoại chặn book_id lạ
def test_05_chen_lesson_voi_book_id_khong_ton_tai_nem_integrityerror(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_lessons(999, [bound(1, 0, 9)])


# ------------------------------------------------------------- 6: cascade thật
def test_06_xoa_book_thi_lesson_bien_mat_theo(db):
    book_id = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9), bound(2, 10, 19)])
    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 2

    with db.transaction() as conn:
        conn.execute("DELETE FROM book WHERE id = ?", (book_id,))

    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 0


def test_06b_xoa_book_cascade_xuong_ca_lesson_word(db):
    book_id = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9)])
    lesson_id = db._conn.execute("SELECT id FROM lesson").fetchone()[0]
    db.replace_vocab(lesson_id, [vocab("认识"), vocab("你好", 2)])

    with db.transaction() as conn:
        conn.execute("DELETE FROM book WHERE id = ?", (book_id,))

    assert db._conn.execute("SELECT COUNT(*) FROM lesson_word").fetchone()[0] == 0


# -------------------------------------------------------- 7 và 8: bảng book
def test_07_find_book_by_hash_chua_co_tra_none(db):
    assert db.find_book_by_hash("chua-co-hash-nay") is None


def test_08_add_book_hai_lan_cung_hash_nem_integrityerror(db):
    them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    with pytest.raises(sqlite3.IntegrityError):
        them_sach(db, "Một quyển khác cùng nội dung", "hash-a")


def test_08b_add_book_tra_id_va_trang_thai_importing(db):
    book_id = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    assert isinstance(book_id, int)
    assert db.find_book_by_hash("hash-a") == book_id

    trang_thai = db._conn.execute(
        "SELECT import_state FROM book WHERE id = ?", (book_id,)
    ).fetchone()[0]
    assert trang_thai == "importing"

    db.set_import_state(book_id, "ready")
    trang_thai = db._conn.execute(
        "SELECT import_state FROM book WHERE id = ?", (book_id,)
    ).fetchone()[0]
    assert trang_thai == "ready"


# ------------------------------------------------ 9, 10, 11: upsert_progress
def test_09_upsert_lan_dau_tao_dong_voi_source_lw_id(db, hai_lw):
    lw_dau, _ = hai_lw
    db.upsert_progress("认识", outcome(HOM_NAY), source_lw_id=lw_dau)

    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word = ?", ("认识",)
    ).fetchone()[0] == lw_dau

    ghi = db.get_progress("认识")
    assert ghi == outcome(HOM_NAY)


def test_10_upsert_lan_hai_khong_ghi_de_source_lw_id(db, hai_lw):
    lw_dau, lw_sau = hai_lw
    db.upsert_progress("认识", outcome(HOM_NAY), source_lw_id=lw_dau)

    sau = outcome(
        HOM_NAY + timedelta(days=6),
        status="learning",
        ease=2.6,
        interval_days=6,
        repetition=2,
    )
    db.upsert_progress("认识", sau, source_lw_id=lw_sau)

    # Tiến độ cập nhật...
    assert db.get_progress("认识") == sau
    # ...nhưng mặt sau của thẻ vẫn trỏ về quyển gặp lần đầu (QT-04 bước 2).
    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word = ?", ("认识",)
    ).fetchone()[0] == lw_dau


def test_10b_source_lw_id_ao_bi_khoa_ngoai_chan(db):
    # Không có dòng lesson_word nào, nên id 7 là số bịa.
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_progress("认识", outcome(HOM_NAY), source_lw_id=7)


def test_11_upsert_voi_source_lw_id_none_tren_tu_moi(db):
    # Thêm từ thẳng từ màn hình Tra cứu, không qua sách.
    db.upsert_progress("你好", outcome(HOM_NAY), source_lw_id=None)

    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word = ?", ("你好",)
    ).fetchone()[0] is None
    assert db.get_progress("你好") is not None


def test_11b_source_lw_id_none_roi_sau_do_co_thi_duoc_dien_vao(db, hai_lw):
    lw_dau, _ = hai_lw
    db.upsert_progress("你好", outcome(HOM_NAY), source_lw_id=None)
    db.upsert_progress("你好", outcome(HOM_NAY), source_lw_id=lw_dau)

    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word = ?", ("你好",)
    ).fetchone()[0] == lw_dau


def test_11c_get_progress_tu_chua_hoc_tra_none(db):
    assert db.get_progress("认识") is None


# ------------------------------------------------------------- 12: due_words
def test_12_due_words_chi_tra_tu_den_han_va_ton_trong_limit(db):
    db.upsert_progress("昨天", outcome(HOM_NAY - timedelta(days=1)), None)
    db.upsert_progress("今天", outcome(HOM_NAY), None)
    db.upsert_progress("明天", outcome(HOM_NAY + timedelta(days=1)), None)

    assert db.due_words(HOM_NAY) == ["昨天", "今天"]
    assert db.due_words(HOM_NAY, limit=1) == ["昨天"]
    assert db.due_words(HOM_NAY - timedelta(days=2)) == []


# --------------------------------------------- 07: hai số ở chân thanh điều hướng
# QT-04 bước 6 gọi hai con số bằng hai tên khác nhau: "đang theo dõi" là số dòng
# progress, "đã thuộc" là số dòng status='known'. Không được trộn hai số này.


def test_progress_counts_kho_rong_tra_khong_khong(db):
    assert db.progress_counts() == (0, 0)


def test_progress_counts_ba_dong_trong_do_mot_dong_known(db):
    db.upsert_progress("认识", outcome(HOM_NAY, status="new"), None)
    db.upsert_progress("你好", outcome(HOM_NAY, status="learning"), None)
    db.upsert_progress("老师", outcome(HOM_NAY, status="known"), None)

    assert db.progress_counts() == (3, 1)


# ---------------------------------------------------------- 13: learned_chars
def test_13_learned_chars_tach_tung_tu_thanh_chu_roi(db):
    db.upsert_progress("认识", outcome(HOM_NAY), None)
    db.upsert_progress("你好", outcome(HOM_NAY), None)

    assert db.learned_chars() == {"认", "识", "你", "好"}


def test_13b_learned_chars_khi_chua_hoc_gi(db):
    assert db.learned_chars() == set()


# ------------------------------------------------- 14: thay thế trọn gói
def test_14_replace_lessons_lan_hai_ngan_hon_khong_con_dong_thua(db):
    book_id = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    db.replace_lessons(book_id, [bound(i, i * 10, i * 10 + 9) for i in (1, 2, 3)])
    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 3

    db.replace_lessons(book_id, [bound(1, 0, 19)])

    dong = list(db._conn.execute("SELECT index_no, page_start, page_end FROM lesson"))
    assert len(dong) == 1
    assert tuple(dong[0]) == (1, 0, 19)


def test_14b_replace_lessons_chi_dung_toi_sach_duoc_chi_dinh(db):
    a = them_sach(db, "Quyển A", "hash-a")
    b = them_sach(db, "Quyển B", "hash-b")
    db.replace_lessons(a, [bound(1, 0, 9)])
    db.replace_lessons(b, [bound(1, 0, 9), bound(2, 10, 19)])

    db.replace_lessons(a, [])

    con_lai = db._conn.execute(
        "SELECT COUNT(*) FROM lesson WHERE book_id = ?", (b,)
    ).fetchone()[0]
    assert con_lai == 2
    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 2


def test_14c_replace_vocab_thay_tron_goi(db):
    book_id = them_sach(db, "Quyển A", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9)])
    lesson_id = db._conn.execute("SELECT id FROM lesson").fetchone()[0]

    db.replace_vocab(lesson_id, [vocab("认识", 1), vocab("你好", 2), vocab("老师", 3)])
    assert db._conn.execute("SELECT COUNT(*) FROM lesson_word").fetchone()[0] == 3

    db.replace_vocab(lesson_id, [vocab("认识", 1)])

    tu = [r[0] for r in db._conn.execute("SELECT word FROM lesson_word")]
    assert tu == ["认识"]


def test_14d_replace_vocab_giu_du_cac_cot_lay_tu_sach(db):
    book_id = them_sach(db, "Quyển A", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9)])
    lesson_id = db._conn.execute("SELECT id FROM lesson").fetchone()[0]

    db.replace_vocab(
        lesson_id,
        [
            vocab(
                "认识",
                order_no=4,
                pinyin_src="rèn shi",
                pos="动",
                meaning_src="quen biết, làm quen",
                source_page=31,
                extract_by="llm",
                needs_review=True,
                review_reason="pinyin không khớp từ điển",
            )
        ],
    )

    row = db._conn.execute(
        "SELECT order_no, word, pos, pinyin_src, meaning_src, source_page, "
        "       extract_by, needs_review FROM lesson_word"
    ).fetchone()
    assert tuple(row) == (4, "认识", "动", "rèn shi", "quen biết, làm quen", 31, "llm", 1)


def test_delete_book(db):
    book_id = them_sach(db, "Quyển Cần Xoá", "hash-delete")
    db.replace_lessons(book_id, [bound(1, 0, 9)])
    lesson_id = db._conn.execute("SELECT id FROM lesson WHERE book_id = ?", (book_id,)).fetchone()[0]
    db.replace_vocab(lesson_id, [vocab("你好", 1)])

    assert len(db.get_books()) == 1
    db.delete_book(book_id)

    assert len(db.get_books()) == 0
    assert db._conn.execute("SELECT COUNT(*) FROM lesson WHERE book_id = ?", (book_id,)).fetchone()[0] == 0
    assert db._conn.execute("SELECT COUNT(*) FROM lesson_word WHERE lesson_id = ?", (lesson_id,)).fetchone()[0] == 0


# --------------------------------------------------------- 15: giao dịch
def test_15_loi_giua_chung_transaction_huy_toan_bo(db):
    book_id = them_sach(db, "Quyển A", "hash-a")

    class LoiCoY(Exception):
        pass

    with pytest.raises(LoiCoY):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO lesson (book_id, index_no, page_start, page_end) "
                "VALUES (?, 1, 0, 9)",
                (book_id,),
            )
            conn.execute(
                "INSERT INTO lesson (book_id, index_no, page_start, page_end) "
                "VALUES (?, 2, 10, 19)",
                (book_id,),
            )
            raise LoiCoY("hỏng giữa chừng")

    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 0


def test_15b_replace_lessons_hong_giua_chung_khong_de_lai_nua_voi(db):
    book_id = them_sach(db, "Quyển A", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9), bound(2, 10, 19)])

    # Hai bài trùng index_no vi phạm UNIQUE (book_id, index_no): lệnh xoá ở đầu
    # replace_lessons phải bị huỷ theo, hai bài cũ còn nguyên.
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_lessons(book_id, [bound(5, 0, 9), bound(5, 10, 19)])

    assert db._conn.execute("SELECT COUNT(*) FROM lesson").fetchone()[0] == 2


def test_15c_replace_vocab_many_loi_bai_sau_huy_ca_bai_truoc(db):
    book_id = them_sach(db, "Quyển A", "hash-a")
    db.replace_lessons(book_id, [bound(1, 0, 9), bound(2, 10, 19)])
    lessons = db.get_lessons(book_id)
    first_id = lessons[0]["id"]
    second_id = lessons[1]["id"]
    db.replace_vocab(first_id, [vocab("旧一")])
    db.replace_vocab(second_id, [vocab("旧二")])

    with pytest.raises(sqlite3.IntegrityError):
        db.replace_vocab_many(
            {
                first_id: [vocab("新一")],
                999_999: [vocab("无效")],
            }
        )

    assert [row["word"] for row in db.get_lesson_words(first_id)] == ["旧一"]
    assert [row["word"] for row in db.get_lesson_words(second_id)] == ["旧二"]


# ------------------------------------------------------------ 16: word_source
def test_16_word_source_tra_lan_gap_dau_tien(db):
    a = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    b = them_sach(db, "Quyển thứ hai", "hash-b")
    db.replace_lessons(a, [bound(3, 20, 29, title="你叫什么名字")])
    db.replace_lessons(b, [bound(1, 0, 9, title="Bài mở đầu")])
    lesson_a, lesson_b = (r[0] for r in db._conn.execute("SELECT id FROM lesson ORDER BY id"))

    db.replace_vocab(lesson_a, [vocab("认识", meaning_src="quen biết, làm quen")])
    db.replace_vocab(lesson_b, [vocab("认识", meaning_src="nhận ra")])

    nguon = db.word_source("认识")
    assert nguon is not None
    assert nguon.book_title == "Giáo trình Hán ngữ 1"
    assert nguon.lesson_no == 3
    assert nguon.lesson_title == "你叫什么名字"
    assert nguon.meaning_src == "quen biết, làm quen"
    assert nguon.page == 12


def test_16b_word_source_on_dinh_khi_nhap_lai_quyen_sau(db):
    a = them_sach(db, "Giáo trình Hán ngữ 1", "hash-a")
    b = them_sach(db, "Quyển thứ hai", "hash-b")
    db.replace_lessons(a, [bound(1, 0, 9)])
    db.replace_lessons(b, [bound(1, 0, 9)])
    lesson_a, lesson_b = (r[0] for r in db._conn.execute("SELECT id FROM lesson ORDER BY id"))
    db.replace_vocab(lesson_a, [vocab("认识", meaning_src="nghĩa của quyển A")])
    db.replace_vocab(lesson_b, [vocab("认识", meaning_src="nghĩa của quyển B")])

    # Nhập lại quyển B sinh dòng lesson_word có id mới, lớn hơn id của quyển A.
    db.replace_vocab(lesson_b, [vocab("认识", meaning_src="nghĩa của quyển B")])

    assert db.word_source("认识").meaning_src == "nghĩa của quyển A"


def test_16c_word_source_tu_chua_co_trong_sach_nao_tra_none(db):
    assert db.word_source("认识") is None


# ------------------------------------------------- ngoài bảng: log và cache
def test_log_review_ghi_mot_dong(db):
    truoc = outcome(HOM_NAY, status="learning", interval_days=6, repetition=2)
    sau = outcome(
        HOM_NAY + timedelta(days=17),
        status="learning",
        ease=2.6,
        interval_days=17,
        repetition=3,
    )
    db.upsert_progress("认识", truoc, None)
    db.log_review("认识", grade=2, q=5, before=truoc, after=sau)

    row = db._conn.execute(
        "SELECT word, grade, q, ease_after, interval_before, interval_after "
        "FROM review_log"
    ).fetchone()
    assert tuple(row) == ("认识", 2, 5, 2.6, 6, 17)


def test_log_review_cascade_khi_xoa_progress(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)
    db.log_review("认识", grade=2, q=5, before=o, after=o)

    with db.transaction() as conn:
        conn.execute("DELETE FROM progress WHERE word = ?", ("认识",))

    assert db._conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 0


# --------------------------- 06b: repetition tách khỏi review_count
# repetition là số lần nhớ đúng LIÊN TIẾP, scheduler đặt về 0 mỗi lần bấm Quên.
# review_count là TỔNG số lần ôn, QT-04 bước 5 chỉ cho tăng. Bậc 1 chỉ có một
# cột nên phiên 06 phải dồn cả hai vào đó; bậc 2 tách ra.


def tao_tep_bac_1(duong_dan: str) -> None:
    """Dựng một tệp đúng như bản phát hành ở bậc 1, chưa có cột repetition.

    Gọi thẳng bước chuyển của bậc 1 thay vì chép lại lược đồ vào test: tệp thật
    của người dùng sinh ra bằng đúng những câu lệnh đó, chép lại thì bản sao sẽ
    trôi khỏi bản gốc.
    """
    conn = sqlite3.connect(duong_dan, isolation_level=None)
    try:
        conn.execute(migrate._TAO_BANG_VERSION)
        conn.execute("BEGIN")
        migrate._len_bac_1(conn)
        migrate._ghi_version(conn, 1)
        conn.execute("COMMIT")
    finally:
        conn.close()


def test_06b_a_nang_tep_bac_1_dang_co_du_lieu_len_bac_2(duong_dan):
    tao_tep_bac_1(duong_dan)
    conn = sqlite3.connect(duong_dan, isolation_level=None)
    try:
        assert "repetition" not in {r[1] for r in conn.execute("PRAGMA table_info(progress)")}
        conn.execute(
            "INSERT INTO progress (word, status, ease, interval_days, due_date, "
            "                      review_count, lapse_count, added_at) "
            "VALUES ('认识', 'learning', 2.6, 6, '2026-07-27', 4, 1, '2026-07-01T08:00:00')"
        )
    finally:
        conn.close()

    u = UserDb(duong_dan)          # mở lên là tự chạy bậc 2
    try:
        assert u._conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0] == 1
        row = u._conn.execute(
            "SELECT status, ease, interval_days, due_date, review_count, "
            "       lapse_count, repetition FROM progress WHERE word = ?",
            ("认识",),
        ).fetchone()
        # Dòng cũ còn nguyên từng cột, cột mới điền mặc định 0.
        assert tuple(row) == ("learning", 2.6, 6, "2026-07-27", 4, 1, 0)
    finally:
        u.close()

    assert doc_ten(duong_dan, "table") == BANG_5_3
    assert doc_ten(duong_dan, "index") == CHI_MUC_5_3


def test_06b_b_upsert_ghi_repetition_va_get_doc_lai_dung(db):
    db.upsert_progress("认识", outcome(HOM_NAY, repetition=3), None)

    assert db.get_progress("认识").repetition == 3
    assert db._conn.execute(
        "SELECT repetition FROM progress WHERE word = ?", ("认识",)
    ).fetchone()[0] == 3


def test_06b_c_upsert_khong_dung_toi_review_count(db):
    db.upsert_progress("认识", outcome(HOM_NAY, repetition=4), None)
    with db.transaction() as conn:
        conn.execute("UPDATE progress SET review_count = 5 WHERE word = ?", ("认识",))

    # Người dùng bấm Quên: scheduler trả repetition về 0. Tổng số lần ôn không
    # được rơi theo.
    db.upsert_progress("认识", outcome(HOM_NAY, repetition=0), None)

    row = db._conn.execute(
        "SELECT review_count, repetition FROM progress WHERE word = ?", ("认识",)
    ).fetchone()
    assert tuple(row) == (5, 0)


def test_06b_c2_dong_moi_bat_dau_voi_review_count_bang_0(db):
    db.upsert_progress("你好", outcome(HOM_NAY, repetition=2), None)

    assert db._conn.execute(
        "SELECT review_count FROM progress WHERE word = ?", ("你好",)
    ).fetchone()[0] == 0


def test_06b_d_log_review_tang_review_count_dung_mot_moi_lan(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)

    for _ in range(3):
        db.log_review("认识", grade=2, q=5, before=o, after=o)

    assert db._conn.execute(
        "SELECT review_count FROM progress WHERE word = ?", ("认识",)
    ).fetchone()[0] == 3
    # Số dòng nhật ký và tổng số lần ôn phải khớp nhau.
    assert db._conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 3


def test_06b_d2_log_review_khong_dung_toi_repetition(db):
    db.upsert_progress("认识", outcome(HOM_NAY, repetition=2), None)
    o = db.get_progress("认识")
    db.log_review("认识", grade=2, q=5, before=o, after=o)

    assert db.get_progress("认识").repetition == 2


def test_06b_e_schema_version_sau_khi_nang_cap_dung_mot_dong_bang_2(duong_dan):
    tao_tep_bac_1(duong_dan)
    assert doc_schema_version(duong_dan)[0][0] == 1

    UserDb(duong_dan).close()

    dong = doc_schema_version(duong_dan)
    assert len(dong) == 1
    assert dong[0][0] == 2 == SCHEMA_VERSION


# ------------------------------- 08a: hoàn tác lần tự đánh giá gần nhất
# Bảng đáp án ở handoff/08a-on-tap-du-lieu.md, ca 1 tới 9. Trạng thái cũ do
# người gọi đưa vào chứ không dựng lại từ nhật ký, xem docstring undo_review.


def mot_lan_on(db: UserDb, word: str, truoc: ReviewOutcome, grade: int = 2):
    """Một lần tự đánh giá đầy đủ: tính bằng scheduler, ghi tiến độ, ghi nhật ký.

    Đi qua đúng đường mà màn hình Ôn tập đi, để cái được hoàn tác là trạng thái
    thật chứ không phải một bộ số bịa ra trong test.
    """
    sau = apply_review(truoc, grade, HOM_NAY)
    db.upsert_progress(word, sau, None)
    db.log_review(word, grade=grade, q=5, before=truoc, after=sau)
    return sau


def dem_log(db: UserDb, word: str) -> int:
    return db._conn.execute(
        "SELECT COUNT(*) FROM review_log WHERE word = ?", (word,)
    ).fetchone()[0]


def id_log(db: UserDb, word: str) -> list[int]:
    return [
        r[0]
        for r in db._conn.execute(
            "SELECT id FROM review_log WHERE word = ? ORDER BY id", (word,)
        )
    ]


def review_count(db: UserDb, word: str) -> int:
    return db._conn.execute(
        "SELECT review_count FROM progress WHERE word = ?", (word,)
    ).fetchone()[0]


def test_08a_01_undo_khoi_phuc_progress_ve_dung_trang_thai_truoc(db):
    truoc = outcome(
        HOM_NAY, status="learning", ease=2.6, interval_days=6, repetition=2,
        lapse_count=1,
    )
    db.upsert_progress("认识", truoc, None)
    sau = mot_lan_on(db, "认识", truoc)
    assert db.get_progress("认识") == sau != truoc      # lần ôn có đổi thật

    db.undo_review("认识", truoc)

    assert db.get_progress("认识") == truoc


def test_08a_02_undo_xoa_dung_mot_dong_nhat_ky(db):
    truoc = outcome(HOM_NAY, status="learning", interval_days=6, repetition=2)
    db.upsert_progress("认识", truoc, None)
    mot_lan_on(db, "认识", truoc)
    assert dem_log(db, "认识") == 1

    db.undo_review("认识", truoc)

    assert dem_log(db, "认识") == 0


def test_08a_03_va_04_undo_mot_lan_chi_xoa_dong_moi_nhat(db):
    hien_tai = outcome(HOM_NAY)
    db.upsert_progress("认识", hien_tai, None)
    truoc_lan_cuoi = None
    for _ in range(3):
        truoc_lan_cuoi = hien_tai
        hien_tai = mot_lan_on(db, "认识", hien_tai)
    ba_id = id_log(db, "认识")
    assert len(ba_id) == 3

    db.undo_review("认识", truoc_lan_cuoi)

    # Còn đúng hai dòng, và là hai dòng CŨ chứ không phải hai dòng bất kỳ.
    assert id_log(db, "认识") == ba_id[:2]


def test_08a_04b_dong_moi_nhat_tinh_theo_reviewed_at_chu_khong_theo_id(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)
    for _ in range(3):
        db.log_review("认识", grade=2, q=5, before=o, after=o)
    a, b, c = id_log(db, "认识")
    # Dòng id giữa được đặt thành mốc muộn nhất: nếu ai đó bỏ reviewed_at khỏi
    # ORDER BY thì test này đỏ vì dòng c bị xoá oan.
    with db.transaction() as conn:
        conn.execute("UPDATE review_log SET reviewed_at = ? WHERE id = ?",
                     ("2026-07-27T08:00:00", a))
        conn.execute("UPDATE review_log SET reviewed_at = ? WHERE id = ?",
                     ("2026-07-27T10:00:00", b))
        conn.execute("UPDATE review_log SET reviewed_at = ? WHERE id = ?",
                     ("2026-07-27T09:00:00", c))

    db.undo_review("认识", o)

    assert id_log(db, "认识") == [a, c]


def test_08a_05_undo_tu_a_khong_dung_toi_nhat_ky_cua_tu_b(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)
    db.upsert_progress("你好", o, None)
    for _ in range(2):
        mot_lan_on(db, "认识", o)
        mot_lan_on(db, "你好", o)
    id_b = id_log(db, "你好")

    db.undo_review("认识", o)

    assert dem_log(db, "认识") == 1
    assert id_log(db, "你好") == id_b
    assert review_count(db, "你好") == 2


def test_08a_06_undo_giam_review_count_di_mot(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)
    for _ in range(3):
        mot_lan_on(db, "认识", o)
    assert review_count(db, "认识") == 3

    db.undo_review("认识", o)

    assert review_count(db, "认识") == 2


def test_08a_07_review_count_dang_bang_0_thi_undo_khong_lam_no_am(db):
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, None)
    assert review_count(db, "认识") == 0

    db.undo_review("认识", o)          # không được ném lỗi

    assert review_count(db, "认识") == 0


def test_08a_08_tu_chua_tung_co_dong_nhat_ky_van_khoi_phuc_duoc_progress(db):
    truoc = outcome(HOM_NAY, status="learning", ease=2.6, interval_days=6,
                    repetition=2, lapse_count=1)
    db.upsert_progress("认识", outcome(HOM_NAY + timedelta(days=17)), None)
    assert dem_log(db, "认识") == 0

    db.undo_review("认识", truoc)

    assert db.get_progress("认识") == truoc


def test_08a_09_undo_giu_nguyen_source_lw_id(db, hai_lw):
    lw_dau, _ = hai_lw
    o = outcome(HOM_NAY)
    db.upsert_progress("认识", o, source_lw_id=lw_dau)
    sau = mot_lan_on(db, "认识", o)
    assert sau != o

    db.undo_review("认识", o)

    assert db._conn.execute(
        "SELECT source_lw_id FROM progress WHERE word = ?", ("认识",)
    ).fetchone()[0] == lw_dau


def test_cache_get_chua_co_tra_none(db):
    assert db.cache_get("认") is None


def test_cache_put_roi_get_tra_dung_payload(db):
    payload = {"bo_thu": "言", "dien_giai": "bộ ngôn nói về lời nói"}
    db.cache_put("认", payload, model="claude-opus-5")

    assert db.cache_get("认") == payload
    assert db._conn.execute(
        "SELECT model FROM explain_cache WHERE key = ?", ("认",)
    ).fetchone()[0] == "claude-opus-5"


def test_cache_put_hai_lan_cung_khoa_thi_ghi_de(db):
    db.cache_put("认", {"v": 1}, model="m1")
    db.cache_put("认", {"v": 2}, model="m2")

    assert db.cache_get("认") == {"v": 2}
    assert db._conn.execute("SELECT COUNT(*) FROM explain_cache").fetchone()[0] == 1
