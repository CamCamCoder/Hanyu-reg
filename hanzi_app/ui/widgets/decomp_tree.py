"""Hàng chiết tự: chữ = thành phần + thành phần, theo mockup mục 7.2.

Widget này chỉ VẼ một DecompNode do service/decomposer dựng sẵn, không tự phân
tách gì thêm.

Ba trường hợp bắt buộc phải phân biệt:

- Nút thường: vẽ vào ô 田字格.
- Nút nhóm (is_group=True): char của nó là một đoạn IDS như '⿰木木', KHÔNG phải
  chữ Hán, nên tuyệt đối không vẽ vào ô 田字格. Nút nhóm chỉ vẽ một cặp ngoặc
  gom các con của nó lại.
- Nút vừa is_group vừa truncated và không có con: cây bị cắt trước khi kịp dựng
  các con, nên vẽ dấu ba chấm để báo là còn nữa, không vẽ cặp ngoặc rỗng, và
  vẫn không vẽ vào ô 田字格.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font
from hanzi_app.ui.widgets.tianzige import TianZiGe

# Ô của chữ đang xét to hơn ô của các tầng dưới, để mắt bám được thứ bậc.
ROOT_BOX = 58
SUB_BOX = 46

# Chú thích dưới ô được chốt cứng hai dòng. Nếu để layout tự tính, nhãn xuống
# dòng có chiều cao phụ thuộc bề rộng, Qt tính hụt chiều cao và chú thích đè lên
# ô 田字格.
CAPTION_LINES = 2

# Dấu ba chấm cho nhánh bị cắt vì chạm giới hạn độ sâu hoặc gặp chu trình.
MORE = "…"


def _text(content: str, font, color: str) -> QLabel:
    label = QLabel(content)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    return label


def _caption_of(node) -> str:
    """Dòng chú thích dưới ô: tên bộ nếu thành phần này chính là một bộ thủ.

    Tên và nghĩa bộ thủ lấy từ bảng radical nên là dữ liệu thật. Nghĩa tiếng
    Việt của chữ (meaning_vi) trong dict.sqlite còn rỗng, nên chỗ đó hiện đúng
    trạng thái rỗng có nhãn, không bịa.
    """
    radical = node.radical
    if radical is not None and node.char in (radical.glyph, radical.glyph_alt):
        return f"{radical.name_hv} · {radical.meaning_vi}"
    if node.meaning_vi:
        return node.meaning_vi
    return "chưa có nghĩa"


class DecompTree(QWidget):
    """Khối chiết tự của MỘT chữ.

    Hàng đầu là chữ đang xét bằng các thành phần tầng một. Mỗi thành phần còn
    tách được sinh thêm một hàng thụt vào bên dưới, nên chữ 识 ra cây hai tầng
    còn chữ 认 chỉ một tầng.
    """

    def __init__(self, node, parent=None) -> None:
        super().__init__(parent)
        # Khối này luôn nằm trong một thẻ, để nền trong suốt cho ăn theo nền thẻ.
        self.setStyleSheet("background: transparent;")
        self._rows = QVBoxLayout(self)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(12)

        if node.children:
            self._add_row(node, depth=0)
        else:
            # Chữ không phân tách được: vẫn cho xem ô 田字格 kèm lời giải thích,
            # để người dùng biết đây là dữ liệu thiếu chứ không phải lỗi.
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(self._char_cell(node, ROOT_BOX, "chữ đủ"))
            reason = (
                "nhánh bị cắt, xem thêm ở tầng dưới"
                if node.truncated
                else "từ điển không tách chữ này thành phần nhỏ hơn"
            )
            row.addWidget(_text(reason, ui_font(13), PALETTE["muted"]))
            row.addStretch(1)
            self._rows.addLayout(row)

    # ------------------------------------------------------------------ hàng
    def _add_row(self, node, depth: int) -> None:
        box = ROOT_BOX if depth == 0 else SUB_BOX
        row = QHBoxLayout()
        row.setSpacing(10)
        if depth:
            row.addSpacing(22 * depth)

        head_caption = "chữ đủ" if depth == 0 else _caption_of(node)
        row.addWidget(self._char_cell(node, box, head_caption), 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._sign("=", box), 0, Qt.AlignmentFlag.AlignTop)

        for i, child in enumerate(node.children):
            if i:
                row.addWidget(self._sign("+", box), 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(self._cell(child, box), 0, Qt.AlignmentFlag.AlignTop)

        row.addStretch(1)
        self._rows.addLayout(row)

        for child in node.children:
            self._descend(child, depth + 1)

    def _descend(self, node, depth: int) -> None:
        """Thành phần nào còn tách được thì sinh thêm một hàng ở tầng dưới.

        Nút nhóm không có hàng riêng vì nó không phải một chữ: đi thẳng vào các
        con của nó, giữ nguyên tầng.
        """
        if node.is_group:
            for child in node.children:
                self._descend(child, depth)
        elif node.children:
            self._add_row(node, depth)

    # -------------------------------------------------------------------- ô
    def _cell(self, node, box: int) -> QWidget:
        if node.is_group:
            return self._group_cell(node, box)
        return self._char_cell(node, box, _caption_of(node))

    def _char_cell(self, node, box: int, caption: str) -> QWidget:
        """Một ô 田字格 kèm chú thích. Chỉ dùng cho nút KHÔNG phải nút nhóm."""
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(TianZiGe(node.char, box), 0, Qt.AlignmentFlag.AlignHCenter)

        font = mono_font(11)
        text = caption + (f" {MORE}" if node.truncated else "")
        label = _text(text, font, PALETTE["muted"])
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        label.setWordWrap(True)
        width = max(box + 52, 116)
        cao_chu = QFontMetrics(font).height() * CAPTION_LINES
        label.setFixedSize(width, cao_chu)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)

        cell.setFixedSize(width, box + layout.spacing() + cao_chu)
        return cell

    def _group_cell(self, node, box: int) -> QWidget:
        """Nút nhóm lồng: không có ô 田字格, chỉ có cặp ngoặc gom các con.

        Nhóm bị cắt mà chưa có con thì chỉ vẽ dấu ba chấm, không vẽ ngoặc rỗng.
        """
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if not node.children:
            dau = _text(MORE, han_font(int(box * 0.5)), PALETTE["muted"])
            dau.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dau.setFixedSize(int(box * 0.7), box)
            layout.addWidget(dau, 0, Qt.AlignmentFlag.AlignTop)
            return cell

        layout.addWidget(self._bracket("(", box), 0, Qt.AlignmentFlag.AlignTop)
        for i, child in enumerate(node.children):
            if i:
                layout.addWidget(self._sign("+", box), 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self._cell(child, box), 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._bracket(")", box), 0, Qt.AlignmentFlag.AlignTop)
        return cell

    # ---------------------------------------------------------------- dấu nối
    def _sign(self, text: str, box: int) -> QLabel:
        """Dấu = và dấu +. Cao đúng bằng ô 田字格 để nằm ngang tâm ô."""
        label = _text(text, ui_font(16), PALETTE["ink2"])
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(20, box)
        return label

    def _bracket(self, text: str, box: int) -> QLabel:
        label = _text(text, ui_font(26), PALETTE["muted"])
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(14, box)
        return label
