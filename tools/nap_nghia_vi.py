"""Nap nghia tieng Viet va am Han-Viet tu data/vi/*.csv vao dict.sqlite.

Chay lai nhieu lan duoc, khong nhan doi du lieu: moi dong la mot UPDATE theo khoa.

    python tools/nap_nghia_vi.py                 # nap vao dict.sqlite o goc kho
    python tools/nap_nghia_vi.py --db duong/dan.sqlite
    python tools/nap_nghia_vi.py --kiem          # chi bao cao, khong ghi

Vi sao khong ghi thang vao build_dict.py: build_dict.py dung lai dict.sqlite tu
dau, moi lan chay la xoa sach hai cot nay. Nguon that nam o data/vi/*.csv, con
dict.sqlite chi la ban dung ra. Sau khi chay lai build_dict.py thi chay lai
kich ban nay.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC_VI = GOC / "data" / "vi"


def doc_csv(duong_dan: Path, so_cot: int | tuple[int, ...]) -> list[list[str]]:
    """Doc tep phan cach bang dau |, bo qua dong trong va dong chu thich.

    so_cot co the la mot so, hoac mot bo cac so cot hop le.
    """
    hop_le = (so_cot,) if isinstance(so_cot, int) else so_cot
    if not duong_dan.exists():
        print(f"  bo qua, khong co tep: {duong_dan.name}")
        return []
    dong_loi: list[tuple[int, str]] = []
    ket_qua: list[list[str]] = []
    with duong_dan.open(encoding="utf-8") as f:
        for so_dong, dong in enumerate(f, 1):
            dong = dong.rstrip("\n")
            if not dong.strip() or dong.lstrip().startswith("#"):
                continue
            phan = dong.split("|")
            if len(phan) not in hop_le:
                dong_loi.append((so_dong, dong))
                continue
            ket_qua.append([p.strip() for p in phan])
    if dong_loi:
        print(f"  CANH BAO {duong_dan.name}: {len(dong_loi)} dong sai dinh dang, da bo qua")
        for so_dong, dong in dong_loi[:5]:
            print(f"    dong {so_dong}: {dong[:60]}")
    return ket_qua


def nap_tu(db: sqlite3.Connection, hang: list[list[str]], kiem: bool) -> tuple[int, list[str]]:
    """Cap nhat word.meaning_vi. Tra ve so dong doi va danh sach tu khong tim thay.

    Sau tu trong dict xuat hien o HAI cap HSK voi nghia khac nhau: 喂, 得, 等, 过,
    还, 长. Vi du 喂 la "a lo" o HSK 1 nhung la "cho an" o HSK 6. Voi nhung tu do,
    them cot thu ba la cap HSK de chi dich danh mot ban ghi:

        喂|a lô (khi nghe điện thoại)|1
        喂|cho ăn; này, ê|6

    Dong hai cot van chay binh thuong cho moi tu khac.
    """
    khop = 0
    khong_thay = []
    for dong in hang:
        if len(dong) == 3:
            tu, nghia, cap = dong
            dieu_kien = "word_simp = ? AND hsk_level = ?"
            khoa: tuple = (tu, int(cap))
            ten = f"{tu} (HSK {cap})"
        else:
            tu, nghia = dong
            dieu_kien = "word_simp = ?"
            khoa = (tu,)
            ten = tu
        co = db.execute(f"SELECT COUNT(*) FROM word WHERE {dieu_kien}", khoa).fetchone()[0]
        if co == 0:
            khong_thay.append(ten)
            continue
        if co > 1:
            print(f"  CANH BAO: '{tu}' khop {co} ban ghi, nghia se de len tat ca. "
                  f"Them cot cap HSK de tach.")
        if not kiem:
            db.execute(f"UPDATE word SET meaning_vi = ? WHERE {dieu_kien}", (nghia, *khoa))
        khop += co
    return khop, khong_thay


def nap_chu(db: sqlite3.Connection, hang: list[list[str]], kiem: bool) -> tuple[int, list[str]]:
    """Cap nhat char.hanviet va char.meaning_vi."""
    khop = 0
    khong_thay = []
    for chu, hanviet, nghia in hang:
        co = db.execute("SELECT COUNT(*) FROM char WHERE char = ?", (chu,)).fetchone()[0]
        if co == 0:
            khong_thay.append(chu)
            continue
        if not kiem:
            db.execute(
                "UPDATE char SET hanviet = ?, meaning_vi = ? WHERE char = ?",
                (hanviet, nghia, chu),
            )
        khop += co
    return khop, khong_thay


def nap_tu_bo_thu(db: sqlite3.Connection, kiem: bool) -> int:
    """Dien hanviet va meaning_vi cho nhung chu BAN THAN la mot bo thu.

    Bang `radical` da co du name_hv va meaning_vi cho ca 214 bo, ke ca dang gian
    luoc trong glyph_alt. Voi chu nhu 口, 木, 讠 thi khong can go tay: lay thang
    tu bang do. Chi dien vao o dang rong, khong de len du lieu go tay trong CSV.
    """
    doi = 0
    for glyph, glyph_alt, name_hv, meaning_vi in db.execute(
        "SELECT glyph, glyph_alt, name_hv, meaning_vi FROM radical"
    ).fetchall():
        for ky_tu in (glyph, glyph_alt):
            if not ky_tu:
                continue
            co = db.execute(
                "SELECT COUNT(*) FROM char WHERE char = ? "
                "AND (hanviet IS NULL OR hanviet = '')",
                (ky_tu,),
            ).fetchone()[0]
            if co == 0:
                continue
            if not kiem:
                db.execute(
                    "UPDATE char SET hanviet = ?, meaning_vi = COALESCE(NULLIF(meaning_vi,''), ?) "
                    "WHERE char = ? AND (hanviet IS NULL OR hanviet = '')",
                    (name_hv, meaning_vi, ky_tu),
                )
            doi += co
    return doi


def main() -> int:
    bo_phan_tich = argparse.ArgumentParser(description="Nap nghia tieng Viet vao dict.sqlite")
    bo_phan_tich.add_argument("--db", default=str(GOC / "dict.sqlite"))
    bo_phan_tich.add_argument("--kiem", action="store_true", help="chi bao cao, khong ghi")
    tham_so = bo_phan_tich.parse_args()

    duong_db = Path(tham_so.db)
    if not duong_db.exists():
        print(f"LOI: khong tim thay {duong_db}")
        return 1

    print(f"Co so du lieu: {duong_db}")
    print(f"Nguon nghia:   {THU_MUC_VI}")
    if tham_so.kiem:
        print("Che do KIEM, khong ghi gi ca.\n")
    else:
        print()

    hang_tu = doc_csv(THU_MUC_VI / "nghia_tu.csv", (2, 3))
    hang_chu = doc_csv(THU_MUC_VI / "nghia_chu.csv", 3)

    db = sqlite3.connect(duong_db)
    try:
        khop_tu, thieu_tu = nap_tu(db, hang_tu, tham_so.kiem)
        khop_chu, thieu_chu = nap_chu(db, hang_chu, tham_so.kiem)
        tu_rad = nap_tu_bo_thu(db, tham_so.kiem)

        if not tham_so.kiem:
            # word_fts la bang FTS5 noi dung ngoai (content='word'), nen phai dung
            # lai chi muc sau khi doi meaning_vi. Thieu buoc nay thi FR-04 tim theo
            # nghia tieng Viet van tra ve rong du du lieu da co trong bang word.
            db.execute("INSERT INTO word_fts(word_fts) VALUES('rebuild')")
            db.commit()

        print(f"\nTu:  {len(hang_tu):5d} dong trong CSV -> {khop_tu} dong trong bang word")
        print(f"Chu: {len(hang_chu):5d} dong trong CSV -> {khop_chu} dong trong bang char")
        print(f"Bo thu: {tu_rad} chu dien tu dong tu bang radical")
        if thieu_tu:
            print(f"  {len(thieu_tu)} tu khong co trong dict: {', '.join(thieu_tu[:10])}")
        if thieu_chu:
            print(f"  {len(thieu_chu)} chu khong co trong dict: {', '.join(thieu_chu[:10])}")

        tong_tu = db.execute("SELECT COUNT(*) FROM word").fetchone()[0]
        co_tu = db.execute(
            "SELECT COUNT(*) FROM word WHERE meaning_vi IS NOT NULL AND meaning_vi <> ''"
        ).fetchone()[0]
        tong_chu = db.execute("SELECT COUNT(*) FROM char").fetchone()[0]
        co_chu = db.execute(
            "SELECT COUNT(*) FROM char WHERE hanviet IS NOT NULL AND hanviet <> ''"
        ).fetchone()[0]
        print(f"\nDo phu sau khi nap:")
        print(f"  word.meaning_vi : {co_tu}/{tong_tu} ({co_tu * 100 / tong_tu:.1f}%)")
        print(f"  char.hanviet    : {co_chu}/{tong_chu} ({co_chu * 100 / tong_chu:.1f}%)")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
