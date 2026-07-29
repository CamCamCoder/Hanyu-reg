"""Bộ phân tách bài học trong sách PDF theo thang nhiều nấc (Regex, LLM API, Book Presets, Heuristics).

Tầng service: nhận danh sách PageSummary từ pdfsource, trả về danh sách LessonBoundary.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from hanzi_app.data.models import (
    BoundaryEvidence,
    BoundaryIssue,
    BoundaryReport,
    LessonBoundary,
    PageEvidence,
    PageSummary,
    SplitResult,
)

if TYPE_CHECKING:
    from hanzi_app.adapter.aiclient import AiClient

# Biểu thức chính quy tìm tiêu đề bài học dạng 第X课 hoặc Bài X hoặc Lesson X
RE_LESSON_HEADER = re.compile(
    r"(?:第\s*(\d+|[一二三四五六七八九十百]+)\s*课|^Bài\s+(\d+)|^Lesson\s+(\d+))",
    re.IGNORECASE,
)

# Chữ số Hán tự sang số tự nhiên
CN_NUMS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


ERROR_CODES = {
    "duplicate_lesson",
    "missing_lesson",
    "start_not_increasing",
    "overlap",
    "page_out_of_range",
    "toc_heading_conflict",
}

RE_TOC_ROW = re.compile(
    r"^\s*(?:Lesson\s*|Bài\s*|第\s*)?(\d+)"
    r"(?:\s*(?:Lesson|Bài|课))?\s+(.+?)\s+(\d+)\s*$",
    re.IGNORECASE,
)


def _parse_cn_num(num_str: str) -> int:
    """Chuyển đổi chuỗi số Hán tự hoặc số La Mã sang số nguyên."""
    if not num_str:
        return 1
    num_str = num_str.strip()
    if num_str.isdigit():
        return int(num_str)
    if num_str in CN_NUMS:
        return CN_NUMS[num_str]
    if "十" in num_str:
        parts = num_str.split("十")
        tens = CN_NUMS.get(parts[0], 1) if parts[0] else 1
        ones = CN_NUMS.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    return 1


class Splitter:
    """Điều phối phân tách bài học trong sách."""

    @staticmethod
    def accepts(summaries: list[PageSummary]) -> tuple[bool, str]:
        """Kiểm tra điều kiện chấp nhận sách."""
        if not summaries:
            return False, "Sách rỗng (0 trang)"

        total_cjk = sum(s.cjk for s in summaries)
        total_pages = len(summaries)

        if total_pages < 2 and total_cjk == 0:
            return False, "Sách không có nội dung văn bản"

        return True, "Hợp lệ"

    @staticmethod
    def _toc_rows(toc_text: str) -> list[tuple[int, str, int]]:
        """Read lesson number, title and printed page from simple TOC rows."""
        rows: list[tuple[int, str, int]] = []
        for line in toc_text.splitlines():
            match = RE_TOC_ROW.match(line)
            if match:
                lesson_no, title, printed_page = match.groups()
                rows.append((int(lesson_no), title.strip(), int(printed_page)))
        return rows

    @staticmethod
    def _page_offset(evidence: list[PageEvidence]) -> int | None:
        """Infer a printed-to-PDF offset only from repeated heading-page pairs."""
        pairs = {
            (item.printed_page, item.pdf_page)
            for item in evidence
            if item.heading_lesson_no is not None and item.printed_page is not None
        }
        offsets = [pdf_page - printed_page for printed_page, pdf_page in pairs]
        if len(offsets) < 2:
            return None
        offset, count = sorted(
            Counter(offsets).items(), key=lambda item: (-item[1], item[0])
        )[0]
        return offset if count >= 2 else None

    @staticmethod
    def _total_pages(
        summaries: list[PageSummary], evidence: list[PageEvidence]
    ) -> int:
        pages = [item.pdf_page for item in summaries]
        pages.extend(item.pdf_page for item in evidence)
        return max(pages, default=-1) + 1

    def validate(
        self,
        boundaries: list[LessonBoundary] | tuple[LessonBoundary, ...],
        evidence: list[BoundaryEvidence] | tuple[BoundaryEvidence, ...],
        total_pages: int,
    ) -> BoundaryReport:
        """Check lesson sequence and source agreement before importing it."""
        issues: list[BoundaryIssue] = []
        lesson_counts = Counter(boundary.index_no for boundary in boundaries)

        for lesson_no, count in sorted(lesson_counts.items()):
            if count > 1:
                issues.append(
                    BoundaryIssue(
                        "duplicate_lesson", "error", lesson_no, None,
                        f"Lesson {lesson_no} occurs {count} times.",
                    )
                )

        positive_numbers = {number for number in lesson_counts if number > 0}
        if positive_numbers:
            for lesson_no in range(1, max(positive_numbers) + 1):
                if lesson_no not in positive_numbers:
                    issues.append(
                        BoundaryIssue(
                            "missing_lesson", "error", lesson_no, None,
                            f"Lesson {lesson_no} is missing.",
                        )
                    )

        ordered = sorted(boundaries, key=lambda boundary: (boundary.index_no, boundary.page_start))
        for previous, current in zip(ordered, ordered[1:]):
            if current.page_start <= previous.page_start:
                issues.append(
                    BoundaryIssue(
                        "start_not_increasing", "error", current.index_no,
                        current.page_start,
                        "Lesson starts must increase with lesson number.",
                    )
                )
            if current.page_start <= previous.page_end:
                issues.append(
                    BoundaryIssue(
                        "overlap", "error", current.index_no, current.page_start,
                        "Lesson pages overlap.",
                    )
                )

        for boundary in boundaries:
            if (
                boundary.page_start < 0
                or boundary.page_end < 0
                or boundary.page_start >= total_pages
                or boundary.page_end >= total_pages
            ):
                issues.append(
                    BoundaryIssue(
                        "page_out_of_range", "error", boundary.index_no,
                        boundary.page_start,
                        "Lesson page lies outside the PDF.",
                    )
                )

        pages_by_source: dict[int, dict[str, set[int]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for item in evidence:
            if item.lesson_no is not None and item.source in {"toc", "heading"}:
                pages_by_source[item.lesson_no][item.source].add(item.page_index)
        for lesson_no, sources in sorted(pages_by_source.items()):
            toc_pages = sources.get("toc", set())
            heading_pages = sources.get("heading", set())
            if toc_pages and heading_pages and toc_pages != heading_pages:
                issues.append(
                    BoundaryIssue(
                        "toc_heading_conflict", "error", lesson_no, None,
                        "TOC and heading point to different lesson pages.",
                    )
                )

        return BoundaryReport(
            valid=not issues,
            issues=tuple(issues),
            missing_lesson_nos=tuple(
                issue.lesson_no for issue in issues if issue.code == "missing_lesson"
            ),
        )

    def propose(
        self,
        summaries: list[PageSummary],
        evidence: list[PageEvidence] | tuple[PageEvidence, ...],
        ai_client: AiClient | None = None,
        evidence_image: bytes | None = None,
    ) -> SplitResult:
        """Fuse local TOC, heading and layout evidence into lesson boundaries."""
        del ai_client, evidence_image
        page_evidence = list(evidence)
        boundary_evidence: list[BoundaryEvidence] = []
        offset = self._page_offset(page_evidence)

        for item in page_evidence:
            if item.heading_lesson_no is not None:
                boundary_evidence.append(
                    BoundaryEvidence(
                        "heading", item.pdf_page, item.heading_lesson_no,
                        item.heading_title, 0.8, item.top_text,
                    )
                )
            if item.toc_text and offset is not None:
                for lesson_no, title, printed_page in self._toc_rows(item.toc_text):
                    boundary_evidence.append(
                        BoundaryEvidence(
                            "toc", printed_page + offset, lesson_no, title,
                            0.75, f"printed page {printed_page}",
                        )
                    )

        grouped: dict[int, dict[int, list[BoundaryEvidence]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for item in boundary_evidence:
            if item.lesson_no is not None and item.lesson_no > 0:
                grouped[item.lesson_no][item.page_index].append(item)

        fingerprint_headings: dict[str, set[int]] = defaultdict(set)
        for item in page_evidence:
            if item.layout_fingerprint and item.heading_lesson_no is not None:
                fingerprint_headings[item.layout_fingerprint].add(item.pdf_page)
        confirmed_fingerprints = {
            fingerprint
            for fingerprint, pages in fingerprint_headings.items()
            if len(pages) >= 2
        }
        for item in page_evidence:
            if item.layout_fingerprint not in confirmed_fingerprints:
                continue
            for lesson_no, pages in grouped.items():
                candidate_items = pages.get(item.pdf_page)
                if not candidate_items:
                    continue
                title = next(
                    (candidate.title for candidate in candidate_items if candidate.title),
                    None,
                )
                layout = BoundaryEvidence(
                    "layout", item.pdf_page, lesson_no, title, 0.7,
                    item.layout_fingerprint,
                )
                candidate_items.append(layout)
                boundary_evidence.append(layout)

        total_pages = self._total_pages(summaries, page_evidence)
        boundaries: list[LessonBoundary] = []
        if grouped:
            selected: list[tuple[int, int, list[BoundaryEvidence]]] = []
            for lesson_no, pages in grouped.items():
                page_index, items = min(
                    pages.items(),
                    key=lambda pair: (-len({item.source for item in pair[1]}), pair[0]),
                )
                selected.append((lesson_no, page_index, items))
            selected.sort(key=lambda item: item[0])

            for position, (lesson_no, page_start, items) in enumerate(selected):
                sources = {item.source for item in items}
                title = next(
                    (item.title for item in items if item.source == "heading" and item.title),
                    next((item.title for item in items if item.title), None),
                )
                page_end = (
                    selected[position + 1][1] - 1
                    if position + 1 < len(selected)
                    else total_pages - 1
                )
                confidence = (
                    0.65
                    if len(sources) == 1
                    else min(0.95, 0.55 + 0.15 * len(sources))
                )
                boundaries.append(
                    LessonBoundary(
                        lesson_no, title, page_start, page_end, confidence, "lesson"
                    )
                )
        else:
            boundaries = self.split_by_regex(summaries) or self.split_by_heuristics(summaries)

        report = self.validate(boundaries, boundary_evidence, total_pages)
        return SplitResult(
            tuple(boundaries), tuple(boundary_evidence), report, not report.valid
        )

    def split_by_boya1_preset(self, total_pages: int) -> list[LessonBoundary]:
        """Preset ranh giới 30 bài học thực tế cho giáo trình Boya Sơ cấp 1 (270 trang scan)."""
        page_starts = [
            36, 41, 48, 54, 61, 67, 73, 81, 88, 96,
            103, 110, 117, 124, 131, 138, 144, 151, 158, 166,
            173, 179, 185, 192, 199, 207, 214, 220, 227, 234,
        ]
        boundaries: list[LessonBoundary] = []
        for i, ps in enumerate(page_starts):
            if ps < total_pages:
                idx_no = i + 1
                pe = page_starts[i + 1] - 1 if i + 1 < len(page_starts) else total_pages - 1
                boundaries.append(
                    LessonBoundary(
                        index_no=idx_no,
                        title=f"Bài {idx_no}",
                        page_start=ps,
                        page_end=pe,
                        confidence=0.95,
                        kind="lesson",
                    )
                )
        return boundaries

    def split_by_llm(
        self, summaries: list[PageSummary], ai_client: AiClient
    ) -> list[LessonBoundary]:
        """Phân tách bài học bằng AI LLM cho tệp PDF có text native."""
        if not ai_client.is_configured():
            return []

        lines = []
        for s in summaries:
            if s.head:
                lines.append(f"Trang {s.pdf_page + 1}: [{s.head}] (Font: {s.max_size:.1f}, CJK: {s.cjk})")
        
        if not lines:
            return []

        summaries_text = "\n".join(lines[:100])
        raw_list = ai_client.split_lessons(summaries_text)
        if not raw_list:
            return []

        boundaries: list[LessonBoundary] = []
        for item in raw_list:
            try:
                boundaries.append(
                    LessonBoundary(
                        index_no=int(item.get("index_no", len(boundaries) + 1)),
                        title=str(item.get("title", "")),
                        page_start=int(item.get("page_start", 0)),
                        page_end=int(item.get("page_end", 0)),
                        confidence=0.95,
                        kind="lesson",
                    )
                )
            except Exception:
                continue

        return boundaries

    def split_by_regex(self, summaries: list[PageSummary]) -> list[LessonBoundary]:
        """Phân tách bài học bằng biểu thức chính quy (第X课 / Bài X / Lesson X)."""
        matches: list[tuple[int, int, str]] = []

        for s in summaries:
            m = RE_LESSON_HEADER.search(s.head)
            if m:
                num_g = m.group(1) or m.group(2) or m.group(3)
                idx_no = _parse_cn_num(num_g) if num_g else len(matches) + 1
                matches.append((idx_no, s.pdf_page, s.head.strip()))

        if not matches:
            return []

        total_pages = len(summaries)
        boundaries: list[LessonBoundary] = []
        for i, (idx_no, page_start, title) in enumerate(matches):
            page_end = matches[i + 1][1] - 1 if i + 1 < len(matches) else total_pages - 1
            boundaries.append(
                LessonBoundary(
                    index_no=idx_no,
                    title=title,
                    page_start=page_start,
                    page_end=page_end,
                    confidence=0.9,
                    kind="lesson",
                )
            )

        return boundaries

    def split_by_heuristics(self, summaries: list[PageSummary]) -> list[LessonBoundary]:
        """Phân tách dự phòng theo font_size lớn hoặc gom đều trang."""
        if not summaries:
            return []

        avg_max_size = sum(s.max_size for s in summaries) / len(summaries)
        head_pages: list[PageSummary] = [
            s for s in summaries
            if s.max_size >= avg_max_size * 1.3 and s.head
        ]

        if not head_pages:
            head_pages = [s for i, s in enumerate(summaries) if i % 10 == 0]

        boundaries: list[LessonBoundary] = []
        total_pages = len(summaries)

        for i, s in enumerate(head_pages):
            idx_no = i + 1
            page_start = s.pdf_page
            page_end = head_pages[i + 1].pdf_page - 1 if i + 1 < len(head_pages) else total_pages - 1
            title = s.head if s.head else f"Bài {idx_no}"

            boundaries.append(
                LessonBoundary(
                    index_no=idx_no,
                    title=title,
                    page_start=page_start,
                    page_end=page_end,
                    confidence=0.7,
                    kind="lesson",
                )
            )

        return boundaries

    def split(
        self, summaries: list[PageSummary], ai_client: AiClient | None = None
    ) -> list[LessonBoundary]:
        """Compatibility wrapper for callers that only have page summaries."""
        ok, _reason = self.accepts(summaries)
        if not ok:
            return []

        result = self.propose(summaries, (), ai_client=ai_client)
        return list(result.boundaries) if result.report.valid else []
