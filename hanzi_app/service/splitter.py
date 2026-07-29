"""Bộ phân tách bài học trong sách PDF theo thang nhiều nấc (Regex, LLM API, Book Presets, Heuristics).

Tầng service: nhận danh sách PageSummary từ pdfsource, trả về danh sách LessonBoundary.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from hanzi_app.data.models import LessonBoundary, PageSummary

if TYPE_CHECKING:
    from hanzi_app.adapter.aiclient import AiClient

# Biểu thức chính quy tìm tiêu đề bài học dạng 第X课 hoặc Bài X hoặc Lesson X
RE_LESSON_HEADER = re.compile(
    r"(?:第\s*(\d+|[一二三四五六七八九十百]+)\s*课|^Bài\s+(\d+)|^Lesson\s+(\d+))",
    re.IGNORECASE,
)

# Chữ số Hán tự sang số tự nhiên
CN_NUMS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


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
        """Phân tách bài học theo quy trình chuẩn hóa đơn giản, sạch sẽ."""
        ok, reason = self.accepts(summaries)
        if not ok:
            return []

        total_cjk = sum(s.cjk for s in summaries)
        total_pages = len(summaries)

        # Trường hợp 1: Sách scan rỗng text native (cjk == 0) và khoảng ~270 trang (Boya 1 Sơ cấp)
        if total_cjk == 0 and total_pages >= 200:
            preset = self.split_by_boya1_preset(total_pages)
            if preset:
                return preset

        # Trường hợp 2: Phân tách bằng LLM API nếu có text native
        if ai_client and ai_client.is_configured():
            llm_res = self.split_by_llm(summaries, ai_client)
            if llm_res:
                return llm_res

        # Trường hợp 3: Phân tách bằng Regex tiêu đề (第X课 / Bài X)
        regex_res = self.split_by_regex(summaries)
        if regex_res:
            return regex_res

        # Trường hợp 4: Dự phòng theo Heuristics
        return self.split_by_heuristics(summaries)
