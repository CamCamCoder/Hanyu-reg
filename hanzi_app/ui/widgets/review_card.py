"""Thẻ ôn tập: mặt trước chỉ có chữ, mặt sau có âm, nghĩa, chiết tự và ba nút.

QT-04 bước 3 tới 5. Widget này KHÔNG biết gì về SM-2 và không chạm cơ sở dữ
liệu: nó nhận sẵn một WordDetail cùng một Decomposer, vẽ ra, rồi phát tín hiệu
``graded`` kèm số grade của nút vừa bấm. Toàn bộ phần tính lịch là của
``service/scheduler.py``, đã xong từ phiên 02.

Mặt trước lật sang mặt sau bằng nút "Hiện đáp án"; ba nút đánh giá chỉ xuất hiện
sau khi lật, để người dùng không chấm điểm trước khi thật sự nhớ ra.

Mặt sau có thêm âm Hán-Việt và cây chiết tự. Đó là hai thứ phân biệt thẻ này với
một thẻ flashcard bất kỳ: 认识 không chỉ là "quen biết", mà là 认 gồm 讠 ngôn cộng
人 nhân. Thẻ vẫn không tự dựng Decomposer mà nhận qua tham số, đúng luật phụ
thuộc một chiều của mục 13.1.
"""

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font
from hanzi_app.ui.widgets.decomp_tree import DecompTree
from hanzi_app.ui.widgets.tianzige import TianZiGe

# Ba nút của QT-04 bước 5. Số đứng đầu là grade, tức là KHOÁ của
# scheduler.GRADE_TO_Q, không phải giá trị q. Thẻ chỉ phát grade ra ngoài; việc
# đổi grade sang q là của bên gọi, đúng một chỗ duy nhất.
NUT_DANH_GIA = (
    (0, "Quên", "accent", "card", "accent"),
    (1, "Khó", "warn_ink", "warn_bg", "warn"),
    (2, "Nhớ", "accent2", "accent2_bg", "accent2_line"),
)

# Cỡ chữ mặt trước. Từ một chữ vào ô 田字格; TianZiGe vẽ chữ ở 0,66 lần cạnh ô
# nên cạnh 132 cho ra nét chữ xấp xỉ 88 px, bằng cỡ chữ trơn của từ nhiều chữ.
FRONT_PX = 88
FRONT_BOX = 132

# Bề rộng tối đa của khối chữ ở mặt sau. Dài hơn thì mắt phải quét ngang quá xa.
RONG_CHU = 520

GOI_Y_PHIM = "Phím tắt: cách để lật · 1 quên · 2 khó · 3 nhớ"


class WrapLabel(QLabel):
    """QLabel xuống dòng mà layout tính ĐÚNG chiều cao.

    QLabel bật ``setWordWrap(True)`` trả về ``minimumSizeHint`` chỉ bằng MỘT
    dòng chữ. Đo thật trên PySide6 6.11.1 với một nghĩa dài ở bề rộng 520 px:
    cần 38 px nhưng ``minimumSizeHint`` báo 19 px. Khi layout bị ép, nó co nhãn
    xuống 19 px trong khi chữ vẫn vẽ đủ hai dòng, nên dòng thứ hai tràn ra đè
    lên widget bên dưới và phần cuối thẻ bị cắt.

    Lớp này cài ``heightForWidth`` thật, rồi cho cả ``sizeHint`` lẫn
    ``minimumSizeHint`` bám theo nó, nên layout không bao giờ co nhãn xuống
    dưới chiều cao thật sự cần.

    Đây là cùng một cái bẫy mà phiên 05 đã gặp ở ``decomp_tree.py`` và xử lý
    bằng cách chốt cứng chiều cao. Lần này xử lý ở đúng gốc.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding
        )

    def _rong_tham_chieu(self) -> int:
        rong = self.maximumWidth()
        if rong >= 16777215:          # QWIDGETSIZE_MAX, tức là chưa đặt trần
            rong = self.width() or RONG_CHU
        return max(rong, 1)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 (tên do Qt quy định)
        return True

    def heightForWidth(self, rong: int) -> int:  # noqa: N802
        co = self.fontMetrics().boundingRect(
            QRect(0, 0, max(rong, 1), 0),
            int(Qt.TextFlag.TextWordWrap) | int(self.alignment()),
            self.text(),
        )
        return co.height() + 2        # cộng 2 px đệm cho phần chân chữ

    def sizeHint(self) -> QSize:  # noqa: N802
        rong = self._rong_tham_chieu()
        return QSize(rong, self.heightForWidth(rong))

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()


def _label(text: str, font, color: str, wrap: bool = False) -> QLabel:
    label = WrapLabel(text) if wrap else QLabel(text)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def _section(text: str) -> QLabel:
    """Nhãn mục nhỏ: đơn cách, in hoa, giãn chữ, theo mục 6.2."""
    font = mono_font(11)
    font.setLetterSpacing(font.SpacingType.PercentageSpacing, 106)
    return _label(text.upper(), font, PALETTE["muted"])


def _duong_ke() -> QFrame:
    """Đường kẻ mảnh ngăn giữa hai cây chiết tự."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setMaximumWidth(RONG_CHU)
    line.setStyleSheet(f"background: {PALETTE['line']}; border: none;")
    return line


def pinyin_cua(detail) -> str:
    """Âm đọc cho mặt sau, ưu tiên âm in trong sách của người dùng.

    QT-04 bước 2 muốn mặt sau là thứ người dùng đã gặp trong sách. Chừng nào
    luồng nhập sách chưa làm thì detail.source luôn None và nhánh này rơi về âm
    của từ điển.
    """
    if detail.source is not None and detail.source.pinyin_src:
        return detail.source.pinyin_src
    if detail.word is not None:
        return detail.word.pinyin_tone
    if detail.chars:
        return detail.chars[0].pinyin
    return ""


def hanviet_cua(detail) -> str:
    """Âm Hán-Việt của cả từ, ghép từ âm của từng chữ, nối bằng dấu cách.

    Với người học người Việt đây là công cụ nhớ chữ mạnh nhất: biết 识 đọc là
    "thức" thì nhớ 认识 dễ hơn hẳn. Cột char.hanviet hiện phủ 958 chữ, không
    phải toàn bộ 9534, nên chữ nào thiếu thì bỏ qua chữ đó. Không chữ nào có
    thì trả chuỗi rỗng và bên gọi bỏ luôn cả dòng — thà không hiện còn hơn hiện
    một dòng trống hoặc một dòng "chưa có dữ liệu" vô nghĩa.

    Ưu tiên âm in trong sách nếu có, theo đúng tinh thần QT-04 bước 2.
    """
    if detail.source is not None and detail.source.hanviet_src:
        return detail.source.hanviet_src
    am = [c.hanviet for c in detail.chars if c.hanviet]
    return " ".join(am)


def nghia_cua(detail) -> tuple[str, str]:
    """(nghĩa, nhãn mục) cho mặt sau, theo thứ tự ưu tiên của QT-04 bước 2.

    Nghĩa của sách trước, rồi nghĩa tiếng Việt của từ điển, rồi tiếng Anh. Nhãn
    luôn nói rõ nghĩa đang lấy từ đâu: một mặt thẻ ghi tiếng Anh mà không nói là
    tiếng Anh thì người học tưởng từ điển đã có nghĩa tiếng Việt.
    """
    if detail.source is not None and detail.source.meaning_src:
        return detail.source.meaning_src, "Nghĩa theo sách"

    word = detail.word
    if word is not None and word.meaning_vi:
        return word.meaning_vi, "Nghĩa"
    if word is not None and word.meaning_en:
        return word.meaning_en, "Nghĩa · tiếng Anh"

    # Chuỗi chưa có mục từ trong từ điển: ghép nghĩa của từng chữ đơn.
    if detail.chars:
        vi = [c.meaning_vi for c in detail.chars if c.meaning_vi]
        if len(vi) == len(detail.chars):
            return " + ".join(vi), "Nghĩa · ghép từ từng chữ"
        en = [c.meaning_en for c in detail.chars if c.meaning_en]
        if len(en) == len(detail.chars):
            return " + ".join(en), "Nghĩa · từng chữ, tiếng Anh"

    return "chưa có dữ liệu", "Nghĩa"


class ReviewCard(QFrame):
    """Một thẻ ôn tập của đúng một từ.

    ``graded`` mang grade 0 quên, 1 khó, 2 nhớ, đúng khoá của
    ``scheduler.GRADE_TO_Q``.
    """

    graded = Signal(int)

    def __init__(self, word: str, detail, decomposer, parent=None) -> None:
        super().__init__(parent)
        self._word = word
        self._da_lat = False
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(18)

        layout.addWidget(self._mat_truoc(word), 0, Qt.AlignmentFlag.AlignHCenter)

        self._nut_lat = QPushButton("Hiện đáp án")
        self._nut_lat.setObjectName("Primary")
        self._nut_lat.setFont(ui_font(14, bold=True))
        self._nut_lat.setMinimumSize(168, 38)
        self._nut_lat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nut_lat.clicked.connect(self.reveal)
        layout.addWidget(self._nut_lat, 0, Qt.AlignmentFlag.AlignHCenter)

        # Mặt sau dựng sẵn nhưng giấu đi, để lúc lật không phải dựng lại layout.
        # setVisible(False) trên widget chưa có cha là an toàn; chỉ có
        # setVisible(True) mới biến nó thành cửa sổ cấp cao nhất.
        self._mat_sau = self._dung_mat_sau(detail, decomposer)
        self._mat_sau.setVisible(False)
        layout.addWidget(self._mat_sau, 0, Qt.AlignmentFlag.AlignHCenter)

        self._cai_phim_tat()

    @property
    def word(self) -> str:
        return self._word

    # ------------------------------------------------------------- mặt trước
    def _mat_truoc(self, word: str) -> QWidget:
        """Chỉ chữ Hán cỡ lớn, không âm không nghĩa: đó là cả bài kiểm tra."""
        if len(word) == 1:
            return TianZiGe(word, FRONT_BOX)

        # Từ nhiều chữ không vào ô 田字格: ô đó vẽ đúng một chữ theo mục 6.
        return _label(word, han_font(FRONT_PX), PALETTE["ink"])

    # --------------------------------------------------------------- mặt sau
    def _dung_mat_sau(self, detail, decomposer) -> QWidget:
        mat_sau = QWidget()
        mat_sau.setStyleSheet("background: transparent;")
        mat_sau.setMaximumWidth(RONG_CHU + 40)
        layout = QVBoxLayout(mat_sau)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        am = pinyin_cua(detail)
        if am:
            layout.addWidget(_label(am, mono_font(24), PALETTE["accent"]))

        hanviet = hanviet_cua(detail)
        if hanviet:
            layout.addWidget(_label(hanviet, mono_font(16), PALETTE["ink2"]))

        nghia, nhan = nghia_cua(detail)
        layout.addWidget(_section(nhan))
        y = _label(nghia, ui_font(16), PALETTE["ink"], wrap=True)
        y.setMaximumWidth(RONG_CHU)
        layout.addWidget(y)

        self._them_chiet_tu(layout, detail, decomposer)

        layout.addSpacing(6)
        layout.addWidget(_section("Bạn nhớ tới đâu"))
        layout.addLayout(self._hang_nut())
        layout.addWidget(_label(GOI_Y_PHIM, mono_font(11), PALETTE["muted"]))
        return mat_sau

    def _them_chiet_tu(self, layout: QVBoxLayout, detail, decomposer) -> None:
        """Một cây chiết tự cho mỗi chữ của từ, xếp dọc, có đường kẻ ngăn.

        Gọi ``decomposer.tree()`` ngay tại đây là có ý: mặt sau chỉ dựng đúng
        một lần cho mỗi thẻ, mà ScreenReview lại dựng thẻ theo từng từ chứ
        không dựng trước cả danh sách tới hạn. Nên số lần gọi bằng đúng số thẻ
        người dùng thật sự xem.
        """
        if not detail.chars:
            return

        layout.addSpacing(6)
        layout.addWidget(_section("Chiết tự"))
        for i, info in enumerate(detail.chars):
            if i:
                layout.addWidget(_duong_ke(), 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(
                DecompTree(decomposer.tree(info.char)),
                0,
                Qt.AlignmentFlag.AlignHCenter,
            )

    def _hang_nut(self) -> QHBoxLayout:
        hang = QHBoxLayout()
        hang.setSpacing(12)
        hang.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        for grade, ten, chu, nen, vien in NUT_DANH_GIA:
            nut = QPushButton(ten)
            nut.setFont(ui_font(14, bold=True))
            nut.setMinimumSize(112, 40)
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            nut.setStyleSheet(
                f"QPushButton {{ color: {PALETTE[chu]}; background: {PALETTE[nen]};"
                f" border: 1px solid {PALETTE[vien]}; border-radius: 4px; }}"
                f"QPushButton:hover {{ background: {PALETTE['bg']}; }}"
            )
            # Bắt grade vào mặc định của lambda: nếu để biến vòng lặp tự do thì
            # cả ba nút cùng phát grade của lần lặp cuối.
            nut.clicked.connect(lambda _=False, g=grade: self.graded.emit(g))
            hang.addWidget(nut)
        return hang

    # -------------------------------------------------------------- phím tắt
    def _cai_phim_tat(self) -> None:
        """Cách hoặc Enter để lật; 1, 2, 3 để chấm.

        App này dùng mỗi ngày nên đưa tay lên chuột hoá ra chậm. Ba phím số
        không ăn trước khi lật: chấm điểm mà chưa thấy đáp án thì con số ghi vào
        lịch không còn nghĩa gì.
        """
        for phim in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._them_phim(QKeySequence(phim), self.reveal)
        for grade, _ten, *_mau in NUT_DANH_GIA:
            self._them_phim(
                QKeySequence(str(grade + 1)),
                lambda g=grade: self._cham_bang_phim(g),
            )

    def _them_phim(self, seq: QKeySequence, slot) -> None:
        tat = QShortcut(seq, self)
        tat.setContext(Qt.ShortcutContext.WindowShortcut)
        tat.activated.connect(slot)

    def _cham_bang_phim(self, grade: int) -> None:
        if self._da_lat:
            self.graded.emit(grade)

    def reveal(self) -> None:
        """Lật thẻ. Nút lật biến mất để không lật hai lần."""
        if self._da_lat:
            return
        self._da_lat = True
        self._nut_lat.setVisible(False)
        self._mat_sau.setVisible(True)
