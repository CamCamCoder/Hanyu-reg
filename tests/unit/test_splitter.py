"""Kiểm thử unit cho service/splitter.py."""

from hanzi_app.data.models import LessonBoundary, PageEvidence, PageSummary
from hanzi_app.service.splitter import Splitter


def test_splitter_accepts():
    splitter = Splitter()
    # Rỗng -> False
    ok, _ = splitter.accepts([])
    assert ok is False

    # Có dữ liệu -> True
    summaries = [
        PageSummary(id=1, pdf_page=0, folio="1", max_size=20.0, head="第一课", cjk=10)
    ]
    ok, _ = splitter.accepts(summaries)
    assert ok is True


def test_splitter_regex_lessons():
    splitter = Splitter()
    summaries = [
        PageSummary(id=1, pdf_page=0, folio="1", max_size=24.0, head="第一课 你好", cjk=5),
        PageSummary(id=2, pdf_page=1, folio="2", max_size=12.0, head="Nội dung bài 1", cjk=20),
        PageSummary(id=3, pdf_page=2, folio="3", max_size=24.0, head="第二课 谢谢", cjk=5),
        PageSummary(id=4, pdf_page=3, folio="4", max_size=12.0, head="Nội dung bài 2", cjk=20),
    ]

    boundaries = splitter.split_by_regex(summaries)
    assert len(boundaries) == 2
    assert boundaries[0].index_no == 1
    assert boundaries[0].page_start == 0
    assert boundaries[0].page_end == 1
    assert boundaries[1].index_no == 2
    assert boundaries[1].page_start == 2
    assert boundaries[1].page_end == 3


def test_splitter_heuristics_fallback():
    splitter = Splitter()
    summaries = [
        PageSummary(id=1, pdf_page=0, folio="1", max_size=30.0, head="TIEU DE DAI", cjk=0),
        PageSummary(id=2, pdf_page=1, folio="2", max_size=10.0, head="Van ban 1", cjk=0),
        PageSummary(id=3, pdf_page=2, folio="3", max_size=30.0, head="BAI 2 MAU", cjk=0),
    ]

    boundaries = splitter.split(summaries)
    assert len(boundaries) >= 1


def test_boya_preset_matches_verified_opening_pages():
    boundaries = Splitter().split_by_boya1_preset(270)
    assert len(boundaries) == 30
    assert [b.page_start for b in boundaries[:5]] == [36, 41, 48, 54, 61]
    assert boundaries[-1].page_start == 234


def test_boundary_validator_rejects_missing_lessons_and_overlap():
    boundaries = [
        LessonBoundary(1, "Bài 1", 15, 25, 0.7, "lesson"),
        LessonBoundary(3, "Bài 3", 24, 35, 0.7, "lesson"),
    ]
    report = Splitter().validate(boundaries, (), total_pages=144)
    assert report.valid is False
    assert report.missing_lesson_nos == (2,)
    assert {issue.code for issue in report.issues} >= {
        "missing_lesson", "overlap"
    }


def test_local_toc_and_heading_fuse_into_complete_boundaries():
    evidence = [
        PageEvidence(
            0,
            "scan",
            "Contents",
            "i",
            "1 One 001\n2 Two 005\n3 Three 010",
            None,
            None,
            None,
            True,
        ),
        PageEvidence(15, "scan", "Lesson 1 One", "1", None, 1, 1, "Lesson 1 One", False),
        PageEvidence(19, "scan", "Lesson 2 Two", "5", None, 5, 2, "Lesson 2 Two", False),
        PageEvidence(24, "scan", "Lesson 3 Three", "10", None, 10, 3, "Lesson 3 Three", False),
    ]
    result = Splitter().propose([], evidence)
    assert [boundary.index_no for boundary in result.boundaries] == [1, 2, 3]
    assert [boundary.page_start for boundary in result.boundaries] == [15, 19, 24]
    assert result.report.valid is True
    assert all(boundary.confidence < 1.0 for boundary in result.boundaries)


def test_fusion_marks_conflicting_toc_and_heading_pages_invalid():
    evidence = [
        PageEvidence(0, "scan", "Contents", "i", "1 One 002", None, None, None, True),
        PageEvidence(15, "scan", "Lesson 1 One", "1", None, 1, 1, "Lesson 1 One", False),
        PageEvidence(19, "scan", "Lesson 2 Two", "5", None, 5, 2, "Lesson 2 Two", False),
        PageEvidence(24, "scan", "Lesson 3 Three", "10", None, 10, 3, "Lesson 3 Three", False),
    ]

    result = Splitter().propose([], evidence)

    assert result.report.valid is False
    assert "toc_heading_conflict" in {issue.code for issue in result.report.issues}


def test_layout_evidence_only_strengthens_existing_heading_candidates():
    evidence = [
        PageEvidence(5, "scan", "Lesson 1 One", "", None, None, 1, "Lesson 1 One", False, "open"),
        PageEvidence(10, "scan", "Lesson 2 Two", "", None, None, 2, "Lesson 2 Two", False, "open"),
        PageEvidence(15, "scan", "Vocabulary", "", None, None, None, None, False, "open"),
    ]

    result = Splitter().propose([], evidence)

    assert [boundary.index_no for boundary in result.boundaries] == [1, 2]
    assert all(boundary.confidence > 0.65 for boundary in result.boundaries)
    assert all(item.lesson_no is not None for item in result.evidence if item.source == "layout")


def test_single_source_heading_confidence_is_capped_at_point_65():
    evidence = [
        PageEvidence(5, "scan", "Lesson 1 One", "", None, None, 1, "Lesson 1 One", False),
    ]

    result = Splitter().propose([], evidence)

    assert result.boundaries[0].confidence <= 0.65


def test_layout_strengthens_a_toc_candidate_on_a_non_heading_page():
    evidence = [
        PageEvidence(
            0,
            "scan",
            "Contents",
            "i",
            "1 One 001\n2 Two 005\n3 Three 010\n4 Four 015",
            None,
            None,
            None,
            True,
        ),
        PageEvidence(15, "scan", "Lesson 1 One", "1", None, 1, 1, "Lesson 1 One", False, "opening"),
        PageEvidence(19, "scan", "Lesson 2 Two", "5", None, 5, 2, "Lesson 2 Two", False, "opening"),
        PageEvidence(24, "scan", "Lesson 3 Three", "10", None, 10, 3, "Lesson 3 Three", False),
        PageEvidence(29, "scan", "Vocabulary", "15", None, 15, None, None, False, "opening"),
    ]

    result = Splitter().propose([], evidence)

    lesson_four = next(boundary for boundary in result.boundaries if boundary.index_no == 4)
    assert lesson_four.confidence > 0.65
    assert any(
        item.source == "layout" and item.lesson_no == 4 and item.page_index == 29
        for item in result.evidence
    )


def test_duplicate_offset_pair_does_not_confirm_toc_mapping():
    heading = PageEvidence(15, "scan", "Lesson 1 One", "1", None, 1, 1, "Lesson 1 One", False)
    evidence = [
        PageEvidence(0, "scan", "Contents", "i", "1 One 001\n2 Two 005", None, None, None, True),
        heading,
        heading,
    ]

    result = Splitter().propose([], evidence)

    assert [boundary.index_no for boundary in result.boundaries] == [1]


def test_propose_does_not_use_ai_when_local_evidence_is_absent():
    class ForbiddenAi:
        def is_configured(self):
            raise AssertionError("Task 2 must not ask an AI client to split boundaries")

    result = Splitter().propose([], [], ai_client=ForbiddenAi())

    assert result.boundaries == ()


def test_repeated_opening_banner_stops_at_appendix_and_requires_repetition():
    def evidence(page, text, banner=False):
        return PageEvidence(page, "scan", text, "", None, None, None, None, False,
                            "captioned-opening-banner" if banner else None)

    pages = [evidence(2, "FIRST", True), evidence(5, "SECOND", True),
             evidence(9, "THIRD", True), evidence(13, "Translation of the texts")]
    result = Splitter().propose([], pages)
    assert [(b.page_start, b.page_end) for b in result.boundaries] == [(2, 4), (5, 8), (9, 12)]
    assert all(item.source == "layout" for item in result.evidence)
    assert not Splitter().propose([], pages[:2]).boundaries
