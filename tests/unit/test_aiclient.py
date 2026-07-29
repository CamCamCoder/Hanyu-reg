"""Kiểm thử unit cho adapter/aiclient.py."""

from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from hanzi_app.adapter.aiclient import AiClient, AiRateLimitError


def test_aiclient_unconfigured():
    client = AiClient(api_key=None)
    assert client.is_configured() is False
    res_split = client.split_lessons("Trang 1: 第一课")
    assert res_split == []

    res_vocab = client.extract_vocab("1 你好 nǐhǎo Xin chào")
    assert res_vocab == []


def test_aiclient_parse_json():
    client = AiClient()
    sample_text = """
    Sau đây là kết quả JSON:
    [
      {"index_no": 1, "title": "Bài 1", "page_start": 0, "page_end": 5}
    ]
    """
    res = client._parse_json_list(sample_text)
    assert len(res) == 1
    assert res[0]["index_no"] == 1
    assert res[0]["title"] == "Bài 1"


def test_vision_raises_rate_limit_instead_of_returning_empty_result():
    """A HTTP 429 must remain an API failure, never masquerade as zero words."""
    client = AiClient(api_key="test-key")
    error = HTTPError(
        url="https://example.invalid",
        code=429,
        msg="Too Many Requests",
        hdrs={"Retry-After": "17"},
        fp=BytesIO(b'{"error":{"message":"quota exceeded"}}'),
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(AiRateLimitError) as caught:
            client.extract_vocab_from_image(b"fake-image")

    assert caught.value.retry_after == 17


def test_default_client_uses_high_volume_multimodal_model():
    """The default import path must use the validated high-volume Vision model."""
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"[]"}]}}]}'

    def urlopen(request, timeout):
        if "models/gemini-3.1-flash-lite:generateContent" not in request.full_url:
            raise AssertionError("Low-quota model selected")
        return Response()

    client = AiClient(api_key="test-key")
    with patch("urllib.request.urlopen", side_effect=urlopen):
        assert client.extract_vocab_from_image(b"image") == []
