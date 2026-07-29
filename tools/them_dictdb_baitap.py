"""Chen candidate_meanings va candidate_hanviet vao hanzi_app/data/dictdb.py.

Day la phan tang du lieu cua bai tap trac nghiem o man hinh On tap. Goc goi la
phien 08a; kich ban nay lam thay de khoi phai chay them mot phien agent.

Ca hai tra ve mot RO ung vien theo thu tu XAC DINH. Viec boc ngau nhien 3 dap
an nhieu tu ro do la cua tang ui. Neu boc ngau nhien ngay o day thi khong phien
nao sau nay kiem thu duoc.

Chay tu goc kho:

    python tools/them_dictdb_baitap.py           # xem truoc, khong ghi gi
    python tools/them_dictdb_baitap.py --ghi     # ghi that, co sao luu
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
TEP = GOC / "hanzi_app" / "data" / "dictdb.py"

PHUONG_THUC = '''
    def candidate_meanings(
        self, exclude_word: str, hsk_level: int | None, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài tập chọn nghĩa.

        Trả về ``[(word_simp, meaning_vi), ...]``. Chỉ lấy dòng có meaning_vi
        khác rỗng, và bỏ chính ``exclude_word``.

        ``hsk_level`` khác None thì lọc đúng cấp đó. Đáp án nhiễu cùng cấp mới
        thành bài tập thật: bốc ngẫu nhiên toàn bộ 5001 từ thì người học loại
        trừ được ngay bằng cảm giác độ khó chứ không cần biết nghĩa. Truyền
        None khi không đủ ứng viên trong cấp.

        Thứ tự trả về là XÁC ĐỊNH, sắp theo freq_rank rồi id. Việc bốc ngẫu
        nhiên 3 đáp án từ rổ này là của tầng ui; giữ tầng data không ngẫu nhiên
        thì mới kiểm thử được.
        """
        if hsk_level is None:
            sql = (
                "SELECT word_simp, meaning_vi FROM word "
                "WHERE word_simp <> ? AND meaning_vi IS NOT NULL AND meaning_vi <> '' "
                "ORDER BY freq_rank IS NULL, freq_rank, id LIMIT ?"
            )
            tham_so: tuple = (exclude_word, limit)
        else:
            sql = (
                "SELECT word_simp, meaning_vi FROM word "
                "WHERE word_simp <> ? AND hsk_level = ? "
                "  AND meaning_vi IS NOT NULL AND meaning_vi <> '' "
                "ORDER BY freq_rank IS NULL, freq_rank, id LIMIT ?"
            )
            tham_so = (exclude_word, hsk_level, limit)
        return [(r["word_simp"], r["meaning_vi"]) for r in self._conn.execute(sql, tham_so)]

    def candidate_hanviet(
        self, exclude_char: str, limit: int = 30
    ) -> list[tuple[str, str]]:
        """Rổ ứng viên làm đáp án nhiễu cho bài tập chọn âm Hán-Việt.

        Trả về ``[(char, hanviet), ...]``. Chỉ lấy dòng có hanviet khác rỗng,
        bỏ chính ``exclude_char``. Cột hanviet hiện phủ 958 chữ chứ không phải
        toàn bộ 9534, nên bên gọi phải kiểm còn đủ ứng viên hay không.

        Thứ tự XÁC ĐỊNH, sắp theo freq_rank rồi codepoint. Lý do như
        candidate_meanings.
        """
        return [
            (r["char"], r["hanviet"])
            for r in self._conn.execute(
                "SELECT char, hanviet FROM char "
                "WHERE char <> ? AND hanviet IS NOT NULL AND hanviet <> '' "
                "ORDER BY freq_rank IS NULL, freq_rank, codepoint LIMIT ?",
                (exclude_char, limit),
            )
        ]
'''

MOC = (
    "    def find_words_by_hanzi(self",
    "    def get_chars(self",
    "    def close(self",
)


def main() -> int:
    bo = argparse.ArgumentParser(description="Chen hai phuong thuc ro dap an nhieu")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh xem truoc")
    tham_so = bo.parse_args()

    if not TEP.is_file():
        print(f"LOI: khong thay {TEP}. Chay kich ban tu goc kho.")
        return 1

    goc = TEP.read_text(encoding="utf-8")

    if "def candidate_meanings" in goc:
        print("DictDb da co candidate_meanings roi, khong lam gi ca.")
        return 0

    vi_tri, moc_dung = -1, ""
    for m in MOC:
        vi_tri = goc.find(m)
        if vi_tri != -1:
            moc_dung = m
            break

    if vi_tri == -1:
        print("LOI: khong tim thay cho chen trong dictdb.py.")
        return 1

    moi = goc[:vi_tri] + PHUONG_THUC.lstrip("\n") + "\n" + goc[vi_tri:]

    print(f"Tep : {TEP.relative_to(GOC)}")
    print(f"Chen: candidate_meanings + candidate_hanviet, truoc {moc_dung.strip()}")
    try:
        ast.parse(moi)
    except SyntaxError as loi:
        print(f"\nLOI CU PHAP sau khi chen: dong {loi.lineno}: {loi.msg}")
        return 1
    print("      cu phap sau khi chen: OK")
    print()

    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
        return 0

    shutil.copy2(TEP, TEP.with_suffix(".py.truoc-baitap"))
    TEP.write_text(moi, encoding="utf-8")
    print("Da ghi. Ban goc luu o dictdb.py.truoc-baitap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
