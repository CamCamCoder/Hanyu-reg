"""Kiểm thử unit cho service/vocab.py."""

from unittest.mock import MagicMock

from hanzi_app.data.models import LessonBoundary, TextSpan, VocabBlock, VocabRow
from hanzi_app.service.vocab import VocabExtractor, render_block_crop


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

def _span(text, x, y, width=50, height=14):
    return TextSpan(text, (x, y, x + width, y + height), float(height), True)


def _vocab_region(title, orders, y0):
    spans = [_span(title, 20, y0, 100, 18)]
    for offset, order in enumerate(orders, start=1):
        y = y0 + 30 * offset
        spans.extend([
            _span(str(order), 20, y, 20),
            _span(f"词{order}", 80, y, 45),
            _span("cí", 160, y, 45),
        ])
    return spans


def test_locator_finds_disjoint_blocks_and_ignores_prose():
    pages = {
        0: [_span("Trong bài này 生词 nghĩa là từ mới", 20, 100, 300)],
        1: _vocab_region("New Words", (1, 2, 3), 100),
        2: [_span("A: 你好", 20, 100), _span("B: 你好", 20, 140)],
        3: _vocab_region("生词", (4, 5), 300),
    }
    pdf = MagicMock()
    pdf.page_count.return_value = 4
    pdf.spans.side_effect = lambda page: pages[page]
    lesson = LessonBoundary(1, "Bài 1", 0, 3, 1.0, "lesson")

    blocks = VocabExtractor().locate_blocks(pdf, lesson)

    assert [(block.block_no, block.page_index) for block in blocks] == [(1, 1), (2, 3)]
    assert [block.expected_rows for block in blocks] == [3, 2]
    assert [(block.first_order, block.last_order) for block in blocks] == [(1, 3), (4, 5)]
    assert all(block.bbox[1] < block.bbox[3] for block in blocks)


def test_locator_splits_two_blocks_on_one_page_in_deterministic_order():
    page = (
        _vocab_region("生词", (8, 9), 300)
        + _vocab_region("New Words", (1, 2), 50)
        + [_span("99", 900, 600, 20)]
    )
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = page
    lesson = LessonBoundary(7, "Bài 7", 0, 0, 1.0, "lesson")

    first = VocabExtractor().locate_blocks(pdf, lesson)
    second = VocabExtractor().locate_blocks(pdf, lesson)

    assert [
        (b.id, b.lesson_id, b.block_no, b.expected_rows, b.first_order, b.last_order)
        for b in first
    ] == [
        (None, None, 1, 2, 1, 2),
        (None, None, 2, 2, 8, 9),
    ]
    assert first == second


def test_locator_returns_no_block_when_signals_do_not_reach_two_of_three():
    pdf = MagicMock()
    pdf.page_count.return_value = 2
    pdf.spans.side_effect = [
        [_span("生词 chỉ là một thuật ngữ trong đoạn văn", 20, 100, 300)],
        [_span("1", 20, 100), _span("2", 20, 140),
         _span("không có chữ Hán hay pinyin", 80, 100, 250)],
    ]
    lesson = LessonBoundary(2, "Bài 2", 0, 1, 1.0, "lesson")

    assert VocabExtractor().locate_blocks(pdf, lesson) == []


def test_render_block_crop_uses_exact_page_bbox_and_dpi():
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"crop-png"
    block = VocabBlock(None, None, 2, 5, (10.0, 20.0, 300.0, 450.0), None, 4, 7, 10)

    data = render_block_crop(pdf, block)

    assert data == b"crop-png"
    pdf.get_page_crop_image_bytes.assert_called_once_with(
        5, (10.0, 20.0, 300.0, 450.0), dpi=250
    )


def test_locator_splits_vertically_separated_tables_with_one_heading():
    page = (
        _vocab_region("Vocabulary", (1, 2), 40)
        + [
            _span("3", 20, 420, 20),
            _span("词3", 80, 420, 45),
            _span("cí", 160, 420, 45),
            _span("4", 20, 450, 20),
            _span("词4", 80, 450, 45),
            _span("cí", 160, 450, 45),
        ]
    )
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = page

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(8, "Bài 8", 0, 0, 1.0, "lesson")
    )

    assert [
        (block.block_no, block.expected_rows, block.first_order, block.last_order)
        for block in blocks
    ] == [(1, 2, 1, 2), (2, 2, 3, 4)]
    assert blocks[0].bbox[3] < blocks[1].bbox[1]


def test_locator_splits_side_by_side_titled_tables():
    left = _vocab_region("新词", (1, 2), 40)
    right = [
        _span(
            span.text,
            span.bbox[0] + 400,
            span.bbox[1],
            span.bbox[2] - span.bbox[0],
            span.bbox[3] - span.bbox[1],
        )
        for span in _vocab_region("Vocabulary", (3, 4), 40)
    ]
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = left + right

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(9, "Bài 9", 0, 0, 1.0, "lesson")
    )

    assert [(block.first_order, block.last_order) for block in blocks] == [
        (1, 2),
        (3, 4),
    ]
    assert blocks[0].bbox[2] < blocks[1].bbox[0]


def test_locator_rejects_two_column_dialogue_even_with_valid_pinyin_words():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("我", 20, 100, 30),
        _span("wǒ", 100, 100, 40),
        _span("门", 20, 140, 30),
        _span("mén", 100, 140, 40),
        _span("你好", 20, 180, 40),
        _span("hello", 100, 180, 60),
        _span("再见", 20, 220, 40),
        _span("goodbye", 100, 220, 70),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(10, "Bài 10", 0, 0, 1.0, "lesson")
    )

    assert blocks == []


def test_locator_accepts_new_generic_heading_markers():
    extractor = VocabExtractor()
    assert extractor.is_vocab_page([_span("新词", 20, 20, 80)]) is True
    assert extractor.is_vocab_page([_span("Vocabulary", 20, 20, 120)]) is True

    for heading in ("新词", "Vocabulary"):
        pdf = MagicMock()
        pdf.page_count.return_value = 1
        pdf.spans.return_value = _vocab_region(heading, (1, 2), 40)
        blocks = extractor.locate_blocks(
            pdf, LessonBoundary(11, "Bài 11", 0, 0, 1.0, "lesson")
        )
        assert len(blocks) == 1


def test_locator_finds_disjoint_continuation_with_numbered_pinyin():
    page = _vocab_region("New Words", (1, 2), 40) + [
        _span("3", 20, 420, 20),
        _span("你好", 80, 420, 45),
        _span("ni3 hao3", 160, 420, 80),
        _span("4", 20, 450, 20),
        _span("中国", 80, 450, 45),
        _span("zhong1guo2", 160, 450, 90),
        _span("5", 20, 480, 20),
        _span("我", 80, 480, 45),
        _span("wo3", 160, 480, 45),
    ]
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = page

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(12, "Bài 12", 0, 0, 1.0, "lesson")
    )

    assert [
        (block.expected_rows, block.first_order, block.last_order)
        for block in blocks
    ] == [(2, 1, 2), (3, 3, 5)]


def test_locator_rejects_english_women_in_three_column_dialogue():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("我们", 20, 100, 45),
        _span("women", 100, 100, 70),
        _span("chúng tôi", 220, 100, 90),
        _span("女人", 20, 140, 45),
        _span("women", 100, 140, 70),
        _span("phụ nữ", 220, 140, 90),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(13, "Bài 13", 0, 0, 1.0, "lesson")
    )

    assert blocks == []


def test_locator_preserves_tone_marked_and_distinctive_plain_pinyin():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("你好", 20, 100, 45),
        _span("nǐhǎo", 100, 100, 70),
        _span("greeting", 220, 100, 90),
        _span("中国", 20, 140, 45),
        _span("zhongguo", 100, 140, 80),
        _span("country", 220, 140, 90),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(14, "Bài 14", 0, 0, 1.0, "lesson")
    )

    assert len(blocks) == 1
    assert blocks[0].expected_rows == 2

def test_locator_accepts_u_colon_numbered_pinyin_in_continuation_block():
    page = _vocab_region("New Words", (1, 2), 40) + [
        _span("3", 20, 420, 20),
        _span("女", 80, 420, 45),
        _span("nu:3", 160, 420, 55),
        _span("4", 20, 450, 20),
        _span("绿", 80, 450, 45),
        _span("lu:4", 160, 450, 55),
        _span("5", 20, 480, 20),
        _span("女绿", 80, 480, 45),
        _span("nu:3 lu:4", 160, 480, 90),
        _span("6", 20, 510, 20),
        _span("绿女", 80, 510, 45),
        _span("lu:4nu:3", 160, 510, 90),
    ]
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = page

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(15, "Bài 15", 0, 0, 1.0, "lesson")
    )

    assert [
        (block.expected_rows, block.first_order, block.last_order)
        for block in blocks
    ] == [(2, 1, 2), (4, 3, 6)]


def test_locator_rejects_china_change_three_column_bilingual_prose():
    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [
        _span("中国", 20, 100, 45),
        _span("China", 100, 100, 70),
        _span("Trung Quốc", 220, 100, 90),
        _span("改变", 20, 140, 45),
        _span("change", 100, 140, 70),
        _span("thay đổi", 220, 140, 90),
    ]

    blocks = VocabExtractor().locate_blocks(
        pdf, LessonBoundary(16, "Bài 16", 0, 0, 1.0, "lesson")
    )

    assert blocks == []


def _block_row(word, order_no, block_id, pinyin="cí"):
    return VocabRow(
        order_no,
        word,
        pinyin,
        None,
        None,
        1,
        "regex",
        False,
        None,
        source_block_id=block_id,
    )


def test_coverage_rejects_four_of_twelve_rows():
    block = VocabBlock(
        7, 2, 1, 10, (0, 0, 100, 200), "crop.png", 12, 1, 12
    )
    rows = [_block_row(f"词{i}", i, 7) for i in range(1, 5)]

    report = VocabExtractor().validate_block_coverage(block, rows, [], rows)

    assert report.passed is False
    assert report.missing_orders == tuple(range(5, 13))
    assert "expected_row_mismatch" in report.issues


def test_unknown_expected_rows_requires_two_equal_nonzero_sources():
    block = VocabBlock(
        8, 2, 2, 11, (0, 0, 100, 200), "crop.png", None, None, None
    )
    local = [_block_row("你", 1, 8), _block_row("好", 2, 8)]
    ai = [
        _block_row("你", 1, 8, pinyin="nǐ"),
        _block_row("好", 2, 8, pinyin="hǎo"),
    ]

    local_only = VocabExtractor().validate_block_coverage(
        block, local, [], local
    )
    agreed = VocabExtractor().validate_block_coverage(
        block, local, ai, local
    )

    assert local_only.passed is False
    assert "expected_rows_unknown_needs_review" in local_only.issues
    assert agreed.passed is True


def test_merge_keeps_same_word_from_different_blocks_and_deduplicates_exact_key():
    first = _block_row("行", 1, 11)
    exact_duplicate = _block_row("行", 1, 11)
    second = _block_row("行", 9, 12)

    result = VocabExtractor().merge_block_rows(
        [first, exact_duplicate], [second]
    )

    assert [(row.word, row.source_block_id) for row in result] == [
        ("行", 11),
        ("行", 12),
    ]


def test_three_column_block_keeps_word_when_meaning_is_absent():
    spans = [
        _span("STT", 10, 50),
        _span("Chữ Hán", 80, 50),
        _span("Pinyin", 180, 50),
        _span("1", 10, 100),
        _span("你好", 80, 100),
        _span("nǐhǎo", 180, 100),
    ]

    rows = VocabExtractor().extract_table_spans(spans, source_page=1)

    assert len(rows) == 1
    assert rows[0].word == "你好"
    assert rows[0].pinyin_src == "nǐhǎo"
    assert rows[0].meaning_src is None


def test_extract_blocks_crops_to_manifest_and_attaches_source_block():
    block = VocabBlock(
        31, 4, 1, 0, (0, 40, 260, 130), "crop.png", 1, 1, 1
    )
    page_spans = [
        _span("STT", 10, 50),
        _span("Chữ Hán", 80, 50),
        _span("Pinyin", 180, 50),
        _span("1", 10, 100),
        _span("你好", 80, 100),
        _span("nǐhǎo", 180, 100),
        _span("课文", 400, 100),
    ]
    pdf = MagicMock()
    pdf.spans.return_value = page_spans
    pdf.ocr_spans.return_value = page_spans

    result = VocabExtractor().extract_blocks(pdf, [block])

    assert result.complete is True
    assert [(row.word, row.source_block_id) for row in result.rows] == [
        ("你好", 31)
    ]
    assert result.coverage[0].passed is True
    assert result.blocks[0].status == "local_ok"


def test_shifted_four_columns_without_recognized_headers_are_inferred():
    spans = [
        _span("Index", 250, 50, 60),
        _span("Term", 430, 50, 70),
        _span("Romanisation", 700, 50, 110),
        _span("Definition", 900, 50, 90),
        _span("1", 250, 140, 20),
        _span("你好", 430, 140, 50),
        _span("nǐhǎo", 700, 140, 70),
        _span("xin chào", 900, 140, 90),
        _span("2", 250, 180, 20),
        _span("老师", 430, 180, 50),
        _span("lǎoshī", 700, 180, 70),
        _span("giáo viên", 900, 180, 100),
        _span("page", 1080, 20, 40),
    ]

    rows = VocabExtractor().extract_table_spans(spans, source_page=3)

    assert [(row.order_no, row.word) for row in rows] == [
        (1, "你好"),
        (2, "老师"),
    ]
    assert [row.pinyin_src for row in rows] == ["nǐhǎo", "lǎoshī"]
    assert [row.meaning_src for row in rows] == ["xin chào", "giáo viên"]


def test_two_columns_without_headers_keep_hanzi_as_only_required_field():
    spans = [
        _span("你好", 360, 140, 50),
        _span("xin chào", 760, 140, 90),
        _span("老师", 360, 180, 50),
        _span("giáo viên", 760, 180, 100),
        _span("page", 1080, 20, 40),
    ]

    rows = VocabExtractor().extract_table_spans(spans, source_page=3)

    assert [row.word for row in rows] == ["你好", "老师"]
    assert all(row.pinyin_src is None for row in rows)
    assert [row.meaning_src for row in rows] == ["xin chào", "giáo viên"]


def test_extract_blocks_reports_raw_exact_duplicates_before_dedup(monkeypatch):
    block = VocabBlock(
        42, 4, 1, 0, (0, 40, 260, 130), "crop.png", 1, 1, 1
    )
    duplicate = _block_row("你好", 1, 42, pinyin="nǐhǎo")
    extractor = VocabExtractor()
    monkeypatch.setattr(
        extractor,
        "extract_table_spans",
        lambda _spans, source_page: [duplicate, duplicate],
    )
    pdf = MagicMock()
    pdf.spans.return_value = [_span("你好", 80, 100)]
    pdf.ocr_spans.return_value = []

    result = extractor.extract_blocks(pdf, [block])

    assert len(result.rows) == 1
    assert result.complete is False
    assert "abnormal_exact_duplicates" in result.coverage[0].issues
    assert result.blocks[0].status == "incomplete"
