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
from math import ceil
from typing import TYPE_CHECKING

from hanzi_app.adapter.aiclient import AiClientError, AiRateLimitError
from hanzi_app.data.models import (
    BlockCoverage,
    ExtractionResult,
    TextSpan,
    VocabBlock,
    VocabRow,
)

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
    return re.sub(r"\s+", "", " ".join(span.text for span in spans)).lower()


_VOCAB_HEADING_MARKERS = (
    "newwords",
    "vocabulary",
    "词语表",
    "生词",
    "新词",
    "từmới",
)
_PINYIN_INITIALS = (
    "",
    "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h",
    "j", "q", "x", "zh", "ch", "sh", "r", "z", "c", "s", "y", "w",
)
_PINYIN_FINALS = (
    "a", "ai", "an", "ang", "ao", "e", "ei", "en", "eng", "er",
    "i", "ia", "ian", "iang", "iao", "ie", "in", "ing", "iong", "iu",
    "o", "ong", "ou", "u", "ua", "uai", "uan", "uang", "ui", "un", "uo",
    "v", "ve", "van", "vn",
)
_PINYIN_SYLLABLES = frozenset(
    initial + final
    for initial in _PINYIN_INITIALS
    for final in _PINYIN_FINALS
)


def _line_has_vocab_heading(spans: list[TextSpan]) -> bool:
    compact = _compact_line(spans)
    return any(
        compact.startswith(marker) and len(compact) <= len(marker) + 24
        for marker in _VOCAB_HEADING_MARKERS
    )


def _has_vocab_heading(spans: list[TextSpan]) -> bool:
    if spans and any(not hasattr(span, "bbox") for span in spans):
        return _line_has_vocab_heading(spans)
    return any(_line_has_vocab_heading(line) for line in _line_groups(spans))


def _segment_plain_pinyin(value: str) -> tuple[str, ...] | None:
    paths: dict[int, tuple[str, ...]] = {0: ()}
    for start in range(len(value)):
        if start not in paths:
            continue
        for end in range(start + 1, min(len(value), start + 6) + 1):
            syllable = value[start:end]
            if syllable in _PINYIN_SYLLABLES and end not in paths:
                paths[end] = paths[start] + (syllable,)
    if len(value) in paths:
        return paths[len(value)]
    if value.endswith("r") and len(value) - 1 in paths:
        return paths[len(value) - 1]
    return None


def _can_segment_numbered_pinyin(value: str) -> bool:
    reachable = {0}
    for start in range(len(value)):
        if start not in reachable or value[start].isdigit():
            continue
        for end in range(start + 1, min(len(value), start + 6) + 1):
            if value[end - 1].isdigit():
                break
            syllable = _plain_pinyin(value[start:end])
            if syllable not in _PINYIN_SYLLABLES:
                continue
            next_index = end
            if next_index < len(value) and value[next_index] in "012345":
                next_index += 1
            reachable.add(next_index)
    return len(value) in reachable


def _is_distinctive_plain_syllable(syllable: str) -> bool:
    distinctive_initials = {"zh", "ch", "sh", "q", "x", "z", "c"}
    distinctive_finals = {
        "ai", "ao", "ang", "eng", "ong", "ian", "iang", "iao",
        "iong", "iu", "ua", "uai", "uan", "uang", "ui", "uo",
        "v", "ve", "van", "vn",
    }
    initial = max(
        (
            candidate
            for candidate in _PINYIN_INITIALS
            if syllable.startswith(candidate)
            and syllable[len(candidate):] in _PINYIN_FINALS
        ),
        key=len,
        default="",
    )
    final = syllable[len(initial):]
    return initial in distinctive_initials or final in distinctive_finals


def _pinyin_evidence_strength(text: str) -> int:
    value = text.strip()
    if not value or not re.fullmatch(
        r"[A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ0-5:'’ -]+",
        value,
    ):
        return 0
    raw_tokens = [
        token for token in re.split(r"[\s'’-]+", value) if token
    ]
    segmentations: list[tuple[str, ...]] = []
    has_number = any(character.isdigit() for character in value)
    for token in raw_tokens:
        if any(character.isdigit() for character in token):
            if not _can_segment_numbered_pinyin(token):
                return 0
            continue
        segmentation = _segment_plain_pinyin(_plain_pinyin(token))
        if segmentation is None:
            return 0
        segmentations.append(segmentation)

    has_tone_mark = any(character in PINYIN_VOWELS for character in value)
    has_u_colon = "u:" in value.lower()
    boundary_is_syllabic = (
        len(raw_tokens) >= 2
        and all(len(segmentation) == 1 for segmentation in segmentations)
    )
    if has_number or has_tone_mark or has_u_colon or boundary_is_syllabic:
        return 2
    distinctive_plain = any(
        _is_distinctive_plain_syllable(syllable)
        for segmentation in segmentations
        for syllable in segmentation
    )
    return 1 if distinctive_plain else 0


def _is_pinyin_text(text: str) -> bool:
    return _pinyin_evidence_strength(text) > 0

def _numeric_column_clusters(
    spans: list[TextSpan],
) -> list[list[tuple[int, float, list[TextSpan]]]]:
    candidates: list[tuple[int, float, list[TextSpan]]] = []
    for line in _line_groups(spans):
        for span in line:
            if re.fullmatch(r"\d{1,3}", span.text.strip()):
                candidates.append(
                    (
                        int(span.text.strip()),
                        (span.bbox[0] + span.bbox[2]) / 2,
                        line,
                    )
                )
    clusters: list[list[tuple[int, float, list[TextSpan]]]] = []
    for candidate in sorted(candidates, key=lambda item: item[1]):
        if not clusters:
            clusters.append([candidate])
            continue
        center = sum(item[1] for item in clusters[-1]) / len(clusters[-1])
        if abs(candidate[1] - center) <= 35:
            clusters[-1].append(candidate)
        else:
            clusters.append([candidate])
    return [
        cluster
        for cluster in clusters
        if len({round((item[2][0].bbox[1] + item[2][0].bbox[3]) / 2) for item in cluster}) >= 2
    ]


def _region_evidence(
    spans: list[TextSpan],
) -> tuple[
    list[list[TextSpan]],
    list[list[TextSpan]],
    list[int],
    bool,
    bool,
    int,
]:
    row_lines: list[list[TextSpan]] = []
    cjk_centers: list[float] = []
    pinyin_centers: list[float] = []
    third_centers: list[float] = []
    strong_pinyin_rows = 0
    for line in _line_groups(spans):
        numeric = [
            span for span in line
            if re.fullmatch(r"\d{1,3}", span.text.strip())
        ]
        cjk = [span for span in line if RE_CJK_WORD.search(span.text)]
        pinyin_evidence = [
            (span, _pinyin_evidence_strength(span.text))
            for span in line
            if _pinyin_evidence_strength(span.text) > 0
        ]
        pinyin = [span for span, _strength in pinyin_evidence]
        if cjk and pinyin:
            row_lines.append(line)
            if any(strength >= 2 for _span, strength in pinyin_evidence):
                strong_pinyin_rows += 1
            cjk_centers.append((cjk[0].bbox[0] + cjk[0].bbox[2]) / 2)
            pinyin_centers.append((pinyin[0].bbox[0] + pinyin[0].bbox[2]) / 2)
            other = [
                span for span in line
                if span not in numeric and span not in cjk and span not in pinyin
            ]
            if other:
                third_centers.append((other[0].bbox[0] + other[0].bbox[2]) / 2)

    clusters = _numeric_column_clusters(spans)
    aligned_orders = max(
        clusters,
        key=lambda cluster: (len(cluster), -min(item[1] for item in cluster)),
        default=[],
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
        and len(third_centers) >= 2
        and max(cjk_centers) - min(cjk_centers) <= 35
        and max(pinyin_centers) - min(pinyin_centers) <= 35
        and max(third_centers) - min(third_centers) <= 35
    )
    return (
        row_lines,
        order_lines,
        unique_orders,
        sequential,
        aligned,
        strong_pinyin_rows,
    )

def _signal_line(line: list[TextSpan]) -> bool:
    if _line_has_vocab_heading(line):
        return True
    if any(re.fullmatch(r"\d{1,3}", span.text.strip()) for span in line):
        return True
    return (
        any(RE_CJK_WORD.search(span.text) for span in line)
        and any(_is_pinyin_text(span.text) for span in line)
    )


def _split_page_regions(spans: list[TextSpan]) -> list[list[TextSpan]]:
    signal_lines = [line for line in _line_groups(spans) if _signal_line(line)]
    if not signal_lines:
        return []
    heights = [
        max(span.bbox[3] for span in line) - min(span.bbox[1] for span in line)
        for line in signal_lines
    ]
    gap_limit = max(72.0, statistics.median(heights) * 5)
    vertical_bands: list[list[list[TextSpan]]] = []
    for line in signal_lines:
        if not vertical_bands:
            vertical_bands.append([line])
            continue
        previous_bottom = max(
            span.bbox[3] for previous in vertical_bands[-1] for span in previous
        )
        current_top = min(span.bbox[1] for span in line)
        if current_top - previous_bottom > gap_limit:
            vertical_bands.append([line])
        else:
            vertical_bands[-1].append(line)

    regions: list[list[TextSpan]] = []
    for band_lines in vertical_bands:
        band = [span for line in band_lines for span in line]
        numeric_clusters = _numeric_column_clusters(band)
        if len(numeric_clusters) >= 2:
            seeds = sorted(
                sum(item[1] for item in cluster) / len(cluster)
                for cluster in numeric_clusters
            )
        else:
            heading_centers = sorted(
                (span.bbox[0] + span.bbox[2]) / 2
                for span in band
                if _line_has_vocab_heading([span])
            )
            seeds = heading_centers if len(heading_centers) >= 2 else []
        if len(seeds) < 2:
            regions.append(band)
            continue
        cuts = [
            (left + right) / 2 for left, right in zip(seeds, seeds[1:])
        ]
        for index in range(len(seeds)):
            left = cuts[index - 1] if index else float("-inf")
            right = cuts[index] if index < len(cuts) else float("inf")
            region = [
                span for span in band
                if left <= (span.bbox[0] + span.bbox[2]) / 2 < right
            ]
            if region:
                regions.append(region)
    return regions

def render_block_crop(pdf: PdfSource, block: VocabBlock, dpi: int = 250) -> bytes:
    """Render exactly the persisted page and rectangle of one vocabulary block."""
    return pdf.get_page_crop_image_bytes(
        block.page_index, block.bbox, dpi=dpi
    )

class VocabExtractor:
    """Bóc tách từ vựng từ bài học theo kiến trúc 2 Lớp sạch sẽ, minh bạch."""

    def __init__(self, dict_db=None) -> None:
        self.dict_db = dict_db
        self.lesson_ai_attempts = 0

    def locate_blocks(
        self, pdf: PdfSource, lesson: LessonBoundary
    ) -> list[VocabBlock]:
        """Locate every independent vocabulary table region inside a lesson."""
        candidates: list[tuple[
            int,
            float,
            float,
            tuple[float, float, float, float],
            int | None,
            int | None,
            int | None,
        ]] = []
        page_count = pdf.page_count()
        start = max(0, lesson.page_start)
        end = min(lesson.page_end, page_count - 1)
        for page_index in range(start, end + 1):
            spans = list(pdf.spans(page_index))
            for region in _split_page_regions(spans):
                (
                    row_lines,
                    order_lines,
                    orders,
                    sequential_orders,
                    aligned_columns,
                    strong_pinyin_rows,
                ) = _region_evidence(region)
                has_heading = _has_vocab_heading(region)
                has_rows = len(row_lines) >= 2 and (
                    strong_pinyin_rows >= 1
                    or has_heading
                    or sequential_orders
                )
                signals = (
                    has_heading,
                    has_rows,
                    sequential_orders or aligned_columns,
                )
                if sum(signals) < 2:
                    continue

                relevant_lines = list(row_lines)
                relevant_lines.extend(order_lines)
                relevant_lines.extend(
                    line
                    for line in _line_groups(region)
                    if _line_has_vocab_heading(line)
                )
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
                        bbox[0],
                        bbox,
                        expected_rows or None,
                        orders[0] if orders else None,
                        orders[-1] if orders else None,
                    )
                )

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
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
                _x_start,
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
        self,
        image_bytes: bytes,
        ai_client: AiClient,
        source_page: int,
        issue_context: str | None = None,
    ) -> list[VocabRow]:
        """Issue one Vision request; retry budgeting belongs to the orchestrator."""
        try:
            if issue_context is None:
                raw_list = ai_client.extract_vocab_from_image(image_bytes)
            else:
                raw_list = ai_client.extract_vocab_from_image(
                    image_bytes, issue_context=issue_context
                )
        except (AiRateLimitError, AiClientError):
            raise
        except Exception:
            return []
        if not raw_list:
            raise RuntimeError("Vision không trả về dữ liệu từ mới")

        rows: list[VocabRow] = []
        seen_words: set[str] = set()
        for item in raw_list:
            word = _optional_text(item.get("word")) or ""
            if not word or word in seen_words:
                continue
            seen_words.add(word)
            rows.append(
                VocabRow(
                    order_no=int(item.get("order_no") or len(rows) + 1),
                    word=word,
                    pinyin_src=_optional_text(item.get("pinyin")),
                    pos=_optional_text(item.get("pos")),
                    meaning_src=_optional_text(
                        item.get("meaning_vi", item.get("meaning_en", item.get("meaning")))
                    ),
                    source_page=source_page,
                    extract_by="vision",
                    needs_review=True,
                    review_reason="đầu ra Vision chưa qua validator",
                    hanviet_src=_optional_text(item.get("hanviet")),
                )
            )
        if not rows:
            raise RuntimeError("Vision không trả về dữ liệu từ mới")
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
        """Nhận diện tiêu đề bảng từ mới bằng các mẫu ngôn ngữ tổng quát."""
        return _has_vocab_heading(spans)
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
        aliases = {
            "order": {"stt", "no.", "序号", "编号"},
            "word": {"chữhán", "hanzi", "汉字", "chữtrung"},
            "pinyin": {"pinyin", "拼音"},
            "pos": {"từloại", "词性", "pos"},
            "hanviet": {"hán-việt", "hánviệt", "han-viet"},
            "meaning_en": {"english", "nghĩaanh", "英语"},
            "meaning_vi": {"nghĩaviệt", "nghĩa", "vietnamese", "越南语"},
        }

        def header_role(span: TextSpan) -> str | None:
            label = re.sub(r"\s+", "", span.text.strip().lower())
            return next(
                (
                    role
                    for role, labels in aliases.items()
                    if label in labels
                ),
                None,
            )

        lines = _line_groups(spans)
        header_line = max(
            lines,
            key=lambda line: sum(header_role(span) is not None for span in line),
            default=[],
        )
        if not any(header_role(span) is not None for span in header_line):
            header_line = []
        header_roles = {
            role: (span.bbox[0] + span.bbox[2]) / 2
            for span in header_line
            if (role := header_role(span)) is not None
        }
        table_end = float("inf")
        if header_line:
            header_y = min(span.bbox[1] for span in header_line)
            stop_candidates = [
                span.bbox[1]
                for span in spans
                if span.bbox[1] > header_y + 80
                and span.bbox[0] > width * 0.72
                and span.text.strip().lower()
                in {"proper", "language", "note", "exercise", "exercises"}
            ]
            if stop_candidates:
                table_end = min(stop_candidates) - 10
        body_lines = [
            line
            for line in lines
            if line is not header_line
            and min(span.bbox[1] for span in line) < table_end
            and any(RE_CJK_WORD.search(span.text) for span in line)
        ]
        body = [span for line in body_lines for span in line]
        if width <= 0 or not body:
            return []

        if "word" in header_roles and len(header_roles) >= 2:
            columns = sorted(header_roles.items(), key=lambda item: item[1])
            cuts = [
                (left[1] + right[1]) / 2
                for left, right in zip(columns, columns[1:])
            ]
            roles = [role for role, _center in columns]
            rows: list[VocabRow] = []
            for line in body_lines:
                cells = {role: [] for role in roles}
                for span in line:
                    center = (span.bbox[0] + span.bbox[2]) / 2
                    cells[roles[sum(center >= cut for cut in cuts)]].append(
                        span
                    )
                word = "".join(
                    ch
                    for span in sorted(
                        cells.get("word", []), key=lambda item: item.bbox[0]
                    )
                    for ch in span.text
                    if RE_CJK_ONLY.match(ch)
                )
                if not word:
                    continue
                raw_order = self._join_cell(cells.get("order", [])) or ""
                match = re.search(r"\d+", raw_order)
                pinyin = self._join_cell(cells.get("pinyin", []))
                rows.append(VocabRow(
                    int(match.group()) if match else len(rows) + 1,
                    word,
                    pinyin,
                    self._join_cell(cells.get("pos", [])),
                    self._join_cell(cells.get("meaning_vi", []))
                    or self._join_cell(cells.get("meaning_en", [])),
                    source_page,
                    "regex",
                    pinyin is None,
                    "không đọc được pinyin" if pinyin is None else None,
                    self._join_cell(cells.get("hanviet", [])),
                ))
            return rows

        tolerance = max(12.0, width * 0.02)
        clusters: list[list[TextSpan]] = []
        for span in sorted(body, key=lambda item: item.bbox[0]):
            if not clusters:
                clusters.append([span])
                continue
            center = statistics.median(
                item.bbox[0] for item in clusters[-1]
            )
            if abs(span.bbox[0] - center) <= tolerance:
                clusters[-1].append(span)
            else:
                clusters.append([span])
        repeated = [
            cluster
            for cluster in clusters
            if len({
                round((span.bbox[1] + span.bbox[3]) / 2)
                for span in cluster
            }) >= 2
        ]
        if 2 <= len(repeated) <= 7:
            centers = [
                statistics.median(span.bbox[0] for span in cluster)
                for cluster in repeated
            ]
            cjk_counts = [
                sum(
                    bool(RE_CJK_ONLY.fullmatch(span.text.strip()))
                    for span in cluster
                )
                for cluster in repeated
            ]
            word_column = max(
                range(len(repeated)), key=lambda index: cjk_counts[index]
            )
            if cjk_counts[word_column]:
                required_rows = ceil(len(body_lines) * 0.6)
                digit_counts = [
                    sum(
                        bool(re.fullmatch(r"\d{1,3}", span.text.strip()))
                        for span in cluster
                    )
                    for cluster in repeated
                ]
                order_candidates = [
                    index
                    for index, count in enumerate(digit_counts)
                    if index != word_column and count >= required_rows
                ]
                order_column = min(
                    order_candidates,
                    key=lambda index: (-digit_counts[index], centers[index]),
                    default=None,
                )
                pos_counts = [
                    sum(bool(RE_POS.fullmatch(span.text.strip())) for span in cluster)
                    for cluster in repeated
                ]
                pos_candidates = [
                    index
                    for index, count in enumerate(pos_counts)
                    if index not in {word_column, order_column}
                    and count >= required_rows
                ]
                pos_column = min(
                    pos_candidates,
                    key=lambda index: (-pos_counts[index], centers[index]),
                    default=None,
                )

                def is_unambiguous_pinyin(value: str) -> bool:
                    if not _pinyin_evidence_strength(value):
                        return False
                    lower = value.lower()
                    if any(
                        character in "üāǎēěīǐōǒūǔǖǘǚǜ"
                        for character in lower
                    ) or "u:" in lower or any(
                        character.isdigit() for character in lower
                    ):
                        return True
                    return " " not in lower and _pinyin_evidence_strength(value) == 1

                pinyin_counts = [
                    sum(is_unambiguous_pinyin(span.text) for span in cluster)
                    for cluster in repeated
                ]
                pinyin_candidates = [
                    index
                    for index, count in enumerate(pinyin_counts)
                    if index not in {word_column, order_column, pos_column}
                    and count >= required_rows
                    and count == len(repeated[index])
                ]
                pinyin_column = min(
                    pinyin_candidates,
                    key=lambda index: (-pinyin_counts[index], centers[index]),
                    default=None,
                )
                remaining = [
                    index
                    for index in range(len(repeated))
                    if index not in {
                        word_column,
                        order_column,
                        pos_column,
                        pinyin_column,
                    }
                    and centers[index] > centers[word_column]
                ]
                hanviet_column = remaining[0] if len(remaining) >= 2 else None
                meaning_column = remaining[-1] if remaining else None
                inferred_rows: list[VocabRow] = []
                for line in body_lines:
                    cells: list[list[TextSpan]] = [
                        [] for _center in centers
                    ]
                    for span in line:
                        column = min(
                            range(len(centers)),
                            key=lambda index: abs(
                                span.bbox[0] - centers[index]
                            ),
                        )
                        cells[column].append(span)
                    word = "".join(
                        ch
                        for span in sorted(
                            cells[word_column],
                            key=lambda item: item.bbox[0],
                        )
                        for ch in span.text
                        if RE_CJK_ONLY.match(ch)
                    )
                    if not word:
                        continue
                    raw_order = (
                        self._join_cell(cells[order_column])
                        if order_column is not None
                        else None
                    ) or ""
                    match = re.search(r"\d+", raw_order)
                    pinyin = (
                        self._join_cell(cells[pinyin_column])
                        if pinyin_column is not None
                        else None
                    )
                    if pinyin is not None and not is_unambiguous_pinyin(pinyin):
                        pinyin = None
                    inferred_rows.append(VocabRow(
                        int(match.group()) if match else len(inferred_rows) + 1,
                        word,
                        pinyin,
                        self._join_cell(cells[pos_column])
                        if pos_column is not None
                        else None,
                        self._join_cell(cells[meaning_column])
                        if meaning_column is not None
                        else None,
                        source_page,
                        "regex",
                        pinyin is None,
                        "không đọc được pinyin" if pinyin is None else None,
                        self._join_cell(cells[hanviet_column])
                        if hanviet_column is not None
                        else None,
                    ))
                if inferred_rows:
                    return inferred_rows
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

    @staticmethod
    def _row_key(
        row: VocabRow,
    ) -> tuple[str, str | None, int | None, int | None]:
        return (
            row.word,
            row.pinyin_src,
            row.source_block_id,
            row.order_no,
        )

    def merge_block_rows(
        self,
        local_rows: list[VocabRow],
        ai_rows: list[VocabRow],
    ) -> list[VocabRow]:
        """Merge evidence without collapsing repeated words in other blocks."""
        merged: list[VocabRow] = []
        seen: set[tuple[str, str | None, int | None, int | None]] = set()
        for row in [*local_rows, *ai_rows]:
            key = self._row_key(row)
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
        return sorted(
            merged,
            key=lambda row: (
                row.source_page,
                row.source_block_id if row.source_block_id is not None else -1,
                row.order_no if row.order_no is not None else 10**9,
            ),
        )

    def validate_block_coverage(
        self,
        block: VocabBlock,
        local_rows: list[VocabRow],
        ai_rows: list[VocabRow],
        final_rows: list[VocabRow],
    ) -> BlockCoverage:
        """Reject a non-empty block when its row evidence is still incomplete."""
        issues: list[str] = []
        keys = [self._row_key(row) for row in final_rows]
        duplicate_in_source = any(
            len(source_keys) != len(set(source_keys))
            for source_keys in (
                [self._row_key(row) for row in local_rows],
                [self._row_key(row) for row in ai_rows],
            )
        )
        if duplicate_in_source or len(keys) != len(set(keys)):
            issues.append("abnormal_exact_duplicates")
        if not final_rows:
            issues.append("zero_rows")

        missing_orders: tuple[int, ...] = ()
        if block.first_order is not None and block.last_order is not None:
            observed = {
                row.order_no for row in final_rows if row.order_no is not None
            }
            missing_orders = tuple(
                order
                for order in range(block.first_order, block.last_order + 1)
                if order not in observed
            )
            if missing_orders:
                issues.append("missing_orders")

        if block.expected_rows is None:
            sources_agree = (
                len(local_rows) > 0
                and len(ai_rows) > 0
                and len(local_rows) == len(ai_rows)
            )
            if not sources_agree:
                issues.append("expected_rows_unknown_needs_review")
        else:
            if len(final_rows) != block.expected_rows:
                issues.append("expected_row_mismatch")
            if len(final_rows) < ceil(block.expected_rows * 0.8):
                issues.append("coverage_below_80_percent")

        blocking = {
            "abnormal_exact_duplicates",
            "zero_rows",
            "missing_orders",
            "coverage_below_80_percent",
            "expected_rows_unknown_needs_review",
        }
        return BlockCoverage(
            block.id,
            block.expected_rows,
            len(local_rows),
            len(ai_rows),
            len(final_rows),
            missing_orders,
            tuple(dict.fromkeys(issues)),
            not any(issue in blocking for issue in issues),
        )

    @staticmethod
    def _spans_in_block(
        spans: list[TextSpan], block: VocabBlock
    ) -> list[TextSpan]:
        x0, y0, x1, y1 = block.bbox
        return [
            span
            for span in spans
            if x0 <= (span.bbox[0] + span.bbox[2]) / 2 <= x1
            and y0 <= (span.bbox[1] + span.bbox[3]) / 2 <= y1
        ]

    def _extract_local_block(
        self, pdf: PdfSource, block: VocabBlock
    ) -> list[VocabRow]:
        chinese = self._spans_in_block(
            list(pdf.spans(block.page_index)), block
        )
        latin = (
            self._spans_in_block(
                list(pdf.ocr_spans(
                    block.page_index, language="en-US", dpi=250
                )),
                block,
            )
            if hasattr(pdf, "ocr_spans")
            else []
        )
        merged = self.merge_bilingual_spans(chinese, latin)
        unique_spans = list({
            (span.text, span.bbox, span.font_size, span.is_ocr): span
            for span in merged
        }.values())
        return [
            replace(row, source_block_id=block.id)
            for row in self.extract_table_spans(
                unique_spans, source_page=block.page_index + 1
            )
        ]

    @staticmethod
    def _coverage_issue(
        report: BlockCoverage, issue: str
    ) -> BlockCoverage:
        return replace(
            report,
            issues=tuple(dict.fromkeys((*report.issues, issue))),
            passed=False,
        )

    @staticmethod
    def _block_issue_context(
        block: VocabBlock, report: BlockCoverage
    ) -> str:
        if report.missing_orders:
            missing = ", ".join(str(value) for value in report.missing_orders)
            detail = f"thiếu STT {missing}"
        else:
            detail = ", ".join(report.issues) or "coverage chưa đạt"
        return f"Block {block.block_no}: {detail}; chỉ chép các dòng còn thiếu"

    def extract_blocks(
        self,
        pdf: PdfSource,
        blocks: list[VocabBlock],
        ai_client: AiClient | None = None,
    ) -> ExtractionResult:
        """Extract blocks with a three-request budget shared by one lesson."""
        local_rows: list[list[VocabRow]] = []
        ai_rows: list[list[VocabRow]] = []
        final_rows: list[list[VocabRow]] = []
        reports: list[BlockCoverage] = []
        attempt_counts = [0 for _block in blocks]

        for block in blocks:
            local = self._extract_local_block(pdf, block)
            final = self.merge_block_rows(local, [])
            report = self.validate_block_coverage(block, local, [], final)
            local_rows.append(local)
            ai_rows.append([])
            final_rows.append(final)
            reports.append(report)

        prior_attempts = max(
            self.lesson_ai_attempts,
            sum(block.ai_attempts for block in blocks),
        )
        remaining = max(0, 3 - prior_attempts)
        queue = [
            index
            for index, report in enumerate(reports)
            if not report.passed
        ]
        attempts = 0
        configured = ai_client is not None and ai_client.is_configured()

        while configured and queue and attempts < remaining:
            index = queue.pop(0)
            block = blocks[index]
            image = render_block_crop(pdf, block)
            if not image:
                reports[index] = self._coverage_issue(
                    reports[index], "crop_empty"
                )
                continue

            attempts += 1
            attempt_counts[index] += 1
            context = self._block_issue_context(block, reports[index])
            try:
                extracted = [
                    replace(row, source_block_id=block.id)
                    for row in self.extract_by_llm_image(
                        image,
                        ai_client,
                        block.page_index + 1,
                        issue_context=context,
                    )
                ]
            except AiRateLimitError:
                reports[index] = self._coverage_issue(
                    reports[index], "rate_limited"
                )
                break
            except AiClientError:
                reports[index] = self._coverage_issue(
                    reports[index], "ai_error"
                )
                break
            except RuntimeError:
                reports[index] = self._coverage_issue(
                    reports[index], "ai_empty"
                )
                if attempts < remaining:
                    queue.append(index)
                continue

            ai_rows[index].extend(extracted)
            final_rows[index] = self.merge_block_rows(
                local_rows[index], ai_rows[index]
            )
            reports[index] = self.validate_block_coverage(
                block,
                local_rows[index],
                ai_rows[index],
                final_rows[index],
            )
            if not reports[index].passed and attempts < remaining:
                queue.append(index)

        updated: list[VocabBlock] = []
        all_rows: list[VocabRow] = []
        for index, block in enumerate(blocks):
            report = reports[index]
            status = (
                "ai_ok" if report.passed and ai_rows[index]
                else "local_ok" if report.passed
                else "incomplete"
            )
            updated.append(replace(
                block,
                status=status,
                ai_attempts=block.ai_attempts + attempt_counts[index],
            ))
            all_rows.extend(final_rows[index])

        self.lesson_ai_attempts = prior_attempts + attempts
        return ExtractionResult(
            tuple(self.merge_block_rows(all_rows, [])),
            tuple(reports),
            tuple(updated),
            attempts,
            bool(blocks) and all(report.passed for report in reports),
        )

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
                    source_block_id=row.source_block_id,
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
