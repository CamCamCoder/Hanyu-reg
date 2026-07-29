"""Truyen them decomposer vao ScreenReview trong main_window.py.

Phien 08b doi chu ky:
    ScreenReview(lookup, user_db, scheduler)
  ->
    ScreenReview(lookup, user_db, scheduler, decomposer)

Decomposer dung de ve cay chiet tu o mat sau the on tap. No dat CUOI danh sach
tham so nen thu tu ba tham so cu khong doi.

Chay tu goc kho:

    python tools/va_main_window.py           # xem truoc, khong ghi gi
    python tools/va_main_window.py --ghi     # ghi that, co sao luu
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
TEP = GOC / "hanzi_app" / "ui" / "main_window.py"

GOI = re.compile(r"ScreenReview\(\s*(?P<dt>[^)]*?)\s*\)")


def main() -> int:
    bo = argparse.ArgumentParser(description="Them decomposer vao ScreenReview")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh xem truoc")
    tham_so = bo.parse_args()

    if not TEP.is_file():
        print(f"LOI: khong thay {TEP}. Chay kich ban tu goc kho.")
        return 1

    goc = TEP.read_text(encoding="utf-8")
    tim = list(GOI.finditer(goc))

    if not tim:
        print("Khong tim thay cho nao goi ScreenReview(...).")
        print("Mo hanzi_app/ui/main_window.py, tim ScreenReview roi them decomposer tay.")
        return 1

    doi = []
    moi = goc
    for m in reversed(tim):
        dt = m.group("dt")
        if "decomposer" in dt:
            print(f"  Bo qua, da co decomposer: ScreenReview({dt})")
            continue
        thay = f"ScreenReview({dt}, decomposer)" if dt.strip() else "ScreenReview(decomposer)"
        moi = moi[: m.start()] + thay + moi[m.end():]
        doi.append((f"ScreenReview({dt})", thay))

    if not doi:
        print("\nKhong co gi phai sua.")
        return 0

    print(f"Tep: {TEP.relative_to(GOC)}")
    for cu, mm in doi:
        print(f"      {cu}")
        print(f"   -> {mm}")

    # Kiem so bo: bien decomposer phai co trong pham vi ham do.
    if "decomposer" not in goc:
        print()
        print("  CANH BAO: khong thay chu 'decomposer' o cho nao khac trong tep nay.")
        print("  Co the MainWindow chua nhan decomposer lam tham so. Mo tep kiem tay")
        print("  truoc khi chay --ghi, neu khong app se bao NameError luc khoi dong.")

    print()
    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
        return 0

    shutil.copy2(TEP, TEP.with_suffix(".py.truoc-08b"))
    TEP.write_text(moi, encoding="utf-8")
    print("Da ghi. Ban goc luu o main_window.py.truoc-08b")
    return 0


if __name__ == "__main__":
    sys.exit(main())
