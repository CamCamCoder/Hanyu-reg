# Chia đúng bài và lấy đúng bảng từ mới trong HSK1/HSK2

Kế hoạch ngày 23/11/2026. Trạng thái: chờ thực hiện. Người nhập sách cần thấy bảng rõ được lấy tự động, vùng mơ hồ được khoanh trên trang gốc, và có thể bổ sung bảng bị bỏ sót trước khi từ được đưa vào học.

## 1. QA hàng đợi hiện có và chuẩn bị PDF

- [ ] Làm phiên QA đã ghi trong AGENTS.md trước. Mở hàng đợi trên bản sao hồ sơ, ưu tiên HSK1 Bài 2/3/5/6/8/10/11 và HSK2 Bài 17. Kiểm tra lọc theo bài, sửa dòng, chuyển nhanh giữa hai bài, ảnh nguồn khớp dòng đã chọn và xác nhận đúng dòng. Ghi lỗi kèm bài/trang và cách tái hiện.
- [ ] Tại thời điểm lập kế hoạch, hai đường dẫn PDF của sách id 4 và 5 đều không còn trỏ tới tệp đọc được. Lấy lại đúng hai PDF và đối chiếu với thông tin tệp đã nhập trước khi đánh số trang. Khi thiếu PDF vẫn kiểm được thao tác hàng đợi, nhưng phải để mở kết luận về ảnh nguồn và độ đúng dữ liệu.
- [ ] Dùng hồ sơ tạm riêng cho mọi lần nhập thử. Giữ nguyên sách và tiến độ thật. Toàn bộ phép đo dùng OCR cục bộ, tắt đường gọi Vision/AI.

## 2. Đo lỗi trước khi sửa

- [ ] Đọc trực tiếp hai PDF để lập đáp án độc lập. Ghi ranh giới mỗi bài, trang PDF, vùng bảng và từ đầu/cuối của từng vùng. Trang hiển thị tính từ 1, chuyển sang chỉ số từ 0 khi gọi adapter. Bảng kéo dài qua hai trang có hai vùng thuộc cùng bảng. Hai bảng nằm cạnh nhau có hai định danh riêng. Ghi cả vùng hội thoại, ngữ pháp dễ nhầm trên các trang khó.
- [ ] Với mỗi sách, dùng cùng kết quả OCR trong hai lượt trên hai hồ sơ trống. Lượt A dùng ranh giới tự động và ghi riêng xung đột cần duyệt. Lượt B cấp ranh giới từ đáp án rồi chạy cùng bộ tìm bảng. Bảng xuất hiện đúng ở B sau khi bị mất hoặc gán sai ở A là ca điều tra chia bài. Bảng vẫn thừa, thiếu hoặc cắt sai ở B là ca điều tra định vị.
- [ ] Đối chiếu từng vùng theo trang và nội dung. Đếm riêng vùng sót, vùng lấy nhầm, vùng gán sai bài, vùng cắt mất hàng hoặc lấn sang hội thoại. Ghi số trang cần người mở duyệt trên tổng số trang. Báo số đếm và mẫu số riêng cho mỗi sách. Giữ lại một số bài của cả hai sách để nghiệm thu sau khi chốt quy tắc.

## 3. Sửa theo nhóm lỗi tái hiện được

- [ ] Nếu lỗi do chia bài, thêm ca kiểm thử từ mẫu xung đột vào test_splitter.py. Tận dụng đối chiếu mục lục, tiêu đề và số trang in hiện có. Khi còn hai mốc hợp lý, hiện hai trang ứng viên trong bước xác nhận ranh giới.
- [ ] Nếu lỗi do xác định bảng, thêm ca hồi quy vào test_vocab.py rồi sửa quy tắc hẹp nhất giải thích được mẫu. Kiểm cả trường hợp đối nghịch trên cùng bố cục, ví dụ bảng một hàng dưới tiêu đề mờ và một dòng hội thoại đánh số. Dùng cấu trúc cột, vị trí tiêu đề và khoảng cách tới đoạn kế tiếp để kiểm biên. Giữ vùng có bằng chứng yếu cho bước duyệt.
- [ ] Chạy lại A/B sau từng nhóm sửa. Chỉ giữ thay đổi khi nhóm lỗi mục tiêu giảm và các bài đối chứng không xuất hiện lỗi mới. Mỗi phiên triển khai giới hạn ở một module theo AGENTS.md.

## 4. Duyệt khung ngay trên trang và nghiệm thu

- [ ] Mở rộng luồng PySide6 hiện có. Sau xác nhận ranh giới và trước khi chấp nhận từ, hiện trang gốc với khung ứng viên. Người dùng có thể xác nhận, kéo chỉnh, bỏ qua hoặc mở một trang bất kỳ trong bài để vẽ khung bị thiếu. Ảnh tải nền, chuyển bài khi ảnh đang tải vẫn phải hiện đúng trang mới.
- [ ] Lưu quyết định theo bài, trang và tọa độ PDF bằng cơ chế checkpoint hiện có. Chỉnh khung làm mất hiệu lực crop và hàng trích từ khung cũ. Chỉ trích lại vùng bị tác động. Bỏ qua phải có hiệu lực sau khi tiếp tục nhập. Hủy thao tác giữ nguyên quyết định đã lưu. Tách phiên lưu dữ liệu, phiên điều phối và phiên giao diện theo tầng.
- [ ] Kiểm bằng Qt offscreen cho kéo khung ở hai mức phóng đại, vẽ thêm, bỏ qua, hủy và đóng/mở lại. Với khung đã chỉnh, kiểm từ đầu/cuối khớp ảnh và hàng cũ không bị nhập trùng. Chạy các test chia bài, định vị, importer, dialog và toàn bộ suite an toàn.
- [ ] Nghiệm thu trước duyệt bằng bảng số liệu từng sách so với phiên 2, gồm cả công duyệt. Nghiệm thu sau duyệt khi đối chiếu đủ hai sách có 0 bảng sót, 0 bảng thừa, 0 bảng sai bài, đủ hàng hai đầu và không lẫn hàng ngoài bảng. Sửa chính tả từng ô OCR là phép kiểm riêng. Cập nhật trạng thái AGENTS.md cuối mỗi phiên đã thực hiện.

## Lý do chọn cách này

Viết ngay thêm từ khóa theo từng giáo trình có chi phí ban đầu thấp khi OCR giữ đúng tiêu đề. Cách này dễ hỏng ở chính các bảng nhỏ có tiêu đề mờ, và không giúp phát hiện bài bị cắt sai trang. Hai lượt A/B tốn công lập đáp án một lần nhưng cho biết cần sửa tầng nào. Khoanh vùng để duyệt tốn thêm thao tác ở trang khó, đổi lại người dùng có thể sửa cả bảng lấy nhầm lẫn bảng bị bỏ sót. Chỉ đặt mục tiêu giảm công duyệt bằng con số sau khi đã đo lượt đầu.
