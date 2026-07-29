"""Va loi chop cua so lan 2: setVisible(True) tren widget CHUA CO CHA.

NGUYEN NHAN. Trong _hang_them cua screen_lookup.py, hai widget _nut_them va
_nhan_da_them duoc tao roi goi setVisible ngay, TRUOC khi layout chua chung duoc
gan vao mot widget. Widget khong cha ma bao hien len thi Qt coi no la cua so cap
cao nhat va Windows cap cho no mot HWND that -> mot cua so chop len roi tat khi
addLayout gan no vao cay widget.

CACH SUA. Widget nam trong layout thi MAC DINH da hien, nen khong bao gio can
setVisible(True) luc dung. Chi can an cai khong dung, va setVisible(False) thi
luon an toan vi no khong tao cua so.

    self._nut_them.setVisible(not da_co)        ->   if da_co:
    self._nhan_da_them.setVisible(da_co)                 self._nut_them.setVisible(False)
                                                     else:
                                                         self._nhan_da_them.setVisible(False)

Chay tu goc kho:

    python tools/va_loi_chop_lan_2.py           # xem truoc, khong ghi gi
    python tools/va_loi_chop_lan_2.py --ghi     # ghi that, co sao luu
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC = GOC / "hanzi_app"

# Cap hai dong lien nhau: mot cai setVisible(not X), cai kia setVisible(X).
CAP = re.compile(
    r"^(?P<thut>[ \t]*)(?P<a>self\.[A-Za-z_][A-Za-z0-9_]*)\.setVisible\(not (?P<bien>[A-Za-z_][A-Za-z0-9_]*)\)[ \t]*\n"
    r"[ \t]*(?P<b>self\.[A-Za-z_][A-Za-z0-9_]*)\.setVisible\((?P=bien)\)[ \t]*$",
    re.MULTILINE,
)

# Truong hop le loi: mot dong setVisible(True) don doc luc dung.
DON = re.compile(
    r"^(?P<thut>[ \t]*)(?P<ten>self\.[A-Za-z_][A-Za-z0-9_]*)\.setVisible\(True\)[ \t]*$",
    re.MULTILINE,
)

CHU_THICH = (
    "# Khong goi setVisible(True) luc dung: widget chua co cha se bi Qt coi la\n"
    "# cua so cap cao nhat va Windows cap cho no mot HWND that, gay ra mot cua\n"
    "# so chop len roi tat. Widget trong layout thi mac dinh da hien, nen chi\n"
    "# can an cai khong dung; setVisible(False) luon an toan.\n"
)


def _thay_cap(m: re.Match) -> str:
    thut, a, b, bien = m.group("thut"), m.group("a"), m.group("b"), m.group("bien")
    ct = "".join(thut + d + "\n" for d in CHU_THICH.rstrip("\n").split("\n"))
    return (
        f"{ct}"
        f"{thut}if {bien}:\n"
        f"{thut}    {a}.setVisible(False)\n"
        f"{thut}else:\n"
        f"{thut}    {b}.setVisible(False)"
    )


def va_mot_tep(duong_dan: Path, ghi: bool) -> list[str]:
    goc = duong_dan.read_text(encoding="utf-8")
    moi, so_cap = CAP.subn(_thay_cap, goc)

    bao: list[str] = []
    if so_cap:
        bao.append(f"{so_cap} cap setVisible(not X)/setVisible(X) -> if/else chi an")

    con_lai = DON.findall(moi)
    if con_lai:
        ten = ", ".join(sorted({t for _, t in con_lai}))
        bao.append(f"CANH BAO: van con setVisible(True) don doc tren: {ten} — xem tay")

    if so_cap and ghi:
        shutil.copy2(duong_dan, duong_dan.with_suffix(duong_dan.suffix + ".truoc-khi-va2"))
        duong_dan.write_text(moi, encoding="utf-8")

    return bao


def main() -> int:
    bo = argparse.ArgumentParser(description="Va loi setVisible tren widget chua co cha")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh chi xem truoc")
    tham_so = bo.parse_args()

    if not THU_MUC.is_dir():
        print(f"LOI: khong thay {THU_MUC}. Chay kich ban tu goc kho.")
        return 1

    print(f"Quet: {THU_MUC}")
    print("Che do: GHI THAT, sao luu duoi .truoc-khi-va2\n" if tham_so.ghi
          else "Che do: XEM TRUOC, khong ghi gi ca\n")

    tong = 0
    for tep in sorted(THU_MUC.rglob("*.py")):
        if "__pycache__" in tep.parts:
            continue
        bao = va_mot_tep(tep, tham_so.ghi)
        if not bao:
            continue
        print(f"  {tep.relative_to(GOC)}")
        for d in bao:
            print(f"      {d}")
            if d.startswith(("1 cap", "2 cap", "3 cap")) or "cap setVisible" in d:
                tong += 1

    print()
    if tong == 0:
        print("Khong tim thay cap setVisible nao khop mau.")
        print("Gui lai tep screen_lookup.py de xem truc tiep.")
        return 0

    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
    else:
        print("Da ghi. Tat han app roi mo lai, bam qua lai vai tu de kiem tra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
