"""Chay app kem bo theo doi, in ra ten widget nao bat len thanh CUA SO that.

Dung khi van thay mot cua so chop len roi tat ma khong biet no la cai gi.

    python tools/chan_doan_cua_so.py

Roi lam dung thao tac gay loi: go tu, bam Tim, bam chon mot tu, bam sang tu khac.
Moi lan co cua so cap cao nhat hien ra, cong cu in ten lop widget do cong voi
day goi ham dan toi cho tao ra no. Chep toan bo phan in ra gui lai.

Cua so chinh MainWindow hien mot lan luc khoi dong la binh thuong. Bat ky dong
nao SAU do deu la thu phai sua.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from PySide6.QtCore import QEvent, QObject  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from hanzi_app import main as m  # noqa: E402

_dem = 0


class TheoDoi(QObject):
    """Bo loc su kien gan tren QApplication nen nhan duoc su kien cua MOI doi tuong."""

    def eventFilter(self, obj, ev):  # noqa: N802 (ten do Qt quy dinh)
        global _dem
        if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            _dem += 1
            ten_lop = type(obj).__name__
            ten = obj.objectName() or "(khong dat ten)"
            print(f"\n{'=' * 70}")
            print(f"[{_dem}] CUA SO HIEN RA: {ten_lop}   objectName={ten}")
            print(f"     kich thuoc={obj.size().width()}x{obj.size().height()}")
            print(f"{'-' * 70}")
            # Bo qua cac khung cua chinh cong cu nay, chi giu ma cua ung dung.
            khung = [
                d for d in traceback.format_stack()[:-1]
                if "chan_doan_cua_so.py" not in d and "PySide6" not in d
            ]
            print("".join(khung[-8:]) or "  (khong co khung nao thuoc ma ung dung)")
            print("=" * 70)
        return False


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    app = QApplication(sys.argv)
    theo_doi = TheoDoi()
    app.installEventFilter(theo_doi)

    for dong in m.load_fonts():
        print(f"[phong] {dong}")
    app.setStyleSheet(m.QSS.format(**m.PALETTE))

    print("\nBo theo doi da bat. Cua so dau tien la MainWindow, binh thuong.")
    print("Hay go mot tu, bam Tim, roi bam chon vai tu khac nhau.\n")

    window = m.build_window()
    window.show()
    ma = app.exec()

    print(f"\nTong so cua so da hien ra trong phien nay: {_dem}")
    if _dem <= 1:
        print("Chi co MainWindow. Khong bat duoc cua so la nao ca.")
    return ma


if __name__ == "__main__":
    sys.exit(main())
