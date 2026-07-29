"""Bài tập ôn tập: lớp nền ``BaiTap`` và kiểu trắc nghiệm ``ChonMotDap``.

Widget ở đây KHÔNG biết gì về SM-2 và không chạm cơ sở dữ liệu. Nó nhận sẵn câu
hỏi, đáp án đúng và danh sách đáp án nhiễu, rồi phát ``answered`` kèm grade 0, 1
hoặc 2 — đúng khoá của ``scheduler.GRADE_TO_Q``. Việc tính lịch vẫn của
``service/scheduler.py``, và việc ghi tiến độ vẫn của ``ScreenReview._cham``.
Bài tập chỉ thay phần HỎI, không thay phần CHẤM.

Ánh xạ điểm, chốt ở phiên 08c:

    đúng ngay lần thử đầu      -> grade 2  (Nhớ)
    đúng ở lần thử thứ hai     -> grade 1  (Khó)
    sai cả hai lần             -> grade 0  (Quên)

Mỗi câu cho đúng hai lần thử. Lý do có lần thứ hai: trắc nghiệm bốn lựa chọn mà
chỉ cho một lần thì đoán bừa trúng 25%, đủ để làm hỏng lịch ôn. Loại được một
đáp án rồi mới đoán thì tỷ lệ đó không còn phản ánh việc nhớ hay không.
"""

import random

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font
from hanzi_app.ui.widgets.review_card import WrapLabel, _section

# Khoảng nghỉ sau khi trả lời, để người học kịp nhìn đáp án đúng sáng lên trước
# khi sang câu sau. Ngắn hơn thì hụt, dài hơn thì sốt ruột khi làm liên tục.
NGHI_MS = 700

RONG = 520


def _label(text: str, font, color: str, wrap: bool = False) -> QLabel:
    label = WrapLabel(text) if wrap else QLabel(text)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class BaiTap(QFrame):
    """Lớp nền cho mọi kiểu bài tập.

    Lớp con dựng phần thân câu hỏi và gọi ``_cham(dung)`` khi người dùng trả
    lời. Lớp nền lo đếm số lần thử, ánh xạ sang grade, và phát ``answered``.

    Lớp con phải cài hai phương thức: ``_hien_dap_an()`` làm sáng đáp án đúng,
    và ``_khoa()`` chặn không cho trả lời tiếp.
    """

    answered = Signal(int)

    def __init__(self, word: str, parent=None) -> None:
        super().__init__(parent)
        self._word = word
        self._lan_thu = 0
        self._xong = False
        self.setObjectName("Card")

    @property
    def word(self) -> str:
        return self._word

    # --------------------------------------------------- lớp con phải cài
    def _hien_dap_an(self) -> None:
        raise NotImplementedError

    def _khoa(self) -> None:
        raise NotImplementedError

    def _bao(self, text: str) -> None:
        """Hiện một dòng phản hồi. Lớp con cài nếu muốn."""

    # ------------------------------------------------------------- chấm
    def _cham(self, dung: bool) -> None:
        if self._xong:
            return

        if dung:
            self._hien_dap_an()
            self._khoa()
            self._ket_thuc(2 if self._lan_thu == 0 else 1)
            return

        if self._lan_thu == 0:
            self._lan_thu = 1
            self._bao("Chưa đúng. Còn một lần thử.")
            return

        self._hien_dap_an()
        self._khoa()
        self._ket_thuc(0)

    def _ket_thuc(self, grade: int) -> None:
        self._xong = True
        # Đợi một nhịp rồi mới phát, để người học kịp thấy đáp án đúng. Dùng
        # dạng singleShot có đối tượng ngữ cảnh: nếu widget bị xoá trước khi hết
        # giờ thì Qt tự huỷ lời gọi, không nổ RuntimeError trên đối tượng đã chết.
        QTimer.singleShot(NGHI_MS, self, lambda: self.answered.emit(grade))


class ChonMotDap(BaiTap):
    """Trắc nghiệm bốn lựa chọn, dùng chung cho nhiều nguồn câu hỏi.

    ``cau_hoi`` là chuỗi hiện to ở trên, thường là chữ Hán. ``dap_an`` là đáp án
    đúng, ``nhieu`` là ba đáp án sai. Bên gọi lo việc loại đáp án nhiễu trùng
    nghĩa với đáp án đúng trước khi truyền vào đây.
    """

    def __init__(
        self,
        word: str,
        cau_hoi: str,
        dap_an: str,
        nhieu: list[str],
        nhan_hoi: str = "Chọn nghĩa đúng",
        han: bool = True,
        parent=None,
    ) -> None:
        super().__init__(word, parent)
        self._dap_an = dap_an
        self._nut: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(14)

        font = han_font(72) if han else ui_font(28, bold=True)
        layout.addWidget(_label(cau_hoi, font, PALETTE["ink"]), 0,
                         Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(_section(nhan_hoi), 0, Qt.AlignmentFlag.AlignHCenter)

        # Trộn Ở ĐÂY, tại tầng ui. Tầng data cố ý trả rổ ứng viên theo thứ tự
        # xác định để kiểm thử được; ngẫu nhiên là việc của tầng này.
        lua_chon = [dap_an, *nhieu]
        random.shuffle(lua_chon)

        for i, text in enumerate(lua_chon):
            nut = QPushButton(f"{i + 1}.  {text}")
            nut.setFont(ui_font(15))
            nut.setMinimumSize(RONG, 46)
            nut.setMaximumWidth(RONG)
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            nut.setStyleSheet(self._kieu_thuong())
            nut.clicked.connect(lambda _=False, t=text: self._bam(t))
            self._nut[text] = nut
            layout.addWidget(nut, 0, Qt.AlignmentFlag.AlignHCenter)
            self._them_phim(str(i + 1), text)

        self._dong_bao = _label("", mono_font(12), PALETTE["warn_ink"], wrap=True)
        self._dong_bao.setMaximumWidth(RONG)
        layout.addWidget(self._dong_bao, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(
            _label("Phím tắt: 1 · 2 · 3 · 4", mono_font(11), PALETTE["muted"]),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

    # ------------------------------------------------------------- kiểu nút
    @staticmethod
    def _kieu(chu: str, nen: str, vien: str, ro: bool = True) -> str:
        goc = (
            f"QPushButton {{ color: {PALETTE[chu]}; background: {PALETTE[nen]};"
            f" border: 1px solid {PALETTE[vien]}; border-radius: 4px;"
            f" text-align: left; padding-left: 16px; }}"
        )
        return goc + (
            f"QPushButton:hover {{ border: 1px solid {PALETTE['accent']}; }}" if ro else ""
        )

    def _kieu_thuong(self) -> str:
        return self._kieu("ink", "card", "line")

    def _bam(self, text: str) -> None:
        if self._xong:
            return
        if text == self._dap_an:
            self._cham(True)
            return
        # Đáp án sai thì xám đi và không bấm được nữa; ba nút kia còn dùng.
        nut = self._nut[text]
        nut.setEnabled(False)
        nut.setStyleSheet(self._kieu("muted", "bg", "line", ro=False))
        self._cham(False)

    def _them_phim(self, phim: str, text: str) -> None:
        tat = QShortcut(QKeySequence(phim), self)
        tat.setContext(Qt.ShortcutContext.WindowShortcut)
        tat.activated.connect(lambda t=text: self._bam(t))

    # --------------------------------------------------- lớp nền gọi xuống
    def _hien_dap_an(self) -> None:
        nut = self._nut[self._dap_an]
        nut.setEnabled(True)
        nut.setStyleSheet(self._kieu("accent2", "accent2_bg", "accent2_line", ro=False))

    def _khoa(self) -> None:
        for nut in self._nut.values():
            nut.setEnabled(False)
        self._dong_bao.setText("")

    def _bao(self, text: str) -> None:
        self._dong_bao.setText(text)


class GoPinyin(BaiTap):
    """Bài tập gõ pinyin cho từ đang học.

    Hiện chữ Hán to ở trên, người học gõ pinyin vào ô rồi nhấn Enter hoặc nút
    Kiểm tra. Chấm bằng ``pinyin.to_plain``, nên chấp nhận cả dạng có dấu
    (``rènshi``), không dấu (``renshi``) và dạng số (``ren4shi5``). Sau khi trả
    lời luôn hiện dạng có dấu đúng để người học thấy thanh điệu.

    Không import scheduler và không chạm cơ sở dữ liệu; chỉ phát ``answered``.
    """

    def __init__(self, word: str, pinyin_tone: str, parent=None) -> None:
        super().__init__(word, parent)
        self._pinyin_tone = pinyin_tone
        # to_plain của đáp án đúng, dùng để so sánh bất kể cách gõ.
        # Import cục bộ tránh vòng import và giữ phụ thuộc ui → service một chiều.
        from hanzi_app.service import pinyin as py_mod
        self._py = py_mod
        self._plain_dung = py_mod.to_plain(pinyin_tone)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(14)

        layout.addWidget(
            _label(word, han_font(72), PALETTE["ink"]),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addWidget(
            _section("Gõ pinyin của từ trên"),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        from PySide6.QtWidgets import QHBoxLayout, QLineEdit

        self._o_nhap = QLineEdit()
        self._o_nhap.setFont(mono_font(18))
        self._o_nhap.setMinimumSize(280, 44)
        self._o_nhap.setMaximumWidth(400)
        self._o_nhap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._o_nhap.setStyleSheet(
            f"QLineEdit {{ color: {PALETTE['ink']}; background: {PALETTE['card']};"
            f" border: 1px solid {PALETTE['line']}; border-radius: 4px;"
            f" padding: 4px 12px; }}"
            f"QLineEdit:focus {{ border: 1px solid {PALETTE['accent']}; }}"
        )
        self._o_nhap.returnPressed.connect(self._kiem_tra)
        layout.addWidget(self._o_nhap, 0, Qt.AlignmentFlag.AlignHCenter)

        self._nut_kt = QPushButton("Kiểm tra")
        self._nut_kt.setFont(ui_font(14))
        self._nut_kt.setMinimumSize(160, 40)
        self._nut_kt.setMaximumWidth(280)
        self._nut_kt.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nut_kt.setStyleSheet(
            f"QPushButton {{ color: {PALETTE['card']}; background: {PALETTE['accent']};"
            f" border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}"
            f"QPushButton:disabled {{ background: {PALETTE['line']};"
            f" color: {PALETTE['muted']}; }}"
        )
        self._nut_kt.clicked.connect(self._kiem_tra)
        layout.addWidget(self._nut_kt, 0, Qt.AlignmentFlag.AlignHCenter)

        # Dòng phản hồi: hiện "Chưa đúng" hoặc pinyin đúng sau khi xong.
        self._dong_bao = _label("", mono_font(14), PALETTE["warn_ink"], wrap=True)
        self._dong_bao.setMaximumWidth(400)
        layout.addWidget(self._dong_bao, 0, Qt.AlignmentFlag.AlignHCenter)

        # Dòng gợi ý chấp nhận nhiều cách gõ.
        layout.addWidget(
            _label(
                "Chấp nhận: dạng dấu (rènshi), không dấu (renshi), số (ren4shi5)",
                mono_font(11),
                PALETTE["muted"],
            ),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

    def _kiem_tra(self) -> None:
        if self._xong:
            return
        nhap = self._o_nhap.text().strip()
        if not nhap:
            return
        plain_nhap = self._py.to_plain(nhap)
        # Thử thêm dạng chuyển đổi từ dạng số (ren4shi5 → rènshi → renshi).
        if plain_nhap != self._plain_dung:
            plain_nhap2 = self._py.to_plain(self._py.num_to_tone(nhap))
            if plain_nhap2 == self._plain_dung:
                plain_nhap = plain_nhap2
        self._cham(plain_nhap == self._plain_dung)

    # ----------------------------------------------- lớp nền gọi xuống
    def _hien_dap_an(self) -> None:
        """Hiện pinyin đúng có dấu màu accent2 để người học thấy thanh điệu."""
        self._dong_bao.setStyleSheet(
            f"color: {PALETTE['accent2']}; background: transparent;"
        )
        self._dong_bao.setText(f"Đáp án đúng: {self._pinyin_tone}")

    def _khoa(self) -> None:
        self._o_nhap.setEnabled(False)
        self._nut_kt.setEnabled(False)

    def _bao(self, text: str) -> None:
        self._dong_bao.setStyleSheet(
            f"color: {PALETTE['warn_ink']}; background: transparent;"
        )
        self._dong_bao.setText(text)


class _ManhButton(QFrame):
    """Nút mảnh bộ thủ: glyph to + nghĩa nhỏ bên dưới, không khưng.

    Khi chưa chọn: nền trong suốt. Khi chọn: nền nhấn nhẹ + chữ glyph đổi màu.
    Dùng QFrame thay QPushButton để dùng được nhiều cỡ chữ khác nhau.
    """

    def __init__(
        self,
        glyph: str,
        name_hv: str | None,
        meaning_vi: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.glyph = glyph
        self._checked = False
        self.setFixedSize(80, 68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(1)

        self._lbl_glyph = QLabel(glyph)
        self._lbl_glyph.setFont(han_font(30))
        self._lbl_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl_glyph)

        # Hiện meaning_vi nếu có, không thì hiện name_hv
        nhan = meaning_vi or name_hv or ""
        short = nhan[:12] + "…" if len(nhan) > 12 else nhan
        self._lbl_mean = QLabel(short)
        self._lbl_mean.setFont(mono_font(10))
        self._lbl_mean.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if meaning_vi:
            self._lbl_mean.setToolTip(meaning_vi)
        lay.addWidget(self._lbl_mean)

        self._update_style()

    # -------------------------------------------------------- style
    def _update_style(self) -> None:
        if self._checked:
            self.setStyleSheet(
                f"QFrame {{ background: {PALETTE['accent2_bg']}; border-radius: 6px; }}"
            )
            self._lbl_glyph.setStyleSheet(
                f"color: {PALETTE['accent2']}; background: transparent;"
            )
            self._lbl_mean.setStyleSheet(
                f"color: {PALETTE['accent2']}; background: transparent;"
            )
        else:
            self.setStyleSheet("QFrame { background: transparent; }")
            self._lbl_glyph.setStyleSheet(
                f"color: {PALETTE['ink']}; background: transparent;"
            )
            self._lbl_mean.setStyleSheet(
                f"color: {PALETTE['muted']}; background: transparent;"
            )

    def set_correct(self) -> None:
        """Nền xanh accent2 (mảnh đúng)."""
        self.setStyleSheet(
            f"QFrame {{ background: {PALETTE['accent2_bg']}; border-radius: 6px; }}"
        )
        self._lbl_glyph.setStyleSheet(
            f"color: {PALETTE['accent2']}; background: transparent;"
        )
        self._lbl_mean.setStyleSheet(
            f"color: {PALETTE['accent2']}; background: transparent;"
        )

    def set_wrong(self) -> None:
        """Chữ mờ (mảnh sai)."""
        self.setStyleSheet("QFrame { background: transparent; }")
        self._lbl_glyph.setStyleSheet(
            f"color: {PALETTE['muted']}; background: transparent;"
        )
        self._lbl_mean.setStyleSheet(
            f"color: {PALETTE['muted']}; background: transparent;"
        )

    # -------------------------------------------------------- bấm
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._update_style()
            if callable(getattr(self, "on_toggle", None)):
                self.on_toggle(self.glyph, self._checked)
        super().mousePressEvent(event)

    def set_enabled(self, enabled: bool) -> None:
        """Vô hiệu hoá: ẩn con trỏ và ngừng nhận bấm."""
        self.setEnabled(enabled)
        self.setCursor(
            Qt.CursorShape.ArrowCursor if not enabled
            else Qt.CursorShape.PointingHandCursor
        )


class GhepBoThu(BaiTap):
    """Bài tập chọn đúng TẬP các bộ thủ cấu thành chữ.

    ``dung`` và ``nhieu`` là danh sách tuple ``(glyph, name_hv, meaning_vi)``.
    ``dung`` là các thành phần thật, ``nhieu`` là các mảnh nhiễu. Tổng 5–6 mảnh.
    Người học chọn đúng tập rồi nhấn Xác nhận.

    Không import scheduler và không chạm cơ sở dữ liệu; chỉ phát ``answered``.
    """

    _TONG_MANH = 6  # số mảnh hiển thị (đúng + nhiễu)

    def __init__(
        self,
        word: str,
        char: str,
        dung: list[tuple[str, str | None, str | None]],
        nhieu: list[tuple[str, str | None, str | None]],
        parent=None,
    ) -> None:
        super().__init__(word, parent)
        self._char = char
        # Tập glyph đúng — dùng để so sánh khi chấm.
        self._dung_set = {t[0] for t in dung}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 32)
        layout.setSpacing(14)

        layout.addWidget(
            _label(char, han_font(72), PALETTE["ink"]),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addWidget(
            _section("Chọn các bộ thủ tạo nên chữ trên"),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        # Gộp và trộn mảnh.
        from PySide6.QtWidgets import QGridLayout, QHBoxLayout
        import random as _rand

        tat_ca = list(dung) + list(nhieu)
        _rand.shuffle(tat_ca)

        # Nút mảnh dạng _ManhButton — cho phép chọn nhiều.
        self._manh_buttons: dict[str, _ManhButton] = {}
        self._da_chon: set[str] = set()

        grid = QGridLayout()
        grid.setSpacing(10)
        cols = 3
        for i, (glyph, name_hv, meaning_vi) in enumerate(tat_ca):
            btn = _ManhButton(glyph, name_hv, meaning_vi)
            btn.on_toggle = self._bam_manh
            self._manh_buttons[glyph] = btn
            grid.addWidget(btn, i // cols, i % cols)

        hang_grid = QHBoxLayout()
        hang_grid.addStretch(1)
        hang_grid.addLayout(grid)
        hang_grid.addStretch(1)
        layout.addLayout(hang_grid)

        self._nut_xn = QPushButton("Xác nhận")
        self._nut_xn.setFont(ui_font(14))
        self._nut_xn.setMinimumSize(160, 40)
        self._nut_xn.setMaximumWidth(280)
        self._nut_xn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nut_xn.setStyleSheet(
            f"QPushButton {{ color: {PALETTE['card']}; background: {PALETTE['accent']};"
            f" border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}"
            f"QPushButton:disabled {{ background: {PALETTE['line']};"
            f" color: {PALETTE['muted']}; }}"
        )
        self._nut_xn.clicked.connect(self._xac_nhan)
        layout.addWidget(self._nut_xn, 0, Qt.AlignmentFlag.AlignHCenter)

        self._dong_bao = _label("", mono_font(12), PALETTE["warn_ink"], wrap=True)
        self._dong_bao.setMaximumWidth(480)
        layout.addWidget(self._dong_bao, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(
            _label(
                f"Chọn đúng {len(dung)} bộ thủ, rồi nhấn Xác nhận",
                mono_font(11),
                PALETTE["muted"],
            ),
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

    def _bam_manh(self, glyph: str, checked: bool) -> None:
        if self._xong:
            return
        if checked:
            self._da_chon.add(glyph)
        else:
            self._da_chon.discard(glyph)

    def _xac_nhan(self) -> None:
        if self._xong:
            return
        if not self._da_chon:
            self._bao("Hãy chọn ít nhất một bộ thủ.")
            return
        dung = self._da_chon == self._dung_set
        self._cham(dung)

    # ----------------------------------------------- lớp nền gọi xuống
    def _hien_dap_an(self) -> None:
        """Sáng lên các mảnh đúng (accent2), làm xám mảnh sai."""
        for glyph, btn in self._manh_buttons.items():
            if glyph in self._dung_set:
                btn.set_correct()
            else:
                btn.set_wrong()

    def _khoa(self) -> None:
        for btn in self._manh_buttons.values():
            btn.set_enabled(False)
        self._nut_xn.setEnabled(False)

    def _bao(self, text: str) -> None:
        self._dong_bao.setText(text)



