# -*- coding: utf-8 -*-
"""
Bảng 214 bộ thủ Khang Hy: tên Hán-Việt, nghĩa tiếng Việt, dạng biến thể.

CẦN RÀ LẠI. Bảng này soạn thủ công, không có nguồn mở nào cung cấp sẵn.
Tên Hán-Việt của bộ thủ khá thống nhất giữa các từ điển, nhưng nghĩa tiếng Việt
thì mỗi sách diễn đạt một kiểu, và một số bộ hiếm dễ nhầm. Nên đối chiếu với một
cuốn từ điển Hán-Việt trước khi đưa vào báo cáo.

Cột glyph_alt là dạng bộ khi đứng trong chữ, hoặc dạng giản thể. None nghĩa là bộ
không đổi hình.
"""

# idx: (name_hv, meaning_vi, glyph_alt)
RADICALS = {
1:("nhất","một",None), 2:("cổn","nét sổ",None), 3:("chủ","dấu chấm",None),
4:("phiệt","nét phẩy",None), 5:("ất","can Ất","乚"), 6:("quyết","nét móc",None),
7:("nhị","hai",None), 8:("đầu","phần đầu",None), 9:("nhân","người","亻"),
10:("nhi","trẻ nhỏ",None), 11:("nhập","vào",None), 12:("bát","tám","丷"),
13:("quynh","vùng biên",None), 14:("mịch","khăn trùm",None), 15:("băng","nước đá",None),
16:("kỷ","ghế dựa",None), 17:("khảm","há miệng",None), 18:("đao","con dao","刂"),
19:("lực","sức mạnh",None), 20:("bao","bao bọc",None), 21:("chuỷ","cái thìa",None),
22:("phương","hộp vuông",None), 23:("hệ","che đậy",None), 24:("thập","mười",None),
25:("bốc","bói toán",None), 26:("tiết","đốt tre","㔾"), 27:("hán","sườn núi",None),
28:("tư","riêng tư",None), 29:("hựu","lại nữa, tay phải",None), 30:("khẩu","cái miệng",None),
31:("vi","vây quanh",None), 32:("thổ","đất",None), 33:("sĩ","kẻ sĩ",None),
34:("truy","đi chậm",None), 35:("tuy","đi chậm",None), 36:("tịch","buổi tối",None),
37:("đại","to lớn",None), 38:("nữ","đàn bà",None), 39:("tử","con",None),
40:("miên","mái nhà",None), 41:("thốn","tấc",None), 42:("tiểu","nhỏ","⺌"),
43:("uông","yếu ớt","尣"), 44:("thi","thây người",None), 45:("triệt","mầm cây",None),
46:("sơn","núi",None), 47:("xuyên","sông","川"), 48:("công","công việc",None),
49:("kỷ","bản thân",None), 50:("cân","cái khăn",None), 51:("can","can, khiên",None),
52:("yêu","nhỏ bé",None), 53:("nghiễm","mái nhà",None), 54:("dẫn","bước dài",None),
55:("củng","chắp tay",None), 56:("dặc","bắn tên có dây",None), 57:("cung","cái cung",None),
58:("kệ","đầu con nhím","彑"), 59:("sam","lông tóc",None), 60:("xích","bước ngắn",None),
61:("tâm","tim, lòng","忄"), 62:("qua","cây giáo",None), 63:("hộ","cửa một cánh","户"),
64:("thủ","tay","扌"), 65:("chi","cành nhánh",None), 66:("phộc","đánh khẽ","攵"),
67:("văn","văn vẻ",None), 68:("đẩu","cái đấu",None), 69:("cân","cái rìu",None),
70:("phương","vuông",None), 71:("vô","không có","旡"), 72:("nhật","mặt trời",None),
73:("viết","nói rằng",None), 74:("nguyệt","mặt trăng",None), 75:("mộc","cây",None),
76:("khiếm","thiếu",None), 77:("chỉ","dừng lại",None), 78:("đãi","xương tàn","歺"),
79:("thù","binh khí",None), 80:("vô","chớ","母"), 81:("tỉ","so sánh",None),
82:("mao","lông",None), 83:("thị","họ",None), 84:("khí","hơi",None),
85:("thuỷ","nước","氵"), 86:("hoả","lửa","灬"), 87:("trảo","móng vuốt","爫"),
88:("phụ","cha",None), 89:("hào","hào quẻ",None), 90:("tường","mảnh gỗ","丬"),
91:("phiến","mảnh",None), 92:("nha","răng",None), 93:("ngưu","trâu bò","牜"),
94:("khuyển","con chó","犭"), 95:("huyền","đen huyền",None), 96:("ngọc","ngọc","王"),
97:("qua","quả dưa",None), 98:("ngoã","ngói",None), 99:("cam","ngọt",None),
100:("sinh","sinh ra",None), 101:("dụng","dùng",None), 102:("điền","ruộng",None),
103:("thất","vải, chân",None), 104:("nạch","bệnh tật",None), 105:("bát","gạt ngược",None),
106:("bạch","màu trắng",None), 107:("bì","da",None), 108:("mãnh","bát đĩa",None),
109:("mục","mắt",None), 110:("mâu","cây mâu",None), 111:("thỉ","mũi tên",None),
112:("thạch","đá",None), 113:("thị","chỉ bảo, thần linh","礻"), 114:("nhựu","vết chân thú",None),
115:("hoà","cây lúa",None), 116:("huyệt","cái hang",None), 117:("lập","đứng",None),
118:("trúc","tre","⺮"), 119:("mễ","gạo",None), 120:("mịch","sợi tơ","纟"),
121:("phẫu","đồ sành",None), 122:("võng","cái lưới","罒"), 123:("dương","con dê","⺷"),
124:("vũ","lông vũ",None), 125:("lão","già","耂"), 126:("nhi","mà, râu",None),
127:("lỗi","cái cày",None), 128:("nhĩ","tai",None), 129:("duật","cây bút","肀"),
130:("nhục","thịt","⺼"), 131:("thần","bề tôi",None), 132:("tự","tự mình, mũi",None),
133:("chí","đến",None), 134:("cữu","cái cối",None), 135:("thiệt","cái lưỡi",None),
136:("suyễn","sai lệch",None), 137:("chu","con thuyền",None), 138:("cấn","quẻ Cấn",None),
139:("sắc","màu sắc",None), 140:("thảo","cỏ","艹"), 141:("hô","vằn hổ",None),
142:("trùng","sâu bọ",None), 143:("huyết","máu",None), 144:("hành","đi",None),
145:("y","áo","衤"), 146:("á","che đậy","覀"), 147:("kiến","nhìn thấy","见"),
148:("giác","cái sừng",None), 149:("ngôn","lời nói","讠"), 150:("cốc","thung lũng",None),
151:("đậu","hạt đậu",None), 152:("thỉ","con lợn",None), 153:("trĩ","loài sâu",None),
154:("bối","vỏ sò, tiền","贝"), 155:("xích","màu đỏ",None), 156:("tẩu","chạy",None),
157:("túc","bàn chân",None), 158:("thân","thân mình",None), 159:("xa","xe","车"),
160:("tân","cay",None), 161:("thần","chi Thìn",None), 162:("sước","bước đi","辶"),
163:("ấp","vùng đất","阝"), 164:("dậu","chi Dậu",None), 165:("biện","phân biệt",None),
166:("lý","dặm, làng",None), 167:("kim","kim loại","钅"), 168:("trường","dài","长"),
169:("môn","cửa","门"), 170:("phụ","gò đất","阝"), 171:("đãi","bắt kịp",None),
172:("chuy","chim đuôi ngắn",None), 173:("vũ","mưa",None), 174:("thanh","màu xanh","青"),
175:("phi","không phải",None), 176:("diện","khuôn mặt",None), 177:("cách","da thuộc",None),
178:("vi","da mềm","韦"), 179:("cửu","rau hẹ",None), 180:("âm","âm thanh",None),
181:("hiệt","đầu, trang","页"), 182:("phong","gió","风"), 183:("phi","bay","飞"),
184:("thực","ăn","饣"), 185:("thủ","cái đầu",None), 186:("hương","thơm",None),
187:("mã","con ngựa","马"), 188:("cốt","xương",None), 189:("cao","cao",None),
190:("tiêu","tóc dài",None), 191:("đấu","đánh nhau",None), 192:("sưởng","rượu nếp",None),
193:("cách","cái đỉnh",None), 194:("quỷ","con quỷ",None), 195:("ngư","con cá","鱼"),
196:("điểu","con chim","鸟"), 197:("lỗ","đất mặn","卤"), 198:("lộc","con hươu",None),
199:("mạch","lúa mạch","麦"), 200:("ma","cây gai",None), 201:("hoàng","màu vàng","黄"),
202:("thử","lúa nếp",None), 203:("hắc","màu đen",None), 204:("chỉ","thêu thùa",None),
205:("mãnh","con ếch","黾"), 206:("đỉnh","cái đỉnh",None), 207:("cổ","cái trống",None),
208:("thử","con chuột",None), 209:("tị","cái mũi",None), 210:("tề","ngang bằng","齐"),
211:("xỉ","răng","齿"), 212:("long","con rồng","龙"), 213:("quy","con rùa","龟"),
214:("dược","ống sáo",None),
}

assert len(RADICALS) == 214, len(RADICALS)
