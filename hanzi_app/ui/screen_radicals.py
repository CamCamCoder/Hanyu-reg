"""Màn hình Bộ thủ: duyệt 214 bộ Khang Hy, xem chữ dùng từng bộ.

Bố cục:
  - Trái: lưới bộ thủ (lọc theo số nét dạng 2 hàng gọn gàng, tìm kiếm)
  - Phải: panel chi tiết — thông tin bộ thủ + danh sách chữ dùng bộ (click chữ nhảy tới bộ thủ tương ứng)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.data.models import Radical
from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font

# Số chữ hiển thị tối đa trong panel chi tiết bên phải.
CHARS_LIMIT = 120

# Số cột trong lưới bộ thủ bên trái.
GRID_COLS = 5


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['line']};")
    return line


class _BoThuCard(QFrame):
    """Một ô trong lưới bộ thủ trái: glyph to + tên HV + nghĩa."""

    clicked = Signal(object)  # phát Radical khi bấm

    def __init__(self, radical: Radical, parent=None) -> None:
        super().__init__(parent)
        self._radical = radical
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(82, 72)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 4, 2, 4)
        lay.setSpacing(1)

        self._lbl_glyph = QLabel(radical.glyph)
        self._lbl_glyph.setFont(han_font(26))
        self._lbl_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl_glyph)

        self._lbl_name = QLabel(radical.name_hv or "")
        self._lbl_name.setFont(ui_font(10))
        self._lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl_name)

        nghia = radical.meaning_vi or ""
        short = nghia[:9] + "…" if len(nghia) > 9 else nghia
        self._lbl_mean = QLabel(short)
        self._lbl_mean.setFont(mono_font(9))
        self._lbl_mean.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if nghia:
            self._lbl_mean.setToolTip(nghia)
        lay.addWidget(self._lbl_mean)

        self._update_style()

    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self._update_style()

    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"QFrame {{ background: {PALETTE['accent2_bg']}; border-radius: 6px; }}"
            )
            for lbl in (self._lbl_glyph, self._lbl_name, self._lbl_mean):
                lbl.setStyleSheet(f"color: {PALETTE['accent2']}; background: transparent;")
        else:
            self.setStyleSheet("QFrame { background: transparent; }")
            self._lbl_glyph.setStyleSheet(
                f"color: {PALETTE['ink']}; background: transparent;"
            )
            self._lbl_name.setStyleSheet(
                f"color: {PALETTE['ink2']}; background: transparent;"
            )
            self._lbl_mean.setStyleSheet(
                f"color: {PALETTE['muted']}; background: transparent;"
            )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._radical)
        super().mousePressEvent(event)


class _CharCard(QFrame):
    """Card chữ Hán bên phải: BỎ HOÀN TOÀN KHUNG.

    Chỉ có glyph + Hán-Việt/Pinyin + Nghĩa. Khi rê chuột vào sáng nhẹ background.
    Khi bấm phát ra tín hiệu `clicked(char)`.
    """

    clicked = Signal(str)

    def __init__(self, char: str, hanviet: str | None, meaning: str | None, parent=None) -> None:
        super().__init__(parent)
        self.char = char
        self.setFixedSize(76, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame { background: transparent; border: none; border-radius: 6px; }"
            f"QFrame:hover {{ background: {PALETTE['card']}; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 4, 2, 4)
        lay.setSpacing(1)

        lbl_glyph = QLabel(char)
        lbl_glyph.setFont(han_font(24))
        lbl_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_glyph.setStyleSheet(f"color: {PALETTE['ink']}; background: transparent;")
        lay.addWidget(lbl_glyph)

        lbl_hv = QLabel(hanviet or "—")
        lbl_hv.setFont(ui_font(10, bold=True))
        lbl_hv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hv.setStyleSheet(f"color: {PALETTE['ink2']}; background: transparent;")
        lay.addWidget(lbl_hv)

        nghia = meaning or "—"
        short = nghia[:9] + "…" if len(nghia) > 9 else nghia
        lbl_mean = QLabel(short)
        lbl_mean.setFont(mono_font(9))
        lbl_mean.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mean.setStyleSheet(f"color: {PALETTE['muted']}; background: transparent;")
        if meaning:
            lbl_mean.setToolTip(meaning)
        lay.addWidget(lbl_mean)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.char)
        super().mousePressEvent(event)


class _NutNet(QPushButton):
    """Nút lọc số nét tinh tế, gọn gàng."""

    def __init__(self, label: str, parent=None) -> None:
        super().__init__(label, parent)
        self.setFont(mono_font(10))
        self.setFixedHeight(24)
        self.setMinimumWidth(26)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{ color: {PALETTE['ink2']}; background: transparent;"
            f" border: 1px solid {PALETTE['line']}; border-radius: 4px;"
            f" padding: 0 4px; }}"
            f"QPushButton:checked {{ color: {PALETTE['card']};"
            f" background: {PALETTE['accent']}; border-color: {PALETTE['accent']}; }}"
            f"QPushButton:hover:!checked {{ background: {PALETTE['bg']}; }}"
        )


class ScreenRadicals(QWidget):
    """Màn hình Bộ thủ: duyệt 214 bộ + xem chữ dùng từng bộ."""

    def __init__(self, dict_db, parent=None) -> None:
        super().__init__(parent)
        self._dict = dict_db
        self._tat_ca: list[Radical] = dict_db.all_radicals()
        self._dang_chon: Radical | None = None
        self._cards: dict[int, _BoThuCard] = {}

        # Tra cứu bộ thủ theo glyph
        self._radical_by_glyph: dict[str, Radical] = {}
        for r in self._tat_ca:
            if r.glyph:
                self._radical_by_glyph[r.glyph] = r
            if r.glyph_alt:
                self._radical_by_glyph[r.glyph_alt] = r

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left(), 0)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {PALETTE['line']};")
        root.addWidget(sep)

        self._right_panel = QWidget()
        self._right_lay = QVBoxLayout(self._right_panel)
        self._right_lay.setContentsMargins(20, 20, 20, 20)
        self._right_lay.setSpacing(12)
        self._hien_placeholder()
        root.addWidget(self._right_panel, 1)

    # =========================================================== panel trái
    def _build_left(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(460)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        tieu_de = QLabel("214 Bộ thủ Khang Hy")
        tieu_de.setFont(ui_font(16, bold=True))
        tieu_de.setStyleSheet(f"color: {PALETTE['ink']};")
        lay.addWidget(tieu_de)

        self._o_tim = QLineEdit()
        self._o_tim.setPlaceholderText("Tìm bộ thủ (glyph, tên HV hoặc nghĩa)…")
        self._o_tim.setMinimumHeight(32)
        self._o_tim.textChanged.connect(self._loc_text)
        lay.addWidget(self._o_tim)

        lay.addWidget(self._build_loc_net())

        self._scroll_left = QScrollArea()
        self._scroll_left.setWidgetResizable(True)
        self._scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(4)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._scroll_left.setWidget(self._container)
        lay.addWidget(self._scroll_left, 1)

        self._ve_luoi(self._tat_ca)
        return panel

    def _build_loc_net(self) -> QWidget:
        """Hàng nút lọc số nét bố trí gọn gàng trong 2 hàng, không dùng ScrollBar thô."""
        widget = QWidget()
        v_lay = QVBoxLayout(widget)
        v_lay.setContentsMargins(0, 0, 0, 0)
        v_lay.setSpacing(4)

        self._nhom_net = QButtonGroup(self)
        self._nhom_net.setExclusive(True)

        net_co = sorted({r.strokes for r in self._tat_ca if r.strokes})
        mid = len(net_co) // 2 + 1

        # Hàng 1: Tất cả + các nét nhỏ
        h1 = QWidget()
        lay1 = QHBoxLayout(h1)
        lay1.setContentsMargins(0, 0, 0, 0)
        lay1.setSpacing(3)

        nut_tat_ca = _NutNet("Tất cả")
        nut_tat_ca.setChecked(True)
        self._nhom_net.addButton(nut_tat_ca, 0)
        lay1.addWidget(nut_tat_ca)

        for net in net_co[:mid]:
            nut = _NutNet(str(net))
            self._nhom_net.addButton(nut, net)
            lay1.addWidget(nut)
        lay1.addStretch(1)
        v_lay.addWidget(h1)

        # Hàng 2: Các nét lớn còn lại
        h2 = QWidget()
        lay2 = QHBoxLayout(h2)
        lay2.setContentsMargins(0, 0, 0, 0)
        lay2.setSpacing(3)

        for net in net_co[mid:]:
            nut = _NutNet(str(net))
            self._nhom_net.addButton(nut, net)
            lay2.addWidget(nut)
        lay2.addStretch(1)
        v_lay.addWidget(h2)

        self._nhom_net.idClicked.connect(self._loc_net)
        return widget

    def _ve_luoi(self, ds: list[Radical]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        for i, r in enumerate(ds):
            card = _BoThuCard(r)
            card.clicked.connect(self._chon_bo)
            self._cards[r.idx] = card
            self._grid.addWidget(card, i // GRID_COLS, i % GRID_COLS)

        self._grid.setRowStretch(len(ds) // GRID_COLS + 1, 1)

        if self._dang_chon and self._dang_chon.idx in self._cards:
            self._cards[self._dang_chon.idx].set_selected(True)

    # =========================================================== panel phải
    def _hien_placeholder(self) -> None:
        lbl = QLabel("Chọn một bộ thủ để xem chi tiết và các chữ liên quan")
        lbl.setFont(ui_font(14))
        lbl.setStyleSheet(f"color: {PALETTE['muted']};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_lay.addWidget(lbl, 1, Qt.AlignmentFlag.AlignCenter)

    def _xoa_right(self) -> None:
        while self._right_lay.count():
            item = self._right_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _lay_thong_tin_chu(self, ch: str) -> tuple[str, str]:
        """Tra cứu Hán Việt / Pinyin và Nghĩa tiếng Việt cho một chữ Hán.

        Bảo đảm không bao giờ để rỗng.
        """
        c_info = self._dict.get_char(ch)
        hv = ""
        meaning = ""

        if c_info:
            hv = c_info.hanviet or c_info.pinyin or ""
            meaning = c_info.meaning_vi or ""

        # Nếu thiếu meaning, tra trong bảng word
        if not meaning and hasattr(self._dict, "_conn"):
            row = self._dict._conn.execute(
                "SELECT meaning_vi, pinyin_tone FROM word WHERE word_simp = ? AND meaning_vi IS NOT NULL AND meaning_vi != '' LIMIT 1",
                (ch,)
            ).fetchone()
            if not row:
                row = self._dict._conn.execute(
                    "SELECT meaning_vi, pinyin_tone FROM word WHERE word_simp LIKE ? AND meaning_vi IS NOT NULL AND meaning_vi != '' LIMIT 1",
                    (f"%{ch}%",)
                ).fetchone()
            if row:
                meaning = row["meaning_vi"]
                if not hv and row["pinyin_tone"]:
                    hv = row["pinyin_tone"]

        # Nếu trùng với bộ thủ Khang Hy
        if not meaning and ch in self._radical_by_glyph:
            r = self._radical_by_glyph[ch]
            meaning = r.meaning_vi or ""
            if not hv:
                hv = r.name_hv or ""

        return (hv or "—", meaning or "—")

    def _hien_chi_tiet(self, r: Radical, thong_bao_extra: str | None = None) -> None:
        self._xoa_right()

        # Glyph to (+ dạng thay thế nếu có)
        glyph_txt = r.glyph
        if r.glyph_alt:
            glyph_txt += f"   ({r.glyph_alt})"
        lbl_glyph = QLabel(glyph_txt)
        lbl_glyph.setFont(han_font(64))
        lbl_glyph.setStyleSheet(f"color: {PALETTE['ink']};")
        lbl_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_lay.addWidget(lbl_glyph)

        # Thông tin chi tiết nằm ngang
        info = QWidget()
        info_lay = QHBoxLayout(info)
        info_lay.setSpacing(24)
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def _item(label: str, val: str) -> None:
            w = QWidget()
            v_lay = QVBoxLayout(w)
            v_lay.setSpacing(2)
            v_lay.setContentsMargins(0, 0, 0, 0)
            lbl_cap = QLabel(label)
            lbl_cap.setFont(ui_font(10))
            lbl_cap.setStyleSheet(f"color: {PALETTE['muted']};")
            lbl_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val = QLabel(val)
            lbl_val.setFont(ui_font(14, bold=True))
            lbl_val.setStyleSheet(f"color: {PALETTE['ink']};")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_lay.addWidget(lbl_cap)
            v_lay.addWidget(lbl_val)
            info_lay.addWidget(w)

        _item("Số thứ tự", f"#{r.idx}")
        _item("Tên Hán-Việt", r.name_hv or "—")
        _item("Nghĩa tiếng Việt", r.meaning_vi or "—")
        _item("Số nét", str(r.strokes))

        self._right_lay.addWidget(info)

        if thong_bao_extra:
            lbl_tb = QLabel(thong_bao_extra)
            lbl_tb.setFont(ui_font(12, bold=True))
            lbl_tb.setStyleSheet(f"color: {PALETTE['accent2']}; background: {PALETTE['accent2_bg']}; padding: 4px 12px; border-radius: 4px;")
            lbl_tb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._right_lay.addWidget(lbl_tb, 0, Qt.AlignmentFlag.AlignCenter)

        self._right_lay.addWidget(_sep())

        # Chữ dùng bộ này
        tieu = QLabel(f"Các chữ Hán dùng bộ  {r.glyph}  (Bấm vào chữ để chuyển tới bộ thủ của chữ đó)")
        tieu.setFont(ui_font(13, bold=True))
        tieu.setStyleSheet(f"color: {PALETTE['ink']};")
        self._right_lay.addWidget(tieu)

        chars = self._dict.chars_with_radical(r.idx, CHARS_LIMIT)
        if chars:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            cont = QWidget()
            g = QGridLayout(cont)
            g.setSpacing(6)
            g.setContentsMargins(0, 4, 0, 4)
            char_cols = 7
            for i, ch in enumerate(chars):
                hv, meaning = self._lay_thong_tin_chu(ch)
                card = _CharCard(ch, hv, meaning)
                card.clicked.connect(self._nhay_toi_bo_cua_chu)
                g.addWidget(card, i // char_cols, i % char_cols)
            g.setRowStretch(len(chars) // char_cols + 1, 1)
            scroll.setWidget(cont)
            self._right_lay.addWidget(scroll, 1)
        else:
            khong = QLabel("Không tìm thấy chữ nào dùng bộ này trong từ điển")
            khong.setFont(mono_font(12))
            khong.setStyleSheet(f"color: {PALETTE['muted']};")
            self._right_lay.addWidget(khong)
            self._right_lay.addStretch(1)

    # =========================================================== sự kiện
    def _chon_bo(self, r: Radical, msg_extra: str | None = None) -> None:
        if self._dang_chon and self._dang_chon.idx in self._cards:
            self._cards[self._dang_chon.idx].set_selected(False)
        self._dang_chon = r
        if r.idx in self._cards:
            card = self._cards[r.idx]
            card.set_selected(True)
            self._scroll_left.ensureWidgetVisible(card)
        self._hien_chi_tiet(r, msg_extra)

    def _nhay_toi_bo_cua_chu(self, char: str) -> None:
        """Khi bấm vào một chữ Hán ở panel bên phải: nhảy tới bộ thủ của chữ đó!"""
        c_info = self._dict.get_char(char)
        rad_idx = c_info.radical_idx if c_info else None
        
        # Nếu không có radical_idx, tra từ radical_by_glyph xem char có phải bản thân là một bộ không
        if not rad_idx and char in self._radical_by_glyph:
            rad_idx = self._radical_by_glyph[char].idx

        if rad_idx:
            rad = self._dict.get_radical(rad_idx)
            if rad:
                # Nếu bộ đó khác bộ hiện tại hoặc ô tìm kiếm đang lọc
                if self._o_tim.text():
                    self._o_tim.blockSignals(True)
                    self._o_tim.clear()
                    self._o_tim.blockSignals(False)
                    self._ve_luoi(self._tat_ca)

                hv, meaning = self._lay_thong_tin_chu(char)
                msg = f"Chữ {char} ({hv} — {meaning}) thuộc Bộ thủ #{rad.idx} ({rad.glyph} {rad.name_hv or ''})"
                self._chon_bo(rad, msg)

    def _loc_text(self, text: str) -> None:
        q = text.strip().lower()
        if not q:
            self._loc_net(self._nhom_net.checkedId())
            return
        ds = [
            r for r in self._tat_ca
            if (q in r.glyph
                or (r.glyph_alt and q in r.glyph_alt)
                or (r.name_hv and q in r.name_hv.lower())
                or (r.meaning_vi and q in r.meaning_vi.lower()))
        ]
        self._ve_luoi(ds)

    def _loc_net(self, net: int) -> None:
        if self._o_tim.text().strip():
            return
        if net == 0:
            self._ve_luoi(self._tat_ca)
        else:
            self._ve_luoi([r for r in self._tat_ca if r.strokes == net])
