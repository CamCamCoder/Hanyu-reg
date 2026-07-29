"""Tiện ích pinyin: chuẩn hoá, tách âm tiết, đổi qua lại giữa dạng số và dạng dấu.

Module thuần tuý, không chạm cơ sở dữ liệu, không chạm mạng, không chạm Qt.
Đặc tả ở mục 13.5, bảng đáp án ở mục 14.2.
"""

import re
import unicodedata

# Bốn dấu thanh dưới dạng ký tự kết hợp. Dấu tách âm U+0308 (¨ của ü) KHÔNG nằm
# trong tập này: xoá nó thì 'nǚ' ra 'nu' thay vì 'nv' và mọi tra cứu âm có ü hỏng.
_TONE_MARKS = {
    0x0304: 1,  # ngang
    0x0301: 2,  # sắc
    0x030C: 3,  # hỏi
    0x0300: 4,  # huyền
}

# Nguyên âm mang dấu, xếp theo thanh 1..4, phần tử thứ năm là dạng không dấu.
_MARKED = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "v": "ǖǘǚǜü",
}

# Bảng âm tiết pinyin chuẩn, xếp theo phụ âm đầu. ü viết là v cho khớp dạng phẳng.
_SYLLABLE_TABLE = """
a ai an ang ao e ei en eng er o ou
ya yan yang yao ye yi yin ying yo yong you yu yuan yue yun
wa wai wan wang wei wen weng wo wu
ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu
pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu
ma mai man mang mao me mei men meng mi mian miao mie min ming miu mo mou mu
fa fan fang fei fen feng fo fou fu
da dai dan dang dao de dei den deng di dia dian diao die ding diu dong dou
du duan dui dun duo
ta tai tan tang tao te tei teng ti tian tiao tie ting tong tou tu tuan tui
tun tuo
na nai nan nang nao ne nei nen neng ni nian niang niao nie nin ning niu nong
nou nu nuan nuo nv nve
la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu long
lou lu luan lun luo lv lve
ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo
ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo
ha hai han hang hao he hei hen heng hong hou hu hua huai huan huang hui hun huo
ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun
qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun
xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun
zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai
zhuan zhuang zhui zhun zhuo
cha chai chan chang chao che chen cheng chi chong chou chu chua chuai chuan
chuang chui chun chuo
sha shai shan shang shao she shei shen sheng shi shou shu shua shuai shuan
shuang shui shun shuo
ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo
za zai zan zang zao ze zei zen zeng zi zong zou zu zuan zui zun zuo
ca cai can cang cao ce cen ceng ci cong cou cu cuan cui cun cuo
sa sai san sang sao se sen seng si song sou su suan sui sun suo
"""

_SYLLABLES = frozenset(_SYLLABLE_TABLE.split())
_MAX_SYLLABLE_LEN = max(len(s) for s in _SYLLABLES)

# Một âm tiết dạng số: các chữ cái rồi tới số thanh, số thanh có thể vắng.
_NUMBERED = re.compile(r"[a-z]+[0-5]?")


def to_plain(s: str) -> str:
    """'rènshi' -> 'renshi'; 'nǚ' -> 'nv'.

    Bỏ dấu thanh, bỏ khoảng trắng và dấu nháy; ü, u: và v đều quy về 'v'.
    Trình tự bắt buộc: NFD, lọc bỏ đúng bốn dấu thanh, NFC lại, rồi mới đổi ü.
    """
    decomposed = unicodedata.normalize("NFD", s)
    without_tone = "".join(c for c in decomposed if ord(c) not in _TONE_MARKS)
    recomposed = unicodedata.normalize("NFC", without_tone).lower()
    return (
        recomposed.replace("u:", "v")
        .replace("ü", "v")
        .replace("'", "")
        .replace("’", "")
        .replace(" ", "")
    )


def num_to_tone(s: str) -> str:
    """'ren4 shi5' -> 'rènshi'; 'nu:3' -> 'nǚ'. Thanh 5 và thanh 0 không đánh dấu."""
    text = s.lower().replace("u:", "v")
    return "".join(_syllable_to_tone(m.group()) for m in _NUMBERED.finditer(text))


def tone_to_num(s: str) -> str:
    """'rènshi' -> 'ren4shi5'. Dạng ra là chuỗi liền, khinh thanh ghi số 5."""
    letters: list[str] = []
    tones: list[int] = []
    for ch in unicodedata.normalize("NFC", s.lower()):
        base, tone = _strip_tone(ch)
        if not base.isalpha():
            continue
        letters.append(base)
        tones.append(tone)

    plain = "".join(letters)
    syllables = _walk(plain, 0, None) or [plain]

    parts = []
    pos = 0
    for syllable in syllables:
        tone = next((t for t in tones[pos:pos + len(syllable)] if t != 5), 5)
        parts.append(f"{syllable}{tone}")
        pos += len(syllable)
    return "".join(parts)


def split_syllables(s: str, expect: int | None = None) -> list[str] | None:
    """Tách chuỗi pinyin liền thành các âm tiết.

    expect là số âm tiết mong đợi, thường là số chữ Hán của từ. Truyền expect
    vào thì chỉ trả về cách tách có đúng số âm tiết đó, nhờ vậy các ca nhập
    nhằng như 'xian' tự được giải quyết. Không có cách tách hợp lệ thì trả None.
    """
    return _walk(to_plain(s), 0, expect)


def query_variants(q: str) -> list[str]:
    """Sinh các biến thể của chuỗi người dùng gõ, phục vụ FR-03.

    'lu' -> ['lu', 'lv'] vì người Việt quen gõ u thay cho ü.
    """
    base = to_plain(q)
    variants = [base]
    swapped = re.sub(r"([ln])u", r"\1v", base)
    if swapped != base:
        variants.append(swapped)
    return variants


# --------------------------------------------------------------- phần nội bộ
def _syllable_to_tone(syllable: str) -> str:
    """'chang2' -> 'cháng'; 'shi5' -> 'shi'."""
    if syllable[-1].isdigit():
        body, tone = syllable[:-1], int(syllable[-1])
    else:
        body, tone = syllable, 5
    if tone in (0, 5):
        return body.replace("v", "ü")

    # a và e luôn nhận dấu; trong 'ou' thì o nhận; còn lại nguyên âm cuối nhận.
    if "a" in body:
        i = body.index("a")
    elif "e" in body:
        i = body.index("e")
    elif "ou" in body:
        i = body.index("o")
    else:
        i = max((body.rfind(v) for v in "aeiouv"), default=-1)
        if i < 0:
            return body.replace("v", "ü")
    marked = body[:i] + _MARKED[body[i]][tone - 1] + body[i + 1:]
    return marked.replace("v", "ü")


def _strip_tone(ch: str) -> tuple[str, int]:
    """Tách một ký tự thành phần chữ và số thanh; 'ǚ' -> ('v', 3)."""
    tone = 5
    base = ""
    for c in unicodedata.normalize("NFD", ch):
        if ord(c) in _TONE_MARKS:
            tone = _TONE_MARKS[ord(c)]
        else:
            base += c
    return unicodedata.normalize("NFC", base).replace("ü", "v"), tone


def _walk(plain: str, pos: int, remaining: int | None) -> list[str] | None:
    """Tìm cách tách plain[pos:] thành đúng remaining âm tiết, None là không ràng buộc.

    Thử âm tiết dài trước để cách tách ít mảnh nhất được ưu tiên khi không có
    ràng buộc; quay lui khi phần đuôi không tách được.
    """
    if pos == len(plain):
        return [] if remaining in (None, 0) else None
    if remaining == 0:
        return None
    longest = min(len(plain), pos + _MAX_SYLLABLE_LEN)
    for end in range(longest, pos, -1):
        head = plain[pos:end]
        if head not in _SYLLABLES:
            continue
        tail = _walk(plain, end, None if remaining is None else remaining - 1)
        if tail is not None:
            return [head] + tail
    return None
