"""Truy cập user.sqlite, đọc ghi, quản lý giao dịch. Lược đồ ở mục 5.3, chữ ký
phương thức ở mục 13.4 của đặc tả.

Tệp này thay thế trọn bản tối thiểu dựng tạm ở phiên giao diện Tra cứu; hai
phương thức ``word_source`` và ``get_progress`` giữ nguyên chữ ký nên
LookupService.detail() không phải sửa gì.

Hai điều bắt buộc khi mở kết nối, ghi ở cuối mục 5.3:

- ``PRAGMA foreign_keys = ON``. SQLite mặc định TẮT khoá ngoại và KHÔNG báo lỗi
  khi thiếu, nên mọi ON DELETE CASCADE trong lược đồ sẽ im lặng không chạy. Sai
  sót chỉ lộ ra rất muộn dưới dạng dữ liệu rác. Pragma này đặt theo từng KẾT NỐI
  chứ không lưu vào tệp, nên nó phải nằm ở đây chứ không nằm trong migrate.
- ``PRAGMA journal_mode = WAL``, để luồng nền nhập PDF ghi song song được với
  giao diện đang đọc.

Tầng data không import bất cứ thứ gì của Qt và không gọi sang tầng service.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from hanzi_app.data import migrate
from hanzi_app.data.models import LessonBoundary, ReviewOutcome, VocabRow, WordSource


def _bay_gio() -> str:
    return datetime.now().isoformat(timespec="seconds")


class UserDb:
    """Dữ liệu học tập của người dùng: sách đã nhập, từ mới, tiến độ ôn tập."""

    def __init__(self, path: str) -> None:
        self.path = path
        # isolation_level=None tắt phần quản lý giao dịch ngầm của sqlite3: mọi
        # lệnh tự vào thẳng tệp, còn ranh giới giao dịch do transaction() đặt
        # tường minh. Không có nó thì sqlite3 tự mở giao dịch quanh các lệnh ghi
        # và hai lớp quản lý sẽ giẫm lên nhau.
        self._conn = sqlite3.connect(path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._depth = 0
        migrate.upgrade(self._conn)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------- giao dịch
    @contextmanager
    def transaction(self):
        """Bao một cụm thao tác ghi. Ném lỗi ở giữa thì cả cụm bị huỷ.

        Cài bằng SAVEPOINT chứ không phải BEGIN để lồng được: các phương thức
        ghi bên dưới đều tự bọc mình trong transaction(), mà người gọi vẫn có
        quyền gộp nhiều phương thức vào một giao dịch lớn hơn. SAVEPOINT ngoài
        cùng tự mở giao dịch, nên trường hợp không lồng vẫn đúng.
        """
        ten = f"sp{self._depth}"
        self._conn.execute(f"SAVEPOINT {ten}")
        self._depth += 1
        try:
            yield self._conn
        except Exception:
            self._conn.execute(f"ROLLBACK TO {ten}")
            self._conn.execute(f"RELEASE {ten}")
            self._depth -= 1
            raise
        self._conn.execute(f"RELEASE {ten}")
        self._depth -= 1

    # ------------------------------------------------------------------ sách
    def add_book(
        self,
        title: str,
        file_path: str,
        file_hash: str,
        page_count: int | None = None,
        page_offset: int | None = None,
        is_scanned: int | None = None,
        split_method: str | None = None,
    ) -> int:
        """Ghi một quyển mới, trả về id.

        Trạng thái ban đầu luôn là 'importing': chỉ 'ready' mới hiện trong thư
        viện, nên một lần nhập hỏng giữa chừng không để lại quyển sách dở dang.
        Cột file_hash là UNIQUE, nhập trùng ném sqlite3.IntegrityError.
        """
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO book (title, file_path, file_hash, page_count, "
                "                  page_offset, is_scanned, split_method, "
                "                  import_state, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'importing', ?)",
                (
                    title,
                    file_path,
                    file_hash,
                    page_count,
                    page_offset,
                    is_scanned,
                    split_method,
                    _bay_gio(),
                ),
            )
            return int(cur.lastrowid)

    def find_book_by_hash(self, file_hash: str) -> int | None:
        row = self._conn.execute(
            "SELECT id FROM book WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return None if row is None else int(row["id"])

    def set_import_state(self, book_id: int, state: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE book SET import_state = ? WHERE id = ?", (state, book_id)
            )

    def get_books(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, title, file_path, page_count, import_state FROM book ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_book(self, book_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT id, title, file_path, page_count, import_state "
            "FROM book WHERE id = ?",
            (book_id,),
        ).fetchone()
        return None if row is None else dict(row)

    def delete_book(self, book_id: int) -> None:
        """Xoá một quyển sách khỏi SQLite theo book_id.
        Tự động xoá bài học và từ vựng liên quan nhờ ON DELETE CASCADE.
        """
        with self.transaction() as conn:
            conn.execute("DELETE FROM book WHERE id = ?", (book_id,))

    def get_lessons(self, book_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, index_no, title, page_start, page_end, confidence "
            "FROM lesson WHERE book_id = ? ORDER BY index_no",
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_lesson_words(self, lesson_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, order_no, word, pos, pinyin_src, hanviet_src, "
            "       meaning_src, source_page, extract_by, needs_review "
            "FROM lesson_word WHERE lesson_id = ? ORDER BY order_no, id",
            (lesson_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_lesson_boundary(
        self,
        lesson_id: int,
        title: str | None,
        page_start: int,
        page_end: int,
    ) -> None:
        if page_start < 0 or page_end < page_start:
            raise ValueError("Khoảng trang bài học không hợp lệ")
        with self.transaction() as conn:
            conn.execute(
                "UPDATE lesson SET title = ?, page_start = ?, page_end = ? "
                "WHERE id = ?",
                (title, page_start, page_end, lesson_id),
            )

    # ------------------------------------------------- bài học và bảng từ mới
    def replace_lessons(self, book_id: int, bounds: list[LessonBoundary]) -> None:
        """Thay TRỌN GÓI danh sách bài của một quyển, trong một giao dịch.

        Xoá hết bài cũ rồi chèn danh sách mới, không phải upsert từng dòng.
        Nhập lại một quyển hoặc sửa ranh giới rồi lưu là ghi đè cả cụm, nên
        không bao giờ để lại trạng thái nửa vời.

        LessonBoundary.kind không có cột riêng trong lược đồ vì nó suy ra được
        từ dấu của index_no: mục ôn tập mang số âm, xem QT-02 bước 3.

        Xoá bài học kéo theo cả bảng từ mới của bài đó qua ON DELETE CASCADE,
        nên người gọi phải chèn lại từ mới sau khi gọi hàm này.
        """
        with self.transaction() as conn:
            conn.execute("DELETE FROM lesson WHERE book_id = ?", (book_id,))
            conn.executemany(
                "INSERT INTO lesson (book_id, index_no, title, page_start, "
                "                    page_end, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (book_id, b.index_no, b.title, b.page_start, b.page_end,
                     b.confidence)
                    for b in bounds
                ],
            )

    def replace_vocab(self, lesson_id: int, rows: list[VocabRow]) -> None:
        """Thay TRỌN GÓI bảng từ mới của một bài, trong một giao dịch.

        VocabRow.review_reason không được lưu: lược đồ mục 5.3 chỉ có cờ
        needs_review, không có cột lý do. Lý do là thứ hiện lên màn hình sửa
        tay ngay trong phiên nhập, không phải dữ liệu cần giữ lại.

        Cột hanviet_src lấy nguyên văn từ bảng giáo trình.
        """
        self.replace_vocab_many({lesson_id: rows})

    def replace_vocab_many(
        self, rows_by_lesson: dict[int, list[VocabRow]]
    ) -> None:
        """Thay bảng từ của nhiều bài trong cùng một giao dịch nguyên tử."""
        with self.transaction() as conn:
            for lesson_id, rows in rows_by_lesson.items():
                conn.execute(
                    "DELETE FROM lesson_word WHERE lesson_id = ?",
                    (lesson_id,),
                )
                conn.executemany(
                    "INSERT INTO lesson_word (lesson_id, order_no, word, pos, "
                    "                         pinyin_src, hanviet_src, meaning_src, source_page, "
                    "                         extract_by, needs_review) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            lesson_id,
                            r.order_no,
                            r.word,
                            r.pos,
                            r.pinyin_src,
                            r.hanviet_src,
                            r.meaning_src,
                            r.source_page,
                            r.extract_by,
                            int(r.needs_review),
                        )
                        for r in rows
                    ],
                )

    def word_source(self, word: str) -> WordSource | None:
        """Lần gặp ĐẦU TIÊN của từ này trong sách của người dùng.

        Xếp theo id quyển rồi tới số bài: quyển nhập trước lên trước, và thứ tự
        này không đổi khi người dùng nhập lại một quyển sau đó, khác với xếp
        theo lesson_word.id. None nếu từ chưa nằm trong quyển nào.
        """
        row = self._conn.execute(
            "SELECT b.title AS book_title, l.index_no, l.title AS lesson_title, "
            "       lw.source_page, lw.pinyin_src, lw.hanviet_src, lw.meaning_src "
            "FROM lesson_word lw "
            "JOIN lesson l ON l.id = lw.lesson_id "
            "JOIN book b   ON b.id = l.book_id "
            "WHERE lw.word = ? "
            "ORDER BY b.id, l.index_no, lw.id LIMIT 1",
            (word,),
        ).fetchone()
        if row is None:
            return None
        return WordSource(
            book_title=row["book_title"],
            lesson_no=row["index_no"],
            lesson_title=row["lesson_title"],
            page=row["source_page"],
            pinyin_src=row["pinyin_src"],
            hanviet_src=row["hanviet_src"],
            meaning_src=row["meaning_src"],
        )

    # --------------------------------------------------------------- tiến độ
    def get_progress(self, word: str) -> ReviewOutcome | None:
        row = self._conn.execute(
            "SELECT status, ease, interval_days, due_date, repetition, "
            "       lapse_count FROM progress WHERE word = ?",
            (word,),
        ).fetchone()
        if row is None:
            return None
        return ReviewOutcome(
            ease=row["ease"],
            interval_days=row["interval_days"],
            # repetition và review_count là HAI con số khác nhau, xem bậc 2 của
            # migrate. Scheduler cần bậc lặp liên tiếp, tức cột repetition.
            repetition=row["repetition"],
            lapse_count=row["lapse_count"],
            status=row["status"],
            due_date=date.fromisoformat(row["due_date"]),
        )

    def upsert_progress(
        self, word: str, outcome: ReviewOutcome, source_lw_id: int | None
    ) -> None:
        """Tạo hoặc cập nhật bản ghi tiến độ của một từ.

        source_lw_id KHÔNG được ghi đè khi dòng đã tồn tại, theo QT-04 bước 2:
        mặt sau của thẻ phải luôn hiện nghĩa của quyển sách mà người dùng gặp
        từ đó lần đầu. COALESCE lấy giá trị CŨ trước; giá trị mới chỉ được dùng
        khi cột cũ đang NULL, tức là từ trước đó thêm thẳng từ màn hình Tra cứu
        và nay mới có chỗ bám trong sách.

        added_at cũng giữ nguyên vì đó là mốc bắt đầu học, không phải mốc sửa.

        review_count KHÔNG nằm trong câu lệnh này. Nó là tổng số lần ôn, chỉ do
        log_review tăng theo QT-04 bước 5; nếu upsert ghi đè nó bằng
        outcome.repetition thì một lần bấm Quên, vốn đặt repetition về 0, sẽ xoá
        sạch tổng số lần ôn. Dòng mới lấy mặc định 0 của lược đồ.
        """
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO progress (word, status, ease, interval_days, "
                "                      due_date, repetition, lapse_count, "
                "                      source_lw_id, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(word) DO UPDATE SET "
                "    status        = excluded.status, "
                "    ease          = excluded.ease, "
                "    interval_days = excluded.interval_days, "
                "    due_date      = excluded.due_date, "
                "    repetition    = excluded.repetition, "
                "    lapse_count   = excluded.lapse_count, "
                "    source_lw_id  = COALESCE(progress.source_lw_id, "
                "                             excluded.source_lw_id)",
                (
                    word,
                    outcome.status,
                    outcome.ease,
                    outcome.interval_days,
                    outcome.due_date.isoformat(),
                    outcome.repetition,
                    outcome.lapse_count,
                    source_lw_id,
                    _bay_gio(),
                ),
            )

    def due_words(self, on: date, limit: int = 100) -> list[str]:
        """Các từ tới hạn ôn tính đến ngày ``on``, từ quá hạn lâu nhất lên trước.

        due_date lưu dạng ISO nên so sánh chuỗi trùng với so sánh ngày.
        """
        return [
            row["word"]
            for row in self._conn.execute(
                "SELECT word FROM progress WHERE due_date <= ? "
                "ORDER BY due_date, word LIMIT ?",
                (on.isoformat(), limit),
            )
        ]

    def progress_counts(self) -> tuple[int, int]:
        """(đang theo dõi, đã thuộc) — số dòng progress, và số dòng status='known'.

        Hai con số của QT-04 bước 6. Đếm ở tầng data bằng một truy vấn, vì tầng ui
        không được phép mở kết nối cơ sở dữ liệu theo mục 13.1.

        Một truy vấn chứ không phải hai: SUM của một biểu thức so sánh đếm luôn
        các dòng 'known' ngay trong lượt quét của COUNT(*). Bảng rỗng thì SUM trả
        NULL chứ không trả 0, nên phải bọc COALESCE.
        """
        row = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(status = 'known'), 0) FROM progress"
        ).fetchone()
        return int(row[0]), int(row[1])

    def log_review(
        self,
        word: str,
        grade: int,
        q: int,
        before: ReviewOutcome,
        after: ReviewOutcome,
    ) -> None:
        """Một dòng nhật ký cho mỗi lần tự đánh giá, phục vụ biểu đồ tiến độ.

        QT-04 bước 5 buộc hai việc đi cùng nhau: ghi dòng review_log VÀ tăng
        review_count thêm 1. Chúng nằm trong cùng một giao dịch để tổng số lần
        ôn không bao giờ lệch với số dòng nhật ký. review_count chỉ tăng, khác
        với repetition ở bảng progress vốn bị đặt lại về 0 mỗi lần bấm Quên.
        """
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO review_log (word, reviewed_at, grade, q, ease_after, "
                "                        interval_before, interval_after) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    word,
                    _bay_gio(),
                    grade,
                    q,
                    after.ease,
                    before.interval_days,
                    after.interval_days,
                ),
            )
            conn.execute(
                "UPDATE progress SET review_count = review_count + 1 WHERE word = ?",
                (word,),
            )

    def undo_review(self, word: str, before: ReviewOutcome) -> None:
        """Hoàn tác lần tự đánh giá gần nhất của một từ.

        Ba việc, trong MỘT giao dịch: khôi phục dòng progress về đúng trạng thái
        ``before``, xoá dòng review_log MỚI NHẤT của từ đó, và giảm review_count
        đi 1 nhưng không bao giờ xuống dưới 0. Nửa vời ở đây nghĩa là tổng số lần
        ôn lệch khỏi số dòng nhật ký, đúng thứ mà log_review đã cố tránh.

        Trạng thái cũ do người gọi đưa vào chứ không dựng lại từ nhật ký, vì
        review_log chỉ lưu interval_before và ease_after, không lưu ease_before,
        repetition, lapse_count, status hay due_date của lúc trước. Nên hoàn tác
        chỉ chạy trong phiên đang mở: màn hình Ôn tập giữ cặp (word, before)
        trong bộ nhớ. Muốn hoàn tác xuyên phiên thì phải thêm bốn cột vào
        review_log bằng một bậc migration mới.

        Xoá theo id của đúng một dòng chứ không xoá theo word, vì xoá theo word
        là xoá sạch lịch sử của từ đó. Dòng mới nhất chọn theo reviewed_at rồi
        tới id: dấu thời gian chỉ tới giây nên hai lần ôn trong cùng một giây
        trùng nhau, khi đó chỉ id mới phân biệt được.

        Từ chưa từng ôn lần nào vẫn khôi phục được progress, không ném lỗi:
        câu xoá không khớp dòng nào và MAX(..., 0) chặn review_count ở 0.
        """
        with self.transaction() as conn:
            # source_lw_id để None: COALESCE trong upsert_progress giữ giá trị
            # đang có, nên mặt sau của thẻ không bị hoàn tác làm mất.
            self.upsert_progress(word, before, None)
            conn.execute(
                "DELETE FROM review_log WHERE id = ("
                "    SELECT id FROM review_log WHERE word = ? "
                "    ORDER BY reviewed_at DESC, id DESC LIMIT 1)",
                (word,),
            )
            conn.execute(
                "UPDATE progress SET review_count = MAX(review_count - 1, 0) "
                "WHERE word = ?",
                (word,),
            )

    def learned_chars(self) -> set[str]:
        """Tập các chữ RỜI đã gặp, tách từ mọi từ trong progress.

        Đơn vị đếm ở màn hình Bản đồ bộ thủ là số chữ khác nhau chứ không phải
        số từ, xem mục 5.4, nên phép tách phải làm ở đây chứ không lưu sẵn.
        """
        return {
            ch
            for row in self._conn.execute("SELECT word FROM progress")
            for ch in row["word"]
        }

    # -------------------------------------------------- bộ nhớ đệm giải thích
    def cache_get(self, key: str) -> dict | None:
        row = self._conn.execute(
            "SELECT payload FROM explain_cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None or row["payload"] is None:
            return None
        return json.loads(row["payload"])

    def cache_put(self, key: str, payload: dict, model: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO explain_cache (key, payload, model, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET "
                "    payload    = excluded.payload, "
                "    model      = excluded.model, "
                "    created_at = excluded.created_at",
                (key, json.dumps(payload, ensure_ascii=False), model, _bay_gio()),
            )

    # -------------------------------------------------- cài đặt hệ thống
    def get_setting(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM setting WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else row["value"]

    def set_setting(self, key: str, val: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO setting (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, val),
            )
