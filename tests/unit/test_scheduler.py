"""Kiểm thử module service/scheduler.py theo bảng đáp án ở mục 14.5 của đặc tả."""

from datetime import date

import pytest

from hanzi_app.service.scheduler import (
    GRADE_TO_Q,
    ReviewOutcome,
    apply_review,
    initial,
)

QUEN, KHO, NHO = 0, 1, 2

TODAY = date(2026, 1, 1)


# ------------------------------------------------------------------- initial
def test_initial_theo_qt04_buoc_2():
    out = initial(TODAY)
    assert out.ease == pytest.approx(2.5, abs=1e-9)
    assert out.interval_days == 0
    assert out.repetition == 0
    assert out.lapse_count == 0
    assert out.status == "new"
    assert out.due_date == TODAY


def test_anh_xa_ba_nut_sang_q():
    assert GRADE_TO_Q == {0: 2, 1: 3, 2: 5}


# ----------------------------------------------- bảng 14.5: chuỗi 8 lần đánh giá
# (lần, nút, ease sau, repetition, interval, status)
CHUOI_14_5 = [
    (1, NHO, 2.60, 1, 1, "learning"),
    (2, NHO, 2.70, 2, 6, "learning"),
    (3, NHO, 2.80, 3, 17, "learning"),
    (4, NHO, 2.90, 4, 49, "known"),
    (5, KHO, 2.76, 4, 59, "known"),
    (6, QUEN, 2.44, 0, 1, "learning"),
    (7, NHO, 2.54, 1, 1, "learning"),
    (8, NHO, 2.64, 2, 6, "learning"),
]


def test_chuoi_danh_gia_lien_tiep():
    """Chạy liền tám lần đánh giá trên cùng một từ, đối chiếu từng dòng."""
    current = initial(TODAY)
    lapse_mong_doi = 0

    for lan, nut, ease, repetition, interval, status in CHUOI_14_5:
        current = apply_review(current, nut, TODAY)
        if nut == QUEN:
            lapse_mong_doi += 1

        assert current.ease == pytest.approx(ease, abs=1e-9), f"lần {lan}: ease"
        assert current.repetition == repetition, f"lần {lan}: repetition"
        assert current.interval_days == interval, f"lần {lan}: interval"
        assert current.status == status, f"lần {lan}: status"
        assert current.lapse_count == lapse_mong_doi, f"lần {lan}: lapse_count"


@pytest.mark.parametrize(
    "lan, nut, ease, repetition, interval, status", CHUOI_14_5
)
def test_tung_dong_cua_bang_14_5(lan, nut, ease, repetition, interval, status):
    """Cùng chuỗi trên nhưng tách từng dòng, để báo lỗi chỉ đúng dòng sai."""
    current = initial(TODAY)
    for _, nut_truoc, *_ in CHUOI_14_5[: lan - 1]:
        current = apply_review(current, nut_truoc, TODAY)

    current = apply_review(current, nut, TODAY)
    assert current.ease == pytest.approx(ease, abs=1e-9)
    assert current.repetition == repetition
    assert current.interval_days == interval
    assert current.status == status


def test_lan_3_dung_ease_moi_khong_dung_ease_cu():
    """6 × 2.80 = 16.8 -> 17. Nếu dùng ease cũ 2.70 thì ra 16, tức là sai."""
    current = initial(TODAY)
    for nut in (NHO, NHO):
        current = apply_review(current, nut, TODAY)
    assert current.ease == pytest.approx(2.70, abs=1e-9)

    current = apply_review(current, NHO, TODAY)
    assert current.interval_days == 17


# --------------------------------------------------------------- bốn ca biên
def test_ca_bien_chan_duoi_he_so_de():
    """ease 1.40 bấm Quên: 1.40 − 0.32 = 1.08, phải bị chặn ở 1.30."""
    before = ReviewOutcome(
        ease=1.40,
        interval_days=10,
        repetition=3,
        lapse_count=0,
        status="learning",
        due_date=TODAY,
    )
    out = apply_review(before, QUEN, TODAY)
    assert out.ease == pytest.approx(1.30, abs=1e-9)
    assert out.repetition == 0
    assert out.interval_days == 1
    assert out.lapse_count == 1


def test_ca_bien_lam_tron_nua_len():
    """interval 2, ease 1.75, bấm Nhớ ở bậc 3 -> interval 4, không phải 3."""
    before = ReviewOutcome(
        ease=1.75,
        interval_days=2,
        repetition=2,
        lapse_count=0,
        status="learning",
        due_date=TODAY,
    )
    out = apply_review(before, NHO, TODAY)
    assert out.repetition == 3
    assert out.ease == pytest.approx(1.85, abs=1e-9)
    assert out.interval_days == 4


def test_lam_tron_nua_len_khong_phai_ve_so_chan():
    """1 × 2.5 = 2.5. round dựng sẵn trả về 2, làm tròn nửa lên phải ra 3."""
    before = ReviewOutcome(
        ease=2.40,
        interval_days=1,
        repetition=4,
        lapse_count=0,
        status="learning",
        due_date=TODAY,
    )
    out = apply_review(before, NHO, TODAY)
    assert out.ease == pytest.approx(2.50, abs=1e-9)
    assert out.interval_days == 3


def test_ca_bien_ngay_den_han():
    """today 2026-07-27 với interval 6 -> due_date 2026-08-02, qua tháng."""
    hom_nay = date(2026, 7, 27)
    before = ReviewOutcome(
        ease=2.50,
        interval_days=1,
        repetition=1,
        lapse_count=0,
        status="learning",
        due_date=hom_nay,
    )
    out = apply_review(before, NHO, hom_nay)
    assert out.interval_days == 6
    assert out.due_date == date(2026, 8, 2)


def test_ca_bien_khoang_toi_thieu():
    """interval 0 bấm Khó: 0 × 1.2 = 0, phải nâng lên 1."""
    before = ReviewOutcome(
        ease=2.50,
        interval_days=0,
        repetition=0,
        lapse_count=0,
        status="new",
        due_date=TODAY,
    )
    out = apply_review(before, KHO, TODAY)
    assert out.interval_days == 1
    assert out.due_date == TODAY.replace(day=2)


# ------------------------------------------------- QT-04 bước 6: chuyển trạng thái
def test_new_sang_learning_ngay_lan_on_dau_tien():
    out = apply_review(initial(TODAY), KHO, TODAY)
    assert out.status == "learning"


def test_learning_sang_known_khi_interval_tu_21():
    before = ReviewOutcome(
        ease=2.50,
        interval_days=20,
        repetition=3,
        lapse_count=0,
        status="learning",
        due_date=TODAY,
    )
    out = apply_review(before, KHO, TODAY)
    assert out.interval_days == 24
    assert out.status == "known"


def test_known_tro_ve_learning_khi_bam_quen():
    before = ReviewOutcome(
        ease=2.50,
        interval_days=40,
        repetition=5,
        lapse_count=2,
        status="known",
        due_date=TODAY,
    )
    out = apply_review(before, QUEN, TODAY)
    assert out.status == "learning"
    assert out.lapse_count == 3


def test_known_giu_nguyen_khi_khong_bam_quen():
    before = ReviewOutcome(
        ease=2.50,
        interval_days=30,
        repetition=5,
        lapse_count=0,
        status="known",
        due_date=TODAY,
    )
    out = apply_review(before, NHO, TODAY)
    assert out.status == "known"


# ------------------------------------------------------------- tính thuần tuý
def test_khong_sua_ban_ghi_dau_vao():
    before = initial(TODAY)
    apply_review(before, NHO, TODAY)
    assert before.ease == pytest.approx(2.5, abs=1e-9)
    assert before.interval_days == 0
    assert before.repetition == 0
    assert before.status == "new"


def test_khong_goi_dong_ho_he_thong():
    """Ngày hôm nay chỉ đến từ tham số today, kể cả khi đó là ngày trong quá khứ."""
    hom_nay = date(1999, 12, 31)
    out = apply_review(initial(hom_nay), NHO, hom_nay)
    assert out.due_date == date(2000, 1, 1)
