# AGENTS.md — đọc trước khi làm bất cứ việc gì

## TRẠNG THÁI DỰ ÁN

Dự án được chia thành các phiên độc lập, làm **đúng theo thứ tự**. Bảng này là
nguồn sự thật duy nhất về việc đang ở đâu. Sau khi hoàn thành một phiên, cập nhật
cột Trạng thái rồi mới sang phiên sau.

| Phiên | Module | Tệp sinh ra | Trạng thái |
|---|---|---|---|
| 01 | pinyin | `service/pinyin.py`, `tests/unit/test_pinyin.py` | xong, 27 test xanh |
| 02 | scheduler | `service/scheduler.py`, `tests/unit/test_scheduler.py` | xong, 23 test xanh |
| 03 | decomposer | `data/models.py`, `data/dictdb.py`, `service/decomposer.py`, `tests/unit/test_decomposer.py` | xong, 30 test xanh, tổng 80 |
| 04 | lookup | `service/lookup.py`, `tests/unit/test_lookup.py` | xong, 39 xanh 1 skip, tổng 120 |
| 05 | lát cắt giao diện Tra cứu | `main.py`, `ui/main_window.py`, `ui/screen_lookup.py`, `ui/widgets/tianzige.py`, `ui/widgets/decomp_tree.py`, `data/userdb.py` (bản tối thiểu) | xong, nghiệm thu bằng mắt 8 mục; mục 5 đạt về cấu trúc nhưng cột `pos` rỗng nên chưa có dữ liệu từ loại |
| 06 | userdb | `data/migrate.py`, `data/userdb.py`, `tests/unit/test_userdb.py` | xong, 35 test xanh, tổng 154 xanh 1 skip |
| 06b | bảo trì, tách `repetition` khỏi `review_count` | `data/migrate.py`, `data/userdb.py` | xong, +7 test, tổng 161 xanh 1 skip |
| 07 | màn hình Ôn tập, kèm tách `ui/theme.py` | `ui/theme.py`, `ui/screen_review.py`, `ui/widgets/review_card.py` | xong, +2 test `progress_counts`, tổng 163 xanh 1 skip; nghiệm thu bằng mắt 7/7 mục |
| 08a | hoàn tác ôn tập + rổ đáp án nhiễu | `data/userdb.py`, `data/dictdb.py`, `tests/unit/test_dictdb.py` | xong, +20 test (9 userdb, 11 dictdb), tổng 183 xanh 1 skip |
| 08b | cải thiện thẻ ôn tập | cây chiết tự mặt sau, âm Hán-Việt, nút Hoàn tác, phím tắt | xong |
| 08c | bài tập trắc nghiệm | `ui/widgets/bai_tap.py`, chọn nghĩa và chọn âm Hán-Việt | xong |
| 08d | bài tập gõ pinyin + ghép bộ thủ | `ui/widgets/bai_tap.py` (thêm `GoPinyin`, `GhepBoThu`), `ui/screen_review.py` | xong, 183 test xanh 1 skip |
| B1 | pdfsource & ocr | `adapter/pdfsource.py`, `adapter/ocr.py`, `tests/unit/test_pdfsource.py` | xong, +5 test xanh |
| B2 | splitter | `service/splitter.py`, `tests/unit/test_splitter.py` | xong, +3 test xanh |
| B3 | vocab | `service/vocab.py`, `tests/unit/test_vocab.py` | xong, +1 test xanh |
| B4 | giao diện Sách & nhập PDF | `ui/screen_books.py`, `ui/dialog_import.py`, `service/importer.py` | xong, nghiệm thu 4/4 màn hình |
| B5 | Smart Import AI (LLM API + Hybrid) | `adapter/aiclient.py`, `tests/unit/test_aiclient.py` | xong, +2 test xanh |
| B6 | Universal 2-Layer Hybrid Engine | `service/splitter.py`, `service/vocab.py`, `service/importer.py`, `ui/screen_books.py`, `tests/unit/test_universal_engine.py` | xong, +3 test xanh, tổng 197 test xanh 1 skip |
| B7a | prototype nhập Boya local-first | fallback Windows OCR, mốc 30 bài đã đối chiếu, locator bảng, parser 7 cột, lưu âm Hán-Việt, validator sơ bộ | xong prototype; +3 test, tổng 202 xanh 1 skip; thử thật Bài 5 và 29 còn nhiễu ở pinyin/nghĩa nên chưa đạt nghiệm thu dữ liệu |
| B7b | OCR song ngữ + Vision crop-only + golden Boya | hợp nhất OCR Trung–Anh, biên cột theo bảng thật, validator `char_reading`, bơm `DictDb` vào importer, golden Bài 5/29 | xong; +2 unit test, tổng 204 xanh 1 skip; 2 golden xanh; Bài 5 recall 70%/precision 93,3%, Bài 29 recall 86,4%/precision 100% |
| B7c | duyệt kết quả nhập sách | trạng thái `review`, dialog sửa ranh giới và bảng 7 cột, tô dòng lỗi, preview crop nguồn, chặn Ôn tập trước xác nhận | xong; +1 test Qt offscreen, tổng 205 xanh 1 skip; QA render đạt |
| B7d | xác nhận ranh giới trước OCR + Vision chọn lọc | tách worker phân bài/OCR, dialog xác nhận khoảng trang, trạng thái `review_bounds`/`extracting`, chạy lại Vision crop-only cho một bài và chỉ lưu sau duyệt | xong; +1 test Qt offscreen, tổng 206 xanh 1 skip; 2 golden Boya Bài 5/29 xanh; QA render đạt |
| B7e | nghiệm thu Vision crop-only trên Boya thật | chạy API key đã lưu trên đúng crop bảng từ mới Bài 5 và Bài 29, đo theo golden độc lập | xong; Bài 5 đúng 20/20 (recall 100%, precision 100%, 1 dòng được gắn cờ duyệt); Bài 29 đúng 22/22 (recall 100%, precision 100%, 0 dòng gắn cờ); không cần nới validator |
| B7f | dừng an toàn khi AI lỗi + tiếp tục bài đã nhập + thử A/B | phân biệt HTTP 429, không coi 0 từ là thành công, giữ bài đã có khi chạy lại; so local với Vision ghép trang trên golden Bài 5/29 | xong; +3 test, tổng 209 xanh 1 skip; local recall 70%/86,4%, Vision một request mỗi bài đạt 100%/100%; ghép nhiều bài thành một raster không khả thi do giới hạn kích thước/bộ nhớ |
| B7g | Vision một request mỗi bài + hoàn tất Boya | ghép/co crop cùng bài xuống tối đa 1200 px; Flash-Lite; khử trùng/null; fallback từng trang khi độ bao phủ thấp; resume và dừng an toàn | xong; tổng 216 xanh 1 skip, 2 golden xanh; 30/30 bài, 722 từ, 17 dòng gắn cờ, không bài rỗng/trùng/thứ tự lỗi/chuỗi `None`; Bài 5 đúng 20/20 và Bài 29 đúng 22/22 |
| B7h | sửa preview ảnh nguồn | bỏ heuristic nửa trên/nửa dưới và `source_page - 1`; tái định vị, crop và ghép toàn bộ bảng theo ranh giới bài, cache 64 preview | xong; +1 test, tổng 217 xanh 1 skip, 2 golden xanh; QA Bài 5 và 15 hiển thị đủ bảng nhiều trang |
| B7i | sửa preview làm treo giao diện | `PreviewWorker` kết xuất crop ở luồng nền, trạng thái đang tải, giải mã ảnh có kiểm tra và scale nhanh | xong; +1 test, tổng 218 xanh 1 skip, 2 golden xanh; QA thật Bài 5 trả thao tác sau 0,9 ms, ảnh hiện sau 6,12 giây |
| B7j | sửa locator preview Bài 20 | nhận tiêu đề `生词` bị tách thành nhiều span ở đầu trang, không bắt buộc hậu tố `表` | xong; +1 test, tổng 219 xanh 1 skip, 2 golden xanh; QA dialog thật Bài 20 hiển thị pixmap sau 12,65 giây, không khóa UI |
| B7k | chặn preview cũ ghi đè bài mới | vô hiệu hóa worker khi chuyển bài, chỉ worker mới nhất được cập nhật preview, giữ và dọn các thread cũ an toàn | xong; +1 test, tổng 220 xanh 1 skip, 2 golden xanh |
| B7l | hàng đợi duyệt từ cần xác nhận | bảng tổng hợp theo bài/trang, lọc, tìm kiếm, sửa và xác nhận chọn lọc nguyên tử, đồng bộ hai tab, preview nền tuần tự đúng bài, nút hoàn tất riêng | xong; +13 test, tổng 233 xanh 3 skip; QA Boya thật còn 16 dòng thuộc 13 bài, không ô tích sẵn, gọi preview trả sau 0,22 ms và ảnh hiện sau 6,32 giây |
| B7m | Universal Evidence Fusion Import | evidence fusion tổng quát, bảng 2–7 cột, coverage theo block, checkpoint/resume/429, preview crop đã lưu và xác nhận block thủ công | xong phần tự động; tổng unit 307 xanh 1 skip; toàn suite an toàn 307 xanh 3 skip; 2 golden live-data được khóa bằng RUN_LIVE_GOLDEN=1 và chưa chạy theo yêu cầu không chạm PDF/SQLite thật |
| B7n | bảng từ mới nhỏ xen trong bài học | heading tách/trộn OCR, nối heading với dữ liệu thấp hơn, suy luận cột Hán lặp và hàng song song, crop dừng trước hội thoại | xong phần locator; +6 test, tổng unit 314 xanh 1 skip; nghiệm thu HSK Bài 1 đọc-only tự tìm 3 block ở trang PDF 16–18 với 2/6/4 hàng OCR; không gọi Vision và không ghi SQLite thật |
| B7o | retry locator khi OCR thoáng qua trả rỗng | `service/importer.py`, `tests/unit/test_universal_engine.py` | xong phần tự động; locator thử lại đúng một lần bằng `PdfSource`/OCR adapter mới trước khi báo không có block, không gọi AI; +1 test, toàn suite 315 xanh 3 skip; chẩn đoán read-only Bài 1 vẫn tìm đúng 3 block trong QThread |
| B7p | bảo toàn Unicode Windows OCR trong app GUI | `adapter/ocr.py`, `tests/unit/test_pdfsource.py` | xong phần tự động; PowerShell mã hóa JSON UTF-8 thành Base64 ASCII trước khi trả về Python, không còn phụ thuộc console code page; +3 test, toàn suite 318 xanh 3 skip; kiểm chứng detached Bài 1 trả 243/281/212/151 span, không `?`/`�`, locator tìm đúng 3 block 2/6/4 hàng |

| B7q | nhật ký debug lệnh nhập sách | `hanzi_app/main.py`, `hanzi_app/service/importer.py`, `hanzi_app/ui/dialog_import.py`, `tests/unit/test_debug_logging.py` | xong; toàn suite 324 xanh 3 skip; logging chỉ ghi metadata chẩn đoán, không dùng PDF/SQLite/AI thật trong kiểm chứng; privacy/diff scope đạt |
| B7r | stale manifest recovery khi tiếp tục nhập | `hanzi_app/service/vocab.py`, `hanzi_app/data/userdb.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_userdb.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 335 xanh 3 skip; STT dương/liên tiếp, tự sửa manifest tự động cũ, clear rows cache sai, giữ block thủ công và `ai_attempts`, ghép mơ hồ báo `manifest_needs_review` |
| B7s | tự phục hồi duplicate orders HSK Bài 1 | `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 339 xanh 3 skip; chọn AI-only khi sạch, nới `expected_rows` khi block không có range, renumber AI theo range, hòa giải rows đã checkpoint không reset `ai_attempts` |
| B7t | tự sửa manifest HSK2 range count lệch expected_rows | `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 341 xanh 3 skip; checkpoint AI có range 9–12 tự chuẩn hóa `expected_rows`, ghi lại manifest bằng `repair_import_blocks`, không gọi locator nên tránh `manifest_needs_review` giả |
| B7u | bỏ qua block lỗi và gom lỗi import sau | `hanzi_app/service/importer.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 342 xanh 3 skip; lỗi coverage như thiếu STT được checkpoint `incomplete` rồi chạy tiếp bài sau, cuối lượt giữ sách `incomplete` và không phát modal lỗi; riêng HTTP 429 vẫn dừng an toàn |
| B7v | report gom lỗi import toàn sách | `hanzi_app/service/importer.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 343 xanh 3 skip; thêm `collect_import_issues()` read-only để phân nhóm `NO_BLOCKS`, `EMPTY_BLOCK`, `MISSING_ORDERS`, `ROW_COUNT_MISMATCH`, `OCR_NOISE`, `GRAMMAR_TABLE_FALSE_POSITIVE`, `AI_EXHAUSTED`; HSK2 hiện còn 22 mục lỗi gom được |
| B7w | sửa cụm locator/budget HSK2 | `hanzi_app/service/vocab.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 344 xanh 3 skip; Vision budget chuyển sang một lượt cho mỗi block pending trong mỗi lần chạy, block đã xài 3 lượt được gắn `ai_exhausted`, locator bỏ region chỉ có heading/STT và reject bảng tham chiếu/ngữ pháp để tránh false-positive kiểu Bài 25 |
| B7x | full-page recovery cho block HSK2 thiếu nhiều | `hanzi_app/adapter/aiclient.py`, `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 345 xanh 1 skip; Vision prompt chấp nhận crop hoặc nguyên trang, block `ai_attempts >= 2` dùng full-page recovery thay vì crop cũ, giới hạn tự động nâng lên 4 và report `AI_EXHAUSTED` đồng bộ; report read-only trên bản copy HSK2 còn 18 mục lỗi nhưng không còn `AI_EXHAUSTED`, chưa ghi SQLite thật |
| B7y | locator HSK2 cho marker `Dịch nghĩa từ mới` bị OCR méo | `hanzi_app/service/vocab.py`, `tests/unit/test_vocab.py` | xong; toàn suite 347 xanh 1 skip; thêm detector marker `Dich/D-ch/nghla/moi`, cho phép block một dòng khi có marker dịch nghĩa từ mới, diagnostic thật xác nhận Bài 8/9/18/20 từ `NO_BLOCKS` chuyển sang có block; không gọi AI và không ghi SQLite thật |
| B7z | reject bảng tham chiếu HSK2 Bài 25 | `hanzi_app/service/vocab.py`, `tests/unit/test_vocab.py` | xong; toàn suite 349 xanh 1 skip; `_looks_like_non_vocab_reference_region()` sort text theo dòng/bbox trước khi match term, reject `词性/简称/词性对照表` và `来自本册`; diagnostic thật Bài 25 không còn sinh block page 134/140 từ locator mới; chưa dọn manifest cũ trong SQLite thật |

| B7aa | cleanup manifest cũ và reconcile checkpoint HSK2 | `hanzi_app/data/userdb.py`, `hanzi_app/service/importer.py`, `tests/unit/test_userdb.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 354 xanh 1 skip; `cleanup_import_issues()` xóa block non-manual false-positive và tự reconcile block checkpoint đã đủ dữ liệu; đã backup DB thật rồi dọn HSK2 từ 9 còn 8 issue, Bài 20 block 2 sạch; không gọi AI/API ngoài |
| B7ab | dọn false-positive locator HSK2 còn lại | `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 360 xanh 1 skip; reject vùng ngữ pháp/hán tự/bài tập hỏi đáp không heading, cleanup tùy chọn PDF xóa block lỗi không còn được locator mới xác nhận; DB thật HSK2 từ 8 xuống 2 issue, backup `user.sqlite.bak-stale-locator-20260812-062836` và `user.sqlite.bak-question-locator-20260812-064024`; không gọi AI/API ngoài |
| B7ac | xử lý 2 issue HSK2 cuối | `hanzi_app/service/importer.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 361 xanh 1 skip; cleanup reconcile block không range có rows Vision đáng tin (Bài 9 block 1), sửa tay Bài 21 từ OCR page 112 thành 2 block manual cần duyệt, DB thật HSK2 còn 0 issue và `import_state=ready`; backup `user.sqlite.bak-b9-trusted-rows-20260812-131132` và `user.sqlite.bak-b21-manual-20260812-131335`; không gọi AI/API ngoài |
| B7ad | cleanup sau OCR lại HSK1/HSK2 | `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong phần tự động an toàn; toàn suite 367 xanh 1 skip; importer tự chạy cleanup trước khi chốt trạng thái, locator giữ crop HSK1 khi có heading `生词/New Words` nhưng STT/pinyin OCR nhiễu, cleanup giữ rows Vision/AI và bỏ regex noise; DB thật HSK2 id 5 còn 0 issue và `import_state=review`, HSK1 id 4 giảm 11 còn 8 issue; backup `user.sqlite.bak-hsk2-restore-20260812-165345` và `user.sqlite.bak-hsk1-airow-cleanup-20260812-165651`; không gọi AI/API ngoài |
| B7ae | quality gate OCR rác và phục hồi HSK1/HSK2 | `hanzi_app/service/vocab.py`, `hanzi_app/service/importer.py`, `tests/unit/test_vocab.py`, `tests/unit/test_universal_engine.py` | xong; toàn suite 370 xanh 1 skip; validator/report bắt local-only OCR fragment thành `local_ocr_noise`/`OCR_NOISE`, cleanup xóa block `local_ok` rác khi bài còn block khác; DB thật HSK1 id 4 phục hồi thủ công từ OCR local còn 0 issue, `import_state=review`, 238 từ; HSK2 id 5 xóa block rác và khôi phục Bài 17 từ backup sạch còn 0 issue, `import_state=review`, 114 từ; backup `user.sqlite.bak-hsk1-local-noise-cleanup-20260812-225030`, `user.sqlite.bak-hsk1-manual-recovery-20260812-225717`, `user.sqlite.bak-hsk2-quality-cleanup-20260812-230043`; không gọi AI/API ngoài |
| Đóng gói Windows | bản chạy độc lập x64 | `Hanyu Recognize.exe` | xong; đã mở cửa sổ chính và tra `renshi` được 3 kết quả, có `认识`, trên hồ sơ tạm; dùng `user.sqlite` cạnh EXE nếu có, nếu thiếu thì lưu vào `%LOCALAPPDATA%\Hanyu Recognize` |
| B7af | QA hàng đợi HSK1/HSK2 | UI duyệt sách và liên kết ảnh nguồn | xong trên bản sao, xác nhận chọn lọc giữ đủ 22/22 và 2/2 liên kết nguồn trong bài đã thử. Người dùng chuyển phép đo PDF sang Boya sơ cấp 1 và 2 |
| B7ag | phân bài và định vị bảng chính Boya | `adapter/pdfsource.py`, `service/splitter.py`, `service/vocab.py`, đáp án 55 bài | xong, 30/30 và 25/25 khoảng bài đúng hai đầu, đúng 58/58 và 51/51 trang chứa bảng chính, 0 trang thừa hoặc sai bài, ảnh cắt đủ hai từ ở hai đầu của 55 bảng |
| B7ah | quyết định duyệt khung và nhập tiếp | migration 4, userdb, importer, dialog phân bài và sửa khung | xong, lưu trạng thái chờ duyệt/chấp nhận/bỏ qua, bảo toàn sửa tay, kiểm phiên bản khi ghi, QA các thao tác trên hồ sơ tạm. Suite an toàn 380 xanh 5 skip, 4 golden PDF thật xanh |
| Đóng gói Windows sau B7ah | bản x64 có duyệt khung | `Hanyu Recognize.exe` | xong, đối chiếu 10 module trong EXE với mã nguồn, chạy cửa sổ chính trên hồ sơ thử, migration 3 lên 4 giữ thiết lập cũ |

| B7ai | Ngăn console bật khi nhập PDF | adapter/ocr.py | xong, Windows OCR chạy với CREATE_NO_WINDOW, 14 test xanh và đọc được hai trang Boya thật |

**Phiên tiếp theo phải làm: nếu tiếp tục tối ưu nhập Boya, ưu tiên độ đủ dòng và độ đúng chữ của OCR cục bộ trên các ảnh bảng đã đối chiếu. Hai lượt nhập thử Boya 1/2 còn 58 và 51 vùng cần xác nhận độ đủ dòng. Xem [biên bản QA](plans/journals/2026-11-23-boya-qa.md).**

Phiên 08a thêm đúng ba phương thức: `UserDb.undo_review`, `DictDb.candidate_meanings`
và `DictDb.candidate_hanviet`, không đổi lược đồ, không thêm bậc migration. Hoàn tác
chỉ chạy trong phiên đang mở vì `review_log` không lưu đủ trạng thái cũ; người gọi
phải giữ cặp `(word, before)` trong bộ nhớ. Hai phương thức rổ đáp án nhiễu trả về
thứ tự XÁC ĐỊNH, việc bốc ngẫu nhiên thuộc tầng giao diện ở phiên 08c.
`tests/unit/test_dictdb.py` là tệp test đầu tiên chạy trên `dict.sqlite` thật.

Trước B1 còn hai việc tay chặn giai đoạn B, xem `handoff/VIEC-CAN-LAM.md`: xác nhận
`bounds_boya.json` và `git init`. Cả hai là việc của người, không giao phiên agent.

Phiên 07 sửa sáu tệp đã có, đúng như packet hẹn trước: `data/userdb.py` thêm đúng
một phương thức `progress_counts()`, còn `ui/widgets/tianzige.py`,
`ui/widgets/decomp_tree.py`, `ui/main_window.py`, `ui/screen_lookup.py` và `main.py`
đổi lệnh import theo việc tách `theme.py`. `MainWindow` và `ScreenLookup` nhận thêm
hai tham số `user_db` và `scheduler` ở cuối danh sách tham số.

Phiên bảo trì **06b**: bảng `progress` ở mục 5.3 thiếu cột `repetition` trong khi
`ReviewOutcome` ở mục 13.3 có trường đó, nên phiên 06 buộc phải ánh xạ nó sang cột
`review_count`. Hai con số khác nghĩa và ánh xạ đó sai. Xem lỗi 9 trong `BAN-GIAO.md`.
**Phải chạy trước phiên 07**, vì màn hình Ôn tập gọi thẳng vào đường này.

Phiên 06 ghi nhận một chỗ lệch giữa packet và đặc tả: packet nói user.sqlite có
"chín bảng", mục 5.3 của đặc tả chỉ định nghĩa **tám** (`schema_version`, `book`,
`lesson`, `lesson_word`, `progress`, `review_log`, `explain_cache`, `setting`).
Đã cài theo đặc tả, tám bảng cộng đúng năm chỉ mục. Nếu bản sau cần bảng thứ chín
thì thêm một bậc mới vào `migrate._CAC_BAC`, đừng sửa bậc 1.

Phiên bảo trì **03b**, chạy sau 04: thêm `DecompNode.is_group` vào `models.py` và cho
`decomposer.tree()` đặt cờ đó, cộng 2 test. Đây không phải một phiên trong dãy, không
đánh số lại; nó giải thích vì sao phiên 03 nhảy từ 28 lên 30 test và tổng nhảy từ 117
lên 120.

Nếu người dùng yêu cầu một phiên mà phiên trước nó chưa xong, hãy dừng lại và nói
rõ phiên nào còn thiếu, đừng tự tạo bù các tệp của phiên trước.

Cập nhật bảng này là **việc bắt buộc cuối mỗi phiên** và không tính là vi phạm quy
tắc "không sửa tệp khác": đổi trạng thái phiên vừa xong, đổi dòng "Phiên tiếp theo
phải làm". Đây là bộ nhớ duy nhất nối các phiên với nhau.

## TỆP HẠ TẦNG ĐƯỢC PHÉP TẠO

Ngoài các tệp liệt kê trong packet, được phép tạo thêm hai tệp sau nếu chưa có, và
chỉ hai tệp này:

- `conftest.py` ở gốc kho, nội dung tối thiểu để `pytest` tìm thấy gói `hanzi_app`.
  Có tệp này rồi thì **không** chèn `sys.path` vào từng tệp test nữa.
- `pytest.ini` hoặc `pyproject.toml` tối thiểu, nếu cần khai báo đường dẫn test.
- `data/models.py` chứa các dataclass ở mục 13.3. Tệp này thuộc phiên 03. Phiên nào
  cần một dataclass trước khi nó ra đời thì khai báo tạm ngay trong module của mình
  kèm ghi chú, rồi phiên 03 gom về một chỗ và sửa lại lệnh import.

## KHÔNG LÀM NHỮNG VIỆC SAU

- Không lập kế hoạch kiến trúc cho toàn bộ ứng dụng. Kiến trúc đã chốt ở mục 13
  của đặc tả; việc của mỗi phiên là cài đặt đúng một module.
- Không tạo thư mục `frontend/`, không dùng React, Vue, Vite hay bất kỳ công nghệ
  web nào. Giao diện là PySide6, ứng dụng desktop.
- Không gộp `dict.sqlite` với `user.sqlite` thành một tệp. Hai tệp tách nhau có lý
  do ở mục 4.3 của đặc tả.
- Không tạo "chế độ giả lập" sinh dữ liệu mẫu trông như thật cho phần diễn giải.
  Toàn bộ luận điểm của đồ án là đầu ra của mô hình luôn phải qua kiểm chứng.
- Không hỏi khoá API. Chưa phiên nào trong bốn phiên trên cần gọi mạng.

## Bối cảnh

Ứng dụng desktop học từ vựng tiếng Trung cho người Việt. Python 3.12, PySide6,
SQLite, chạy trên Windows. Đây là đồ án tốt nghiệp, nên mã phải đọc được và giải
thích được, không tối ưu quá mức.

Môi trường thực tế đang chạy: Python 3.12.9 trên Windows, PySide6 6.11.1, pytest
9.1.1. Bản đặc tả đầu ghi Python 3.11; đã đổi thành 3.12 cho khớp máy đang dùng vì
toàn bộ 120 test xanh trên bản này. Nếu nơi bảo vệ đồ án bắt buộc 3.11 thì đổi lại
ở đây trước, rồi mới chạy phiên tiếp theo. Phụ thuộc ghi ở `requirements.txt` gốc kho.

## Năm quy tắc không được vi phạm

1. **Bộ test là chân lý.** Các bảng số trong đặc tả đã được kiểm chứng độc lập
   bằng một cài đặt riêng. Test đỏ nghĩa là mã sai. Không sửa test, không nới điều
   kiện, không thêm `pytest.approx` rộng hơn mức đặc tả cho phép, không đánh dấu
   `xfail`. Nếu bạn tin rằng test sai, hãy dừng lại và nói ra lý do, đừng tự sửa.

2. **Một phiên một module.** Chỉ tạo đúng các tệp được liệt kê ở mục "Cần tạo".
   Không tạo module khác, không viết sẵn tệp cho bước sau, không dựng khung ứng
   dụng, không thêm `__main__`, không thêm giao diện dòng lệnh.

3. **Không tự thêm tính năng.** Không thêm tham số, không thêm phương thức, không
   thêm xử lý ngoại lệ ngoài phần đặc tả nêu. Thiếu thông tin thì hỏi, đừng đoán.

4. **Phân tầng.** `data/` không được import bất cứ thứ gì của Qt. `service/` không
   được tự mở kết nối cơ sở dữ liệu và không đọc tệp PDF trực tiếp, mà nhận các
   đối tượng tầng dưới qua tham số khởi tạo.

5. **Chỉ dùng thư viện đã có trong đặc tả.** Thư viện chuẩn của Python, cộng
   PySide6, PyMuPDF, pytest. Không thêm phụ thuộc mới nếu không được yêu cầu.

## Xong là khi nào

`pytest tests/unit/<tên tệp test>.py -v` xanh toàn bộ, và không có tệp nào khác
trong kho bị sửa.

## Định dạng trả lời mong muốn

Viết thẳng nội dung từng tệp, mỗi tệp một khối mã có ghi rõ đường dẫn. Không tóm
tắt lại đặc tả, không giải thích dài dòng trước khi viết mã. Sau khi viết xong,
liệt kê ngắn gọn những chỗ bạn phải tự quyết vì đặc tả chưa nói rõ.

---

### 13.1. Nguyên tắc phân tầng

Bốn tầng, phụ thuộc chỉ đi xuống, không bao giờ đi lên hoặc đi ngang giữa hai module
cùng tầng:

```
ui/            →  chỉ gọi xuống service/, không được import trực tiếp data/
service/       →  lookup, decomposer, importer, scheduler
adapter/       →  pdfsource, aiclient, ocr
data/          →  dictdb, userdb, và các kiểu dữ liệu dùng chung
```

Ba hệ quả bắt buộc:
- `data/` không import bất cứ thứ gì của Qt. Nhờ vậy toàn bộ tầng dưới kiểm thử được
  mà không cần dựng ứng dụng đồ hoạ.
- `service/` không mở kết nối cơ sở dữ liệu và không đọc tệp PDF trực tiếp. Nó nhận
  các đối tượng tầng dưới qua tham số khởi tạo. Nhờ vậy kiểm thử thay được bằng bản
  giả lập.
- `adapter/` là chỗ duy nhất biết tới PyMuPDF, PaddleOCR và HTTP. Đổi thư viện OCR
  hay đổi nhà cung cấp mô hình chỉ sửa trong thư mục này.

### 13.2. Cây thư mục

```
hanzi_app/
    main.py                   điểm vào, dựng các đối tượng rồi bơm vào nhau
    data/
        models.py             toàn bộ dataclass dùng chung
        dictdb.py             truy cập dict.sqlite, chỉ đọc
        userdb.py             truy cập user.sqlite, đọc ghi, quản lý giao dịch
        migrate.py            kịch bản chuyển đổi lược đồ theo schema_version
    adapter/
        pdfsource.py          bọc PyMuPDF, che khác biệt giữa trang chữ và trang ảnh
        ocr.py                bọc PaddleOCR
        aiclient.py           gọi API, ép lược đồ JSON, không chứa logic nghiệp vụ
    service/
        pinyin.py             chuẩn hoá, tách âm tiết, đổi qua lại số và dấu
        lookup.py             FR-01 tới FR-08
        decomposer.py         FR-10 tới FR-15
        splitter.py           thang năm nấc của QT-02 và QT-02b
        vocab.py              QT-03
        importer.py           điều phối QT-02, chạy trong luồng nền
        scheduler.py          SM-2, QT-04
    ui/
        main_window.py
        screen_lookup.py      screen_books.py  screen_review.py  screen_radicals.py
        dialog_import.py
        widgets/              ô 田字格, cây chiết tự, thẻ ôn tập
    resources/
        fonts/  dict.sqlite  qss/
tests/
    unit/  golden/  fixtures/
```

### 13.3. Kiểu dữ liệu dùng chung

> **Đây là bản CHÉP từ `dac-ta-ung-dung-v0.5.md` và nó đã trôi một lần.** Phiên 03
> sót `DecompNode.is_group` đúng vì đọc bản chép cũ ở đây thay vì đặc tả gốc, phải
> chạy phiên bảo trì 03b để vá. Trước mỗi phiên đụng tới dataclass, đối chiếu khối
> này với mục 13.3 của đặc tả gốc; lệch thì sửa ở đây trước rồi mới bắt đầu phiên.
> Bản này đã đồng bộ tới hết phiên 05.

Đặt hết trong `data/models.py`. Tất cả là dataclass đông cứng, không có phương thức
nghiệp vụ. Lý do dùng dataclass thay vì dict: sai tên trường bị bắt lúc viết mã chứ
không phải lúc chạy, và đây là thứ giúp một tác nhân sinh mã đỡ tự bịa tên trường.

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class CharInfo:
    char: str
    pinyin: str            # âm đọc chính, có dấu
    readings: tuple[str, ...]   # toàn bộ âm đọc, có dấu, lấy từ char_reading
    hanviet: str | None
    meaning_vi: str | None
    meaning_en: str | None
    radical_idx: int | None
    total_strokes: int | None
    trad_form: str | None
    ids: str | None
    hsk_level: int | None
    freq_rank: int | None

@dataclass(frozen=True)
class WordInfo:
    id: int
    simplified: str
    traditional: str | None
    pinyin_tone: str       # 'rènshi'
    pos: str | None
    meaning_vi: str | None
    meaning_en: str | None
    hsk_level: int | None
    freq_rank: int | None

@dataclass(frozen=True)
class Radical:
    idx: int               # 1..214
    glyph: str             # '言'
    glyph_alt: str | None  # '讠'
    name_hv: str           # 'ngôn'
    meaning_vi: str        # 'lời nói'
    strokes: int

@dataclass(frozen=True)
class WordSource:
    # Từ này xuất hiện ở đâu trong sách của người dùng. Lấy từ lesson_word,
    # lesson và book trong user.sqlite. None nếu từ chưa nằm trong quyển nào.
    book_title: str
    lesson_no: int
    lesson_title: str | None
    page: int | None
    pinyin_src: str | None
    hanviet_src: str | None
    meaning_src: str | None

@dataclass(frozen=True)
class WordDetail:
    query: str
    word: WordInfo | None            # None nếu chỉ tra được ở mức chữ đơn
    chars: tuple[CharInfo, ...]      # từng chữ của từ, theo đúng thứ tự
    source: WordSource | None
    status: str | None               # 'new' | 'learning' | 'known'; None nếu chưa ôn tập

# WordDetail CỐ Ý không chứa cây chiết tự và không chứa phần diễn giải của FR-13.
# Lookup và decomposer cùng nằm ở tầng service, mà mục 13.1 cấm phụ thuộc đi ngang
# giữa hai module cùng tầng. Cây do Decomposer.tree() dựng, tầng giao diện gọi cả
# hai rồi ghép.

@dataclass(frozen=True)
class SearchHit:
    kind: str              # 'word' | 'char'
    word: WordInfo | None
    char: CharInfo | None
    score: float           # điểm xếp hạng, càng lớn càng lên trên
    matched_by: str        # 'hanzi' | 'pinyin_tone' | 'pinyin_plain' | 'pinyin_num' | 'meaning' | 'fuzzy'

@dataclass(frozen=True)
class DecompNode:
    char: str
    ids: str | None
    meaning_vi: str | None
    radical: Radical | None
    children: tuple["DecompNode", ...]
    truncated: bool = False   # True nếu dừng vì chạm giới hạn độ sâu hoặc gặp chu trình
    is_group: bool = False    # True với nút nhóm lồng

# Nút nhóm lồng. Chuỗi IDS '⿱木⿰木木' của chữ 森 sinh một nút trung gian ứng với
# '⿰木木', mà cụm đó không phải một chữ Hán. Nút loại này đặt char VÀ ids bằng chính
# đoạn IDS con, meaning_vi và radical bằng None, is_group bằng True. Nút nhóm bị cắt
# vì MAX_DEPTH vẫn giữ is_group bằng True dù không có con. Giao diện BẮT BUỘC kiểm
# tra is_group trước khi vẽ: nút nhóm không được vẽ vào ô 田字格, vì char của nó là
# chuỗi IDS chứ không phải chữ.

@dataclass(frozen=True)
class PageSummary:
    id: int                # số thứ tự dòng trong bản tóm lược, đánh từ 1
    pdf_page: int          # chỉ số trang trong tệp, từ 0
    folio: str | None      # số trang in đọc được
    max_size: float
    head: str              # dòng lớn nhất ở phần trên trang, cắt còn 30 ký tự
    cjk: int

@dataclass(frozen=True)
class LessonBoundary:
    index_no: int          # âm với mục ôn tập, xem QT-02 bước 3
    title: str | None
    page_start: int
    page_end: int
    confidence: float      # 0..1
    kind: str              # 'lesson' | 'review'

@dataclass(frozen=True)
class VocabRow:
    order_no: int | None
    word: str
    pinyin_src: str | None
    pos: str | None
    meaning_src: str | None
    source_page: int
    extract_by: str        # 'regex' | 'llm' | 'vision' | 'manual'
    needs_review: bool
    review_reason: str | None   # lý do gắn cờ, hiện lên giao diện sửa tay

@dataclass(frozen=True)
class ReviewOutcome:
    ease: float
    interval_days: int
    repetition: int
    lapse_count: int
    status: str            # 'new' | 'learning' | 'known'
    due_date: date
```
