"""Chiết tự chữ Hán, FR-10 tới FR-15. Đặc tả ở mục 13.7, bảng đáp án ở mục 14.3.

Không tự mở cơ sở dữ liệu: nhận DictDb qua tham số khởi tạo.
"""

from hanzi_app.data.dictdb import DictDb
from hanzi_app.data.models import DecompNode, Radical

# Mười hai toán tử mô tả cấu trúc chữ. Hai toán tử nhận ba toán hạng, mười toán
# tử còn lại nhận hai.
IDC_THREE = "⿲⿳"
IDC_TWO = "⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻"


def _arity(c: str) -> int:
    """Số toán hạng của một toán tử IDS, 0 nếu ký tự đó không phải toán tử."""
    if c in IDC_THREE:
        return 3
    if c in IDC_TWO:
        return 2
    return 0


def _span(ids: str, i: int) -> int:
    """Độ dài đoạn con mô tả đúng một toán hạng bắt đầu tại vị trí i."""
    if i >= len(ids):
        return 0
    length = 1
    for _ in range(_arity(ids[i])):
        phan = _span(ids, i + length)
        if phan == 0:      # chuỗi thiếu toán hạng, lấy phần đọc được
            break
        length += phan
    return length


def _operands(ids: str) -> list[str]:
    """Các toán hạng ở tầng ngoài cùng của một chuỗi IDS.

    '⿱木⿰木木' cho ['木', '⿰木木'] chứ không phải ['木', '木', '木'].
    """
    arity = _arity(ids[0]) if ids else 0
    if arity == 0:
        return []

    ket_qua, i = [], 1
    for _ in range(arity):
        phan = _span(ids, i)
        if phan == 0:
            break
        ket_qua.append(ids[i:i + phan])
        i += phan
    return ket_qua


class Decomposer:
    MAX_DEPTH = 6

    def __init__(self, dict_db: DictDb) -> None:
        self._db = dict_db
        # Tập 214 bộ Khang Hy, tra theo hình chữ. Dùng cho quy tắc dừng số 2.
        self._radicals_by_glyph: dict[str, Radical] = {}
        for radical in dict_db.all_radicals():
            if radical.glyph:
                self._radicals_by_glyph[radical.glyph] = radical
            if radical.glyph_alt:
                self._radicals_by_glyph[radical.glyph_alt] = radical

    # ------------------------------------------------------------------ FR-11
    def tree(self, ch: str) -> DecompNode:
        """Cây chiết tự của một chữ, theo ba quy tắc dừng ở mục 13.7."""
        return self._char_node(ch, depth=0, path=frozenset(), is_root=True)

    def _char_node(
        self, ch: str, depth: int, path: frozenset[str], is_root: bool
    ) -> DecompNode:
        info = self._db.get_char(ch)
        ids = info.ids if info else None
        meaning_vi = info.meaning_vi if info else None
        radical = self._radical_of_idx(info.radical_idx) if info else None

        # Quy tắc 2. Bộ Khang Hy là nút lá, kể cả khi dữ liệu có chuỗi IDS cho
        # nó. Chỉ áp cho thành phần; người dùng tra thẳng một bộ thì vẫn xem
        # được cấu tạo của nó.
        if not is_root and ch in self._radicals_by_glyph:
            return DecompNode(ch, ids, meaning_vi, radical, (), False)

        # Quy tắc 3. Gặp lại một chữ đã có trên đường đi thì dừng nhánh.
        if ch in path:
            return DecompNode(ch, ids, meaning_vi, radical, (), True)

        # Chữ không phân tách được: nút lá thật, không phải nút bị cắt.
        if not self._decomposable(ch, ids):
            return DecompNode(ch, ids, meaning_vi, radical, (), False)

        if depth >= self.MAX_DEPTH:
            return DecompNode(ch, ids, meaning_vi, radical, (), True)

        children = self._children(ids, depth, path | {ch})
        return DecompNode(ch, ids, meaning_vi, radical, children, False)

    def _group_node(
        self, ids: str, depth: int, path: frozenset[str]
    ) -> DecompNode:
        """Nút cho một nhóm lồng bên trong chuỗi IDS, ví dụ ⿰木木 trong ⿱木⿰木木.
        Nhóm không phải một chữ nên không có nghĩa và không có bộ; trường char
        giữ nguyên đoạn IDS, kèm cờ is_group để giao diện biết không được vẽ nó
        vào ô 田字格 mà chỉ gom các con của nó lại."""
        if depth >= self.MAX_DEPTH:
            return DecompNode(ids, ids, None, None, (), True, is_group=True)
        return DecompNode(
            ids, ids, None, None, self._children(ids, depth, path), False, is_group=True
        )

    def _children(
        self, ids: str, depth: int, path: frozenset[str]
    ) -> tuple[DecompNode, ...]:
        """Dựng các nút con từ những toán hạng ở tầng ngoài cùng của chuỗi IDS.
        Quy tắc 1: toán hạng dài hơn một ký tự là một nhóm lồng, giữ nguyên tầng
        của nó chứ không trải phẳng."""
        nodes = []
        for operand in _operands(ids):
            if len(operand) == 1:
                nodes.append(
                    self._char_node(operand, depth + 1, path, is_root=False)
                )
            else:
                nodes.append(self._group_node(operand, depth + 1, path))
        return tuple(nodes)

    @staticmethod
    def _decomposable(ch: str, ids: str | None) -> bool:
        """Chuỗi IDS rỗng, hoặc chỉ gồm chính chữ đó, nghĩa là nguồn không phân
        tách chữ này."""
        return bool(ids) and len(ids) > 1 and ids != ch

    # ------------------------------------------------------------------ FR-10
    def radical_of(self, ch: str) -> Radical | None:
        info = self._db.get_char(ch)
        if info is None:
            return None
        return self._radical_of_idx(info.radical_idx)

    def _radical_of_idx(self, idx: int | None) -> Radical | None:
        return None if idx is None else self._db.get_radical(idx)

    # ------------------------------------------------------------------ FR-15
    def same_radical_learned(self, ch: str, limit: int = 12) -> list[str]:
        """Các chữ cùng bộ với chữ đang xem.

        Điều kiện "đã học" nằm ở bảng progress trong user.sqlite; tầng userdb
        chưa tồn tại và Decomposer chỉ nhận DictDb, nên hiện lọc theo bộ trên
        toàn từ điển và xếp chữ phổ biến lên trước.
        """
        info = self._db.get_char(ch)
        if info is None or info.radical_idx is None:
            return []

        # Lấy dư một chữ để còn chỗ bỏ chính chữ đang xem.
        cung_bo = self._db.chars_with_radical(info.radical_idx, limit + 1)
        return [c for c in cung_bo if c != ch][:limit]

    # ------------------------------------------------------------------ FR-34
    def radical_map(self) -> list[tuple[Radical, int]]:
        """214 bộ kèm số chữ khác nhau thuộc bộ đó.

        FR-34 muốn đếm số lần người dùng gặp bộ; số đó nằm ở user.sqlite nên ở
        đây đếm trên từ điển, cùng lý do như same_radical_learned.
        """
        counts = self._db.radical_char_counts()
        return [(radical, counts.get(radical.idx, 0)) for radical in self._db.all_radicals()]
