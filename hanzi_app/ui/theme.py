"""Bảng màu mục 6.1 và phông mục 6.2, dùng chung cho cả tầng ui.

Hai khối này nằm trong ``ui/widgets/tianzige.py`` từ phiên 05, vì phiên đó chỉ
được tạo sáu tệp. Từ phiên 07 có ba màn hình cùng dùng bảng màu, mà bắt một màn
hình import màu từ một module widget là sai thứ bậc, nên tách ra đây. Nội dung
chuyển nguyên văn: không đổi giá trị màu, không đổi tên khoá, không đổi cỡ chữ.

Module này là gốc của tầng ui, không import bất cứ module ui nào khác, nên nó
không thể sinh vòng import.
"""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics

# --------------------------------------------------------------- mục 6.1, màu
PALETTE = {
    "bg": "#F5F4F0",            # nền ứng dụng
    "card": "#FFFFFF",          # nền thẻ, nền ô 田字格
    "ink": "#1B1A18",           # chữ chính
    "ink2": "#605D57",          # chữ phụ
    "muted": "#716D66",         # chữ mờ, trạng thái rỗng
    "line": "#E1DED6",          # đường kẻ, viền thẻ
    "accent": "#A83A2C",        # nhấn chính
    "accent_hover": "#933327",  # nhấn chính khi rê
    "accent2": "#3F7A68",       # nhấn phụ
    "accent2_bg": "#F2F8F6",    # nền nhấn phụ
    "accent2_line": "#BFD6CE",  # viền nhấn phụ
    "warn": "#9C7318",          # cảnh báo
    "warn_bg": "#FBF7EC",       # nền cảnh báo
    "warn_ink": "#6B5310",      # chữ trên nền cảnh báo
}

# --------------------------------------------------------------- mục 6.2, chữ
# Ba phông của đặc tả phải được đóng gói kèm sản phẩm và nạp bằng QFontDatabase.
# Đường dẫn phải trỏ tới đúng thư mục cũ: tệp này nằm nông hơn tianzige.py một
# bậc, nên parents[1] ở đây bằng parents[2] ở đó, cùng là hanzi_app/.
FONT_DIR = Path(__file__).resolve().parents[1] / "resources" / "fonts"

REQUESTED = {
    "han": "Noto Serif SC",     # chữ Hán, thể có chân giống giáo trình
    "ui": "IBM Plex Sans",      # tiêu đề và nội dung
    "mono": "IBM Plex Mono",    # pinyin và số liệu
}

# Phông hệ thống dùng tạm khi phông đóng gói chưa có trong kho. Không tự tải về.
SYSTEM_FALLBACK = {
    "han": ("Noto Serif CJK SC", "Source Han Serif SC", "SimSun", "NSimSun",
            "Microsoft YaHei"),
    "ui": ("Segoe UI", "Arial"),
    "mono": ("Consolas", "Courier New"),
}

# Nhóm ký tự thanh ba và ü có dấu mà rất nhiều phông đơn cách bỏ sót. Thiếu một
# ký tự là hệ điều hành thay phông cho riêng ký tự đó, hỏng đúng lý do chọn phông
# đơn cách, nên khi thiếu thì chuyển pinyin sang phông sans.
TONE_THREE = "ǎěǐǒǔǚǜ"

# Tên phông thực sự dùng khi vẽ. load_fonts() cập nhật lại sau khi có QApplication.
FONT = dict(REQUESTED)


def load_fonts() -> list[str]:
    """Nạp phông đóng gói trong resources/fonts và chốt tên phông thực dùng.

    Trả về danh sách dòng cảnh báo; gọi sau khi đã dựng QApplication. Không tự
    tải phông về, cũng không im lặng bỏ qua: mọi thứ thiếu đều thành một dòng
    cảnh báo để bên gọi in ra console.
    """
    warnings: list[str] = []

    files: list[Path] = []
    if FONT_DIR.is_dir():
        for pattern in ("*.ttf", "*.otf", "*.ttc"):
            files += sorted(FONT_DIR.glob(pattern))
    else:
        warnings.append(f"Chua co thu muc phong {FONT_DIR}")

    for path in files:
        if QFontDatabase.addApplicationFont(str(path)) == -1:
            warnings.append(f"Khong nap duoc phong {path.name}")

    available = set(QFontDatabase.families())
    for role, family in REQUESTED.items():
        if family in available:
            continue
        thay_the = next(
            (f for f in SYSTEM_FALLBACK[role] if f in available), None
        )
        FONT[role] = thay_the or FONT[role]
        warnings.append(
            f"Thieu phong dong goi '{family}' ({role}), dung phong he thong "
            f"'{FONT[role]}'"
        )

    # Kiểm tra bao phủ ký tự thanh ba của phông đơn cách, theo mục 6.2.
    metrics = QFontMetrics(QFont(FONT["mono"]))
    thieu = [c for c in TONE_THREE if not metrics.inFont(c)]
    if thieu:
        warnings.append(
            f"Phong don cach '{FONT['mono']}' thieu ky tu thanh ba "
            f"({''.join(thieu)}), chuyen pinyin sang '{FONT['ui']}'"
        )
        FONT["mono"] = FONT["ui"]

    return warnings


def han_font(pixel_size: int) -> QFont:
    """Phông chữ Hán ở một cỡ pixel cho trước."""
    font = QFont(FONT["han"])
    font.setPixelSize(pixel_size)
    return font


def mono_font(pixel_size: int) -> QFont:
    """Phông đơn cách cho pinyin và số liệu."""
    font = QFont(FONT["mono"])
    font.setPixelSize(pixel_size)
    return font


def ui_font(pixel_size: int, bold: bool = False) -> QFont:
    """Phông sans cho tiêu đề và nội dung."""
    font = QFont(FONT["ui"])
    font.setPixelSize(pixel_size)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    return font
