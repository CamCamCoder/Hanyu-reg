#!/usr/bin/env python3
"""
build_dict.py v2 — dựng dict.sqlite từ các nguồn mở.

Khác v1 ở bốn điểm:
  1. char_reading suy ngược từ bảng từ HSK bằng cách gióng âm tiết với chữ.
     makemeahanzi chỉ có 8 chữ đa âm, khiến 长 mất âm cháng và 和 mất âm huo,
     làm ca kiểm chứng 长大 ở mục 14.6 đỏ oan.
  2. Giải bộ thủ có bước lùi đệ quy: bộ chưa map được thì tra chính ký tự đó như
     một chữ rồi lấy bộ của nó.
  3. to_plain chỉ xoá bốn dấu thanh và GIỮ dấu tách âm U+0308. Bản v1 xoá luôn
     U+0308 nên 'nǚ' ra 'nu' thay vì 'nv', làm hỏng tra cứu mọi âm có ü.
  4. freq_rank sinh từ cấp HSK làm giá trị thay thế, có ghi rõ là ước lượng.
  5. Lược đồ nhúng thẳng trong tệp này, đường dẫn tính theo vị trí tệp, nên chạy
     được trên Windows và không cần schema_dict.sql bên ngoài.

Chạy:  python build_dict.py
Kết quả: dict.sqlite nằm cạnh tệp này. Cần mạng ở lần chạy đầu để tải nguồn về
thư mục src/; các lần sau dùng lại bản đã tải.
"""
import io, json, os, re, sqlite3, sys, unicodedata, urllib.request
from radicals_vi import RADICALS
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCHEMA = r"""
-- Chữ đơn. Nguồn: Unihan, cjkvi-ids, chaizi.
CREATE TABLE char (
    char           TEXT PRIMARY KEY,  -- ký tự, ví dụ '认'
    codepoint      TEXT,              -- 'U+8BA4'
    pinyin         TEXT,              -- 'rèn', có dấu thanh
    pinyin_plain   TEXT,              -- 'ren', đã khử dấu, dùng để tìm kiếm
    meaning_en     TEXT,              -- nghĩa tiếng Anh từ Unihan
    meaning_vi     TEXT,              -- nghĩa tiếng Việt, bổ sung thủ công
    hanviet        TEXT,              -- âm Hán-Việt, ví dụ 'nhận'
    radical_idx    INTEGER,           -- số hiệu bộ thủ, 1..214
    radical_stroke INTEGER,           -- số nét còn lại ngoài bộ
    total_strokes  INTEGER,           -- tổng số nét
    trad_form      TEXT,              -- dạng phồn thể tương ứng, ví dụ '認'
    ids            TEXT,              -- chuỗi IDS, ví dụ '⿰讠人'
    hsk_level      INTEGER,           -- 1..6, NULL nếu ngoài danh sách HSK
    freq_rank      INTEGER            -- thứ hạng tần suất, càng nhỏ càng phổ biến
);

-- Toàn bộ âm đọc của một chữ. Phải là bảng riêng chứ không phải một cột, vì chữ
-- đa âm (了, 和, 长, 行, 得...) có nhiều âm hợp lệ. Quy trình kiểm chứng ở QT-03
-- bước 4 đối chiếu với bảng này chứ không đối chiếu với cột char.pinyin.
CREATE TABLE char_reading (
    char         TEXT NOT NULL,
    pinyin       TEXT NOT NULL,      -- 'rèn', có dấu thanh
    pinyin_plain TEXT NOT NULL,      -- 'ren', đã khử dấu và khử thanh
    is_primary   INTEGER DEFAULT 0,  -- 1 với âm đọc phổ biến nhất
    PRIMARY KEY (char, pinyin)
);

-- Thành phần cấu tạo. Một chữ có thể có nhiều cách chiết tự.
CREATE TABLE char_part (
    char     TEXT NOT NULL,               -- chữ được phân tách
    part     TEXT NOT NULL,               -- một thành phần
    variant  INTEGER NOT NULL DEFAULT 0,  -- 0 là cách chính, 1 trở đi là cách thay thế
    order_no INTEGER NOT NULL,            -- vị trí thành phần theo thứ tự đọc của chuỗi IDS
    PRIMARY KEY (char, variant, order_no)
);

-- Từ ghép. Nguồn: CC-CEDICT, bổ sung nghĩa tiếng Việt và từ loại thủ công.
-- Một dạng chữ có thể ứng với nhiều mục từ khác âm khác nghĩa, nên phải có id
-- riêng, không thể lấy word_simp làm khoá chính.
CREATE TABLE word (
    id             INTEGER PRIMARY KEY,
    word_simp      TEXT NOT NULL,   -- dạng giản thể, ví dụ '认识'
    word_trad      TEXT,            -- dạng phồn thể, ví dụ '認識'
    pinyin_num     TEXT,            -- nguyên bản CC-CEDICT, 'ren4 shi5'
    pinyin_tone    TEXT,            -- dạng có dấu để hiển thị và cho FR-02, 'rènshi'
    pinyin_plain   TEXT,            -- khử dấu, khử khoảng trắng, 'renshi', cho FR-03
    pinyin_numeric TEXT,            -- khử khoảng trắng, giữ số thanh, 'ren4shi5', cho FR-03
    pos            TEXT,            -- từ loại: 名, 动, 形... phục vụ FR-06
    meaning_en     TEXT,            -- các nghĩa nối bằng dấu chấm phẩy
    meaning_vi     TEXT,            -- nghĩa tiếng Việt, phục vụ FR-04 và FR-06
    hsk_level      INTEGER,
    freq_rank      INTEGER          -- thứ hạng tần suất của từ, phục vụ FR-05
);

-- 214 bộ thủ Khang Hy. Nhập thủ công.
CREATE TABLE radical (
    idx        INTEGER PRIMARY KEY,  -- 1..214
    glyph      TEXT,                 -- dạng chuẩn, ví dụ '言'
    glyph_alt  TEXT,                 -- dạng biến thể khi đứng trong chữ, '讠'
    name_hv    TEXT,                 -- tên Hán-Việt, 'ngôn'
    meaning_vi TEXT,                 -- 'lời nói'
    strokes    INTEGER               -- số nét của bộ
);

CREATE INDEX idx_char_pyplain  ON char(pinyin_plain);
CREATE INDEX idx_char_radical  ON char(radical_idx);
CREATE INDEX idx_reading_char  ON char_reading(char);
CREATE INDEX idx_reading_plain ON char_reading(pinyin_plain);
CREATE INDEX idx_part_char     ON char_part(char);
CREATE INDEX idx_part_part     ON char_part(part);
CREATE INDEX idx_word_simp     ON word(word_simp);
CREATE INDEX idx_word_pyplain  ON word(pinyin_plain);
CREATE INDEX idx_word_pynum    ON word(pinyin_numeric);
CREATE INDEX idx_word_freq     ON word(freq_rank);

-- Tìm kiếm theo nghĩa (FR-04) phải dùng chỉ mục toàn văn. Dùng LIKE '%...%' trên
-- vài chục nghìn dòng nghĩa sẽ không giữ được NFR-01 dưới 200 ms.


CREATE VIRTUAL TABLE word_fts USING fts5(
    meaning_vi, meaning_en,
    content = 'word', content_rowid = 'id'
);
"""

RAW = "https://raw.githubusercontent.com"
SRC = {"mmh": f"{RAW}/skishore/makemeahanzi/master/dictionary.txt",
       "gfx": f"{RAW}/skishore/makemeahanzi/master/graphics.txt",
       "ts":  f"{RAW}/BYVoid/OpenCC/master/data/dictionary/TSCharacters.txt"}
HSK = {n: f"{RAW}/glxxyz/hskhsk.com/main/data/lists/"
          f"HSK%20Official%20With%20Definitions%202012%20L{n}.txt" for n in range(1, 7)}
CACHE = str(HERE / "src")
os.makedirs(CACHE, exist_ok=True)

def fetch(name, url):
    p = os.path.join(CACHE, name)
    if not os.path.exists(p):
        urllib.request.urlretrieve(url, p)
    return p

def is_cjk(c):
    return "\u4e00" <= c <= "\u9fff"

# ------------------------------------------------------------------ pinyin
MARKS = {"a": "āáǎàa", "e": "ēéěèe", "i": "īíǐìi",
         "o": "ōóǒòo", "u": "ūúǔùu", "v": "ǖǘǚǜü"}
SYL = re.compile(r"[a-zv]+[0-5]")
TONE_MARKS = {0x0300, 0x0301, 0x0304, 0x030C}   # huyền, sắc, ngang, hỏi

def split_num(s):
    """'chang2qi1' -> ['chang2','qi1'];  'nu:3' -> ['nv3']"""
    return SYL.findall(s.lower().replace("u:", "v").replace(" ", ""))

def num_to_tone(syl):
    """'chang2' -> 'cháng';  'shi5' -> 'shi'"""
    body, tone = syl[:-1], int(syl[-1])
    if tone in (0, 5):
        return body.replace("v", "ü")
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
    return (body[:i] + MARKS[body[i]][tone - 1] + body[i + 1:]).replace("v", "ü")

def to_plain(p):
    """Bỏ dấu thanh, GIỮ dấu tách âm, rồi đổi ü thành v."""
    d = unicodedata.normalize("NFD", p)
    s = unicodedata.normalize("NFC", "".join(c for c in d if ord(c) not in TONE_MARKS))
    return s.lower().replace("ü", "v").replace("'", "").replace(" ", "")

# ------------------------------------------------------------------ bộ thủ
VARIANT = {
    "亻":9,"刂":18,"卩":26,"㔾":26,"廾":55,"彐":58,"彑":58,"忄":61,"扌":64,"攵":66,
    "旡":71,"歺":78,"毋":80,"氵":85,"氺":85,"灬":86,"爫":87,"爻":89,"犭":94,"王":96,
    "玊":96,"疋":103,"癶":105,"罒":122,"罓":122,"网":122,"耂":125,"肀":129,"聿":129,
    "艹":140,"艸":140,"虍":141,"覀":146,"西":146,"辶":162,"辵":162,"阝":170,"青":174,
    "飠":184,"讠":149,"钅":167,"饣":184,"纟":120,"门":169,"马":187,"鸟":196,"鱼":195,
    "贝":154,"见":147,"页":181,"车":159,"风":182,"韦":178,"齿":211,"龙":212,"黾":205,
    "齐":210,"麦":199,"龟":213,"长":168,"飞":183,"糸":120,"礻":113,"衤":145,
    "丬":90,"爿":90,"丷":12,"乚":5,"乛":5,"乙":5,"兀":10,"尣":43,"尢":43,"巛":47,
    "川":47,"幺":52,"广":53,"弋":56,"廴":54,"丿":4,"亠":8,"冫":15,"冖":14,"凵":17,
    "厶":28,"夂":34,"夊":35,"彳":60,"无":71,"歹":78,"母":80,"牜":93,
    # còn sót sau khi ghép tự động, đều là chữ tự trỏ về chính nó
    "巴":49,"巷":49,"巳":49,"巽":49,"民":83,"氓":83,"虎":141,"刁":18,"孑":39,
}

# Khối bộ thủ bổ sung U+2E80..U+2EF3 ghép với khối Khang Hy theo TÊN Unicode.
# NFKC không chuẩn hoá khối này, nên phải ghép bằng tên. Sau khi bỏ hậu tố thứ tự
# (ONE, TWO...), bỏ tiền tố C- và J- (dạng giản thể Trung và dạng Nhật) thì 108
# trên 115 ký tự tự khớp. Bảy ký tự còn lại nằm ở bảng SUPP_MANUAL bên dưới.
_SUF = re.compile(r" (ONE|TWO|THREE|FOUR|FIVE)$")
_SYN = {"PERSON": "MAN", "BOX": "DOWN BOX", "MOTHER": "DO NOT",
        "PAW": "CLAW", "MESH": "NET"}
SUPP_MANUAL = {"⺀": 15, "⺒": 49, "⺓": 52, "⺛": 71, "⺠": 83, "⺷": 123, "⺸": 123}

def build_supplement_map(kx_name):
    out = dict(SUPP_MANUAL)
    for cp in range(0x2E80, 0x2EF4):
        ch = chr(cp)
        if ch in out:
            continue
        try:
            n = unicodedata.name(ch)
        except ValueError:
            continue
        s = _SUF.sub("", n.replace("CJK RADICAL ", "")).replace("SIMPLIFIED ", "")
        s = re.sub(r"^[CJ]-", "", s)
        s = _SYN.get(s, s)
        if s in kx_name:
            out[ch] = kx_name[s]
    return out

def make_resolver(kx_by_glyph, supp, simp_forms, mmh_radical):
    tables = (VARIANT, supp, simp_forms, kx_by_glyph)
    def resolve(glyph, depth=0):
        if not glyph or depth > 4:
            return None
        for g in (glyph, unicodedata.normalize("NFKC", glyph)):
            for t in tables:
                if g in t:
                    return t[g]
        nxt = mmh_radical.get(glyph)
        if nxt and nxt != glyph:
            return resolve(nxt, depth + 1)
        return None
    return resolve

# ------------------------------------------------------------------ main
def main():
    paths = {k: fetch(k + ".txt", u) for k, u in SRC.items()}
    hskp = {n: fetch(f"hsk{n}.txt", u) for n, u in HSK.items()}

    kx = {i + 1: unicodedata.normalize("NFKC", chr(0x2F00 + i)) for i in range(214)}
    kx_by_glyph = {g: i for i, g in kx.items()}
    kx_name = {unicodedata.name(chr(0x2F00 + i)).replace("KANGXI RADICAL ", ""): i + 1
               for i in range(214)}
    supp = build_supplement_map(kx_name)

    strokes = {}
    for line in io.open(paths["gfx"], encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            strokes[o["character"]] = len(o.get("strokes", []))
        except Exception:
            pass

    trad = {}
    for line in io.open(paths["ts"], encoding="utf-8"):
        if line.startswith("#") or "\t" not in line:
            continue
        t, sims = line.rstrip("\n").split("\t", 1)
        for sm in sims.split(" "):
            if sm and sm not in trad:
                trad[sm] = t

    # dạng giản thể của bộ thủ suy từ bảng OpenCC, ví dụ 户 -> 63, 见 -> 147
    simp_forms = {sm: kx_by_glyph[t] for sm, t in trad.items()
                  if t in kx_by_glyph and sm not in kx_by_glyph}

    entries, mmh_radical = [], {}
    for line in io.open(paths["mmh"], encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        mmh_radical[o["character"]] = o.get("radical", "")
        if is_cjk(o["character"]):
            entries.append(o)
    resolve = make_resolver(kx_by_glyph, supp, simp_forms, mmh_radical)

    words = []
    for lvl, path in hskp.items():
        for line in io.open(path, encoding="utf-8-sig"):
            c = line.rstrip("\r\n").split("\t")
            if len(c) >= 5:
                words.append((c[0], c[1], c[2], c[3], c[4], lvl))

    # gióng âm tiết với chữ để suy âm đọc
    readings, aligned, multi, skipped = {}, 0, 0, 0
    for simp, tr, pnum, ptone, defn, lvl in words:
        chars = [c for c in simp if is_cjk(c)]
        # Nguồn HSK ghi chữ đa âm thành nhiều âm ngăn bằng dấu phẩy, ví dụ
        # 长 -> 'chang2, zhang3'. Đây chính là nhóm chữ ta cần nhất, nên phải
        # bắt riêng chứ không được bỏ qua cùng nhóm không gióng được.
        if "," in pnum and len(chars) == 1 == len(simp):
            multi += 1
            for alt in pnum.split(","):
                for sy in split_num(alt):
                    readings.setdefault(chars[0], set()).add(num_to_tone(sy))
            continue
        syls = split_num(pnum)
        if chars and len(chars) == len(simp) == len(syls):
            aligned += 1
            for ch, sy in zip(chars, syls):
                readings.setdefault(ch, set()).add(num_to_tone(sy))
        else:
            skipped += 1
    print(f"gióng âm tiết: {aligned} từ khớp, {multi} chữ đa âm tách theo dấu phẩy, "
          f"{skipped} bỏ qua")

    db_path = str(HERE / "dict.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    for idx, glyph in kx.items():
        name_hv, meaning_vi, alt = RADICALS[idx]
        db.execute("INSERT INTO radical(idx, glyph, glyph_alt, name_hv, meaning_vi, strokes) "
                   "VALUES (?,?,?,?,?,?)",
                   (idx, glyph, alt, name_hv, meaning_vi, strokes.get(glyph)))

    nc = nr = npart = 0
    miss = []
    for o in entries:
        ch = o["character"]
        ridx = resolve(o.get("radical", ""))
        if ridx is None:
            miss.append(ch)
        ids = o.get("decomposition")
        if ids and "？" in ids:
            ids = None
        allr = list(dict.fromkeys(list(o.get("pinyin") or []) + sorted(readings.get(ch, ()))))
        db.execute("INSERT OR IGNORE INTO char(char, codepoint, pinyin, pinyin_plain, "
                   "meaning_en, radical_idx, total_strokes, trad_form, ids) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (ch, "U+%04X" % ord(ch), allr[0] if allr else None,
                    to_plain(allr[0]) if allr else None, o.get("definition"),
                    ridx, strokes.get(ch), trad.get(ch), ids))
        nc += 1
        for i, py in enumerate(allr):
            db.execute("INSERT OR IGNORE INTO char_reading"
                       "(char, pinyin, pinyin_plain, is_primary) VALUES (?,?,?,?)",
                       (ch, py, to_plain(py), 1 if i == 0 else 0))
            nr += 1
        if ids:
            parts = [c for c in ids if is_cjk(c)
                     or "\u2e80" <= c <= "\u2eff" or "\u31c0" <= c <= "\u31ef"]
            for k, part in enumerate(parts):
                db.execute("INSERT OR IGNORE INTO char_part"
                           "(char, part, variant, order_no) VALUES (?,?,0,?)", (ch, part, k))
                npart += 1

    for i, (simp, tr, pnum, ptone, defn, lvl) in enumerate(words):
        db.execute("INSERT INTO word(word_simp, word_trad, pinyin_num, pinyin_tone, "
                   "pinyin_plain, pinyin_numeric, meaning_en, hsk_level, freq_rank) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (simp, tr, pnum, ptone, to_plain(ptone),
                    pnum.lower().replace(" ", ""), defn, lvl, (lvl - 1) * 1000 + i % 1000))
    db.execute("INSERT INTO word_fts(rowid, meaning_vi, meaning_en) "
               "SELECT id, meaning_vi, meaning_en FROM word")
    db.commit()

    poly = db.execute("SELECT COUNT(*) FROM (SELECT char FROM char_reading "
                      "GROUP BY char HAVING COUNT(*)>1)").fetchone()[0]
    print(f"\nchar {nc} | char_reading {nr} | char_part {npart} | word {len(words)}")
    print(f"chữ đa âm: {poly}   (bản v1 chỉ có 8)")
    print(f"thiếu bộ thủ: {len(miss)} ({len(miss) * 100 / nc:.1f}%)  {''.join(miss[:14])}")
    db.close()

if __name__ == "__main__":
    main()
