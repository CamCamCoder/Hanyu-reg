"""Golden test chậm trên PDF Boya thật, chạy riêng ngoài vòng unit test."""

import json
import os
from pathlib import Path

import pytest

from hanzi_app.adapter.pdfsource import PdfSource
from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import LessonBoundary
from hanzi_app.service.vocab import VocabExtractor


ROOT = Path(__file__).resolve().parents[2]
RUN_LIVE_GOLDEN = os.environ.get("RUN_LIVE_GOLDEN") == "1"
PDF = next(ROOT.glob("BOYA*.pdf"), None) if RUN_LIVE_GOLDEN else None
EXPECTED = json.loads(
    (Path(__file__).with_name("boya_vocab_expected.json")).read_text(encoding="utf-8")
)


@pytest.mark.golden
@pytest.mark.skipif(
    not RUN_LIVE_GOLDEN or PDF is None,
    reason="Golden dữ liệu thật chỉ chạy khi RUN_LIVE_GOLDEN=1 và có PDF Boya",
)
@pytest.mark.parametrize("lesson_no", [5, 29])
def test_boya_vocab_word_recall(lesson_no):
    spec = EXPECTED[str(lesson_no)]
    boundary = LessonBoundary(
        index_no=lesson_no,
        title=f"Bài {lesson_no}",
        page_start=spec["page_start"],
        page_end=spec["page_end"],
        confidence=1.0,
        kind="lesson",
    )
    db = DictDb(str(ROOT / "dict.sqlite"))
    try:
        with PdfSource(PDF) as pdf:
            rows = VocabExtractor(db).extract_lesson(pdf, boundary)
    finally:
        db.close()

    actual = {row.word for row in rows}
    expected = set(spec["words"])
    recall = len(actual & expected) / len(expected)
    assert recall >= 0.60
    assert not actual & {"语言点", "练习", "专有名词", "初级起步篇"}
