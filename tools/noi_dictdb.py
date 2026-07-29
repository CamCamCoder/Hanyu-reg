"""Noi dict_db tu main.py xuong ScreenReview, de bai tap lay duoc ro dap an nhieu.

Ba sua doi:
  main.py         MainWindow(...)            -> them , dict_db
  main_window.py  def __init__(self, ...)    -> them dict_db=None truoc parent
  main_window.py  ScreenReview(...)          -> them , dict_db

dict_db la tuy chon o ca hai noi: thieu no thi che do Trac nghiem tu tat con
phan con lai chay nhu cu, khong sap.

Chay tu goc kho:

    python tools/noi_dictdb.py           # xem truoc
    python tools/noi_dictdb.py --ghi     # ghi that, co sao luu
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
MAIN = GOC / "hanzi_app" / "main.py"
CUA_SO = GOC / "hanzi_app" / "ui" / "main_window.py"


def _them_dt(noi_dung: str, ten_ham: str, them: str) -> tuple[str, list[str]]:
    """Them mot doi so vao cuoi moi loi goi ``ten_ham(...)``."""
    mau = re.compile(re.escape(ten_ham) + r"\(\s*(?P<dt>[^()]*?)\s*\)")
    bao: list[str] = []
    ket = noi_dung
    for m in reversed(list(mau.finditer(noi_dung))):
        dt = m.group("dt")
        if them in dt or not dt.strip():
            continue
        thay = f"{ten_ham}({dt}, {them})"
        ket = ket[: m.start()] + thay + ket[m.end():]
        bao.append(f"{ten_ham}({dt})  ->  {thay}")
    return ket, bao


def _them_tham_so(noi_dung: str, lop: str, ten: str) -> tuple[str, list[str]]:
    """Them ``ten=None`` vao truoc ``parent`` trong __init__ cua mot lop."""
    i = noi_dung.find(f"class {lop}")
    if i == -1:
        return noi_dung, []
    j = noi_dung.find("def __init__(", i)
    if j == -1:
        return noi_dung, []
    k = noi_dung.find(")", j)
    chu_ky = noi_dung[j : k + 1]
    if ten in chu_ky:
        return noi_dung, []
    if "parent" in chu_ky:
        moi = chu_ky.replace("parent", f"{ten}=None, parent", 1)
    else:
        moi = chu_ky[:-1].rstrip().rstrip(",") + f", {ten}=None)"
    return noi_dung[:j] + moi + noi_dung[k + 1 :], [f"{chu_ky}  ->  {moi}"]


def _xu_ly(tep: Path, viec, ghi: bool) -> bool:
    if not tep.is_file():
        print(f"  LOI: khong thay {tep}")
        return False
    goc = tep.read_text(encoding="utf-8")
    moi, bao = viec(goc)
    print(f"  {tep.relative_to(GOC)}")
    if not bao:
        print("      khong co gi phai sua")
        return True
    for d in bao:
        print(f"      {d}")
    try:
        ast.parse(moi)
    except SyntaxError as loi:
        print(f"      LOI CU PHAP dong {loi.lineno}: {loi.msg} — khong ghi")
        return False
    print("      cu phap: OK")
    if ghi:
        shutil.copy2(tep, tep.with_suffix(".py.truoc-08c"))
        tep.write_text(moi, encoding="utf-8")
        print("      da ghi")
    return True


def main() -> int:
    bo = argparse.ArgumentParser(description="Noi dict_db xuong ScreenReview")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh xem truoc")
    tham_so = bo.parse_args()

    print("Che do: GHI THAT, sao luu duoi .truoc-08c\n" if tham_so.ghi
          else "Che do: XEM TRUOC, khong ghi gi ca\n")

    def viec_main(s: str):
        return _them_dt(s, "MainWindow", "dict_db")

    def viec_cua_so(s: str):
        s, b1 = _them_tham_so(s, "MainWindow", "dict_db")
        s, b2 = _them_dt(s, "ScreenReview", "dict_db")
        return s, b1 + b2

    ok = _xu_ly(MAIN, viec_main, tham_so.ghi)
    ok = _xu_ly(CUA_SO, viec_cua_so, tham_so.ghi) and ok

    print()
    if not ok:
        print("Co loi. Khong chay app truoc khi xem lai.")
        return 1
    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
    else:
        print("Xong. Chay `python -m hanzi_app.main` de kiem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
