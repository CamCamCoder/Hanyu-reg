"""Bộ bóc tách từ vựng từ các trang PDF bài học (QT-03) bằng Rule-based & LLM API.

Tầng service: bóc tách danh sách VocabRow 7 cột từ TextSpan hoặc LLM API.
"""

from __future__ import annotations

import re
import statistics
import time
import unicodedata
from dataclasses import replace
from itertools import product
from typing import TYPE_CHECKING

from hanzi_app.adapter.aiclient import AiRateLimitError
from hanzi_app.data.models import TextSpan, VocabBlock, VocabRow

if TYPE_CHECKING:
    from hanzi_app.adapter.aiclient import AiClient
    from hanzi_app.adapter.pdfsource import PdfSource
    from hanzi_app.data.models import LessonBoundary

# Biểu thức chính quy nhận diện từ loại phổ biến (pos)
RE_POS = re.compile(
    r"^(名|动|形|副|代|数|量|介|连|助|叹|拟|词|n\.|v\.|adj\.|adv\.|prep\.|conj\.|pron\.|num\.|m\.)$",
    re.IGNORECASE,
)

# Biểu thức chính quy phát hiện chữ Hán (CJK)
RE_CJK_WORD = re.compile(r"[\u4e00-\u9fff]+")
RE_CJK_ONLY = re.compile(r"^[\u3400-\u9fff]+$")

# Các nguyên âm pinyin chuẩn của tiếng Trung
PINYIN_VOWELS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü")
RE_PINYIN_TEXT = re.compile(
    r"^[A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ' -]+$"
)


def _plain_pinyin(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return (
        plain.replace("ü", "v")
        .replace("u:", "v")
        .replace("'", "")
        .replace(" ", "")
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _line_groups(spans: list[TextSpan]) -> list[list[TextSpan]]:
    """Group spans into visual rows without relying on a textbook template."""
    lines: list[list[TextSpan]] = []
    for span in sorted(
        spans, key=lambda item: ((item.bbox[1] + item.bbox[3]) / 2, item.bbox[0])
    ):
        center_y = (span.bbox[1] + span.bbox[3]) / 2
        if not lines:
            lines.append([span])
            continue
        previous_y = sum(
            (item.bbox[1] + item.bbox[3]) / 2 for item in lines[-1]
        ) / len(lines[-1])
        if abs(center_y - previous_y) <= 12:
            lines[-1].append(span)
        else:
            lines.append([span])
    return lines


def _compact_line(spans: list[TextSpan]) -> str:
    return re.sub(
        r"\s+", "", " ".join(span.text for span in spans)
    ).lower()


def _has_vocab_heading(spans: list[TextSpan]) -> bool:
    compact = _compact_line(spans)
    return any(
        marker in compact
        for marker in ("newwords", "词语表", "生词", "từmới")
    )


def _is_pinyin_text(text: str) -> bool:
    value = text.strip()
    return bool(
        value
        and RE_PINYIN_TEXT.fullmatch(value)
        and any(character.isalpha() for character in value)
        and any(
            character.lower() in "aeiouvüāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
            for character in value
        )
    )


def _region_evidence(
    spans: list[TextSpan],
) -> tuple[list[list[TextSpan]], list[list[TextSpan]], list[int], bool]:
    row_lines: list[list[TextSpan]] = []
    numeric_candidates: list[tuple[int, float, list[TextSpan]]] = []
    cjk_centers: list[float] = []
    pinyin_centers: list[float] = []
    for line in _line_groups(spans):
        numeric_spans = [
            span
            for span in line
            if re.fullmatch(r"\d{1,3}", span.text.strip())
        ]
        for span in numeric_spans:
            numeric_candidates.append(
                (
                    int(span.text.strip()),
                    (span.bbox[0] + span.bbox[2]) / 2,
                    line,
                )
            )
        cjk = [span for span in line if RE_CJK_WORD.search(span.text)]
        pinyin = [span for span in line if _is_pinyin_text(span.text)]
        if cjk and pinyin:
            row_lines.append(line)
            cjk_centers.append((cjk[0].bbox[0] + cjk[0].bbox[2]) / 2)
            pinyin_centers.append((pinyin[0].bbox[0] + pinyin[0].bbox[2]) / 2)

    aligned_orders: list[tuple[int, float, list[TextSpan]]] = []
    if numeric_candidates:
        clusters = [
            [
                candidate
                for candidate in numeric_candidates
                if abs(candidate[1] - center) <= 35
            ]
            for _value, center, _line in numeric_candidates
        ]
        aligned_orders = max(
            clusters,
            key=lambda cluster: (
                len(cluster),
                -min(candidate[1] for candidate in cluster),
            ),
        )
    unique_orders = sorted({candidate[0] for candidate in aligned_orders})
    order_lines: list[list[TextSpan]] = []
    for _value, _center, line in aligned_orders:
        if line not in order_lines:
            order_lines.append(line)
    sequential = any(
        right == left + 1
        for left, right in zip(unique_orders, unique_orders[1:])
    )
    aligned = (
        len(row_lines) >= 2
        and max(cjk_centers) - min(cjk_centers) <= 35
        and max(pinyin_centers) - min(pinyin_centers) <= 35
    )
    return row_lines, order_lines, unique_orders, sequential or aligned

def render_block_crop(pdf: PdfSource, block: VocabBlock, dpi: int = 250) -> bytes:
    """Render exactly the persisted page and rectangle of one vocabulary block."""
    return pdf.get_page_crop_image_bytes(
        block.page_index, block.bbox, dpi=dpi
    )

class VocabExtractor:
    """Bóc tách từ vựng từ bài học theo kiến trúc 2 Lớp sạch sẽ, minh bạch."""

    def __init__(self, dict_db=None) -> None:
        self.dict_db = dict_db

    def locate_blocks(
        self, pdf: PdfSource, lesson: LessonBoundary
    ) -> list[VocabBlock]:
        """Locate every independent vocabulary table region inside a lesson."""
        candidates: list[tuple[int, float, tuple[float, float, float, float], int | None, int | None, int | None]] = []
        page_count = pdf.page_count()
        start = max(0, lesson.page_start)
        end = min(lesson.page_end, page_count - 1)
        for page_index in range(start, end + 1):
            spans = list(pdf.spans(page_index))
            if not spans:
                continue
            lines = _line_groups(spans)
            heading_lines = [line for line in lines if _has_vocab_heading(line)]
            heading_starts = sorted(
                min(span.bbox[1] for span in line) for line in heading_lines
            )
            regions: list[tuple[float, float | None]]
            if heading_starts:
                regions = [
                    (
                        y_start,
                        heading_starts[index + 1]
                        if index + 1 < len(heading_starts)
                        else None,
                    )
                    for index, y_start in enumerate(heading_starts)
                ]
            else:
                regions = [(min(span.bbox[1] for span in spans), None)]

            for y_start, y_end in regions:
                region = [
                    span
                    for span in spans
                    if (span.bbox[1] + span.bbox[3]) / 2 >= y_start
                    and (
                        y_end is None
                        or (span.bbox[1] + span.bbox[3]) / 2 < y_end
                    )
                ]
                if not region:
                    continue
                row_lines, order_lines, orders, has_structure = _region_evidence(region)
                signals = (
                    _has_vocab_heading(region),
                    len(row_lines) >= 2,
                    has_structure,
                )
                if sum(signals) < 2:
                    continue

                relevant_lines = list(row_lines)
                relevant_lines.extend(order_lines)
                relevant_lines.extend(
                    line for line in _line_groups(region) if _has_vocab_heading(line)
                )
                if not relevant_lines:
                    relevant_lines = _line_groups(region)
                relevant = [span for line in relevant_lines for span in line]
                bbox = (
                    max(0.0, min(span.bbox[0] for span in relevant) - 8.0),
                    max(0.0, min(span.bbox[1] for span in relevant) - 8.0),
                    max(span.bbox[2] for span in relevant) + 8.0,
                    max(span.bbox[3] for span in relevant) + 8.0,
                )
                expected_rows = max(len(orders), len(row_lines))
                candidates.append(
                    (
                        page_index,
                        bbox[1],
                        bbox,
                        expected_rows or None,
                        orders[0] if orders else None,
                        orders[-1] if orders else None,
                    )
                )

        candidates.sort(key=lambda item: (item[0], item[1]))
        return [
            VocabBlock(
                id=None,
                lesson_id=None,
                block_no=block_no,
                page_index=page_index,
                bbox=bbox,
                crop_path=None,
                expected_rows=expected_rows,
                first_order=first_order,
                last_order=last_order,
            )
            for block_no, (
                page_index,
                _y_start,
                bbox,
                expected_rows,
                first_order,
                last_order,
            ) in enumerate(candidates, start=1)
        ]
    def extract_by_llm(
        self, text_content: str, ai_client: AiClient, source_page: int
    ) -> list[VocabRow]:
        """Sử dụng LLM API bóc tách từ vựng từ văn bản native."""
        if not ai_client.is_configured() or not text_content.strip():
            return []

        raw_list = ai_client.extract_vocab(text_content)
        if not raw_list:
            return []

        rows: list[VocabRow] = []
        seen_words: set[str] = set()
        for item in raw_list:
            w = _optional_text(item.get("word")) or ""
            if not w or w in seen_words:
                continue
            seen_words.add(w)

            rows.append(
                VocabRow(
                    order_no=len(rows) + 1,
                    word=w,
                    pinyin_src=_optional_text(item.get("pinyin")),
                    pos=_optional_text(item.get("pos")),
                    meaning_src=_optional_text(
                        item.get("meaning_vi", item.get("meaning"))
                    ),
                    source_page=source_page,
                    extract_by="llm",
                    needs_review=True,
                    review_reason="đầu ra AI chưa qua validator",
                    hanviet_src=_optional_text(item.get("hanviet")),
                )
            )
        return rows

    def extract_by_llm_image(
        self, image_bytes: bytes, ai_client: AiClient, source_page: int
    ) -> list[VocabRow]:
        """Sử dụng Vision AI đọc ảnh trang sách bóc tách từ vựng (kèm thử lại khi bận)."""
        raw_list = []
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                raw_list = ai_client.extract_vocab_from_image(image_bytes)
                if raw_list:
                    break
            except Exception as err:
                last_error = err
                if not isinstance(err, AiRateLimitError):
                    break
            if attempt < 3:
                retry_after = getattr(last_error, "retry_after", None)
                time.sleep(retry_after or 5 * attempt)

        if not raw_list:
            if isinstance(last_error, AiRateLimitError):
                raise last_error
            if last_error is not None:
                return []
            raise RuntimeError("Vision không trả về dữ liệu từ mới")

        rows: list[VocabRow] = []
        seen_words: set[str] = set()
        for item in raw_list:
            w = _optional_text(item.get("word")) or ""
            if not w or w in seen_words:
                continue
            seen_words.add(w)

            rows.append(
                VocabRow(
                    order_no=len(rows) + 1,
                    word=w,
                    pinyin_src=_optional_text(item.get("pinyin")),
                    pos=_optional_text(item.get("pos")),
                    meaning_src=_optional_text(
                        item.get("meaning_vi", item.get("meaning"))
                    ),
                    source_page=source_page,
                    extract_by="vision",
                    needs_review=True,
                    review_reason="đầu ra Vision chưa qua validator",
                    hanviet_src=_optional_text(item.get("hanviet")),
                )
            )
        return rows

    def extract_spans(self, spans: list[TextSpan], source_page: int) -> list[VocabRow]:
        """Bóc tách từ vựng bằng quy tắc Rule-based cho trang text native."""
        if not spans:
            return []

        lines_map: dict[int, list[TextSpan]] = {}
        for s in spans:
            y_key = int(s.bbox[1] // 10) * 10
            lines_map.setdefault(y_key, []).append(s)

        rows: list[VocabRow] = []
        for y_key in sorted(lines_map.keys()):
            line_spans = lines_map[y_key]
            line_spans.sort(key=lambda s: s.bbox[0])

            full_text = " ".join(s.text for s in line_spans).strip()
            if not full_text or len(full_text) < 2:
                continue

            order_no: int | None = None
            pinyin_src: str | None = None
            pos: str | None = None
            meaning_src: str | None = None

            cjk_match = RE_CJK_WORD.search(full_text)
            if cjk_match:
                word = cjk_match.group(0)
            else:
                tokens = [t.strip(",.:;") for t in full_text.split() if t.strip(",.:;")]
                if not tokens:
                    continue
                word = tokens[1] if tokens[0].isdigit() and len(tokens) > 1 else tokens[0]

            span_texts = [s.text.strip() for s in line_spans if s.text.strip()]
            if span_texts and span_texts[0].isdigit():
                order_no = int(span_texts[0])

            for st in span_texts:
                if any(c in PINYIN_VOWELS for c in st) and not pinyin_src:
                    pinyin_src = st
                if RE_POS.match(st) and not pos:
                    pos = st

            idx = full_text.find(word)
            if idx != -1:
                after = full_text[idx + len(word):].strip()
                if pinyin_src and pinyin_src in after:
                    after = after.replace(pinyin_src, "", 1).strip()
                if pos and pos in after:
                    after = after.replace(pos, "", 1).strip()
                if after:
                    meaning_src = after

            rows.append(
                VocabRow(
                    order_no=order_no or (len(rows) + 1),
                    word=word,
                    pinyin_src=pinyin_src,
                    pos=pos,
                    meaning_src=meaning_src,
                    source_page=source_page,
                    extract_by="regex",
                    needs_review=False,
                    review_reason=None,
                )
            )

        return rows

    @staticmethod
    def is_vocab_page(spans: list[TextSpan]) -> bool:
        """Nhận diện trang bắt đầu bảng từ mới, không quét mù toàn bài."""
        compact = re.sub(r"\s+", "", " ".join(s.text for s in spans)).lower()
        head = re.sub(r"\s+", "", " ".join(s.text for s in spans[:80])).lower()
        return (
            "newwords" in compact
            or "\u8bcd\u8bed\u8868" in compact
            or "\u751f\u8bcd" in head
            or "từmới" in compact
        )

    @staticmethod
    def _join_cell(spans: list[TextSpan]) -> str | None:
        text = " ".join(s.text.strip() for s in sorted(spans, key=lambda x: x.bbox[0]))
        text = re.sub(r"\s+([,.;:?!])", r"\1", text).strip()
        return text or None

    @staticmethod
    def table_bbox(
        spans: list[TextSpan],
    ) -> tuple[float, float, float, float] | None:
        """Tính crop bảng, dừng trước banner phần kế tiếp."""
        if not spans:
            return None
        width = max(s.bbox[2] for s in spans)
        height = max(s.bbox[3] for s in spans)
        header = next((s for s in spans if s.text.strip().upper() == "STT"), None)
        if header:
            y0 = max(0.0, header.bbox[1] - 45)
        else:
            y0 = 70.0
        stops = [
            s.bbox[1]
            for s in spans
            if s.bbox[1] > y0 + 100
            and s.bbox[0] > width * 0.72
            and s.text.strip().lower()
            in {"proper", "language", "note", "exercise", "exercises"}
        ]
        y1 = min(stops) - 15 if stops else height
        return (0.0, y0, width, max(y0 + 1, y1))

    @staticmethod
    def merge_bilingual_spans(
        chinese: list[TextSpan], latin: list[TextSpan]
    ) -> list[TextSpan]:
        """Giữ chữ Hán từ OCR Trung và phần Latin từ OCR Anh."""
        cjk = [
            span
            for span in chinese
            if any(RE_CJK_ONLY.match(ch) for ch in span.text)
        ]
        return cjk + latin

    def extract_table_spans(
        self, spans: list[TextSpan], source_page: int
    ) -> list[VocabRow]:
        """Bóc bảng bảy cột từ OCR spans có tọa độ."""
        if not spans:
            return []

        width = max((s.bbox[2] for s in spans), default=0.0)
        header = next((s for s in spans if s.text.strip().upper() == "STT"), None)
        header_y = header.bbox[1] if header else 80.0
        stop_candidates = [
            s.bbox[1]
            for s in spans
            if s.bbox[1] > header_y + 80
            and s.bbox[0] > width * 0.72
            and s.text.strip().lower() in {"proper", "language", "note", "exercise", "exercises"}
        ]
        table_end = min(stop_candidates) if stop_candidates else float("inf")
        body = [
            s
            for s in spans
            if header_y + 20 < s.bbox[1] < table_end - 10
        ]
        if width <= 0 or not body:
            return []

        lines: list[list[TextSpan]] = []
        for span in sorted(body, key=lambda s: ((s.bbox[1] + s.bbox[3]) / 2, s.bbox[0])):
            cy = (span.bbox[1] + span.bbox[3]) / 2
            if not lines:
                lines.append([span])
                continue
            last_cy = sum((s.bbox[1] + s.bbox[3]) / 2 for s in lines[-1]) / len(lines[-1])
            if abs(cy - last_cy) <= 16:
                lines[-1].append(span)
            else:
                lines.append([span])

        parsed: list[dict[str, object]] = []
        order_centers = [
            (s.bbox[0] + s.bbox[2]) / 2
            for s in body
            if s.bbox[0] < width * 0.20
            and re.fullmatch(r"\d{1,3}", s.text.strip())
        ]
        first_cut = (
            (statistics.median(order_centers) + 20.0) / width
            if order_centers
            else 0.12
        )
        cuts = (first_cut, 0.23, 0.31, 0.40, 0.52, 0.71)
        for line in lines:
            cells: list[list[TextSpan]] = [[] for _ in range(7)]
            for span in line:
                cx = ((span.bbox[0] + span.bbox[2]) / 2) / width
                col = sum(cx >= cut for cut in cuts)
                cells[col].append(span)

            word = "".join(
                ch
                for s in sorted(cells[1], key=lambda x: x.bbox[0])
                for ch in s.text
                if RE_CJK_ONLY.match(ch)
            )
            if word:
                raw_order = self._join_cell(cells[0]) or ""
                order_match = re.search(r"\d+", raw_order)
                parsed.append(
                    {
                        "order_no": int(order_match.group()) if order_match else None,
                        "word": word,
                        "pinyin": self._join_cell(cells[2]),
                        "pos": self._join_cell(cells[3]),
                        "hanviet": self._join_cell(cells[4]),
                        "meaning_en": self._join_cell(cells[5]),
                        "meaning_vi": self._join_cell(cells[6]),
                    }
                )
            elif parsed:
                for key, idx in (
                    ("pinyin", 2),
                    ("hanviet", 4),
                    ("meaning_en", 5),
                    ("meaning_vi", 6),
                ):
                    extra = self._join_cell(cells[idx])
                    if extra:
                        old = str(parsed[-1].get(key) or "")
                        parsed[-1][key] = f"{old} {extra}".strip()

        rows: list[VocabRow] = []
        for index, item in enumerate(parsed, start=1):
            word = str(item["word"])
            pinyin = str(item.get("pinyin") or "") or None
            reasons: list[str] = []
            if self.dict_db is not None:
                exact = [
                    candidate
                    for candidate in self.dict_db.find_words_by_hanzi(word)
                    if candidate.simplified == word
                ]
                if exact:
                    pinyin = exact[0].pinyin_tone
                    if not item.get("pos"):
                        item["pos"] = exact[0].pos
                elif len(word) > 1:
                    reasons.append("từ OCR không có trong từ điển")
                char_map = self.dict_db.get_chars(word)
                if len(char_map) != len(set(word)):
                    reasons.append("có chữ không tồn tại trong từ điển")
                elif pinyin:
                    choices = [
                        tuple(_plain_pinyin(reading) for reading in char_map[ch].readings)
                        or (_plain_pinyin(char_map[ch].pinyin),)
                        for ch in word
                    ]
                    expected = _plain_pinyin(pinyin)
                    if not any("".join(parts) == expected for parts in product(*choices)):
                        reasons.append("pinyin không khớp âm đọc từng chữ")
            if not pinyin:
                reasons.append("không đọc được pinyin")
            elif not RE_PINYIN_TEXT.fullmatch(pinyin) or not any(
                ch.lower() in "aeiouvüāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
                for ch in pinyin
            ):
                reasons.append("pinyin có ký tự OCR bất thường")
            rows.append(
                VocabRow(
                    order_no=int(item.get("order_no") or index),
                    word=word,
                    pinyin_src=pinyin,
                    pos=str(item.get("pos") or "") or None,
                    meaning_src=str(item.get("meaning_vi") or item.get("meaning_en") or "") or None,
                    source_page=source_page,
                    extract_by="regex",
                    needs_review=bool(reasons),
                    review_reason="; ".join(reasons) or None,
                    hanviet_src=str(item.get("hanviet") or "") or None,
                )
            )
        return rows

    def validate_rows(self, rows: list[VocabRow]) -> list[VocabRow]:
        """Kiểm chứng đầu ra OCR/Vision bằng từ điển và âm đọc từng chữ."""
        validated: list[VocabRow] = []
        for row in rows:
            word = row.word.strip()
            pinyin = row.pinyin_src
            reasons: list[str] = []
            if not word or not RE_CJK_ONLY.fullmatch(word):
                reasons.append("từ chứa ký tự không phải chữ Hán")
            if self.dict_db is not None and word:
                exact = [
                    item
                    for item in self.dict_db.find_words_by_hanzi(word)
                    if item.simplified == word
                ]
                if exact:
                    pinyin = exact[0].pinyin_tone
                chars = self.dict_db.get_chars(word)
                if len(chars) != len(set(word)):
                    reasons.append("có chữ không tồn tại trong từ điển")
                elif pinyin:
                    choices = [
                        tuple(_plain_pinyin(reading) for reading in chars[ch].readings)
                        or (_plain_pinyin(chars[ch].pinyin),)
                        for ch in word
                    ]
                    if not any(
                        "".join(parts) == _plain_pinyin(pinyin)
                        for parts in product(*choices)
                    ):
                        reasons.append("pinyin không khớp âm đọc từng chữ")
            if not pinyin:
                reasons.append("không đọc được pinyin")
            validated.append(
                VocabRow(
                    order_no=row.order_no,
                    word=word,
                    pinyin_src=pinyin,
                    pos=row.pos,
                    meaning_src=row.meaning_src,
                    source_page=row.source_page,
                    extract_by=row.extract_by,
                    needs_review=bool(reasons),
                    review_reason="; ".join(reasons) or None,
                    hanviet_src=row.hanviet_src,
                )
            )
        return validated

    def extract_lesson(
        self, pdf: PdfSource, lesson: LessonBoundary, ai_client: AiClient | None = None
    ) -> list[VocabRow]:
        """Định vị bảng trước, rồi bóc local; Vision chỉ là đường lui."""
        located: list[tuple[int, list[TextSpan]]] = []
        found = False
        for p in range(lesson.page_start, lesson.page_end + 1):
            if p >= pdf.page_count():
                break
            spans = pdf.spans(p)
            if self.is_vocab_page(spans):
                found = True
                located.append((p, spans))
            elif found:
                joined = " ".join(s.text for s in spans)
                if "STT" in joined or re.search(r"(?:^|\s)\d{1,2}(?:\s|$)", joined):
                    located.append((p, spans))
                break

        def extract_vision_batch(
            page_items: list[tuple[int, list[TextSpan] | None]],
            combine_images: bool = True,
        ) -> list[VocabRow]:
            images: list[bytes] = []
            for page, spans in page_items:
                bbox = self.table_bbox(spans) if spans else None
                image = (
                    pdf.get_page_crop_image_bytes(page, bbox, dpi=250)
                    if bbox and hasattr(pdf, "get_page_crop_image_bytes")
                    else pdf.get_page_image_bytes(page, dpi=200)
                )
                if image:
                    images.append(image)
            if not images:
                return []

            combined = (
                pdf.stack_image_bytes(images, max_width=1200)
                if combine_images and hasattr(pdf, "stack_image_bytes")
                else b""
            )
            if isinstance(combined, bytes) and combined:
                return self.extract_by_llm_image(
                    combined, ai_client, source_page=page_items[0][0] + 1
                )

            rows: list[VocabRow] = []
            for (page, _spans), image in zip(page_items, images):
                normalized = (
                    pdf.stack_image_bytes([image], max_width=1200)
                    if hasattr(pdf, "stack_image_bytes")
                    else b""
                )
                request_image = (
                    normalized
                    if isinstance(normalized, bytes) and normalized
                    else image
                )
                rows.extend(
                    self.extract_by_llm_image(
                        request_image, ai_client, source_page=page + 1
                    )
                )
            unique_rows: list[VocabRow] = []
            seen_words: set[str] = set()
            for row in rows:
                if row.word not in seen_words:
                    seen_words.add(row.word)
                    unique_rows.append(
                        replace(row, order_no=len(unique_rows) + 1)
                    )
            return unique_rows

        if not located:
            if ai_client and ai_client.is_configured():
                pages = [
                    (page, None)
                    for page in range(lesson.page_start, lesson.page_end + 1)
                    if page < pdf.page_count()
                ]
                vision_rows = extract_vision_batch(pages)
                return [
                    VocabRow(
                        order_no=index,
                        word=row.word,
                        pinyin_src=row.pinyin_src,
                        pos=row.pos,
                        meaning_src=row.meaning_src,
                        source_page=row.source_page,
                        extract_by=row.extract_by,
                        needs_review=row.needs_review,
                        review_reason=row.review_reason,
                        hanviet_src=row.hanviet_src,
                    )
                    for index, row in enumerate(self.validate_rows(vision_rows), start=1)
                ]
            return []

        local_rows: list[VocabRow] = []
        for page, spans in located:
            if hasattr(pdf, "ocr_spans"):
                latin = pdf.ocr_spans(page, language="en-US", dpi=250)
                spans = self.merge_bilingual_spans(spans, latin)
            local_rows.extend(self.extract_table_spans(spans, source_page=page + 1))
        if local_rows:
            seen: set[tuple[str, str | None]] = set()
            unique: list[VocabRow] = []
            for row in local_rows:
                key = (row.word, row.pinyin_src)
                if key not in seen:
                    seen.add(key)
                    unique.append(row)
            if not (ai_client and ai_client.is_configured()):
                return unique

            vision_rows = extract_vision_batch(located)
            checked = self.validate_rows(vision_rows)
            recovered_coverage = False
            coverage_is_low = (
                len(checked) < 10 or len(checked) * 4 < len(unique) * 3
            )
            if coverage_is_low and len(unique) >= 15 and len(located) > 1:
                individual = self.validate_rows(
                    extract_vision_batch(located, combine_images=False)
                )
                individual_score = len(individual) - sum(
                    row.needs_review for row in individual
                )
                checked_score = len(checked) - sum(
                    row.needs_review for row in checked
                )
                if len(individual) >= 15:
                    checked = individual
                    recovered_coverage = True
                elif individual_score > checked_score:
                    checked = individual
            if recovered_coverage:
                return checked
            local_score = len(unique) - sum(row.needs_review for row in unique)
            vision_score = len(checked) - sum(row.needs_review for row in checked)
            return checked if vision_score > local_score else unique

        if ai_client and ai_client.is_configured():
            vision_rows = extract_vision_batch(located)
            return self.validate_rows(vision_rows)
        return []
