"""Chuyển lược đồ user.sqlite theo schema_version. Lược đồ ở mục 5.3 của đặc tả.

Bảng ``schema_version`` phải có ngay từ bản đầu tiên, nếu không thì lời hứa ở mục
4.3 — nâng cấp từ điển và ứng dụng mà không mất dữ liệu học tập — không thực hiện
được: không biết tệp đang ở bậc nào thì không biết phải chạy bước chuyển nào.

``upgrade`` chạy tuần tự từng bậc, nên bản sau chỉ cần thêm một hàm vào
``_CAC_BAC`` chứ không được sửa bậc đã phát hành: tệp của người dùng đang nằm ở
bậc cũ và phải đi qua đúng những bước mà bậc cũ đã đi. Bảng chỉ giữ ĐÚNG MỘT
dòng, ghi bậc hiện tại; nó là con trỏ trạng thái chứ không phải nhật ký.

Tầng data không import bất cứ thứ gì của Qt.
"""

import sqlite3
from datetime import datetime

SCHEMA_VERSION = 2

_TAO_BANG_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL
)
"""

# Bậc 1: toàn bộ lược đồ ban đầu, chép theo mục 5.3.
#
# Viết thành từng câu lệnh rời chứ không dùng executescript, vì executescript
# tự phát một lệnh COMMIT trước khi chạy và như vậy sẽ cắt đôi giao dịch bao
# quanh bước chuyển. Một bậc phải vào trọn gói hoặc không vào gì.
_BAC_1 = (
    """
    CREATE TABLE book (
        id           INTEGER PRIMARY KEY,
        title        TEXT NOT NULL,
        file_path    TEXT NOT NULL,
        file_hash    TEXT NOT NULL UNIQUE,   -- SHA-256, phát hiện nhập trùng
        page_count   INTEGER,
        page_offset  INTEGER,       -- lệch giữa số trang in và chỉ số trang PDF
        is_scanned   INTEGER,       -- 0 PDF số, 1 PDF scan, 2 hỗn hợp
        split_method TEXT,          -- 'outline' | 'toc' | 'llm' | 'heading' | 'manual'
        import_state TEXT NOT NULL, -- importing | review_bounds | extracting | review | ready
        imported_at  TEXT
    )
    """,
    """
    CREATE TABLE lesson (
        id         INTEGER PRIMARY KEY,
        book_id    INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
        index_no   INTEGER NOT NULL,  -- âm với mục ôn tập, xem QT-02 bước 3
        title      TEXT,
        page_start INTEGER NOT NULL,  -- chỉ số trang PDF, không phải số trang in
        page_end   INTEGER NOT NULL,
        confidence REAL,
        UNIQUE (book_id, index_no)
    )
    """,
    """
    CREATE TABLE lesson_word (
        id           INTEGER PRIMARY KEY,
        lesson_id    INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
        order_no     INTEGER,
        word         TEXT NOT NULL,
        pos          TEXT,
        pinyin_src   TEXT,
        hanviet_src  TEXT,     -- âm Hán-Việt in trong sách, xem QT-03 bước 3
        meaning_src  TEXT,
        source_page  INTEGER,
        extract_by   TEXT,     -- 'regex' | 'llm' | 'vision' | 'manual'
        needs_review INTEGER DEFAULT 0,
        UNIQUE (lesson_id, word)
    )
    """,
    """
    CREATE TABLE progress (
        word          TEXT PRIMARY KEY,
        status        TEXT NOT NULL DEFAULT 'new',  -- 'new' | 'learning' | 'known'
        ease          REAL DEFAULT 2.5,
        interval_days INTEGER DEFAULT 0,
        due_date      TEXT,
        review_count  INTEGER DEFAULT 0,
        lapse_count   INTEGER DEFAULT 0,
        -- Dòng lesson_word dùng làm mặt sau của thẻ ôn tập. CỐ Ý cho phép NULL:
        -- từ thêm thẳng từ màn hình Tra cứu không đi qua quyển sách nào.
        source_lw_id  INTEGER REFERENCES lesson_word(id) ON DELETE SET NULL,
        added_at      TEXT
    )
    """,
    """
    CREATE TABLE review_log (
        id              INTEGER PRIMARY KEY,
        word            TEXT NOT NULL REFERENCES progress(word) ON DELETE CASCADE,
        reviewed_at     TEXT NOT NULL,
        grade           INTEGER,   -- 0 quên, 1 khó, 2 nhớ, theo nút bấm
        q               INTEGER,   -- 2 | 3 | 5, thang SM-2, xem QT-04
        ease_after      REAL,
        interval_before INTEGER,
        interval_after  INTEGER
    )
    """,
    """
    CREATE TABLE explain_cache (
        key        TEXT PRIMARY KEY,  -- chữ đơn hoặc cả từ ghép, xem QT-05 bước 2
        payload    TEXT,              -- JSON kết quả đã kiểm chứng
        model      TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE setting (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """,
    "CREATE INDEX idx_lesson_book  ON lesson(book_id)",
    "CREATE INDEX idx_lw_lesson    ON lesson_word(lesson_id)",
    "CREATE INDEX idx_lw_word      ON lesson_word(word)",
    "CREATE INDEX idx_progress_due ON progress(due_date, status)",
    "CREATE INDEX idx_log_word     ON review_log(word)",
)


# Bậc 2: tách bậc lặp ra khỏi tổng số lần ôn.
#
# Bậc 1 chỉ có review_count và userdb buộc phải dùng chung cột đó cho cả hai con
# số, nhưng chúng khác nghĩa: repetition là số lần nhớ đúng LIÊN TIẾP, bị đặt về
# 0 mỗi lần người dùng bấm Quên (scheduler bước Quên), còn review_count là TỔNG
# số lần đánh giá, chỉ tăng theo QT-04 bước 5.
#
# ALTER TABLE ADD COLUMN chứ không dựng lại bảng: các tệp đã phát hành ở bậc 1
# đang mang dữ liệu học tập thật, và mục 4.3 hứa nâng cấp không mất dữ liệu.
# DEFAULT 0 điền sẵn cho mọi dòng cũ, đúng nghĩa "chưa có chuỗi nhớ đúng nào
# đang chạy"; đây là suy đoán an toàn nhất vì bậc 1 không lưu con số này ở đâu.
_BAC_2 = (
    "ALTER TABLE progress ADD COLUMN repetition INTEGER NOT NULL DEFAULT 0",
)


def _len_bac_1(conn: sqlite3.Connection) -> None:
    for cau_lenh in _BAC_1:
        conn.execute(cau_lenh)


def _len_bac_2(conn: sqlite3.Connection) -> None:
    for cau_lenh in _BAC_2:
        conn.execute(cau_lenh)


# Bậc n chạy khi tệp đang ở bậc n-1. Bản sau chỉ thêm một dòng vào đây.
_CAC_BAC = {
    1: _len_bac_1,
    2: _len_bac_2,
}


def current_version(conn: sqlite3.Connection) -> int:
    """Bậc lược đồ hiện tại của tệp. 0 nghĩa là tệp trống, chưa chạy bậc nào."""
    conn.execute(_TAO_BANG_VERSION)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return 0 if row is None or row[0] is None else int(row[0])


def upgrade(conn: sqlite3.Connection) -> int:
    """Đưa tệp lên SCHEMA_VERSION, chạy tuần tự từng bậc còn thiếu.

    Mỗi bậc nằm trong một giao dịch riêng cùng với dòng schema_version của nó,
    nên tệp không bao giờ dừng lại ở giữa một bậc. Trả về bậc sau khi chạy xong.
    """
    dang_o = current_version(conn)

    for bac in range(dang_o + 1, SCHEMA_VERSION + 1):
        conn.execute("BEGIN")
        try:
            _CAC_BAC[bac](conn)
            _ghi_version(conn, bac)
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")

    return SCHEMA_VERSION


def _ghi_version(conn: sqlite3.Connection, bac: int) -> None:
    """Thay dòng cũ bằng dòng mới: bảng luôn có đúng một dòng."""
    conn.execute("DELETE FROM schema_version")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
        (bac, datetime.now().isoformat(timespec="seconds")),
    )
