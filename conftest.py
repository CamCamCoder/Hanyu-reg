"""Cấu hình pytest tối thiểu: thêm thư mục gốc kho vào sys.path để các tệp test
import được gói ``hanzi_app`` mà không phải tự chèn sys.path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
