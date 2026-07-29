"""Màn hình Ôn tập, QT-04 bước 3 tới 6.

Vòng đời một phiên ôn: lấy danh sách từ tới hạn, đưa từng thẻ ra, ghi lại kết
quả mỗi lần bấm, hết thẻ thì tổng kết.

Ba ràng buộc của mục 13.1 được giữ ở đây:

- Không tính lịch. Mọi con số ease, khoảng cách, bậc lặp đều do
  ``service/scheduler.py`` trả về; màn hình chỉ chuyển tiếp.
- Không mở cơ sở dữ liệu. UserDb do ``main.py`` dựng và bơm vào.
- Không gọi ``lookup.detail()`` cho cả danh sách lúc mở màn hình, mà gọi đúng
  lúc dựng từng thẻ. Danh sách tới hạn có thể dài cả trăm từ.

Danh sách được lấy lại mỗi lần màn hình hiện ra, nên rời sang màn hình khác rồi
quay lại là bắt đầu một phiên mới trên đúng những từ còn tới hạn.
"""

import random
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hanzi_app.ui.theme import PALETTE, han_font, mono_font, ui_font
from hanzi_app.ui.widgets.bai_tap import ChonMotDap, GhepBoThu, GoPinyin
from hanzi_app.ui.widgets.review_card import ReviewCard, WrapLabel

# Hai chế độ ôn. Thẻ lật là mặc định vì nó không đòi hỏi dữ liệu gì thêm.
CHE_DO = ("Thẻ lật", "Trắc nghiệm")

# Cần đủ 3 đáp án nhiễu mới dựng được một câu bốn lựa chọn.
SO_NHIEU = 3


def _label(text: str, font, color: str, wrap: bool = False) -> QLabel:
    label = WrapLabel(text) if wrap else QLabel(text)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    return label


def _clear(layout: QLayout) -> None:
    """Xoá sạch nội dung một layout, kể cả layout con.

    KHÔNG dùng setParent(None): trong Qt, cắt cha biến widget thành cửa sổ cấp
    cao nhất và Windows cấp cho nó một HWND thật, gây ra một cửa sổ chớp lên rồi
    tắt ngay trước khi đối tượng bị thu hồi. hide() rồi deleteLater() cho cùng
    kết quả mà không bao giờ tạo cửa sổ.
    """
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())
            item.layout().deleteLater()


class ScreenReview(QWidget):
    """Nhận LookupService, UserDb, module scheduler và Decomposer từ main.py.

    ``progress_changed`` phát mỗi lần bảng progress đổi, để cửa sổ chính cập
    nhật hai con số ở chân thanh điều hướng.

    Decomposer đứng cuối danh sách tham số vì nó thêm ở phiên 08b; thứ tự ba
    tham số cũ không đổi.
    """

    progress_changed = Signal()

    def __init__(
        self, lookup, user_db, scheduler, decomposer, dict_db=None, parent=None
    ) -> None:
        super().__init__(parent)
        self._lookup = lookup
        self._user = user_db
        self._scheduler = scheduler
        self._decomposer = decomposer
        # dict_db chỉ dùng để lấy rổ đáp án nhiễu cho bài tập. Để None được:
        # thiếu nó thì chế độ Trắc nghiệm tự tắt, phần còn lại chạy như cũ.
        self._dict = dict_db
        self._che_do = 0

        self._due: list[str] = []
        self._vi_tri = 0
        self._da_on = 0

        # Ngăn xếp hoàn tác: mỗi phần tử là cặp (word, ReviewOutcome trước khi
        # chấm). Không chú thích kiểu ReviewOutcome ở đây vì mục 13.1 cấm tầng
        # ui import thẳng data/; màn hình chỉ chuyển tiếp đối tượng nhận được từ
        # get_progress() trở lại undo_review().
        #
        # Ngăn xếp CỐ Ý chỉ sống trong phiên đang chạy. review_log không lưu
        # ease_before, repetition_before, status_before hay due_date_before nên
        # không dựng lại được trạng thái cũ từ nhật ký; hoàn tác xuyên phiên sẽ
        # cần một bậc migration thứ ba. Chưa đáng làm: người dùng nhận ra bấm
        # nhầm ngay lập tức chứ không phải sau khi tắt app.
        self._lich_su: list[tuple] = []

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

        self._page.addWidget(_label("Ôn tập", ui_font(20, bold=True), PALETTE["ink"]))

        # Dòng tóm lược và chỗ dành cho nút Hoàn tác. Nhãn sống suốt đời màn
        # hình, còn nút thì dựng lại mỗi lần vẽ, nên nút phải nằm trong một
        # layout riêng để xoá được mà không đụng tới nhãn.
        hang = QHBoxLayout()
        hang.setSpacing(16)
        self._dong_tom_luoc = _label("", mono_font(11), PALETTE["muted"])
        hang.addWidget(self._dong_tom_luoc)
        self._o_hoan_tac = QHBoxLayout()
        self._o_hoan_tac.setContentsMargins(0, 0, 0, 0)
        hang.addLayout(self._o_hoan_tac)
        # Giãn đặt SAU nút, không phải trước. Cho nhãn stretch 1 thì trên màn
        # hình rộng nút bị đẩy ra tận mép phải và người dùng không thấy nó.
        hang.addStretch(1)
        self._page.addLayout(hang)

        if self._dict is not None:
            self._page.addLayout(self._hang_che_do())

        self._than = QVBoxLayout()
        self._than.setSpacing(14)
        self._page.addLayout(self._than)
        self._page.addStretch(1)

    def _hang_che_do(self) -> QHBoxLayout:
        """Hai nút chọn chế độ. Đổi chế độ thì vẽ lại ĐÚNG thẻ hiện tại, không
        nhảy sang từ khác và không đụng tới tiến độ."""
        hang = QHBoxLayout()
        hang.setSpacing(8)
        self._nut_che_do = []
        for i, ten in enumerate(CHE_DO):
            nut = QPushButton(ten)
            nut.setCheckable(True)
            nut.setChecked(i == self._che_do)
            nut.setFont(ui_font(13))
            nut.setMinimumSize(120, 30)
            nut.setCursor(Qt.CursorShape.PointingHandCursor)
            nut.setStyleSheet(
                f"QPushButton {{ color: {PALETTE['ink2']}; background: {PALETTE['card']};"
                f" border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
                f"QPushButton:checked {{ color: {PALETTE['accent']};"
                f" border: 1px solid {PALETTE['accent']}; }}"
            )
            nut.clicked.connect(lambda _=False, k=i: self._doi_che_do(k))
            self._nut_che_do.append(nut)
            hang.addWidget(nut)
        hang.addStretch(1)
        return hang

    def _doi_che_do(self, k: int) -> None:
        self._che_do = k
        for i, nut in enumerate(self._nut_che_do):
            nut.setChecked(i == k)
        self._ve()

    # ------------------------------------------------------------- vòng đời
    def showEvent(self, event) -> None:  # noqa: N802 (tên do Qt quy định)
        """Mỗi lần màn hình hiện ra là một phiên ôn mới, lấy lại danh sách."""
        super().showEvent(event)
        self.reload()

    def reload(self) -> None:
        self._due = self._user.due_words(date.today())
        self._vi_tri = 0
        self._da_on = 0
        # Phiên mới thì lịch sử hoàn tác của phiên cũ hết nghĩa: vị trí trong
        # danh sách đã khác, mà hoàn tác lại lùi đúng theo vị trí đó.
        self._lich_su.clear()
        self._ve()

    # ------------------------------------------------------------------ vẽ
    def _ve(self) -> None:
        _clear(self._than)
        _clear(self._o_hoan_tac)

        # Dựng CÓ ĐIỀU KIỆN chứ không dựng sẵn rồi setVisible(True): widget chưa
        # có cha mà gọi setVisible(True) sẽ thành cửa sổ cấp cao nhất và Windows
        # cấp cho nó một HWND thật, gây chớp một cửa sổ rồi tắt.
        if self._lich_su:
            self._o_hoan_tac.addWidget(self._nut_hoan_tac())

        if not self._due:
            self._dong_tom_luoc.setText("KHÔNG CÓ THẺ NÀO TRONG PHIÊN NÀY")
            self._than.addWidget(self._the_rong())
            return

        if self._vi_tri >= len(self._due):
            self._dong_tom_luoc.setText("XONG PHIÊN HÔM NAY")
            self._than.addWidget(self._the_tong_ket())
            return

        con_lai = len(self._due) - self._vi_tri
        self._dong_tom_luoc.setText(
            f"THẺ {self._vi_tri + 1} / {len(self._due)} · CÒN {con_lai} TỪ TỚI HẠN HÔM NAY"
        )
        word = self._due[self._vi_tri]
        # Gọi detail() và tree() đúng lúc dựng thẻ này, không gọi trước cho cả
        # danh sách tới hạn.
        detail = self._lookup.detail(word)

        the = self._bai_tap(word, detail) if self._che_do == 1 else None
        if the is None:
            the = ReviewCard(word, detail, self._decomposer)
            the.graded.connect(self._cham)
            if self._che_do == 1:
                self._than.addWidget(
                    _label(
                        "Từ này chưa đủ dữ liệu cho bài tập, tạm dùng thẻ lật.",
                        mono_font(11),
                        PALETTE["muted"],
                    )
                )
        else:
            the.answered.connect(self._cham)
        self._than.addWidget(the)

    # --------------------------------------------------------- dựng bài tập
    def _bai_tap(self, word: str, detail):
        """Một câu bài tập cho từ này, hoặc None nếu không đủ dữ liệu.

        Chọn ngẫu nhiên giữa bốn nguồn câu hỏi trong số những nguồn dùng được.
        Kiểu chọn âm Hán-Việt chỉ chạy với chữ có cột hanviet (958 chữ).
        Kiểu ghép bộ thủ chỉ chạy khi cây chiết tự có ít nhất 2 con trực tiếp.
        """
        cach = [self._hoi_nghia, self._hoi_hanviet,
                self._hoi_pinyin, self._hoi_ghep_bo_thu]
        random.shuffle(cach)
        for lam in cach:
            bai = lam(word, detail)
            if bai is not None:
                return bai
        return None

    def _hoi_nghia(self, word: str, detail):
        w = detail.word
        dap_an = (w.meaning_vi or w.meaning_en) if w is not None else None
        if not dap_an:
            return None
        cap = w.hsk_level
        nhieu = self._boc_nhieu(
            [m for _, m in self._dict.candidate_meanings(word, cap, 40)], dap_an
        )
        if len(nhieu) < SO_NHIEU and cap is not None:
            nhieu = self._boc_nhieu(
                [m for _, m in self._dict.candidate_meanings(word, None, 60)], dap_an
            )
        if len(nhieu) < SO_NHIEU:
            return None
        return ChonMotDap(word, word, dap_an, nhieu, "Chọn nghĩa đúng", han=True)

    def _hoi_hanviet(self, word: str, detail):
        co = [c for c in detail.chars if c.hanviet]
        if not co:
            return None
        ch = co[0]
        nhieu = self._boc_nhieu(
            [h for _, h in self._dict.candidate_hanviet(ch.char, 60)], ch.hanviet
        )
        if len(nhieu) < SO_NHIEU:
            return None
        return ChonMotDap(
            word, ch.char, ch.hanviet, nhieu, "Chọn âm Hán-Việt đúng", han=True
        )

    def _hoi_pinyin(self, word: str, detail):
        """Bài tập gõ pinyin. Chạy được với mọi từ có pinyin_tone.

        Không cần dict_db: dữ liệu đã có sẵn trong detail.word.
        """
        w = detail.word
        if w is None or not w.pinyin_tone:
            return None
        return GoPinyin(word, w.pinyin_tone)

    def _hoi_ghep_bo_thu(self, word: str, detail):
        """Bài tập ghép bộ thủ. Lấy chữ đầu tiên của từ, dùng con trực tiếp
        của cây chiết tự làm đáp án đúng, lấy glyph bộ Khang Hy làm mảnh nhiễu.

        Mỗi mảnh truyền vào GhepBoThu dưới dạng tuple (glyph, name_hv, meaning_vi)
        để widget hiển thị đủ thông tin giúp người học nhận ra bộ thủ.

        Điều kiện chạy được:
        - Decomposer tồn tại (luôn tồn tại khi màn hình Ôn tập chạy).
        - Chữ có ít nhất 2 con trực tiếp trong cây chiết tự.
        - dict_db tồn tại để lấy danh sách bộ thủ và tra cứu thông tin.
        """
        if self._dict is None or self._decomposer is None:
            return None
        char = word[0] if word else None
        if not char:
            return None
        node = self._decomposer.tree(char)
        dung_glyphs = [
            c.char for c in node.children
            if not c.is_group and len(c.char) == 1
        ]
        if len(dung_glyphs) < 2:
            return None

        # Bảng tra cứu thông tin bộ Khang Hy theo glyph.
        radical_info: dict[str, tuple] = {}
        tat_ca_bo = self._dict.all_radicals()
        for r in tat_ca_bo:
            if r.glyph:
                radical_info[r.glyph] = (r.name_hv, r.meaning_vi)
            if r.glyph_alt:
                radical_info[r.glyph_alt] = (r.name_hv, r.meaning_vi)

        # Mảnh đúng: glyph + thông tin bộ thủ nếu có. Nếu không có trong 214 bộ, tra từ char.
        dung_set = set(dung_glyphs)
        dung = []
        for g in dung_glyphs:
            if g in radical_info:
                dung.append((g, *radical_info[g]))
            else:
                c_info = self._dict.get_char(g)
                if c_info:
                    dung.append((g, c_info.hanviet, c_info.meaning_vi))
                else:
                    dung.append((g, None, None))

        # Mảnh nhiễu: lấy từ 214 bộ, loại bộ đã là thành phần đúng.
        nhieu_ung_vien = [
            (r.glyph, r.name_hv, r.meaning_vi)
            for r in tat_ca_bo
            if r.glyph and r.glyph not in dung_set
        ]
        random.shuffle(nhieu_ung_vien)
        so_nhieu = max(GhepBoThu._TONG_MANH - len(dung), 2)
        nhieu = nhieu_ung_vien[:so_nhieu]
        if len(nhieu) < 2:
            return None
        return GhepBoThu(word, char, dung, nhieu)

    @staticmethod
    def _boc_nhieu(ro: list[str], dap_an: str) -> list[str]:
        """Bốc ngẫu nhiên 3 đáp án nhiễu, loại mọi cái TRÙNG với đáp án đúng.

        Từ đồng nghĩa có thật trong dữ liệu, mà một câu hỏi có hai đáp án đúng
        thì không chấm được. So sánh sau khi bỏ khoảng trắng thừa và hạ chữ
        thường, vì "Bắc Kinh" và "bắc kinh" là một.
        """
        chuan = dap_an.strip().lower()
        khac = {r.strip() for r in ro if r and r.strip().lower() != chuan}
        khac = list(khac)
        random.shuffle(khac)
        return khac[:SO_NHIEU]

    def _nut_hoan_tac(self) -> QPushButton:
        nut = QPushButton("Hoàn tác")
        nut.setFont(ui_font(13))
        nut.setMinimumSize(104, 30)
        nut.setCursor(Qt.CursorShape.PointingHandCursor)
        nut.setStyleSheet(
            f"QPushButton {{ color: {PALETTE['ink2']}; background: {PALETTE['card']};"
            f" border: 1px solid {PALETTE['line']}; border-radius: 4px; }}"
            f"QPushButton:hover {{ color: {PALETTE['accent']};"
            f" border: 1px solid {PALETTE['accent']}; }}"
        )
        nut.clicked.connect(self._hoan_tac)
        return nut

    def _the_rong(self) -> QFrame:
        """Trạng thái rỗng của QT-04: nói rõ vì sao rỗng, không để trắng màn hình."""
        card, layout = self._khung()

        glyph = _label("复", han_font(52), PALETTE["line"])
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(glyph)

        tieu_de = _label(
            "Hôm nay không có từ nào tới hạn ôn", ui_font(16, bold=True), PALETTE["ink"]
        )
        tieu_de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tieu_de)

        theo_doi, da_thuoc = self._user.progress_counts()
        if theo_doi:
            dong = (
                f"Đang theo dõi {theo_doi} từ, đã thuộc {da_thuoc}. "
                "Quay lại vào ngày tới hạn kế tiếp."
            )
        else:
            dong = (
                "Chưa theo dõi từ nào. Sang màn hình Tra cứu, tìm một từ rồi bấm "
                "“Thêm vào ôn tập”."
            )
        ghi_chu = _label(dong, ui_font(14), PALETTE["muted"], wrap=True)
        ghi_chu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ghi_chu)
        return card

    def _the_tong_ket(self) -> QFrame:
        card, layout = self._khung()

        glyph = _label("好", han_font(52), PALETTE["accent"])
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(glyph)

        tieu_de = _label(
            f"Xong. Đã ôn {self._da_on} từ trong phiên này",
            ui_font(16, bold=True),
            PALETTE["ink"],
        )
        tieu_de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tieu_de)

        theo_doi, da_thuoc = self._user.progress_counts()
        ghi_chu = _label(
            f"Đang theo dõi {theo_doi} từ, đã thuộc {da_thuoc}.",
            ui_font(14),
            PALETTE["muted"],
            wrap=True,
        )
        ghi_chu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ghi_chu)
        return card

    def _khung(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 40, 28, 40)
        layout.setSpacing(10)
        return card, layout

    # ------------------------------------------------------- một lần chấm
    def _cham(self, grade: int) -> None:
        """QT-04 bước 5: tính lịch mới, ghi tiến độ, ghi nhật ký, sang thẻ sau.

        Bốn lệnh dưới đây theo đúng thứ tự của đặc tả. ``before`` phải đọc từ
        cơ sở dữ liệu chứ không dựng lại từ thẻ, vì scheduler cần ease và bậc
        lặp hiện hành.
        """
        word = self._due[self._vi_tri]
        today = date.today()

        before = self._user.get_progress(word)
        # Đẩy vào ngăn xếp SAU khi đọc before và TRƯỚC khi ghi đè: đây là bản
        # trạng thái duy nhất còn nguyên vẹn, ghi xong là mất.
        self._lich_su.append((word, before))

        after = self._scheduler.apply_review(before, grade, today)
        self._user.upsert_progress(word, after, None)
        self._user.log_review(
            word, grade, self._scheduler.GRADE_TO_Q[grade], before, after
        )

        self._da_on += 1
        self._vi_tri += 1
        self.progress_changed.emit()
        self._ve()

    def _hoan_tac(self) -> None:
        """Gỡ lần chấm gần nhất: khôi phục progress, xoá dòng nhật ký, lùi một thẻ.

        Chạy được cả khi đang ở thẻ tổng kết, vì đó chính là lúc người ta nhận
        ra vừa bấm nhầm thẻ cuối.

        Toàn bộ phần cơ sở dữ liệu nằm trong ``UserDb.undo_review``, một giao
        dịch duy nhất. Màn hình chỉ đưa lại cặp (word, before) mà nó đã giữ.
        """
        if not self._lich_su:
            return
        word, before = self._lich_su.pop()
        self._user.undo_review(word, before)
        self._vi_tri = max(self._vi_tri - 1, 0)
        self._da_on = max(self._da_on - 1, 0)
        self.progress_changed.emit()
        self._ve()
