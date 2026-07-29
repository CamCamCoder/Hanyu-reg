"""Kiểm thử unit cho service/vocab.py."""

from hanzi_app.data.models import TextSpan
from hanzi_app.service.vocab import VocabExtractor


def test_vocab_extractor_spans():
    extractor = VocabExtractor()

    spans = [
        TextSpan(text="1", bbox=(10, 100, 20, 115), font_size=12.0),
        TextSpan(text="你好", bbox=(30, 100, 70, 115), font_size=12.0),
        TextSpan(text="nǐhǎo", bbox=(80, 100, 120, 115), font_size=12.0),
        TextSpan(text="n.", bbox=(130, 100, 145, 115), font_size=12.0),
        TextSpan(text="Xin chào", bbox=(150, 100, 200, 115), font_size=12.0),
    ]

    rows = extractor.extract_spans(spans, source_page=1)
    assert len(rows) == 1
    row = rows[0]
    assert row.word == "你好"
    assert row.order_no == 1
    assert row.pinyin_src == "nǐhǎo"
    assert row.pos == "n."
    assert row.source_page == 1
    assert row.extract_by == "regex"


def test_vocab_page_locator_does_not_accept_dialogue():
    extractor = VocabExtractor()
    dialogue = [
        TextSpan(text="你好，你叫什么名字？", bbox=(20, 20, 200, 40), font_size=12),
    ]
    table = [
        TextSpan(text="New Words and Expressions", bbox=(20, 20, 240, 40), font_size=12),
        TextSpan(text="词语表", bbox=(20, 50, 80, 70), font_size=12),
    ]
    assert extractor.is_vocab_page(dialogue) is False
    assert extractor.is_vocab_page(table) is True


def test_vocab_table_spans_seven_columns():
    extractor = VocabExtractor()
    spans = [
        TextSpan(text="STT", bbox=(10, 10, 60, 25), font_size=12),
        TextSpan(text="1", bbox=(15, 50, 25, 65), font_size=12),
        TextSpan(text="专业", bbox=(120, 50, 180, 65), font_size=12),
        TextSpan(text="zhuānyè", bbox=(230, 50, 320, 65), font_size=12),
        TextSpan(text="n.", bbox=(370, 50, 395, 65), font_size=12),
        TextSpan(text="chuyên nghiệp", bbox=(430, 50, 500, 65), font_size=12),
        TextSpan(text="profession", bbox=(600, 50, 700, 65), font_size=12),
        TextSpan(text="chuyên ngành", bbox=(800, 50, 970, 65), font_size=12),
        # Ép chiều rộng trang xấp xỉ 1000.
        TextSpan(text="1", bbox=(990, 0, 1000, 8), font_size=8),
    ]
    rows = extractor.extract_table_spans(spans, source_page=3)
    assert len(rows) == 1
    assert rows[0].word == "专业"
    assert rows[0].pinyin_src == "zhuānyè"
    assert rows[0].hanviet_src == "chuyên nghiệp"
    assert rows[0].meaning_src == "chuyên ngành"


def test_merge_bilingual_spans_giu_han_tu_va_latin_tu_ocr_anh():
    zh = [
        TextSpan(text="专业", bbox=(10, 10, 50, 30), font_size=12, is_ocr=True),
        TextSpan(text="zhudnyö", bbox=(60, 10, 120, 30), font_size=12, is_ocr=True),
    ]
    en = [
        TextSpan(text="zhuānyè", bbox=(60, 10, 120, 30), font_size=12, is_ocr=True),
    ]
    merged = VocabExtractor.merge_bilingual_spans(zh, en)
    assert [span.text for span in merged] == ["专业", "zhuānyè"]


def test_table_bbox_dung_truoc_language_points():
    spans = [
        TextSpan(text="STT", bbox=(10, 100, 50, 120), font_size=12),
        TextSpan(text="专业", bbox=(100, 160, 160, 180), font_size=12),
        TextSpan(text="Language", bbox=(800, 500, 900, 520), font_size=12),
        TextSpan(text="Points", bbox=(910, 500, 970, 520), font_size=12),
    ]
    bbox = VocabExtractor.table_bbox(spans)
    assert bbox is not None
    assert bbox[1] == 55
    assert bbox[3] == 485
