# Tóm tắt dự án — đọc tệp này ĐẦU TIÊN

## Dự án là gì

App desktop học từ vựng tiếng Trung cho người Việt. Python 3.12, PySide6 6.11.1,
SQLite, chạy trên Windows. Đường dẫn kho: `D:\Hanyu recognize`.

Mục tiêu hiện tại: app dùng được hàng ngày, không phải đồ án.

---

## Đọc ngay ba tệp này theo thứ tự

1. **`CLAUDE.md`** — bảng tiến độ 20 phiên, quy tắc chung bắt buộc, dataclass, lược đồ.
   Đây là nguồn sự thật. Mâu thuẫn với tệp khác thì `CLAUDE.md` thắng.

2. **`BAN-GIAO.md`** — quyết định đã chốt, món nợ còn lại, lỗi đã biết, bài học.
   Đọc trước khi đề xuất bất cứ gì để không lặp lại quyết định cũ.

3. **`VIEC-CAN-LAM.md`** — todolist theo thứ tự ưu tiên.

---

## Trạng thái hiện tại (sau phiên 08c)

**Đã xong và chạy được:**
- Màn hình Tra cứu: tìm theo pinyin/chữ Hán/nghĩa tiếng Việt, cây chiết tự
- Màn hình Ôn tập: thẻ lật + trắc nghiệm (chọn nghĩa, chọn âm Hán-Việt)
- Bộ lập lịch SM-2, cơ sở dữ liệu người dùng, hoàn tác lần chấm
- Nghĩa tiếng Việt và âm Hán-Việt cho 601 từ HSK 1-3

**Chưa làm:**
- Bài tập gõ pinyin và ghép bộ thủ (08d)
- Màn hình Sách, nhập PDF
- Nghĩa tiếng Việt HSK 4-6 (4400 từ còn lại)

---

## Cấu trúc tệp quan trọng

```
D:\Hanyu recognize\
├── hanzi_app\
│   ├── main.py               điểm vào
│   ├── data\
│   │   ├── dictdb.py         truy vấn dict.sqlite (chỉ đọc)
│   │   ├── userdb.py         user.sqlite, tiến độ học
│   │   ├── migrate.py        nâng cấp lược đồ, hiện bậc 2
│   │   └── models.py         dataclass dùng chung
│   ├── service\
│   │   ├── scheduler.py      SM-2, ĐỪNG viết lại
│   │   ├── lookup.py         tra từ, tổng hợp
│   │   ├── decomposer.py     cây chiết tự
│   │   └── pinyin.py         chuẩn hoá âm đọc
│   └── ui\
│       ├── theme.py           bảng màu 6.1, phông 6.2
│       ├── main_window.py     cửa sổ chính, 4 màn hình
│       ├── screen_lookup.py   Tra cứu
│       ├── screen_review.py   Ôn tập (thẻ lật + trắc nghiệm)
│       └── widgets\
│           ├── tianzige.py    ô 田字格
│           ├── decomp_tree.py cây chiết tự
│           ├── review_card.py thẻ ôn tập
│           └── bai_tap.py     bài tập trắc nghiệm
├── dict.sqlite                từ điển HSK 1-6, chỉ đọc
├── user.sqlite                tiến độ học, đọc-ghi
├── data\vi\                   nguồn nghĩa tiếng Việt (CSV)
├── tools\                     kịch bản tiện ích
├── tests\unit\                161 test, 1 skip
├── CLAUDE.md
├── BAN-GIAO.md
└── dac-ta-ung-dung-v0.5.md   đặc tả gốc (nếu mâu thuẫn với CLAUDE.md thì hỏi)
```

---

## Ba quy tắc bất di bất dịch

**Quy tắc 1.** Đọc `CLAUDE.md` trước khi làm bất cứ gì.

**Quy tắc 2.** Không sửa tệp không được yêu cầu. Thiếu phương thức ở tầng dưới
thì dừng lại báo, đừng tự thêm.

**Quy tắc 3.** Không `setParent(None)` và không `setVisible(True)` lên widget
chưa gắn vào cây widget — cả hai tạo cửa sổ thật trên Windows, gây cửa sổ chớp
lên rồi tắt. Đã mắc 3 lần, ghi vào mọi packet `ui/` từ giờ.

---

## Lệnh chạy thường dùng

```
cd "D:\Hanyu recognize"
python -m hanzi_app.main          # chạy app
pytest tests\unit -q              # 161 test, phải xanh hết trước khi commit
python tools\nap_nghia_vi.py      # nạp nghĩa tiếng Việt vào dict.sqlite
```

---

## Ghi chú cho AI mới

Dự án có bộ tài liệu đầy đủ được duy trì qua nhiều phiên làm việc. Trước khi
đề xuất bất cứ gì, đọc `BAN-GIAO.md` mục 2 (quyết định đã chốt) để không làm
lại việc cũ hoặc đi ngược quyết định đã có lý do.

Khi viết packet cho agent: luôn ghi rõ (1) tệp nào được phép sửa, (2) dữ liệu
nào còn rỗng trong database, (3) không `setVisible(True)` trên widget chưa có cha.
