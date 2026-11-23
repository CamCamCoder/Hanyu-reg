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


@pytest.mark.golden
@pytest.mark.skipif(not RUN_LIVE_GOLDEN, reason="Cần bật RUN_LIVE_GOLDEN để đọc sách thật")
@pytest.mark.parametrize("volume,lesson_no,digest", [
    (1, 12, "9bda0df9be11dfcf6db3a68e0b813ead"),
    (2, 8, "b413c70a3a51ed5b4c25a2272c0057b2"),
])
def test_main_table_pages_on_holdout(volume, lesson_no, digest):
    import csv
    import hashlib

    candidates = list((Path.home() / "Downloads").glob(f"BOYA*{volume}*.pdf"))
    override = os.environ.get(f"BOYA{volume}_PDF")
    if override:
        candidates = [Path(override)]
    for path in candidates:
        with path.open("rb") as fh:
            if hashlib.file_digest(fh, "md5").hexdigest() == digest:
                break
    else:
        pytest.skip(f"Thiếu bản PDF Boya {volume} đã đối chiếu")
    with Path(__file__).with_name("boya_table_pages.csv").open(encoding="utf8") as fh:
        spec = next(r for r in csv.DictReader(fh)
                    if int(r["volume"]) == volume and int(r["lesson"]) == lesson_no)
    boundary = LessonBoundary(lesson_no, None, int(spec["lesson_start_pdf"]) - 1,
                              int(spec["lesson_end_pdf"]) - 1, 1.0, "lesson")
    with PdfSource(path) as pdf:
        blocks = VocabExtractor().locate_blocks(pdf, boundary)
        assert [b.page_index + 1 for b in blocks] == list(range(
            int(spec["table_start_pdf"]), int(spec["table_end_pdf"]) + 1))
        assert all(pdf.get_page_crop_image_bytes(b.page_index, b.bbox) for b in blocks)
