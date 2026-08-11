"""Unit test kiểm thử Bộ Xử Lý Tổng Quát 2 Lớp (Universal 2-Layer Engine)."""

import hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock
import logging
import pytest

from hanzi_app.adapter.aiclient import AiRateLimitError
from hanzi_app.data.models import (
    BlockCoverage,
    BoundaryIssue,
    BoundaryEvidence,
    BoundaryReport,
    LessonBoundary,
    PageEvidence,
    PageSummary,
    SplitResult,
    ExtractionResult,
    VocabBlock,
    VocabRow,
)
from hanzi_app.data.userdb import UserDb
import hanzi_app.service.importer as importer_module
from hanzi_app.service.importer import (
    BookImporterWorker,
    VocabImporterWorker,
    _write_crop_atomic,
)
from hanzi_app.service.splitter import Splitter, _parse_cn_num
from hanzi_app.service.vocab import VocabExtractor


def test_generic_import_never_accepts_sparse_lesson_sequence():
    numbers = (1, 2, 3, 4, 8, 12, 13, 14)
    boundaries = [
        LessonBoundary(
            number,
            f"Lesson {number}",
            index * 10,
            index * 10 + 9,
            0.6,
            "lesson",
        )
        for index, number in enumerate(numbers)
    ]

    report = Splitter().validate(boundaries, (), total_pages=144)

    assert report.valid is False
    assert report.missing_lesson_nos == (5, 6, 7, 9, 10, 11)


def test_generic_multi_block_book_is_complete_only_after_every_block(monkeypatch):
    row_counts = (5, 4, 6, 3, 2, 7)
    blocks = [
        VocabBlock(
            index,
            1,
            index,
            index,
            (0, 0, 100, 200),
            f"block-{index}.png",
            count,
            1,
            count,
        )
        for index, count in enumerate(row_counts, start=1)
    ]
    extractor = VocabExtractor()
    monkeypatch.setattr(
        extractor,
        "_extract_local_block",
        lambda _pdf, block: [
            VocabRow(
                order_no=order,
                word=f"词{block.id}-{order}",
                pinyin_src="cí",
                pos=None,
                hanviet_src=None,
                meaning_src=None,
                source_page=block.page_index + 1,
                extract_by="regex",
                needs_review=False,
                review_reason=None,
                source_block_id=block.id,
            )
            for order in range(1, block.expected_rows + 1)
        ],
    )

    result = extractor.extract_blocks(MagicMock(), blocks)

    assert result.complete is True
    assert sum(coverage.final_rows for coverage in result.coverage) == 27


def test_parse_cn_num_composite():
    """Kiểm tra giải mã chữ số Hán tự phức hợp (như 十一 = 11, 二十 = 20)."""
    assert _parse_cn_num("1") == 1
    assert _parse_cn_num("一") == 1
    assert _parse_cn_num("十") == 10
    assert _parse_cn_num("十一") == 11
    assert _parse_cn_num("十二") == 12
    assert _parse_cn_num("二十") == 20
    assert _parse_cn_num("二十一") == 21


def test_splitter_calls_ai_only_for_invalid_local_result():
    """A single-source local split is repaired with one bounded Vision request."""
    client = MagicMock()
    client.is_configured.return_value = True
    client.split_lessons_from_image.return_value = [
        {"index_no": 1, "title": "One", "page_start": 0},
        {"index_no": 2, "title": "Two", "page_start": 5},
    ]
    evidence = [
        PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
        PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
    ]

    result = Splitter().propose(
        [], evidence, ai_client=client, evidence_image=b"sheet"
    )

    assert result.report.valid is True
    assert client.split_lessons_from_image.call_count == 1


def test_splitter_skips_ai_for_valid_two_source_local_result():
    """Validated TOC plus heading evidence must not consume an AI request."""
    client = MagicMock()
    client.is_configured.return_value = True
    evidence = [
        PageEvidence(0, "scan", "Contents", "i", "1 One 001\n2 Two 005", None, None, None, True),
        PageEvidence(5, "scan", "Lesson 1 One", "1", None, 1, 1, "Lesson 1 One", False),
        PageEvidence(9, "scan", "Lesson 2 Two", "5", None, 5, 2, "Lesson 2 Two", False),
    ]

    result = Splitter().propose(
        [], evidence, ai_client=client, evidence_image=b"sheet"
    )

    assert result.report.valid is True
    assert client.split_lessons_from_image.call_count == 0


def test_splitter_keeps_local_boundaries_that_ai_omits():
    """A partial AI reply cannot erase a locally detected later lesson."""
    client = MagicMock()
    client.is_configured.return_value = True
    client.split_lessons_from_image.return_value = [
        {"index_no": 1, "title": "One", "page_start": 0},
    ]
    evidence = [
        PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
        PageEvidence(5, "scan", "Lesson 2", "5", None, 5, 2, "Lesson 2", False),
        PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
    ]

    result = Splitter().propose(
        [], evidence, ai_client=client, evidence_image=b"sheet"
    )

    assert result.report.valid is True
    assert [boundary.index_no for boundary in result.boundaries] == [1, 2]


def test_book_worker_does_not_persist_invalid_boundaries(tmp_path):
    """An invalid boundary report must abort before the destructive replace."""
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Test book", "book.pdf", "split-invalid", 40)
    issue = BoundaryIssue("missing_lesson", "error", 2, None, "Lesson 2 missing")
    fake_result = SplitResult(
        (), (), BoundaryReport(False, (issue,), (2,)), True
    )
    worker = BookImporterWorker("book.pdf", db.path)

    with pytest.raises(RuntimeError, match="Lesson 2 missing"):
        worker._store_boundaries_or_raise(db, book_id, fake_result)
    assert db.get_lessons(book_id) == []
    db.close()


def test_ai_merge_preserves_prior_evidence_for_review():
    """Vision evidence augments the detailed local audit trail instead of replacing it."""
    original = (
        BoundaryEvidence("toc", 0, 1, "One", 0.75, "printed page 1"),
        BoundaryEvidence("heading", 0, 1, "One", 0.8, "Lesson 1 One"),
        BoundaryEvidence("layout", 0, 1, "One", 0.7, "opening-grid"),
    )
    previous = SplitResult(
        (LessonBoundary(1, "One", 0, 9, 0.8, "lesson"),),
        original,
        BoundaryReport(True, (), ()),
        False,
    )

    result = Splitter()._merge_ai_candidates(
        previous, [{"index_no": 1, "title": "One", "page_start": 0}], 10
    )

    assert result.evidence[:3] == original
    assert result.evidence[-1].source == "ai"


def test_splitter_retry_receives_validator_issues():
    """The retry prompt must name the actual validator failure from the first reply."""
    client = MagicMock()
    client.is_configured.return_value = True
    client.split_lessons_from_image.side_effect = [
        [],
        [{"index_no": 1, "title": "One", "page_start": 0}],
    ]
    evidence = [
        PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
        PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
    ]

    Splitter().propose([], evidence, ai_client=client, evidence_image=b"sheet")

    assert client.split_lessons_from_image.call_args_list[1].kwargs["issue_context"] == (
        "Vision returned no lesson boundaries."
    )


def test_worker_persists_ai_budget_across_two_failed_runs(tmp_path, monkeypatch):
    """Two failed runs of one existing book can spend only its lifetime budget of two."""
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"same-book")
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book(
        "Book", str(pdf_path), hashlib.md5(b"same-book").hexdigest(), 10
    )
    db.set_import_state(book_id, "review_bounds")
    db.close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            return [
                PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
                PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
            ]

        def boundary_contact_sheet(self, _evidence):
            return b"sheet"

    class EmptyAi:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        def is_configured(self):
            return True

        def split_lessons_from_image(self, *_args, **_kwargs):
            type(self).calls += 1
            return []

    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "AiClient", EmptyAi)

    BookImporterWorker(pdf_path, str(tmp_path / "user.sqlite")).run()
    BookImporterWorker(pdf_path, str(tmp_path / "user.sqlite")).run()

    checked = UserDb(str(tmp_path / "user.sqlite"))
    assert EmptyAi.calls == 2
    assert checked.get_setting(
        f"import.split_ai_calls.{hashlib.md5(b'same-book').hexdigest()}"
    ) == "2"
    checked.close()


def test_worker_scopes_ai_budget_to_file_hash_after_new_book_deletion(
    tmp_path, monkeypatch
):
    """Deleted-book IDs must neither reset one PDF nor exhaust a different PDF."""
    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    pdf_a.write_bytes(b"pdf-a")
    pdf_b.write_bytes(b"pdf-b")
    db_path = str(tmp_path / "user.sqlite")
    UserDb(db_path).close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            return [
                PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
                PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
            ]

        def boundary_contact_sheet(self, _evidence):
            return b"sheet"

    class EmptyAi:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        def is_configured(self):
            return True

        def split_lessons_from_image(self, *_args, **_kwargs):
            type(self).calls += 1
            return []

    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "AiClient", EmptyAi)

    BookImporterWorker(pdf_a, db_path).run()
    BookImporterWorker(pdf_b, db_path).run()
    BookImporterWorker(pdf_a, db_path).run()

    hash_a = hashlib.md5(b"pdf-a").hexdigest()
    hash_b = hashlib.md5(b"pdf-b").hexdigest()
    checked = UserDb(db_path)
    assert EmptyAi.calls == 4
    assert checked.get_setting(f"import.split_ai_calls.{hash_a}") == "2"
    assert checked.get_setting(f"import.split_ai_calls.{hash_b}") == "2"
    checked.close()


def test_worker_counts_an_ai_call_that_raises(tmp_path, monkeypatch):
    """A request that raises still consumes one of the book's two AI calls."""
    pdf_path = tmp_path / "raises.pdf"
    pdf_path.write_bytes(b"raising-book")
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book(
        "Book", str(pdf_path), hashlib.md5(b"raising-book").hexdigest(), 10
    )
    db.set_import_state(book_id, "review_bounds")
    db.close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            return [
                PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
                PageEvidence(9, "scan", "Appendix", "9", None, 9, None, None, False),
            ]

        def boundary_contact_sheet(self, _evidence):
            return b"sheet"

    class RaisingAi:
        def __init__(self, **_kwargs):
            pass

        def is_configured(self):
            return True

        def split_lessons_from_image(self, *_args, **_kwargs):
            raise RuntimeError("AI failed")

    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "AiClient", RaisingAi)
    BookImporterWorker(pdf_path, db_path).run()

    checked = UserDb(db_path)
    assert checked.get_setting(
        f"import.split_ai_calls.{hashlib.md5(b'raising-book').hexdigest()}"
    ) == "1"
    assert checked.get_book(book_id)["import_state"] == "review_bounds"
    checked.close()


def test_worker_restores_existing_book_state_when_census_fails(tmp_path, monkeypatch):
    """A failed retry restores its previous state instead of leaving an importing book."""
    pdf_path = tmp_path / "existing.pdf"
    pdf_path.write_bytes(b"existing-book")
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book(
        "Existing", str(pdf_path), hashlib.md5(b"existing-book").hexdigest(), 10
    )
    db.set_import_state(book_id, "review_bounds")
    db.close()

    class FailingPdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            raise RuntimeError("census failed")

    monkeypatch.setattr(importer_module, "PdfSource", FailingPdfSource)
    BookImporterWorker(pdf_path, str(tmp_path / "user.sqlite")).run()

    checked = UserDb(str(tmp_path / "user.sqlite"))
    assert checked.get_book(book_id)["import_state"] == "review_bounds"
    checked.close()


def test_worker_deletes_new_book_when_census_fails(tmp_path, monkeypatch):
    """A book created during a failed split is removed rather than stranded importing."""
    pdf_path = tmp_path / "new.pdf"
    pdf_path.write_bytes(b"new-book")
    db_path = str(tmp_path / "user.sqlite")
    UserDb(db_path).close()

    class FailingPdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            raise RuntimeError("census failed")

    monkeypatch.setattr(importer_module, "PdfSource", FailingPdfSource)
    BookImporterWorker(pdf_path, db_path).run()

    checked = UserDb(db_path)
    assert checked.get_books() == []
    checked.close()


def test_worker_emits_the_split_result(tmp_path, monkeypatch):
    """The phase-one signal exposes the reviewed result, including its evidence."""
    pdf_path = tmp_path / "signal.pdf"
    pdf_path.write_bytes(b"signal-book")
    db_path = str(tmp_path / "user.sqlite")
    UserDb(db_path).close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            return [
                PageEvidence(0, "scan", "Lesson 1", "1", None, 1, 1, "Lesson 1", False),
            ]

        def boundary_contact_sheet(self, _evidence):
            return b""

    received = []
    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    worker = BookImporterWorker(pdf_path, db_path)
    worker.boundaries_ready.connect(
        lambda book_id, title, result: received.append((book_id, title, result))
    )
    worker.run()

    assert len(received) == 1
    assert isinstance(received[0][2], SplitResult)
    assert received[0][2].evidence[0].source == "heading"


def test_worker_emits_invalid_conflict_for_manual_repair_without_db_lessons(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "conflict.pdf"
    pdf_path.write_bytes(b"conflicting-boundaries")
    db_path = str(tmp_path / "user.sqlite")
    UserDb(db_path).close()
    boundary = LessonBoundary(1, "One", 2, 9, 0.9, "lesson")
    issue = BoundaryIssue(
        "toc_heading_conflict", "error", 1, None, "sources conflict"
    )
    result = SplitResult(
        (boundary,),
        (
            BoundaryEvidence("toc", 2, 1, "One", 0.8, "toc"),
            BoundaryEvidence("heading", 4, 1, "One", 0.8, "heading"),
        ),
        BoundaryReport(False, (issue,), ()),
        True,
    )

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def page_census(self):
            return []

        def boundary_contact_sheet(self, _evidence):
            return b""

    class ConflictingSplitter:
        ai_calls_used = 0

        def propose(self, *_args, **_kwargs):
            return result

    received = []
    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "Splitter", ConflictingSplitter)
    worker = BookImporterWorker(pdf_path, db_path)
    worker.boundaries_ready.connect(
        lambda book_id, title, split_result: received.append(
            (book_id, title, split_result)
        )
    )
    worker.run()

    assert len(received) == 1
    assert received[0][2] == result
    checked = UserDb(db_path)
    assert checked.get_lessons(received[0][0]) == []
    assert checked.get_book(received[0][0])["import_state"] == "review_bounds"
    checked.close()


def test_splitter_top_20_percent_header():
    """Kiểm tra nhận diện tiêu đề 第X课 ở phần 20% trên cùng của trang."""
    summaries = [
        PageSummary(id=1, pdf_page=0, folio="1", max_size=16.0, head="Mục lục", cjk=10),
        PageSummary(id=2, pdf_page=34, folio="35", max_size=20.0, head="第一课 你好", cjk=15),
        PageSummary(id=3, pdf_page=39, folio="40", max_size=20.0, head="第二课 汉语不太难", cjk=12),
        PageSummary(id=4, pdf_page=45, folio="46", max_size=20.0, head="第三课 明天见", cjk=16),
    ]

    splitter = Splitter()
    boundaries = splitter.split_by_regex(summaries)

    assert len(boundaries) == 3
    assert boundaries[0].index_no == 1
    assert boundaries[0].title == "第一课 你好"
    assert boundaries[0].page_start == 34
    assert boundaries[0].page_end == 38

    assert boundaries[1].index_no == 2
    assert boundaries[1].title == "第二课 汉语不太难"
    assert boundaries[1].page_start == 39
    assert boundaries[1].page_end == 44

    assert boundaries[2].index_no == 3
    assert boundaries[2].title == "第三课 明天见"
    assert boundaries[2].page_start == 45


def test_vocab_multi_page_extension_and_fallback():
    """Kiểm tra bóc tách từ vựng đa trang và fallback mượt từ Lớp 2 sang Lớp 1."""
    pdf_mock = MagicMock()
    pdf_mock.page_count.return_value = 50
    pdf_mock.spans.return_value = []
    pdf_mock.get_page_image_bytes.return_value = b"fake_png_bytes"

    ai_client_mock = MagicMock()
    ai_client_mock.is_configured.return_value = True

    # Trả về danh sách từ vựng trên 2 trang liên tiếp (trang 48 và trang 49)
    ai_client_mock.extract_vocab_from_image.side_effect = [
        [
            {"order_no": 1, "word": "明天", "pinyin": "míngtiān", "pos": "n.", "meaning": "Ngày mai"},
            {"order_no": 2, "word": "见", "pinyin": "jiàn", "pos": "v.", "meaning": "Gặp"},
        ],
        [
            {"order_no": 1, "word": "去", "pinyin": "qù", "pos": "v.", "meaning": "Đi"},
            {"order_no": 2, "word": "邮局", "pinyin": "yóujú", "pos": "n.", "meaning": "Bưu điện"},
        ],
    ]

    lesson = LessonBoundary(
        index_no=3,
        title="第三课 明天见",
        page_start=47,  # 0-indexed page 47 & 48
        page_end=48,
        confidence=0.9,
        kind="lesson",
    )

    extractor = VocabExtractor()
    rows = extractor.extract_lesson(pdf_mock, lesson, ai_client=ai_client_mock)

    # Đảm bảo nhận trọn 4 từ vựng từ cả 2 trang với order_no đánh số liên tục 1..4
    assert len(rows) == 4
    assert [r.order_no for r in rows] == [1, 2, 3, 4]
    assert rows[0].word == "明天"
    assert rows[3].word == "邮局"

    # Test fallback khi AI gặp sự cố (Rate Limit / Exception)
    ai_client_error = MagicMock()
    ai_client_error.is_configured.return_value = True
    ai_client_error.extract_vocab_from_image.side_effect = Exception("429 Rate Limit Exceeded")

    fallback_rows = extractor.extract_lesson(pdf_mock, lesson, ai_client=ai_client_error)
    # Không crash app, trả về danh sách từ vựng từ Lớp 1 rule-based spans (hoặc [] nếu không có native spans)
    assert isinstance(fallback_rows, list)


def test_vision_empty_response_is_failure_not_valid_empty_vocab(monkeypatch):
    """Three empty AI responses must stop import instead of becoming a valid lesson."""
    client = MagicMock()
    client.extract_vocab_from_image.return_value = []
    monkeypatch.setattr("hanzi_app.service.vocab.time.sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="không trả về dữ liệu"):
        VocabExtractor().extract_by_llm_image(b"crop", client, source_page=10)


def test_vocab_import_resumes_after_existing_lesson_and_stops_on_empty(
    tmp_path, monkeypatch, caplog
):
    """Resume must preserve completed lessons and must not mark a partial book review."""
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Boya", "boya.pdf", "hash", page_count=20)
    db.replace_lessons(
        book_id,
        [
            LessonBoundary(1, "Bài 1", 0, 4, 1.0, "lesson"),
            LessonBoundary(2, "Bài 2", 5, 9, 1.0, "lesson"),
        ],
    )
    lesson_1, lesson_2 = db.get_lessons(book_id)
    db.replace_vocab(
        lesson_1["id"],
        [VocabRow(1, "你好", "nǐhǎo", None, "xin chào", 1, "vision", False, None)],
    )
    db.close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeExtractor:
        def __init__(self, _dict_db):
            pass

        def extract_lesson(self, _pdf, boundary, ai_client):
            if boundary.index_no == 1:
                return [
                    VocabRow(
                        1, "不应覆盖", None, None, None, 1, "vision", True, "test"
                    )
                ]
            return []

    monkeypatch.setattr("hanzi_app.service.importer.PdfSource", FakePdfSource)
    monkeypatch.setattr("hanzi_app.service.importer.VocabExtractor", FakeExtractor)

    errors = []
    worker = VocabImporterWorker(
        book_id, "boya.pdf", db_path, api_key="test-key"
    )
    worker.failed_import.connect(errors.append)
    with caplog.at_level(logging.ERROR, logger="hanzi_app.service.importer"):
        worker.run()

    checked = UserDb(db_path)
    assert [row["word"] for row in checked.get_lesson_words(lesson_1["id"])] == [
        "你好"
    ]
    assert checked.get_lesson_words(lesson_2["id"]) == []
    assert checked.get_book(book_id)["import_state"] == "review_bounds"
    checked.close()
    assert errors and "Bài 2" in errors[0]
    records = [
        record
        for record in caplog.records
        if record.name == "hanzi_app.service.importer"
    ]
    assert records
    assert records[-1].exc_info is not None
    assert "Vocabulary import failed" in records[-1].getMessage()



def test_multi_page_lesson_uses_one_combined_vision_request():
    """A two-page table must be sent as one lesson image, not two API requests."""
    pdf = MagicMock()
    pdf.page_count.return_value = 2
    pdf.spans.return_value = []
    pdf.get_page_image_bytes.side_effect = [b"page-one", b"page-two"]
    pdf.stack_image_bytes.return_value = b"combined-lesson"

    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.side_effect = [
        [
            {"word": "你好", "pinyin": "nǐhǎo", "meaning_vi": "xin chào"},
            {"word": "老师", "pinyin": "lǎoshī", "meaning_vi": "giáo viên"},
        ],
        AssertionError("Vision was called more than once for one lesson"),
    ]
    lesson = LessonBoundary(1, "Bài 1", 0, 1, 1.0, "lesson")

    rows = VocabExtractor().extract_lesson(pdf, lesson, ai_client=client)

    assert [row.word for row in rows] == ["你好", "老师"]
    assert pdf.stack_image_bytes.call_args.args[0] == [b"page-one", b"page-two"]


def test_configured_vision_checks_even_when_local_rows_are_not_majority_errors(
    monkeypatch,
):
    """A configured AI checks each lesson once instead of trusting a noisy 9/19 local table."""
    extractor = VocabExtractor()
    local_rows = [
        VocabRow(i, f"本地{i}", None, None, None, 1, "regex", i <= 9, "ocr")
        for i in range(1, 20)
    ]
    monkeypatch.setattr(extractor, "is_vocab_page", lambda _spans: True)
    monkeypatch.setattr(
        extractor, "extract_table_spans", lambda _spans, source_page: local_rows
    )
    monkeypatch.setattr(extractor, "table_bbox", lambda _spans: (0, 0, 100, 100))
    monkeypatch.setattr(
        extractor,
        "validate_rows",
        lambda rows: [
            VocabRow(
                row.order_no,
                row.word,
                row.pinyin_src,
                row.pos,
                row.meaning_src,
                row.source_page,
                row.extract_by,
                row.word.startswith("正确"),
                "review" if row.word.startswith("正确") else None,
            )
            for row in rows
        ],
    )

    pdf = MagicMock()
    pdf.page_count.return_value = 1
    pdf.spans.return_value = [MagicMock()]
    pdf.get_page_crop_image_bytes.return_value = b"crop"
    pdf.stack_image_bytes.return_value = b"bounded-crop"
    client = MagicMock()
    client.is_configured.return_value = True

    def vision_result(image):
        if image != b"bounded-crop":
            raise AssertionError("Single-page crop bypassed image size normalization")
        return [
            {"word": f"视觉{i}", "pinyin": "shìjué", "meaning_vi": "đúng"}
            for i in range(1, 21)
        ]

    client.extract_vocab_from_image.side_effect = vision_result

    rows = extractor.extract_lesson(
        pdf, LessonBoundary(4, "Bài 4", 0, 0, 1.0, "lesson"), client
    )

    assert len(rows) == 20
    assert rows[0].word == "视觉1"


def test_vision_duplicate_words_are_removed_before_database_insert():
    """Repeated AI rows must not violate UNIQUE(lesson_id, word)."""
    client = MagicMock()
    client.extract_vocab_from_image.return_value = [
        {"word": "你好", "pinyin": "nǐhǎo", "meaning_vi": "xin chào"},
        {"word": "你好", "pinyin": "nǐhǎo", "meaning_vi": "xin chào"},
        {"word": "老师", "pinyin": "lǎoshī", "meaning_vi": "giáo viên"},
    ]

    rows = VocabExtractor().extract_by_llm_image(
        b"lesson-image", client, source_page=10
    )

    assert [row.word for row in rows] == ["你好", "老师"]
    assert [row.order_no for row in rows] == [1, 2]


def test_vision_json_null_stays_none_in_optional_columns():
    """JSON null must become SQL NULL later, never the literal text 'None'."""
    client = MagicMock()
    client.extract_vocab_from_image.return_value = [
        {
            "word": "玛丽",
            "pinyin": "Mǎlì",
            "pos": None,
            "hanviet": None,
            "meaning_vi": None,
        }
    ]

    row = VocabExtractor().extract_by_llm_image(
        b"lesson-image", client, source_page=10
    )[0]

    assert row.pos is None
    assert row.hanviet_src is None
    assert row.meaning_src is None


def test_short_combined_vision_result_retries_individual_table_pages(monkeypatch):
    """A suspiciously short combined result falls back to its two source crops."""
    extractor = VocabExtractor()
    local_rows = [
        VocabRow(i, f"本地{i}", None, None, None, 1, "regex", i <= 9, "ocr")
        for i in range(1, 20)
    ]
    monkeypatch.setattr(extractor, "is_vocab_page", lambda _spans: True)
    monkeypatch.setattr(
        extractor, "extract_table_spans", lambda _spans, source_page: local_rows
    )
    monkeypatch.setattr(extractor, "table_bbox", lambda _spans: (0, 0, 100, 100))
    monkeypatch.setattr(
        extractor,
        "validate_rows",
        lambda rows: [
            VocabRow(
                row.order_no,
                row.word,
                row.pinyin_src,
                row.pos,
                row.meaning_src,
                row.source_page,
                row.extract_by,
                row.word.startswith("正确"),
                "review" if row.word.startswith("正确") else None,
            )
            for row in rows
        ],
    )

    pdf = MagicMock()
    pdf.page_count.return_value = 2
    pdf.spans.return_value = [MagicMock()]
    pdf.get_page_crop_image_bytes.side_effect = [b"page-1", b"page-2", b"page-1", b"page-2"]
    pdf.stack_image_bytes.side_effect = [b"combined", b"normalized-1", b"normalized-2"]
    client = MagicMock()
    client.is_configured.return_value = True

    def vision_result(image):
        if image == b"combined":
            return [{"word": f"少{i}", "pinyin": "shǎo"} for i in range(1, 12)]
        if image == b"normalized-1":
            return [
                {"word": f"正确{i}", "pinyin": "zhèngquè"}
                for i in range(1, 11)
            ]
        if image == b"normalized-2":
            return [
                {"word": f"正确{i}", "pinyin": "zhèngquè"}
                for i in range(10, 21)
            ]
        raise AssertionError("Individual crop bypassed image normalization")

    client.extract_vocab_from_image.side_effect = vision_result

    rows = extractor.extract_lesson(
        pdf, LessonBoundary(15, "Bài 15", 0, 1, 1.0, "lesson"), client
    )

    assert len(rows) == 20
    assert rows[0].word == "正确1"
    assert rows[-1].word == "正确20"


def test_source_preview_renders_and_stacks_actual_vocab_table_crops(monkeypatch):
    """Review preview must show table crops, not a guessed half of the PDF page."""
    crop_calls = []

    class Span:
        def __init__(self, page, text):
            self.page = page
            self.text = text

    class FakePdf:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def page_count(self):
            return 10

        def spans(self, page):
            return [Span(page, "1" if page == 4 else "text")]

        def get_page_crop_image_bytes(self, page, bbox, dpi):
            crop_calls.append((page, bbox, dpi))
            return f"crop-{page}".encode()

        def stack_image_bytes(self, images, max_width):
            assert images == [b"crop-3", b"crop-4"]
            assert max_width == 1200
            return b"combined-table-preview"

    class FakeExtractor:
        def is_vocab_page(self, spans):
            return spans[0].page == 3

        def table_bbox(self, spans):
            return (0.0, float(spans[0].page), 100.0, 200.0)

    monkeypatch.setattr(importer_module, "PdfSource", FakePdf)
    monkeypatch.setattr(importer_module, "VocabExtractor", FakeExtractor)

    data = importer_module.render_vocab_table_preview(
        "book.pdf", page_start=2, page_end=6, dpi=125
    )

    assert data == b"combined-table-preview"
    assert crop_calls == [
        (3, (0.0, 3.0, 100.0, 200.0), 125),
        (4, (0.0, 4.0, 100.0, 200.0), 125),
    ]


def test_vocab_locator_nhan_header_sinh_tu_bi_tach_span():
    """Boya scan may expose 生词 as separate text spans without the 表 suffix."""

    class Span:
        def __init__(self, text):
            self.text = text

    assert VocabExtractor.is_vocab_page([Span("生"), Span("词")])

def test_crop_writer_is_atomic_and_uses_block_path(tmp_path):
    data = b"png-with-stable-content"

    path = _write_crop_atomic(tmp_path, 4, 9, 2, data)

    stored = Path(path).read_bytes()
    assert stored == data
    assert hashlib.sha256(stored).hexdigest() == hashlib.sha256(data).hexdigest()
    assert Path(path).as_posix().endswith("book-4/lesson-9/block-2.png")
    assert not list(tmp_path.rglob("*.tmp"))


def test_crop_writer_cleans_temp_and_preserves_previous_crop_on_replace_failure(
    tmp_path, monkeypatch
):
    target = tmp_path / "book-4" / "lesson-9" / "block-2.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"previous")

    def fail_replace(_self, _target):
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        _write_crop_atomic(tmp_path, 4, 9, 2, b"new")

    assert target.read_bytes() == b"previous"
    assert not list(tmp_path.rglob("*.tmp"))

def test_vocab_ai_budget_is_three_per_lesson(monkeypatch):
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"crop"
    blocks = [
        VocabBlock(
            i + 1, 2, i + 1, i, (0, 0, 100, 200),
            f"block-{i + 1}.png", 2, i * 2 + 1, i * 2 + 2,
        )
        for i in range(4)
    ]
    extractor = VocabExtractor()
    monkeypatch.setattr(
        extractor, "_extract_local_block", lambda *_args: []
    )
    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.return_value = []

    result = extractor.extract_blocks(pdf, blocks, ai_client=client)

    assert result.complete is False
    assert result.ai_attempts == 3
    assert client.extract_vocab_from_image.call_count == 3


def test_429_result_carries_consumed_attempt(monkeypatch):
    block = VocabBlock(
        9, 2, 1, 4, (0, 0, 100, 200),
        "block.png", 2, 1, 2,
    )
    extractor = VocabExtractor()
    monkeypatch.setattr(
        extractor, "_extract_local_block", lambda *_args: []
    )
    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.side_effect = AiRateLimitError()

    result = extractor.extract_blocks(MagicMock(), [block], client)

    assert result.complete is False
    assert result.ai_attempts == 1
    assert result.blocks[0].ai_attempts == 1
    assert result.blocks[0].status == "incomplete"
    assert "rate_limited" in result.coverage[0].issues


def test_429_keeps_completed_block_and_resume_skips_it(tmp_path, monkeypatch):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Sách thử", "book.pdf", "resume-429", 20)
    db.replace_lessons(
        book_id, [LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")]
    )
    lesson_id = db.get_lessons(book_id)[0]["id"]
    blocks = db.replace_import_blocks(lesson_id, [
        VocabBlock(
            None, lesson_id, 1, 1, (0, 0, 100, 200),
            "done.png", 1, 1, 1,
        ),
        VocabBlock(
            None, lesson_id, 2, 3, (0, 0, 100, 200),
            "pending.png", 2, 2, 3,
        ),
    ])
    db.replace_vocab_block(
        blocks[0]["id"],
        [VocabRow(
            1, "你好", "nǐhǎo", None, None, 2,
            "regex", False, None,
        )],
    )
    db.update_import_block(
        blocks[0]["id"], status="local_ok", ai_attempts=0,
        crop_path=blocks[0]["crop_path"],
    )
    db.close()

    class FakePdfSource:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeExtractor:
        def __init__(self, _dict_db):
            pass

        def extract_blocks(self, _pdf, pending, ai_client=None):
            assert [block.block_no for block in pending] == [2]
            try:
                ai_client.extract_vocab_from_image(b"pending")
            except AiRateLimitError:
                updated = replace(
                    pending[0], status="incomplete", ai_attempts=1
                )
                coverage = BlockCoverage(
                    pending[0].id, 2, 0, 0, 0, (2, 3),
                    ("rate_limited",), False,
                )
                return ExtractionResult(
                    (), (coverage,), (updated,), 1, False
                )
            raise AssertionError("Expected rate limit")

    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.side_effect = AiRateLimitError()
    monkeypatch.setattr(importer_module, "PdfSource", FakePdfSource)
    monkeypatch.setattr(importer_module, "VocabExtractor", FakeExtractor)
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)
    worker.ai_client = client

    worker.run()

    reopened = UserDb(db_path)
    saved = reopened.get_import_blocks(lesson_id)
    assert saved[0]["status"] == "local_ok"
    assert saved[1]["ai_attempts"] == 1
    assert reopened.get_lesson_words(lesson_id)[0]["word"] == "你好"
    assert reopened.get_book(book_id)["import_state"] == "incomplete"
    assert client.extract_vocab_from_image.call_count == 1
    reopened.close()

def test_resume_budget_counts_attempts_used_by_other_blocks(monkeypatch):
    block = VocabBlock(
        7, 2, 2, 4, (0, 0, 100, 200),
        "pending.png", 2, 1, 2,
    )
    extractor = VocabExtractor()
    extractor.lesson_ai_attempts = 2
    monkeypatch.setattr(
        extractor, "_extract_local_block", lambda *_args: []
    )
    client = MagicMock()
    client.is_configured.return_value = True
    client.extract_vocab_from_image.return_value = []

    result = extractor.extract_blocks(MagicMock(), [block], client)

    assert client.extract_vocab_from_image.call_count == 1
    assert result.ai_attempts == 1
    assert result.blocks[0].ai_attempts == 1
    assert result.complete is False


def test_checkpoint_keeps_longer_existing_block_rows(tmp_path):
    db = UserDb(str(tmp_path / "user.sqlite"))
    book_id = db.add_book("Sách thử", "book.pdf", "checkpoint-short", 10)
    db.replace_lessons(
        book_id, [LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")]
    )
    lesson_id = db.get_lessons(book_id)[0]["id"]
    record = db.replace_import_blocks(lesson_id, [
        VocabBlock(
            None, lesson_id, 1, 1, (0, 0, 100, 200),
            "block.png", 2, 1, 2,
        )
    ])[0]
    db.replace_vocab_block(record["id"], [
        VocabRow(
            1, "你好", "nǐhǎo", None, None, 2,
            "regex", False, None,
        ),
        VocabRow(
            2, "老师", "lǎoshī", None, None, 2,
            "regex", False, None,
        ),
    ])
    updated = VocabBlock(
        record["id"], lesson_id, 1, 1, tuple(record["bbox"]),
        record["crop_path"], 2, 1, 2, "incomplete", 2,
    )
    partial = VocabRow(
        1, "你好", "nǐhǎo", None, None, 2,
        "vision", True, "partial", source_block_id=record["id"],
    )
    coverage = BlockCoverage(
        record["id"], 2, 0, 1, 1, (2,),
        ("missing_orders",), False,
    )

    VocabImporterWorker._checkpoint_result(
        db,
        ExtractionResult(
            (partial,), (coverage,), (updated,), 1, False
        ),
    )

    assert [row["word"] for row in db.get_lesson_words(lesson_id)] == [
        "你好", "老师"
    ]
    saved = db.get_import_blocks(lesson_id)[0]
    assert saved["status"] == "incomplete"
    assert saved["ai_attempts"] == 2
    db.close()

def test_load_or_create_blocks_reuses_persisted_manifest(tmp_path):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Sách thử", "book.pdf", "manifest-resume", 10)
    db.replace_lessons(
        book_id, [LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")]
    )
    lesson = db.get_lessons(book_id)[0]
    boundary = LessonBoundary(1, "Một", 0, 9, 1.0, "lesson")
    extractor = MagicMock()
    extractor.locate_blocks.return_value = [
        VocabBlock(
            None, None, 1, 1, (10, 20, 110, 220),
            None, 2, 1, 2,
        )
    ]
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"png"
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)

    first = worker._load_or_create_blocks(
        db, pdf, extractor, lesson, boundary
    )
    second = worker._load_or_create_blocks(
        db, pdf, extractor, lesson, boundary
    )

    assert first == second
    assert first[0].id is not None
    assert Path(first[0].crop_path).read_bytes() == b"png"
    assert extractor.locate_blocks.call_count == 1
    assert pdf.get_page_crop_image_bytes.call_count == 1
    db.close()


def test_load_or_create_blocks_retries_once_with_fresh_pdf_source(tmp_path, monkeypatch):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Test book", "book.pdf", "locator-retry", 10)
    db.replace_lessons(
        book_id, [LessonBoundary(1, "One", 0, 9, 1.0, "lesson")]
    )
    lesson = db.get_lessons(book_id)[0]
    boundary = LessonBoundary(1, "One", 0, 9, 1.0, "lesson")
    located = VocabBlock(
        None, None, 1, 1, (10, 20, 110, 220),
        None, 2, 1, 2,
    )
    extractor = MagicMock()
    extractor.locate_blocks.side_effect = [[], [located]]
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"png"
    retry_source = MagicMock()
    retry_pdf = retry_source.__enter__.return_value
    source_factory = MagicMock(return_value=retry_source)
    monkeypatch.setattr(importer_module, "PdfSource", source_factory)
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)

    blocks = worker._load_or_create_blocks(
        db, pdf, extractor, lesson, boundary
    )

    assert len(blocks) == 1
    assert extractor.locate_blocks.call_count == 2
    assert extractor.locate_blocks.call_args_list[0].args[0] is pdf
    assert extractor.locate_blocks.call_args_list[1].args[0] is retry_pdf
    assert db.get_import_blocks(lesson["id"])[0]["block_no"] == 1
    db.close()
def test_resume_repairs_stale_block_and_preserves_valid_manual_blocks(tmp_path):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Repair", "book.pdf", "resume-repair", 10)
    db.replace_lessons(book_id, [LessonBoundary(1, "One", 0, 9, 1.0, "lesson")])
    lesson = db.get_lessons(book_id)[0]
    records = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 1, (0, 0, 100, 100), "old.png", 2, 0, 2,
                   "incomplete", 4),
        VocabBlock(None, lesson["id"], 2, 2, (0, 0, 50, 50), "valid.png", 1, 1, 1,
                   "local_ok", 7),
        VocabBlock(None, lesson["id"], 3, 3, (0, 0, 50, 50), "manual.png", 1, 1, 1,
                   "manual", 8),
    ])
    db.replace_vocab_block(records[0]["id"], [
        VocabRow(1, "old", "c2", None, None, 1, "regex", False, None,
                 source_block_id=records[0]["id"])
    ])
    db.replace_vocab_block(records[1]["id"], [
        VocabRow(1, "valid", "c2", None, None, 2, "regex", False, None,
                 source_block_id=records[1]["id"])
    ])
    db.replace_vocab_block(records[2]["id"], [
        VocabRow(1, "manual", "c2", None, None, 3, "manual", False, None,
                 source_block_id=records[2]["id"])
    ])
    db.close()

    fresh = VocabBlock(None, None, 1, 1, (10, 10, 110, 110), None, 2, 1, 2)
    extractor = MagicMock()
    extractor.locate_blocks.return_value = [fresh]
    pdf = MagicMock()
    pdf.get_page_crop_image_bytes.return_value = b"fresh-crop"
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)

    reopened = UserDb(db_path)
    repaired = worker._load_or_create_blocks(
        reopened, pdf, extractor, reopened.get_lessons(book_id)[0],
        LessonBoundary(1, "One", 0, 9, 1.0, "lesson"),
    )

    assert repaired[0].id == records[0]["id"]
    assert repaired[0].ai_attempts == 4
    assert repaired[0].page_index == 1
    assert repaired[0].first_order == 1
    assert repaired[0].status == "pending"
    assert Path(repaired[0].crop_path).read_bytes() == b"fresh-crop"
    remaining_rows = reopened.get_lesson_words(lesson["id"])
    assert [row["word"] for row in remaining_rows] == ["valid", "manual"]
    assert {row["source_block_id"] for row in remaining_rows} == {
        records[1]["id"], records[2]["id"]
    }
    saved = reopened.get_import_blocks(lesson["id"])
    assert saved[1]["status"] == "local_ok"
    assert saved[2]["status"] == "manual"
    reopened.close()


def test_resume_rejects_ambiguous_stale_manifest_without_mutation(tmp_path):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Ambiguous", "book.pdf", "resume-ambiguous", 10)
    db.replace_lessons(book_id, [LessonBoundary(1, "One", 0, 9, 1.0, "lesson")])
    lesson = db.get_lessons(book_id)[0]
    record = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 1, (0, 0, 100, 100), "old.png", 2, 0, 2,
                   "incomplete", 4)
    ])[0]
    before = db.get_import_blocks(lesson["id"])
    db.close()

    extractor = MagicMock()
    extractor.locate_blocks.return_value = [
        VocabBlock(None, None, 1, 1, (10, 10, 110, 110), None, 2, 1, 2),
        VocabBlock(None, None, 1, 1, (10, 10, 110, 110), None, 2, 1, 2),
    ]
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)
    reopened = UserDb(db_path)

    with pytest.raises(RuntimeError, match="manifest_needs_review"):
        worker._load_or_create_blocks(
            reopened, MagicMock(), extractor, reopened.get_lessons(book_id)[0],
            LessonBoundary(1, "One", 0, 9, 1.0, "lesson"),
        )

    assert reopened.get_import_blocks(lesson["id"]) == before
    assert not (Path(db_path).parent / "book_crops").exists()
    reopened.close()


def test_resume_clears_stale_rows_for_valid_automatic_manifest(tmp_path):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Rows", "book.pdf", "resume-stale-rows", 10)
    db.replace_lessons(book_id, [LessonBoundary(1, "One", 0, 9, 1.0, "lesson")])
    lesson = db.get_lessons(book_id)[0]
    record = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 1, (0, 0, 100, 100), "valid.png", 2, 1, 2,
                   "ai_ok", 2)
    ])[0]
    db.replace_vocab_block(record["id"], [
        VocabRow(1, "one", None, None, None, 1, "vision", False, None,
                 source_block_id=record["id"]),
        VocabRow(2, "two", None, None, None, 1, "vision", False, None,
                 source_block_id=record["id"]),
        VocabRow(3, "three", None, None, None, 1, "vision", False, None,
                 source_block_id=record["id"]),
    ])
    db.close()

    extractor = MagicMock()
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)
    reopened = UserDb(db_path)

    blocks = worker._load_or_create_blocks(
        reopened, MagicMock(), extractor, reopened.get_lessons(book_id)[0],
        LessonBoundary(1, "One", 0, 9, 1.0, "lesson"),
    )

    assert blocks[0].id == record["id"]
    assert blocks[0].status == "pending"
    assert blocks[0].ai_attempts == 2
    assert blocks[0].first_order == 1
    assert blocks[0].last_order == 2
    assert reopened.get_lesson_words(lesson["id"]) == []
    extractor.locate_blocks.assert_not_called()
    reopened.close()


def test_resume_clears_zero_rows_for_valid_automatic_manifest(tmp_path):
    db_path = str(tmp_path / "user.sqlite")
    db = UserDb(db_path)
    book_id = db.add_book("Zero Rows", "book.pdf", "resume-zero-rows", 10)
    db.replace_lessons(book_id, [LessonBoundary(1, "One", 0, 9, 1.0, "lesson")])
    lesson = db.get_lessons(book_id)[0]
    record = db.replace_import_blocks(lesson["id"], [
        VocabBlock(None, lesson["id"], 1, 1, (0, 0, 100, 100), "valid.png", 2, 1, 2,
                   "local_ok", 2)
    ])[0]
    db.close()

    extractor = MagicMock()
    worker = VocabImporterWorker(book_id, "book.pdf", db_path)
    reopened = UserDb(db_path)

    blocks = worker._load_or_create_blocks(
        reopened, MagicMock(), extractor, reopened.get_lessons(book_id)[0],
        LessonBoundary(1, "One", 0, 9, 1.0, "lesson"),
    )

    assert blocks[0].id == record["id"]
    assert blocks[0].status == "pending"
    assert blocks[0].ai_attempts == 2
    assert reopened.get_lesson_words(lesson["id"]) == []
    extractor.locate_blocks.assert_not_called()
    reopened.close()
