"""Truy cập dict.sqlite, chỉ đọc. Lược đồ theo mục 5.2 của đặc tả.

Phiên này chỉ cài các phương thức mà decomposer cần. Tầng data không import bất
cứ thứ gì của Qt.
"""

import sqlite3

from hanzi_app.data.models import CharInfo, Radical, WordInfo

# Các cột của bảng word, dùng chung cho mọi truy vấn trả về WordInfo.
_WORD_COLS = (
    "id, word_simp, word_trad, pinyin_tone, pos, meaning_vi, meaning_en, "
    "hsk_level, freq_rank"
)


class DictDb:
    """Kết nối chỉ đọc tới từ điển. Mở bằng URI mode=ro nên mọi lệnh ghi đều bị
    SQLite từ chối, không phải chỉ dựa vào quy ước."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def get_char(self, ch: str) -> CharInfo | None:
        row = self._conn.execute(
            "SELECT char, pinyin, hanviet, meaning_vi, meaning_en, radical_idx, "
            "       total_strokes, trad_form, ids, hsk_level, freq_rank "
            "FROM char WHERE char = ?",
            (ch,),
        ).fetchone()
        if row is None:
            return None

        readings = tuple(
            r["pinyin"]
            for r in self._conn.execute(
                "SELECT pinyin FROM char_reading WHERE char = ? "
                "ORDER BY is_primary DESC, pinyin",
                (ch,),
            )
        )
        return CharInfo(
            char=row["char"],
            pinyin=row["pinyin"],
            readings=readings,
            hanviet=row["hanviet"],
            meaning_vi=row["meaning_vi"],
            meaning_en=row["meaning_en"],
            radical_idx=row["radical_idx"],
            total_strokes=row["total_strokes"],
            trad_form=row["trad_form"],
            ids=row["ids"],
            hsk_level=row["hsk_level"],
            freq_rank=row["freq_rank"],
        )

    def get_radical(self, idx: int) -> Radical | None:
        row = self._conn.execute(
            "SELECT idx, glyph, glyph_alt, name_hv, meaning_vi, strokes "
            "FROM radical WHERE idx = ?",
            (idx,),
        ).fetchone()
        return None if row is None else self._to_radical(row)

    def all_radicals(self) -> list[Radical]:
        """Toàn bộ 214 bộ Khang Hy, xếp theo số hiệu."""
        return [
            self._to_radical(row)
            for row in self._conn.execute(
                "SELECT idx, glyph, glyph_alt, name_hv, meaning_vi, strokes "
                "FROM radical ORDER BY idx"
            )
        ]

    def chars_with_radical(self, idx: int, limit: int) -> list[str]:
        """Các chữ thuộc một bộ, chữ phổ biến lên trước, chữ không có thứ hạng
        tần suất xuống cuối."""
        return [
            row["char"]
            for row in self._conn.execute(
                "SELECT char FROM char WHERE radical_idx = ? "
                "ORDER BY freq_rank IS NULL, freq_rank, char LIMIT ?",
                (idx, limit),
            )
        ]

    def radical_char_counts(self) -> dict[int, int]:
        """Số chữ khác nhau của từng bộ trong từ điển."""
        return {
            row["radical_idx"]: row["n"]
            for row in self._conn.execute(
                "SELECT radical_idx, COUNT(DISTINCT char) AS n FROM char "
                "WHERE radical_idx IS NOT NULL GROUP BY radical_idx"
            )
        }

    def get_chars(self, chars: str) -> dict[str, CharInfo]:
        """Tra nhiều chữ trong một truy vấn, kèm một truy vấn nữa cho âm đọc.

        Chữ không có trong từ điển thì vắng mặt trong kết quả. Chuỗi vào có thể
        lặp chữ; khoá của dict là chữ nên phần lặp tự biến mất.
        """
        wanted = list(dict.fromkeys(chars))
        if not wanted:
            return {}

        holes = ",".join("?" * len(wanted))
        readings: dict[str, list[str]] = {}
        for row in self._conn.execute(
            f"SELECT char, pinyin FROM char_reading WHERE char IN ({holes}) "
            "ORDER BY is_primary DESC, pinyin",
            wanted,
        ):
            readings.setdefault(row["char"], []).append(row["pinyin"])

        result: dict[str, CharInfo] = {}
        for row in self._conn.execute(
            "SELECT char, pinyin, hanviet, meaning_vi, meaning_en, radical_idx, "
            "       total_strokes, trad_form, ids, hsk_level, freq_rank "
            f"FROM char WHERE char IN ({holes})",
            wanted,
        ):
            result[row["char"]] = CharInfo(
                char=row["char"],
                pinyin=row["pinyin"],
                readings=tuple(readings.get(row["char"], ())),
                hanviet=row["hanviet"],
                meaning_vi=row["meaning_vi"],
                meaning_en=row["meaning_en"],
                radical_idx=row["radical_idx"],
                total_strokes=row["total_strokes"],
                trad_form=row["trad_form"],
                ids=row["ids"],
                hsk_level=row["hsk_level"],
                freq_rank=row["freq_rank"],
            )
        return result

    def find_words_by_hanzi(self, text: str) -> list[WordInfo]:
        """Các mục từ có dạng chữ đúng bằng text, giản thể hoặc phồn thể.

        Một dạng chữ có thể ứng với nhiều mục từ khác âm khác nghĩa, nên trả về
        danh sách chứ không phải một dòng.
        """
        return self._words(
            f"SELECT {_WORD_COLS} FROM word WHERE word_simp = ? OR word_trad = ? "
            "ORDER BY freq_rank IS NULL, freq_rank, id",
            (text, text),
        )

    def find_words_by_pinyin(self, plain: str, numeric: str | None) -> list[WordInfo]:
        """Các mục từ khớp pinyin dạng phẳng, hoặc khớp pinyin dạng số nếu có."""
        return self._words(
            f"SELECT {_WORD_COLS} FROM word "
            "WHERE (? <> '' AND pinyin_plain = ?) "
            "   OR (? IS NOT NULL AND pinyin_numeric = ?) "
            "ORDER BY freq_rank IS NULL, freq_rank, id",
            (plain, plain, numeric, numeric),
        )

    def find_words_by_meaning(self, query: str, limit: int = 50) -> list[WordInfo]:
        """Tìm theo nghĩa qua chỉ mục toàn văn word_fts, phục vụ FR-04.

        Truy vấn được bọc trong dấu nháy kép nên toàn bộ chuỗi người dùng gõ là
        một cụm cần tìm, và các ký tự có nghĩa đặc biệt của FTS5 không phá cú pháp.
        """
        phrase = '"' + query.replace('"', '""') + '"'
        return self._words(
            f"SELECT {_WORD_COLS} FROM word "
            "WHERE id IN (SELECT rowid FROM word_fts WHERE word_fts MATCH ? "
            "             ORDER BY rank LIMIT ?)",
            (phrase, limit),
        )

    # ------------------------------------------- rổ đáp án nhiễu cho ôn tập
    def candidate_meanings(
        self, exclude_word: str, hsk_level: int | None, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài chọn nghĩa.

        Trả về [(word_simp, meaning_vi), ...]. Chỉ lấy dòng có meaning_vi khác
        rỗng, bỏ chính exclude_word. hsk_level khác None thì lọc đúng cấp đó;
        None thì lấy toàn bảng.

        Lọc theo cấp HSK vì đáp án nhiễu phải cùng cấp mới thành bài tập thật:
        bốc ngẫu nhiên trong cả 5001 từ thì người học loại trừ được ngay bằng
        cảm giác độ khó, không cần biết nghĩa.

        Đây là cái RỔ, không phải bộ đáp án cuối cùng: thứ tự trả về xác định,
        theo freq_rank rồi tới id, nên test lặp lại được. Việc bốc ngẫu nhiên
        vài phần tử trong rổ là của tầng giao diện.
        """
        return [
            (row["word_simp"], row["meaning_vi"])
            for row in self._conn.execute(
                "SELECT word_simp, meaning_vi FROM word "
                "WHERE meaning_vi IS NOT NULL AND meaning_vi <> '' "
                "  AND word_simp <> ? "
                "  AND (? IS NULL OR hsk_level = ?) "
                "ORDER BY freq_rank IS NULL, freq_rank, id LIMIT ?",
                (exclude_word, hsk_level, hsk_level, limit),
            )
        ]

    def candidate_hanviet(
        self, exclude_char: str, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài chọn âm Hán-Việt.

        Trả về [(char, hanviet), ...]. Chỉ lấy dòng có hanviet khác rỗng, bỏ
        chính exclude_char. Không lọc theo cấp HSK vì bảng char không phủ cấp
        đều như bảng word; chỗ giữ cho bài này khó vừa phải là thứ tự tần suất.

        Thứ tự xác định, theo freq_rank rồi tới char, cùng lý do như
        candidate_meanings: bốc ngẫu nhiên là việc của tầng giao diện.
        """
        return [
            (row["char"], row["hanviet"])
            for row in self._conn.execute(
                "SELECT char, hanviet FROM char "
                "WHERE hanviet IS NOT NULL AND hanviet <> '' "
                "  AND char <> ? "
                "ORDER BY freq_rank IS NULL, freq_rank, char LIMIT ?",
                (exclude_char, limit),
            )
        ]

    def _words(self, sql: str, params: tuple) -> list[WordInfo]:
        return [
            WordInfo(
                id=row["id"],
                simplified=row["word_simp"],
                traditional=row["word_trad"],
                pinyin_tone=row["pinyin_tone"],
                pos=row["pos"],
                meaning_vi=row["meaning_vi"],
                meaning_en=row["meaning_en"],
                hsk_level=row["hsk_level"],
                freq_rank=row["freq_rank"],
            )
            for row in self._conn.execute(sql, params)
        ]

    @staticmethod
    def _to_radical(row: sqlite3.Row) -> Radical:
        return Radical(
            idx=row["idx"],
            glyph=row["glyph"],
            glyph_alt=row["glyph_alt"],
            name_hv=row["name_hv"],
            meaning_vi=row["meaning_vi"],
            strokes=row["strokes"],
        )
