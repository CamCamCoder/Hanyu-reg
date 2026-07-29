"""Va loi cua so chop len roi tat ngay khi bam chon mot tu.

NGUYEN NHAN. Trong Qt, `setParent(None)` bien mot widget thanh CUA SO CAP CAO
NHAT. Tren Windows, Qt cap cho no mot HWND that ngay luc do. Ham `_clear` cua
man hinh Tra cuu goi setParent(None) cho tung widget cu truoc khi ve lai, nen moi
lan bam sang mot tu moi la co mot cua so chop len roi tat khi Python thu hoi doi
tuong.

CACH SUA. hide() roi deleteLater() cho cung ket qua ma khong bao gio tao cua so.

Chay tu goc kho:

    python tools/va_loi_chop_cua_so.py           # xem truoc, khong ghi gi
    python tools/va_loi_chop_cua_so.py --ghi     # ghi that, co sao luu

Kich ban chi dong toi dung mot mau lenh, khong dinh gi khac trong tep.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC = GOC / "hanzi_app"

# Bat dung dang `<ten>.setParent(None)` dung mot minh tren mot dong.
MAU = re.compile(r"^(?P<thut>[ \t]*)(?P<ten>[A-Za-z_][A-Za-z0-9_]*)\.setParent\(None\)[ \t]*$")


def va_mot_tep(duong_dan: Path, ghi: bool) -> list[tuple[int, str, str]]:
    """Tra ve danh sach (so_dong, dong_cu, dong_moi). Khong ghi neu ghi=False."""
    goc = duong_dan.read_text(encoding="utf-8")
    dong = goc.split("\n")
    doi: list[tuple[int, str, str]] = []

    ket_qua: list[str] = []
    for so, d in enumerate(dong, 1):
        m = MAU.match(d)
        if m is None:
            ket_qua.append(d)
            continue
        thut, ten = m.group("thut"), m.group("ten")
        moi = f"{thut}{ten}.hide()\n{thut}{ten}.deleteLater()"
        doi.append((so, d.strip(), f"{ten}.hide()  +  {ten}.deleteLater()"))
        ket_qua.append(moi)

    if doi and ghi:
        shutil.copy2(duong_dan, duong_dan.with_suffix(duong_dan.suffix + ".truoc-khi-va"))
        duong_dan.write_text("\n".join(ket_qua), encoding="utf-8")

    return doi


def them_chu_thich(duong_dan: Path, ghi: bool) -> bool:
    """Them mot dong chu thich vao docstring cua ham _clear, neu tim thay."""
    s = duong_dan.read_text(encoding="utf-8")
    neo = '"""Xoá sạch nội dung một layout, kể cả layout con.'
    if neo not in s or "KHÔNG dùng setParent(None)" in s:
        return False
    moi = neo + """

    KHÔNG dùng setParent(None): trên Windows, cắt cha biến widget thành cửa sổ
    cấp cao nhất và Qt cấp cho nó một HWND thật, gây ra một cửa sổ chớp lên rồi
    tắt ngay trước khi đối tượng bị thu hồi."""
    if ghi:
        duong_dan.write_text(s.replace(neo, moi, 1), encoding="utf-8")
    return True


def main() -> int:
    bo = argparse.ArgumentParser(description="Va loi chop cua so khi doi man hinh")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh chi xem truoc")
    tham_so = bo.parse_args()

    if not THU_MUC.is_dir():
        print(f"LOI: khong thay {THU_MUC}. Chay kich ban tu goc kho.")
        return 1

    print(f"Quet: {THU_MUC}")
    print("Che do: GHI THAT, co sao luu .truoc-khi-va\n" if tham_so.ghi
          else "Che do: XEM TRUOC, khong ghi gi ca\n")

    tong = 0
    for tep in sorted(THU_MUC.rglob("*.py")):
        if "__pycache__" in tep.parts:
            continue
        doi = va_mot_tep(tep, tham_so.ghi)
        if not doi:
            continue
        tuong_doi = tep.relative_to(GOC)
        print(f"  {tuong_doi}")
        for so, cu, moi in doi:
            print(f"      dong {so}:  {cu}")
            print(f"               -> {moi}")
        if them_chu_thich(tep, tham_so.ghi):
            print("      (them chu thich vao docstring cua _clear)")
        tong += len(doi)

    print()
    if tong == 0:
        print("Khong tim thay cho nao mac loi. Co the phien 07 da sua roi,")
        print("hoac nguyen nhan nam cho khac. Bao lai de xem tiep.")
        return 0

    print(f"Tong: {tong} cho.")
    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
    else:
        print("Da ghi. Ban goc luu cung thu muc voi duoi .truoc-khi-va")
        print("Chay lai app roi bam qua lai vai tu de kiem tra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
