"""Ô 田字格 vẽ đúng một chữ.

Bảng màu mục 6.1 và phông mục 6.2 từng nằm ở đây, nay chuyển sang
``hanzi_app/ui/theme.py``: từ phiên 07 có ba màn hình dùng chung chúng, mà bắt
một màn hình import màu từ một module widget là sai thứ bậc.

Ô 田字格 là yếu tố nhận diện của ứng dụng: viền màu nhấn chính, hai đường đứt
chia ô thành bốn phần. Widget này chỉ nhận MỘT chữ đơn; nút nhóm lồng của cây
chiết tự (DecompNode.is_group) không bao giờ được đưa vào đây, việc kiểm tra cờ
đó là của decomp_tree.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from hanzi_app.ui.theme import PALETTE, han_font


class TianZiGe(QWidget):
    """Ô 田字格: một chữ đơn, viền màu nhấn chính, hai đường đứt chia tư."""

    def __init__(self, char: str, box: int = 88, parent=None) -> None:
        super().__init__(parent)
        self._char = char
        self._box = box
        self.setFixedSize(box, box)

    def paintEvent(self, event) -> None:  # noqa: N802  (tên do Qt quy định)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, QColor(PALETTE["card"]))

        # Hai đường đứt chia tư. Cùng màu nhấn chính nhưng nhạt hơn viền, để
        # đường phụ không tranh chỗ với chữ.
        dash_color = QColor(PALETTE["accent"])
        dash_color.setAlpha(90)
        dash_pen = QPen(dash_color, 1, Qt.PenStyle.DashLine)
        dash_pen.setDashPattern([3, 3])
        painter.setPen(dash_pen)
        mid_x = rect.left() + rect.width() / 2
        mid_y = rect.top() + rect.height() / 2
        painter.drawLine(int(mid_x), rect.top(), int(mid_x), rect.bottom())
        painter.drawLine(rect.left(), int(mid_y), rect.right(), int(mid_y))

        # Viền ngoài, màu nhấn chính, vẽ sau để đè lên đầu hai đường đứt.
        painter.setPen(QPen(QColor(PALETTE["accent"]), 1.4))
        painter.drawRect(rect)

        painter.setFont(han_font(int(self._box * 0.66)))
        painter.setPen(QColor(PALETTE["ink"]))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._char)
        painter.end()
