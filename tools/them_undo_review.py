"""Chen phuong thuc UserDb.undo_review vao hanzi_app/data/userdb.py.

Day la phan tang du lieu cua nut Hoan tac o man hinh On tap. Goc goi la phien
08a; kich ban nay lam thay de khoi phai chay them mot phien agent.

Ba viec, trong MOT giao dich:
  - khoi phuc dong progress ve dung trang thai `before`
  - xoa dong review_log MOI NHAT cua tu do, dung mot dong
  - giam review_count di 1, khong bao gio xuong duoi 0

Chay tu goc kho:

    python tools/them_undo_review.py           # xem truoc, khong ghi gi
    python tools/them_undo_review.py --ghi     # ghi that, co sao luu
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
TEP = GOC / "hanzi_app" / "data" / "userdb.py"

PHUONG_THUC = '''
    def undo_review(self, word: str, before) -> None:
        """Hoàn tác lần tự đánh giá gần nhất của một từ.

        Ba việc, trong MỘT giao dịch:
          - khôi phục dòng progress về đúng trạng thái ``before``
          - xoá dòng review_log MỚI NHẤT của từ đó, đúng một dòng
          - giảm review_count đi 1, chặn dưới ở 0

        Xoá đúng một dòng chứ không xoá theo ``word`` không thôi, làm vậy là
        xoá sạch lịch sử ôn của từ. SQLite bản mặc định không cho LIMIT trong
        DELETE nên phải đi qua một truy vấn con. Sắp theo ``reviewed_at`` rồi
        ``id``, vì hai lần ôn trong cùng một giây có cùng dấu thời gian và khi
        đó chỉ ``id`` mới phân biệt được.

        ``before`` là một ReviewOutcome, không chứa review_count, nên
        upsert_progress lo sáu trường kia còn review_count phải sửa riêng.

        Từ chưa từng ôn mà gọi undo thì vẫn khôi phục progress, không ném lỗi,
        và review_count không xuống dưới 0.

        transaction() cài bằng SAVEPOINT nên gọi upsert_progress lồng bên trong
        là an toàn.
        """
        with self.transaction() as conn:
            self.upsert_progress(word, before, None)
            conn.execute(
                "DELETE FROM review_log WHERE id = ("
                "    SELECT id FROM review_log WHERE word = ?"
                "    ORDER BY reviewed_at DESC, id DESC LIMIT 1)",
                (word,),
            )
            conn.execute(
                "UPDATE progress SET review_count = MAX(review_count - 1, 0) "
                "WHERE word = ?",
                (word,),
            )
'''

# Chen ngay truoc mot trong nhung moc nay, thu lan luot.
MOC = (
    "    # -------------------------------------------------- bộ nhớ đệm giải thích",
    "    def cache_get(self",
    "    def learned_chars(self",
)


def main() -> int:
    bo = argparse.ArgumentParser(description="Chen undo_review vao UserDb")
    bo.add_argument("--ghi", action="store_true", help="ghi that; mac dinh xem truoc")
    tham_so = bo.parse_args()

    if not TEP.is_file():
        print(f"LOI: khong thay {TEP}. Chay kich ban tu goc kho.")
        return 1

    goc = TEP.read_text(encoding="utf-8")

    if "def undo_review" in goc:
        print("UserDb da co undo_review roi, khong lam gi ca.")
        return 0

    if "def upsert_progress" not in goc:
        print("LOI: khong thay upsert_progress trong userdb.py.")
        print("Tep co ve khac han ban mong doi, dung tu sua. Bao lai de xem.")
        return 1

    vi_tri = -1
    moc_dung = ""
    for m in MOC:
        vi_tri = goc.find(m)
        if vi_tri != -1:
            moc_dung = m
            break

    if vi_tri == -1:
        print("LOI: khong tim thay cho chen. Cac moc da thu:")
        for m in MOC:
            print(f"    {m.strip()}")
        return 1

    moi = goc[:vi_tri] + PHUONG_THUC.lstrip("\n") + "\n" + goc[vi_tri:]

    print(f"Tep : {TEP.relative_to(GOC)}")
    print(f"Chen: undo_review, ngay truoc  {moc_dung.strip()}")
    print(f"      {len(PHUONG_THUC.splitlines())} dong")

    # Kiem cu phap truoc khi ghi de khong bao gio de lai mot tep hong.
    import ast
    try:
        ast.parse(moi)
    except SyntaxError as loi:
        print(f"\nLOI CU PHAP sau khi chen: dong {loi.lineno}: {loi.msg}")
        print("Khong ghi gi ca.")
        return 1
    print("      cu phap sau khi chen: OK")

    print()
    if not tham_so.ghi:
        print("Chay lai voi --ghi de ghi that.")
        return 0

    shutil.copy2(TEP, TEP.with_suffix(".py.truoc-undo"))
    TEP.write_text(moi, encoding="utf-8")
    print("Da ghi. Ban goc luu o userdb.py.truoc-undo")
    print("Chay `pytest tests/unit -q` de chac khong pha gi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
