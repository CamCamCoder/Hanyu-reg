"""Màn hình Tra cứu, mockup mục 7.2.

Tầng ui chỉ gọi xuống tầng service. Màn hình này nhận LookupService và
Decomposer đã dựng sẵn từ main.py, gọi lookup.detail() để lấy thông tin từ rồi
gọi decomposer.tree() cho từng chữ và tự ghép; lookup KHÔNG gọi sang decomposer.

Ba khối cuối của mockup 7.2 — phần diễn giải "vì sao chữ này viết như vậy" và
phần "bạn đã gặp bộ này ở đâu" — để phiên sau, vì cả hai cần dữ liệu chưa có.

Hai chỗ dữ liệu còn rỗng trong dict.sqlite, hiện đúng trạng thái rỗng có nhãn:
cột pos của bảng word rỗng toàn bộ nên không có chip từ loại thật, và cột hanviet
của bảng char cũng rỗng nên không có âm Hán-Việt. Cột meaning_vi của word rỗng
nốt, nên khối NGHĨA TỪ ĐIỂN hiện nghĩa tiếng Anh và ghi rõ nhãn là tiếng Anh.
"""

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.service import pinyin
from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font
from hanzi_app.ui.widgets.decomp_tree import DecompTree
from hanzi_app.ui.widgets.tianzige import TianZiGe

# Nhãn dùng lại nhiều chỗ cho các cột dữ liệu còn rỗng trong dict.sqlite.
TRONG = "chưa có dữ liệu"


def _label(text: str, font, color: str, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setWordWrap(wrap)
    return label


def _section(text: str) -> QLabel:
    """Nhãn mục nhỏ: đơn cách, in hoa, giãn chữ, theo mục 6.2."""
    font = mono_font(11)
    font.setLetterSpacing(font.SpacingType.PercentageSpacing, 106)
    return _label(text.upper(), font, PALETTE["muted"])


def _chip(text: str, muted: bool = False) -> QLabel:
    """Nhãn nhỏ bo góc. Chip mờ dùng cho trạng thái dữ liệu còn rỗng."""
    chip = QLabel(text)
    chip.setFont(mono_font(11))
    mau = PALETTE["muted"] if muted else PALETTE["accent2"]
    vien = PALETTE["line"] if muted else PALETTE["accent2_line"]
    nen = "transparent" if muted else PALETTE["accent2_bg"]
    chip.setStyleSheet(
        f"color: {mau}; background: {nen}; border: 1px solid {vien};"
        "border-radius: 9px; padding: 2px 8px;"
    )
    return chip


def _card() -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("Card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 18)
    layout.setSpacing(10)
    return card, layout


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['line']}; background: {PALETTE['line']};")
    line.setFixedHeight(1)
    return line


def _clear(layout: QVBoxLayout) -> None:
    """Xoá sạch nội dung một layout, kể cả layout con.

    KHÔNG dùng setParent(None): trên Windows, cắt cha biến widget thành cửa sổ
    cấp cao nhất và Qt cấp cho nó một HWND thật, gây ra một cửa sổ chớp lên rồi
    tắt ngay trước khi đối tượng bị thu hồi."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())
            item.layout().deleteLater()


def _hsk_freq(hsk_level, freq_rank) -> str:
    hsk = f"HSK{hsk_level}" if hsk_level else "—"
    freq = f"#{freq_rank}" if freq_rank else "—"
    return f"{hsk} · {freq}"


class _ResultRow(QFrame):
    """Một dòng kết quả tìm kiếm, bấm được."""

    clicked = Signal(str)

    def __init__(self, key: str, hanzi: str, am: str, nghia: str, meta: str,
                 parent=None) -> None:
        super().__init__(parent)
        self._key = key
        self.setObjectName("Row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(14)

        chu = _label(hanzi, han_font(19), PALETTE["ink"])
        chu.setMinimumWidth(60)
        row.addWidget(chu)

        pin = _label(am, mono_font(13), PALETTE["accent"])
        pin.setMinimumWidth(96)
        row.addWidget(pin)

        # Nghĩa lấy từ cột tiếng Anh, nên gắn thẳng nhãn EN vào dòng.
        row.addWidget(_label("EN", mono_font(10), PALETTE["muted"]))
        y = _label(nghia, ui_font(14), PALETTE["ink2"])
        y.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(y, 1)

        row.addWidget(_label(meta, mono_font(11), PALETTE["muted"]))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (tên do Qt quy định)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._key)
        super().mouseReleaseEvent(event)


class ScreenLookup(QWidget):
    """Ô tìm kiếm, danh sách kết quả xếp hạng, và trang chi tiết của một từ.

    ``progress_changed`` phát khi người dùng thêm một từ vào danh sách ôn tập,
    để cửa sổ chính cập nhật hai con số ở chân thanh điều hướng.
    """

    progress_changed = Signal()

    def __init__(self, lookup, decomposer, user_db, scheduler, parent=None) -> None:
        super().__init__(parent)
        self._lookup = lookup
        self._decomposer = decomposer
        self._user = user_db
        self._scheduler = scheduler

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        page = QWidget()
        page.setObjectName("Page")
        self._page = QVBoxLayout(page)
        self._page.setContentsMargins(28, 24, 28, 28)
        self._page.setSpacing(14)
        scroll.setWidget(page)

        self._page.addWidget(_label("Tra cứu", ui_font(20, bold=True), PALETTE["ink"]))
        self._page.addWidget(
            _label(
                "Gõ chữ Hán, pinyin có dấu hoặc không dấu, hoặc nghĩa",
                ui_font(14),
                PALETTE["ink2"],
            )
        )

        thanh = QHBoxLayout()
        thanh.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("renshi, rènshi, ren4shi5, 认识, recognize")
        self.input.setFont(ui_font(15))
        self.input.setMinimumHeight(38)
        self.input.returnPressed.connect(self.do_search)
        thanh.addWidget(self.input, 1)

        self.button = QPushButton("Tìm")
        self.button.setObjectName("Primary")
        self.button.setFont(ui_font(14, bold=True))
        self.button.setMinimumSize(104, 38)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self.do_search)
        thanh.addWidget(self.button)
        self._page.addLayout(thanh)

        self._summary = _label("", mono_font(11), PALETTE["muted"], wrap=True)
        self._page.addWidget(self._summary)

        self._results = QVBoxLayout()
        self._results.setSpacing(0)
        self._page.addLayout(self._results)

        self._detail = QVBoxLayout()
        self._detail.setSpacing(14)
        self._page.addLayout(self._detail)

        self._page.addStretch(1)

    # ------------------------------------------------------------- tìm kiếm
    def do_search(self) -> None:
        query = self.input.text().strip()
        _clear(self._results)
        _clear(self._detail)
        if not query:
            self._summary.setText("")
            return

        hits = self._lookup.search(query)
        if hits:
            self._summary.setText(
                f"{len(hits)} KẾT QUẢ · XẾP THEO ĐỘ KHỚP, HSK RỒI TẦN SUẤT"
            )
            self._add_rows(hits)
            return

        # Không khớp đúng thì mới sang nhánh gợi ý của FR-08.
        goi_y = self._lookup.suggest(query)
        if goi_y:
            self._summary.setText(
                f"KHÔNG CÓ KẾT QUẢ KHỚP ĐÚNG · CÓ PHẢI BẠN MUỐN TÌM {len(goi_y)} MỤC DƯỚI ĐÂY"
            )
            self._add_rows(goi_y)
        else:
            self._summary.setText("KHÔNG CÓ KẾT QUẢ VÀ KHÔNG CÓ GỢI Ý NÀO GẦN GIỐNG")

    def _add_rows(self, hits) -> None:
        box = QFrame()
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, hit in enumerate(hits):
            if i:
                layout.addWidget(_divider())
            if hit.kind == "word":
                w = hit.word
                row = _ResultRow(
                    w.simplified,
                    w.simplified,
                    w.pinyin_tone,
                    w.meaning_vi or w.meaning_en or TRONG,
                    _hsk_freq(w.hsk_level, w.freq_rank),
                )
            else:
                c = hit.char
                row = _ResultRow(
                    c.char,
                    c.char,
                    c.pinyin,
                    c.meaning_vi or c.meaning_en or TRONG,
                    _hsk_freq(c.hsk_level, c.freq_rank),
                )
            row.clicked.connect(self.show_detail)
            layout.addWidget(row)

        self._results.addWidget(box)

    # ------------------------------------------------------------- chi tiết
    def show_detail(self, word: str) -> None:
        """Trang chi tiết: khối thông tin từ, khối chiết tự, khối nguồn nếu có."""
        _clear(self._detail)
        detail = self._lookup.detail(word)
        self._detail.addWidget(self._word_card(detail))
        self._detail.addWidget(self._decomp_card(detail))

    def _word_card(self, detail) -> QFrame:
        card, layout = _card()

        tren = QHBoxLayout()
        tren.setSpacing(18)

        # Mỗi chữ của từ một ô 田字格.
        o_chu = QHBoxLayout()
        o_chu.setSpacing(10)
        o_chu.setAlignment(Qt.AlignmentFlag.AlignTop)
        for ch in detail.query:
            o_chu.addWidget(TianZiGe(ch, 88))
        tren.addLayout(o_chu)

        phai = QVBoxLayout()
        phai.setSpacing(6)
        phai.setAlignment(Qt.AlignmentFlag.AlignTop)

        word = detail.word
        am = word.pinyin_tone if word else (detail.chars[0].pinyin if detail.chars else "")
        phai.addWidget(_label(detail.query, han_font(40), PALETTE["ink"]))
        if am:
            phai.addWidget(
                _label(f"{am} · {pinyin.tone_to_num(am)}", mono_font(16), PALETTE["accent"])
            )

        chips = QHBoxLayout()
        chips.setSpacing(8)
        if word is not None and word.hsk_level:
            chips.addWidget(_chip(f"HSK {word.hsk_level}"))
        else:
            chips.addWidget(_chip("chưa xếp HSK", muted=True))
        # Cột pos của bảng word rỗng toàn bộ 5001 dòng: hiện trạng thái rỗng,
        # không lấy chip [động từ] theo mockup.
        pos = word.pos if word else None
        chips.addWidget(_chip(f"từ loại: {pos}") if pos else _chip(f"từ loại: {TRONG}", muted=True))
        chips.addWidget(
            _chip(f"trạng thái: {detail.status}") if detail.status
            else _chip("chưa ôn tập lần nào", muted=True)
        )
        if word is not None and word.traditional and word.traditional != word.simplified:
            chips.addWidget(_chip(f"phồn thể: {word.traditional}", muted=True))
        chips.addStretch(1)
        phai.addLayout(chips)

        phai.addLayout(self._hang_them(detail))

        tren.addLayout(phai, 1)
        layout.addLayout(tren)

        # NGHĨA THEO SÁCH và NGUỒN chỉ hiện khi từ đã nằm trong quyển nào đó.
        source = detail.source
        if source is not None:
            if source.meaning_src:
                layout.addWidget(_divider())
                layout.addWidget(_section("Nghĩa theo sách"))
                layout.addWidget(_label(source.meaning_src, ui_font(14), PALETTE["ink"], wrap=True))
            layout.addWidget(_divider())
            layout.addWidget(_section("Nguồn"))
            trang = f" · tr. {source.page}" if source.page else ""
            ten_bai = f" {source.lesson_title}" if source.lesson_title else ""
            layout.addWidget(
                _label(
                    f"{source.book_title} · Bài {source.lesson_no}{ten_bai}{trang}",
                    ui_font(14),
                    PALETTE["ink"],
                    wrap=True,
                )
            )

        layout.addWidget(_divider())
        # Cột meaning_vi của bảng word còn rỗng nên khối này hiện nghĩa tiếng
        # Anh, và ghi rõ nhãn là tiếng Anh.
        nghia_vi = word.meaning_vi if word else None
        if nghia_vi:
            layout.addWidget(_section("Nghĩa từ điển"))
            layout.addWidget(_label(nghia_vi, ui_font(14), PALETTE["ink"], wrap=True))
        else:
            nghia_en = word.meaning_en if word else None
            layout.addWidget(_section("Nghĩa từ điển · tiếng Anh"))
            layout.addWidget(
                _label(nghia_en or TRONG, ui_font(14), PALETTE["ink"], wrap=True)
            )
            layout.addWidget(
                _label(
                    "Nghĩa tiếng Việt của mục từ chưa có trong từ điển.",
                    ui_font(12),
                    PALETTE["muted"],
                    wrap=True,
                )
            )

        if word is None:
            layout.addWidget(
                _label(
                    "Chuỗi này chưa có mục từ trong từ điển, dưới đây là dữ liệu mức chữ đơn.",
                    ui_font(12),
                    PALETTE["muted"],
                    wrap=True,
                )
            )
        return card

    # ------------------------------------------------------ thêm vào ôn tập
    def _hang_them(self, detail) -> QHBoxLayout:
        """Nút thêm từ đang xem vào danh sách ôn tập.

        Lệch có ý thức với QT-04 bước 2, vốn chỉ cho từ vào danh sách qua một
        bài trong sách. Luồng nhập sách chưa làm, mà lược đồ đã lường trước:
        ``progress.source_lw_id`` cố ý cho phép NULL cho đúng đường này. Xem
        BAN-GIAO.md mục 2.

        Từ đã có tiến độ thì hiện thẳng nhãn tĩnh, không hiện nút: thêm lại chỉ
        làm hỏng lịch ôn đang chạy.
        """
        hang = QHBoxLayout()
        hang.setSpacing(8)
        hang.setContentsMargins(0, 6, 0, 0)

        # Dựng sẵn cả nút lẫn nhãn rồi giấu bớt một cái, chứ không xoá widget khi
        # bấm: xoá đúng cái nút đang phát tín hiệu là tự rút thảm dưới chân mình.
        self._nut_them = QPushButton("Thêm vào ôn tập")
        self._nut_them.setObjectName("Primary")
        self._nut_them.setFont(ui_font(13, bold=True))
        self._nut_them.setMinimumSize(150, 32)
        self._nut_them.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nut_them.clicked.connect(lambda _=False, w=detail.query: self._them(w))
        hang.addWidget(self._nut_them)

        self._nhan_da_them = _label(
            "đã có trong danh sách ôn tập", ui_font(13), PALETTE["accent2"]
        )
        hang.addWidget(self._nhan_da_them)

        da_co = detail.status is not None
        # Khong goi setVisible(True) luc dung: widget chua co cha se bi Qt coi la
        # cua so cap cao nhat va Windows cap cho no mot HWND that, gay ra mot cua
        # so chop len roi tat. Widget trong layout thi mac dinh da hien, nen chi
        # can an cai khong dung; setVisible(False) luon an toan.
        if da_co:
            self._nut_them.setVisible(False)
        else:
            self._nhan_da_them.setVisible(False)

        hang.addStretch(1)
        return hang

    def _them(self, word: str) -> None:
        """Đưa từ vào bảng progress ở trạng thái ban đầu của QT-04 bước 2.

        Ngày tới hạn do ``scheduler.initial`` đặt bằng chính hôm nay, nên từ vừa
        thêm hiện ra ngay ở màn hình Ôn tập. source_lw_id là None vì từ này
        không đi qua quyển sách nào.
        """
        outcome = self._scheduler.initial(date.today())
        self._user.upsert_progress(word, outcome, None)

        self._nut_them.setVisible(False)
        self._nhan_da_them.setVisible(True)
        self.progress_changed.emit()

    def _decomp_card(self, detail) -> QFrame:
        card, layout = _card()
        layout.addWidget(_section("Chiết tự"))

        if not detail.chars:
            layout.addWidget(
                _label("Không có chữ nào của mục này trong bảng char.",
                       ui_font(14), PALETTE["muted"], wrap=True)
            )
            return card

        for i, info in enumerate(detail.chars):
            if i:
                layout.addWidget(_divider())

            dong = QHBoxLayout()
            dong.setSpacing(10)
            dong.addWidget(_label(info.char, han_font(19), PALETTE["ink"]))
            dong.addWidget(_label(info.pinyin, mono_font(13), PALETTE["accent"]))

            node = self._decomposer.tree(info.char)
            radical = node.radical
            if radical is not None:
                alt = f" ({radical.glyph_alt})" if radical.glyph_alt else ""
                mo_ta = f"bộ {radical.glyph}{alt} — {radical.name_hv}, {radical.meaning_vi}"
            else:
                mo_ta = f"bộ thủ: {TRONG}"
            dong.addWidget(_label(mo_ta, ui_font(14), PALETTE["ink2"]))

            net = f"{info.total_strokes} nét" if info.total_strokes else f"số nét: {TRONG}"
            dong.addWidget(_label(f"· {net}", mono_font(11), PALETTE["muted"]))
            # Cột hanviet của bảng char rỗng toàn bộ 9534 dòng.
            hv = info.hanviet or TRONG
            dong.addWidget(_label(f"· Hán-Việt: {hv}", mono_font(11), PALETTE["muted"]))
            dong.addStretch(1)
            layout.addLayout(dong)

            layout.addWidget(DecompTree(node))

        return card
