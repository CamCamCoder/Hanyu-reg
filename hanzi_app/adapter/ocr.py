"""Adapter bọc OCR Engine.

Chỉ tầng adapter biết tới OCR Engine. Tự động xử lý fallback nếu môi trường
chưa cài Tesseract / PaddleOCR.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from hanzi_app.data.models import TextSpan

if TYPE_CHECKING:
    import fitz

logger = logging.getLogger(__name__)

_WINDOWS_OCR_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
function Await($Operation, [Type]$ResultType) {
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
      $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
  $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
  $task.Wait()
  return $task.Result
}
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($args[0])) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$language = [Windows.Globalization.Language]::new($args[1])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) { throw "Không có Windows OCR cho $($args[1])" }
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$words = @()
foreach ($line in $result.Lines) {
  foreach ($word in $line.Words) {
    $r = $word.BoundingRect
    $words += [ordered]@{
      text = $word.Text
      x0 = [double]$r.X
      y0 = [double]$r.Y
      x1 = [double]($r.X + $r.Width)
      y1 = [double]($r.Y + $r.Height)
    }
  }
}
ConvertTo-Json -Compress -Depth 3 -InputObject @($words)
"""


class OcrAdapter:
    """Bọc OCR Engine cho trang sách quét.

    Hỗ trợ PyMuPDF (fitz) OCR page nếu fitz được biên dịch kèm Tesseract,
    hoặc Tesseract/PaddleOCR qua Python if available.
    """

    def __init__(self, lang: str = "chi_sim+vie+eng") -> None:
        self.lang = lang
        self._available = True
        self._windows_available: bool | None = None

    def is_available(self) -> bool:
        return self._available

    def ocr_page(self, page: fitz.Page) -> list[TextSpan]:
        """Thực hiện OCR trên 1 trang PyMuPDF (fitz.Page).

        Trả về danh sách TextSpan (is_ocr=True).
        """
        if not self._available:
            return []

        spans: list[TextSpan] = []
        try:
            # Thử PyMuPDF built-in Tesseract OCR
            tp = page.get_textpage_ocr(flags=0, language=self.lang)
            text_json = tp.extractDICT()
            for block in text_json.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = tuple(span.get("bbox", (0, 0, 0, 0)))
                            font_size = float(span.get("size", 12.0))
                            spans.append(
                                TextSpan(
                                    text=text,
                                    bbox=bbox,
                                    font_size=font_size,
                                    is_ocr=True,
                                )
                            )
        except Exception as err:
            logger.debug("PyMuPDF/Tesseract không khả dụng, thử Windows OCR: %s", err)

        if spans:
            return spans

        try:
            pix = page.get_pixmap(dpi=250, alpha=False)
            return self.ocr_png_bytes(pix.tobytes("png"))
        except Exception as err:
            self._available = False
            logger.debug("Windows OCR không khả dụng: %s", err)

        return spans

    def ocr_png_bytes(
        self, image_bytes: bytes, language: str = "zh-Hans-CN"
    ) -> list[TextSpan]:
        """OCR ảnh PNG bằng Windows OCR và giữ bounding box từng từ.

        Đây là đường lui không cần cài thêm gói Python trên Windows 10/11.
        """
        if not image_bytes:
            return []

        with tempfile.TemporaryDirectory(prefix="hanzi_ocr_") as tmp:
            image_path = Path(tmp) / "page.png"
            script_path = Path(tmp) / "windows_ocr.ps1"
            image_path.write_bytes(image_bytes)
            script_path.write_text(_WINDOWS_OCR_SCRIPT, encoding="utf-8-sig")
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path.resolve()),
                    str(image_path.resolve()),
                    language,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                check=False,
            )

        if completed.returncode != 0:
            self._windows_available = False
            logger.debug("Windows OCR lỗi: %s", completed.stderr.strip())
            return []

        try:
            data = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError:
            self._windows_available = False
            return []

        if isinstance(data, dict):
            data = [data]
        self._windows_available = True
        return [
            TextSpan(
                text=str(item["text"]).strip(),
                bbox=(
                    float(item["x0"]),
                    float(item["y0"]),
                    float(item["x1"]),
                    float(item["y1"]),
                ),
                font_size=max(1.0, float(item["y1"]) - float(item["y0"])),
                is_ocr=True,
            )
            for item in data
            if str(item.get("text", "")).strip()
        ]
