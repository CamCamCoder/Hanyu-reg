"""Cửa sổ chính: thanh điều hướng trái cố định 212 px, khung nội dung bên phải.

Mục 7.1: cửa sổ tối thiểu 1100 x 700. Thanh điều hướng có đủ bốn mục của mục 7.
Sau phiên 07 có hai màn hình thật là Tra cứu và Ôn tập; Sách và Bộ thủ vẫn mở ra
một chỗ trống có chữ "Chưa làm ở phiên này".
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.ui.screen_books import ScreenBooks
from hanzi_app.ui.screen_lookup import ScreenLookup
from hanzi_app.ui.screen_radicals import ScreenRadicals
from hanzi_app.ui.screen_review import ScreenReview
from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font

NAV_WIDTH = 212
MIN_SIZE = (1100, 700)

# Bốn mục của mục 7. Chỉ mục đầu có màn hình thật ở phiên này.
NAV_ITEMS = (
    ("查", "Tra cứu"),
    ("书", "Sách"),
    ("复", "Ôn tập"),
    ("部", "Bộ thủ"),
)


def _placeholder(ten: str) -> QWidget:
    """Chỗ trống cho ba màn hình chưa dựng."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(8)

    tieu_de = QLabel(ten)
    tieu_de.setFont(ui_font(20, bold=True))
    tieu_de.setStyleSheet(f"color: {PALETTE['ink']};")
    tieu_de.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(tieu_de)

    ghi_chu = QLabel("Chưa làm ở phiên này")
    ghi_chu.setFont(ui_font(14))
    ghi_chu.setStyleSheet(f"color: {PALETTE['muted']};")
    ghi_chu.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(ghi_chu)
    return page


class MainWindow(QMainWindow):
    """Nhận LookupService, Decomposer, UserDb và scheduler đã dựng sẵn từ main.py.

    Hai tham số sau thêm ở phiên 07 và đứng cuối, để thứ tự cũ không đổi.
    scheduler là một MODULE hàm chứ không phải lớp, cửa sổ chỉ chuyển tiếp nó
    xuống hai màn hình cần tính lịch.
    """

    def __init__(self, lookup, decomposer, user_db, scheduler, dict_db=None, parent=None) -> None:
        super().__init__(parent)
        self._user = user_db
        self.setWindowTitle("Học từ qua bộ thủ")
        self.setMinimumSize(*MIN_SIZE)
        self.resize(*MIN_SIZE)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        # Thứ tự các trang phải khớp thứ tự NAV_ITEMS: nút thứ i mở trang thứ i.
        self.stack = QStackedWidget()
        self.screen_lookup = ScreenLookup(lookup, decomposer, user_db, scheduler)
        self.screen_books = ScreenBooks(user_db, dict_db)
        self.screen_review = ScreenReview(lookup, user_db, scheduler, decomposer, dict_db)
        self.screen_radicals = ScreenRadicals(dict_db) if dict_db else _placeholder(NAV_ITEMS[3][1])

        self.stack.addWidget(self.screen_lookup)              # 0 Tra cứu
        self.stack.addWidget(self.screen_books)               # 1 Sách
        self.stack.addWidget(self.screen_review)              # 2 Ôn tập
        self.stack.addWidget(self.screen_radicals)            # 3 Bộ thủ

        layout.addWidget(self._build_nav())
        layout.addWidget(self.stack, 1)

        # Các màn hình đều đụng bảng progress, làm mới 2 con số ở chân nav.
        self.screen_lookup.progress_changed.connect(self._refresh_counts)
        self.screen_books.progress_changed.connect(self._refresh_counts)
        self.screen_review.progress_changed.connect(self._refresh_counts)
        self._refresh_counts()

        self.stack.setCurrentIndex(0)
        self.screen_lookup.input.setFocus()

    # -------------------------------------------------------- thanh điều hướng
    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("Nav")
        nav.setFixedWidth(NAV_WIDTH)

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, (glyph, ten) in enumerate(NAV_ITEMS):
            nut = QPushButton(f"{glyph}   {ten}")
            nut.setObjectName("NavBtn")
            nut.setFont(ui_font(14))
            nut.setCheckable(True)
            nut.setChecked(i == 0)
            nut.setMinimumHeight(40)
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(nut, i)
            layout.addWidget(nut)

        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        layout.addStretch(1)
        layout.addWidget(self._build_footer())
        return nav

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(2)

        glyph = QLabel("部")
        glyph.setFont(han_font(40))
        glyph.setStyleSheet(f"color: {PALETTE['accent']};")
        layout.addWidget(glyph)

        ten = QLabel("Học từ qua bộ thủ")
        ten.setFont(ui_font(14, bold=True))
        ten.setStyleSheet(f"color: {PALETTE['ink']};")
        layout.addWidget(ten)

        phien_ban = QLabel("v0.2")
        phien_ban.setFont(mono_font(11))
        phien_ban.setStyleSheet(f"color: {PALETTE['muted']};")
        layout.addWidget(phien_ban)
        return header

    def _build_footer(self) -> QWidget:
        """Chân thanh điều hướng.

        QT-04 bước 6 buộc gọi hai con số bằng hai tên khác nhau ở mọi màn hình:
        "đang theo dõi" là số dòng progress, "đã thuộc" là số dòng có status
        'known'. Hai số này khác nhau và không được trộn thành một "số từ".

        Dòng bộ thủ thì vẫn để trạng thái rỗng: nó cần đối chiếu learned_chars()
        với dict.sqlite, tức bắc cầu hai cơ sở dữ liệu, không thuộc phiên này.
        """
        footer = QWidget()
        layout = QVBoxLayout(footer)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(3)

        self._dong_theo_doi = QLabel()
        self._dong_da_thuoc = QLabel()
        # Cập nhật dòng bộ thủ
        n_bo = len(self._user.learned_chars()) if hasattr(self._user, 'learned_chars') else 0
        for dong in (
            self._dong_theo_doi,
            self._dong_da_thuoc,
            QLabel(f"Bộ thủ: 214 bộ Khang Hy"),
            QLabel("Ngoại tuyến"),
        ):
            dong.setFont(mono_font(11))
            dong.setStyleSheet(f"color: {PALETTE['muted']};")
            layout.addWidget(dong)
        return footer

    def _refresh_counts(self) -> None:
        """Đọc lại hai con số của QT-04 bước 6 từ tầng data.

        Đếm ở một chỗ duy nhất là UserDb.progress_counts(); cửa sổ không tự mở
        cơ sở dữ liệu và không tự cộng trừ để đoán số mới sau mỗi lần bấm.
        """
        theo_doi, da_thuoc = self._user.progress_counts()
        self._dong_theo_doi.setText(f"Đang theo dõi: {theo_doi}")
        self._dong_da_thuoc.setText(f"Đã thuộc: {da_thuoc}")
