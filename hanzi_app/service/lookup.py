"""Tra cứu từ và chữ: FR-01 tới FR-08. Đặc tả ở mục 13.6, bảng đáp án ở mục 14.4.

Tầng service nên module này không tự mở cơ sở dữ liệu: nó nhận DictDb và UserDb
qua tham số khởi tạo. Không import decomposer, xem ghi chú ở WordDetail trong
data/models.py.
"""

import math
import unicodedata
from difflib import SequenceMatcher

from hanzi_app.data.models import SearchHit, WordDetail
from hanzi_app.service import pinyin

# Mười hai toán tử IDS không bao giờ là truy vấn, nhưng dải chữ Hán thì cần biết
# để chọn nhánh tìm kiếm. Ba khối dưới đây phủ chữ Hán thường gặp trong giáo trình.
_CJK_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))

# Bốn dấu thanh dạng ký tự kết hợp, giống mục 13.5. Dùng để biết truy vấn có
# đánh dấu thanh hay không, từ đó phân biệt 'pinyin_tone' với 'pinyin_plain'.
_TONE_CODEPOINTS = frozenset({0x0300, 0x0301, 0x0304, 0x030C})


def _is_cjk(ch: str) -> bool:
    return any(lo <= ord(ch) <= hi for lo, hi in _CJK_RANGES)


def _has_cjk(text: str) -> bool:
    return any(_is_cjk(c) for c in text)


def _has_tone_mark(text: str) -> bool:
    return any(
        ord(c) in _TONE_CODEPOINTS for c in unicodedata.normalize("NFD", text)
    )


def _norm_tone(text: str) -> str:
    """Dạng so sánh của pinyin có dấu: hạ chữ thường, bỏ khoảng trắng và dấu nháy."""
    return (
        unicodedata.normalize("NFC", text.lower())
        .replace(" ", "")
        .replace("'", "")
        .replace("’", "")
    )


class LookupService:
    """Gộp từ điển và dữ liệu người dùng thành kết quả tra cứu đã xếp hạng."""

    # Trọng số khớp của mục 13.6. Khoá trùng với trường matched_by của SearchHit.
    W_MATCH = {
        "hanzi": 1.00,
        "pinyin_tone": 0.90,
        "pinyin_plain": 0.75,
        "pinyin_num": 0.75,
        "meaning": 0.50,
        "fuzzy": 0.25,
    }

    # Từ mức này trở lên là khớp đúng, dưới mức này là khớp gần. Đây là thành
    # phần thứ nhất của khoá sắp xếp kép, nhờ nó khớp gần luôn nằm sau khớp đúng.
    EXACT_MIN = 0.5

    # Ngưỡng tương đồng của FR-08, lấy đúng mức cutoff mặc định của difflib.
    FUZZY_CUTOFF = 0.6

    # Số ký tự tối đa được bỏ ở cuối truy vấn khi đi tìm ứng viên khớp gần.
    FUZZY_TRIM = 2

    def __init__(self, dict_db, user_db) -> None:
        self._dict = dict_db
        self._user = user_db

    # ------------------------------------------------------------------ FR-01..07
    def search(self, query: str, limit: int = 30) -> list[SearchHit]:
        """Chỉ trả kết quả khớp đúng. Không khớp gì thì trả danh sách rỗng, không
        tự rơi sang khớp gần; nhánh đó là việc của suggest."""
        return self._rank(self._exact_hits(query), limit)

    def detail(self, word: str) -> WordDetail:
        """Gộp dữ liệu từ điển với dữ liệu người dùng: thông tin từ, từng chữ,
        nguồn trong sách nếu có, trạng thái ôn tập nếu có."""
        query = word.strip()

        words = self._dict.find_words_by_hanzi(query) if query else []
        best = None
        if words:
            best = max(words, key=lambda w: self._score("hanzi", w.hsk_level, w.freq_rank))

        found = self._dict.get_chars(query) if query else {}
        chars = tuple(found[c] for c in query if c in found)

        progress = self._user.get_progress(query)
        return WordDetail(
            query=query,
            word=best,
            chars=chars,
            source=self._user.word_source(query),
            status=None if progress is None else progress.status,
        )

    # ---------------------------------------------------------------------- FR-08
    def suggest(self, query: str, limit: int = 5) -> list[SearchHit]:
        """Nhánh không có kết quả: gợi ý các mục gần giống. Khớp gần luôn xếp sau
        toàn bộ nhóm khớp đúng, kể cả khi điểm số của nó cao hơn."""
        return self._rank(self._exact_hits(query) + self._fuzzy_hits(query), limit)

    # ------------------------------------------------------------ phần nội bộ
    def _exact_hits(self, query: str) -> list[SearchHit]:
        text = query.strip()
        if not text:
            return []
        if _has_cjk(text):
            return self._hanzi_hits(text)
        return self._pinyin_hits(text) + self._meaning_hits(text)

    def _hanzi_hits(self, text: str) -> list[SearchHit]:
        """FR-01 và FR-07: khớp đúng dạng chữ. Truy vấn một chữ cho thêm một kết
        quả mức chữ đơn, vì chữ đó có thể chưa nằm trong từ ghép nào."""
        hits = [self._word_hit(w, "hanzi") for w in self._dict.find_words_by_hanzi(text)]
        if len(text) == 1:
            info = self._dict.get_char(text)
            if info is not None:
                hits.append(self._char_hit(info, "hanzi"))
        return hits

    def _pinyin_hits(self, text: str) -> list[SearchHit]:
        """FR-02 và FR-03. Truy vấn có số thanh chỉ đi qua cột pinyin_numeric:
        người dùng đã nói rõ thanh nào thì không trả về toàn bộ từ đồng âm."""
        numeric = self._numeric_variants(text)
        if numeric:
            hits = []
            for form in numeric:
                hits += [
                    self._word_hit(w, "pinyin_num")
                    for w in self._dict.find_words_by_pinyin("", form)
                ]
            return hits

        toned = _has_tone_mark(text)
        compare = _norm_tone(text)
        hits = []
        for variant in pinyin.query_variants(text):
            for w in self._dict.find_words_by_pinyin(variant, None):
                matched_by = (
                    "pinyin_tone"
                    if toned and _norm_tone(w.pinyin_tone) == compare
                    else "pinyin_plain"
                )
                hits.append(self._word_hit(w, matched_by))
        return hits

    def _meaning_hits(self, text: str) -> list[SearchHit]:
        """FR-04, đi qua chỉ mục toàn văn word_fts."""
        return [
            self._word_hit(w, "meaning")
            for w in self._dict.find_words_by_meaning(text)
        ]

    def _fuzzy_hits(self, query: str) -> list[SearchHit]:
        """FR-08. Ứng viên lấy bằng cách bỏ dần ký tự cuối của truy vấn rồi tra
        khớp đúng, sau đó lọc lại theo độ tương đồng."""
        text = query.strip()
        if not text:
            return []

        cjk = _has_cjk(text)
        base = text if cjk else pinyin.to_plain(_strip_tone_digits(text))

        pool: list = []
        for trim in range(1, self.FUZZY_TRIM + 1):
            if len(base) - trim < 1:
                break
            shorter = base[:-trim]
            pool = (
                self._dict.find_words_by_hanzi(shorter)
                if cjk
                else self._dict.find_words_by_pinyin(shorter, None)
            )
            if pool:
                break

        hits = []
        for w in pool:
            other = w.simplified if cjk else pinyin.to_plain(w.pinyin_tone)
            if SequenceMatcher(None, base, other).ratio() >= self.FUZZY_CUTOFF:
                hits.append(self._word_hit(w, "fuzzy"))
        return hits

    def _rank(self, hits: list[SearchHit], limit: int) -> list[SearchHit]:
        """Bỏ trùng, giữ lại cách khớp mạnh nhất của mỗi mục, rồi sắp xếp theo
        khoá kép (khớp đúng, điểm) giảm dần."""
        best: dict[tuple[str, object], SearchHit] = {}
        for hit in hits:
            key = ("word", hit.word.id) if hit.kind == "word" else ("char", hit.char.char)
            old = best.get(key)
            if old is None or self.W_MATCH[hit.matched_by] > self.W_MATCH[old.matched_by]:
                best[key] = hit

        ranked = sorted(
            best.values(),
            key=lambda h: (self.W_MATCH[h.matched_by] >= self.EXACT_MIN, h.score),
            reverse=True,
        )
        return ranked[:limit]

    def _word_hit(self, word, matched_by: str) -> SearchHit:
        return SearchHit(
            kind="word",
            word=word,
            char=None,
            score=self._score(matched_by, word.hsk_level, word.freq_rank),
            matched_by=matched_by,
        )

    def _char_hit(self, char, matched_by: str) -> SearchHit:
        return SearchHit(
            kind="char",
            word=None,
            char=char,
            score=self._score(matched_by, char.hsk_level, char.freq_rank),
            matched_by=matched_by,
        )

    def _score(self, matched_by: str, hsk_level: int | None, freq_rank: int | None) -> float:
        """score = 100·w_khớp + 30·w_hsk + 20·w_tần_suất, đúng công thức mục 13.6."""
        w_hsk = 0.0 if hsk_level is None else (7 - hsk_level) / 6
        w_freq = 0.0 if freq_rank is None else 1 / math.log10(freq_rank + 10)
        return 100 * self.W_MATCH[matched_by] + 30 * w_hsk + 20 * w_freq

    @staticmethod
    def _numeric_variants(text: str) -> list[str]:
        """Biến thể pinyin số của chuỗi người dùng gõ, rỗng nếu truy vấn không có
        số thanh. Phải sinh cả dạng có khinh thanh: người dùng gõ 'ren4shi' còn
        cột pinyin_numeric lưu 'ren4shi5'."""
        base = pinyin.to_plain(text)
        if not any(c.isdigit() for c in base):
            return []
        variants = [base]
        if not base[-1].isdigit():
            variants.append(base + "5")
        return variants


def _strip_tone_digits(text: str) -> str:
    """Bỏ số thanh khỏi truy vấn để so khớp gần trên dạng phẳng."""
    return "".join(c for c in text if not c.isdigit())
