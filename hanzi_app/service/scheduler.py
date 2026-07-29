"""Lịch ôn tập SM-2 theo mục 13.12 và QT-04 của đặc tả.

Module thuần tuý: không chạm cơ sở dữ liệu, không chạm mạng, không chạm Qt và
không chạm đồng hồ hệ thống. Ngày hôm nay luôn được truyền vào qua tham số
``today``.
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from hanzi_app.data.models import ReviewOutcome

# Ba nút trên thẻ ôn tập ánh xạ sang thang chất lượng q của SM-2 (QT-04 bước 5).
GRADE_TO_Q = {0: 2, 1: 3, 2: 5}   # Quên, Khó, Nhớ

EASE_MIN = 1.3
KHO_FACTOR = 1.2
KNOWN_INTERVAL = 21


def _round_half_up(value: float) -> int:
    """Làm tròn nửa LÊN. Hàm round dựng sẵn làm tròn nửa về số chẵn nên
    round(2.5) trả về 2, sai với đặc tả."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def initial(today: date) -> ReviewOutcome:
    """Bản ghi tiến độ lúc mới thêm từ vào danh sách ôn tập (QT-04 bước 2)."""
    return ReviewOutcome(
        ease=2.5,
        interval_days=0,
        repetition=0,
        lapse_count=0,
        status="new",
        due_date=today,
    )


def apply_review(before: ReviewOutcome, grade: int, today: date) -> ReviewOutcome:
    """Áp một lần tự đánh giá lên bản ghi tiến độ, trả về bản ghi mới."""
    q = GRADE_TO_Q[grade]

    # Cập nhật hệ số dễ TRƯỚC, các bậc lặp bên dưới dùng ease MỚI.
    ease = before.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease = max(EASE_MIN, ease)

    repetition = before.repetition
    lapse_count = before.lapse_count

    if q == 2:                       # Quên
        repetition = 0
        interval_days = 1
        lapse_count += 1
    elif q == 3:                     # Khó, giữ nguyên bậc lặp
        interval_days = _round_half_up(before.interval_days * KHO_FACTOR)
    else:                            # Nhớ, lên bậc theo SM-2
        repetition += 1
        if repetition == 1:
            interval_days = 1
        elif repetition == 2:
            interval_days = 6
        else:
            interval_days = _round_half_up(before.interval_days * ease)

    interval_days = max(1, interval_days)

    # QT-04 bước 6.
    status = "learning" if before.status == "new" else before.status
    if q == 2:
        status = "learning"
    elif interval_days >= KNOWN_INTERVAL:
        status = "known"

    return replace(
        before,
        ease=ease,
        interval_days=interval_days,
        repetition=repetition,
        lapse_count=lapse_count,
        status=status,
        due_date=today + timedelta(days=interval_days),
    )
