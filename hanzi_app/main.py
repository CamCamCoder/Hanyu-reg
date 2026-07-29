"""Điểm vào: dựng các đối tượng rồi bơm vào nhau, đúng thứ tự của mục 13.1.

    DictDb + UserDb  ->  LookupService, Decomposer  ->  MainWindow

UserDb và module scheduler đi kèm xuống cửa sổ: màn hình Ôn tập cần ghi tiến độ
và tính lịch, mà tầng ui không được tự mở cơ sở dữ liệu.

Chạy bằng `python -m hanzi_app.main` từ gốc kho.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.userdb import UserDb
from hanzi_app.service.decomposer import Decomposer
from hanzi_app.service.lookup import LookupService
from hanzi_app.service import scheduler
from hanzi_app.ui.main_window import MainWindow
from hanzi_app.ui.theme import PALETTE, load_fonts

ROOT = Path(__file__).resolve().parents[1]

# Mục 13.2 đặt từ điển ở resources/, nhưng bản dựng bằng build_dict.py hiện nằm
# ở gốc kho. Thử cả hai chỗ thay vì cố định một đường dẫn.
DICT_CANDIDATES = (
    ROOT / "dict.sqlite",
    Path(__file__).resolve().parent / "resources" / "dict.sqlite",
)
USER_PATH = ROOT / "user.sqlite"

# Bảng kiểu của mục 6.1. Widget nào vẽ bằng QPainter thì tự lấy màu trong
# PALETTE, phần còn lại đi qua bảng kiểu này.
QSS = """
QWidget {{ background: {bg}; color: {ink}; }}
QWidget#Page {{ background: {bg}; }}

QFrame#Nav {{ background: {card}; border-right: 1px solid {line}; }}
QPushButton#NavBtn {{
    background: transparent; border: none; border-left: 3px solid transparent;
    color: {ink2}; text-align: left; padding-left: 15px;
}}
QPushButton#NavBtn:hover {{ background: {bg}; }}
QPushButton#NavBtn:checked {{
    color: {accent}; border-left: 3px solid {accent}; background: {bg};
}}

QFrame#Card {{ background: {card}; border: 1px solid {line}; border-radius: 6px; }}
QFrame#Row {{ background: {card}; border: none; }}
QFrame#Row:hover {{ background: {bg}; }}

QLineEdit {{
    background: {card}; border: 1px solid {line}; border-radius: 4px;
    padding: 0 10px; color: {ink};
}}
QLineEdit:focus {{ border: 1px solid {accent}; }}

QPushButton#Primary {{
    background: {accent}; color: {card}; border: none; border-radius: 4px;
}}
QPushButton#Primary:hover {{ background: {accent_hover}; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def find_dict() -> Path | None:
    return next((p for p in DICT_CANDIDATES if p.is_file()), None)


def build_window() -> MainWindow:
    """Mở hai cơ sở dữ liệu, dựng hai service, bơm vào cửa sổ chính."""
    dict_path = find_dict()
    if dict_path is None:
        cho = "\n  ".join(str(p) for p in DICT_CANDIDATES)
        raise SystemExit(f"Khong tim thay dict.sqlite. Da tim o:\n  {cho}")

    dict_db = DictDb(str(dict_path))
    user_db = UserDb(str(USER_PATH))
    lookup = LookupService(dict_db, user_db)
    decomposer = Decomposer(dict_db)
    # user_db đi thẳng vào cửa sổ chứ không mở kết nối thứ hai: mục 13.1 cấm
    # tầng ui tự mở cơ sở dữ liệu. scheduler là module hàm, bơm nguyên module.
    return MainWindow(lookup, decomposer, user_db, scheduler, dict_db)


def main() -> int:
    # Cảnh báo phông có dấu tiếng Việt; console Windows mặc định là cp1252 nên
    # ép utf-8 để dòng cảnh báo không tự làm sập chương trình.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    app = QApplication(sys.argv)
    for dong in load_fonts():
        print(f"[phong] {dong}")
    app.setStyleSheet(QSS.format(**PALETTE))

    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
