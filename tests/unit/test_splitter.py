"""Kiểm thử unit cho service/splitter.py."""

from hanzi_app.data.models import PageSummary
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
