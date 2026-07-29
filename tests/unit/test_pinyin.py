"""Kiểm thử module service/pinyin.py theo đúng bảng đáp án ở mục 14.2 của đặc tả."""

import sys
from pathlib import Path

import pytest

# Kho chưa có tệp cấu hình gói, thêm thư mục gốc vào sys.path để import được
# hanzi_app.service.pinyin khi chạy pytest từ thư mục dự án.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hanzi_app.service.pinyin import (  # noqa: E402
    num_to_tone,
    query_variants,
    split_syllables,
    to_plain,
    tone_to_num,
)


# --------------------------------------------------------- bảng 1: num_to_tone
# Quy tắc đặt dấu: a và e luôn nhận dấu; trong 'ou' thì o nhận; còn lại nguyên
# âm cuối nhận. Thanh 5 và thanh 0 không đánh dấu.
NUM_TO_TONE_CASES = [
    ("ren4 shi5", "rènshi"),    # thanh nhẹ không dấu
    ("hao3", "hǎo"),            # a ưu tiên
    ("gou3", "gǒu"),            # ngoại lệ ou
    ("liu2", "liú"),            # nguyên âm cuối
    ("nu:3", "nǚ"),             # quy ước 'u:' của CC-CEDICT
    ("er2", "ér"),              # một nguyên âm
    ("peng2 you5", "péngyou"),  # ghép hai âm tiết
]


@pytest.mark.parametrize("source, expected", NUM_TO_TONE_CASES)
def test_num_to_tone(source, expected):
    assert num_to_tone(source) == expected


# ------------------------------------------------------------ bảng 2: to_plain
TO_PLAIN_CASES = [
    ("rènshi", "renshi"),
    ("nǚ", "nv"),
    ("lǜ", "lv"),
    ("xi'an", "xian"),
]


@pytest.mark.parametrize("source, expected", TO_PLAIN_CASES)
def test_to_plain(source, expected):
    assert to_plain(source) == expected


# ------------------------------------------------------ bảng 3: split_syllables
SPLIT_CASES = [
    ("renshi", 2, ["ren", "shi"]),
    ("xian", 1, ["xian"]),
    ("xian", 2, ["xi", "an"]),
    ("xian", 3, None),
    ("zhongguo", 2, ["zhong", "guo"]),
    ("qwerty", 2, None),
]


@pytest.mark.parametrize("source, expect, expected", SPLIT_CASES)
def test_split_syllables(source, expect, expected):
    assert split_syllables(source, expect) == expected


# --------------------------------------------------------------- tone_to_num
# Đặc tả chỉ cho chữ ký, không cho bảng đáp án, nên kiểm bằng vòng khứ hồi với
# bảng 1: đưa về dạng số rồi đưa lại dạng dấu phải ra đúng chuỗi ban đầu.
@pytest.mark.parametrize("source, toned", NUM_TO_TONE_CASES)
def test_tone_to_num_round_trip(source, toned):
    assert num_to_tone(tone_to_num(toned)) == toned


def test_tone_to_num_format():
    """Dạng ra là chuỗi liền, giữ số thanh của khinh thanh, như cột
    word.pinyin_numeric ở mục 12 ('ren4shi5')."""
    assert tone_to_num("rènshi") == "ren4shi5"
    assert tone_to_num("nǚ") == "nv3"


# -------------------------------------------------------------- query_variants
def test_query_variants_u_thanh_v():
    """Người Việt quen gõ u thay cho ü, xem mục 13.5."""
    assert query_variants("lu") == ["lu", "lv"]


def test_query_variants_khong_nhap_nhang():
    assert query_variants("renshi") == ["renshi"]
