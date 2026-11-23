"""Adapter gọi API LLM (Text & Vision) ép lược đồ JSON cho bóc tách sách.

Chỉ tầng adapter chứa mã gọi API / HTTP. Hỗ trợ cả text và ảnh trang quét (Vision AI).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any
from urllib.error import HTTPError

logger = logging.getLogger(__name__)


class AiClientError(RuntimeError):
    """Lỗi AI phải nổi lên tầng điều phối, không giả thành kết quả rỗng."""


class AiRateLimitError(AiClientError):
    """Google từ chối request do giới hạn tần suất hoặc quota."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        message = "Gemini đang giới hạn lượt gọi (HTTP 429)"
        if retry_after is not None:
            message += f"; thử lại sau {retry_after} giây"
        super().__init__(message)

# Prompt cho phân tách bài học từ ảnh/text
PROMPT_SPLIT_LESSONS = """Bạn là chuyên gia phân tích giáo trình tiếng Trung / song ngữ (như Boya, Hán ngữ).
Dưới đây là thông tin / ảnh các trang PDF.
Hãy nhận diện danh sách các bài học (Lessons) và trả về KẾT QUẢ DUY NHẤT dưới dạng CHUỖI JSON như sau:

[
  {{
    "index_no": 1,
    "title": "Bài 1: 你好 (Xin chào)",
    "page_start": 0,
    "page_end": 10
  }}
]

Không kèm theo lời giải thích nào khác ngoài JSON.

Thông tin trang:
{summaries_text}
"""

# Prompt cho bóc tách từ vựng từ ảnh/text trang sách
PROMPT_EXTRACT_VOCAB = """You extract Chinese textbook vocabulary rows from images.
The input image may be either a clean crop of one vocabulary table or a full-page
recovery fallback. Use the validator context, when present, to identify the target
block/order range. Extract only vocabulary rows from sinh ci / new words tables.
Ignore dialogues, grammar notes, exercises, headers, footers, page numbers, and
reference tables such as part-of-speech lists.

Copy the visible cell text exactly. Do not translate, complete, or invent hidden
content. Return only a JSON array using this schema:

[
  {
    "order_no": 1,
    "word": "你好",
    "pinyin": "nǐhǎo",
    "pos": "v.",
    "hanviet": "nhĩ hảo",
    "meaning_en": "hello",
    "meaning_vi": "xin chào"
  }
]

If the target block has an order range, return only rows in that range. If an order
number is not printed but the visible rows clearly belong to the target block, infer
the sequential order numbers for those rows. Do not return explanatory text.
"""


PROMPT_SPLIT_LESSONS_IMAGE = """You identify lesson boundaries in a Chinese-language textbook.
Read the supplied contact-sheet image and reconcile it with the local evidence below.
Return only a JSON list. Every item must contain a positive integer `index_no`,
an optional `title`, and a zero-based integer `page_start`. Do not invent pages.

Local evidence:
{evidence_text}

Validator issues from the preceding attempt:
{issue_context}
"""


class AiClient:
    """Client kết nối API LLM ép đầu ra dạng JSON."""

    def __init__(
        self, api_key: str | None = None, model: str = "gemini-3.1-flash-lite"
    ) -> None:
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def split_lessons(self, summaries_text: str) -> list[dict[str, Any]]:
        """Gửi tóm tắt các trang cho LLM để phân tách bài học."""
        prompt = PROMPT_SPLIT_LESSONS.format(summaries_text=summaries_text)
        response_text = self._call_llm_text(prompt)
        return self._parse_json_list(response_text)

    def split_lessons_from_image(
        self,
        image_bytes: bytes,
        evidence_text: str,
        issue_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Ask Vision to resolve only lesson boundaries local evidence cannot prove."""
        if not self.api_key or not image_bytes:
            return []

        prompt = PROMPT_SPLIT_LESSONS_IMAGE.format(
            evidence_text=evidence_text,
            issue_context=issue_context or "None.",
        )
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self._parse_json_list(self._call_llm_vision(prompt, image_b64))

    def extract_vocab(self, page_text: str) -> list[dict[str, Any]]:
        """Gửi văn bản trang cho LLM để bóc tách từ vựng."""
        prompt = PROMPT_EXTRACT_VOCAB + "\n\nPage text:\n" + page_text
        response_text = self._call_llm_text(prompt)
        return self._parse_json_list(response_text)

    def extract_vocab_from_image(
        self,
        image_bytes: bytes,
        issue_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read one vocabulary crop with optional validator guidance."""
        if not self.api_key or not image_bytes:
            return []

        prompt = PROMPT_EXTRACT_VOCAB
        if issue_context:
            prompt += f"\n\nValidator context:\n{issue_context}"
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        response_text = self._call_llm_vision(prompt, b64_data)
        return self._parse_json_list(response_text)

    def _call_llm_text(self, prompt: str) -> str:
        if not self.api_key:
            return ""

        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as err:
            logger.warning("Lỗi gọi LLM Text API: %s", err)

        return ""

    def _call_llm_vision(self, prompt: str, image_b64: str) -> str:
        if not self.api_key:
            return ""

        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except HTTPError as err:
            if err.code == 429:
                retry_header = err.headers.get("Retry-After") if err.headers else None
                try:
                    retry_after = int(retry_header) if retry_header else None
                except ValueError:
                    retry_after = None
                raise AiRateLimitError(retry_after) from err
            raise AiClientError(f"Lỗi Gemini Vision HTTP {err.code}") from err
        except Exception as err:
            logger.warning("Lỗi gọi LLM Vision API: %s", err)
            raise AiClientError("Không thể gọi Gemini Vision") from err

    def _parse_json_list(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                json_str = text[start : end + 1]
                data = json.loads(json_str)
                if isinstance(data, list):
                    return data
        except Exception as err:
            logger.warning("Không thể parse JSON từ LLM: %s", err)
        return []
