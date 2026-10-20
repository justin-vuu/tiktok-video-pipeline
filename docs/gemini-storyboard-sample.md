# Storyboard thử nghiệm: Chỗ Của Mình

Đích đến: tạo từng ảnh bằng Gemini trên trình duyệt, dùng tài khoản người dùng
đã chọn. Không sử dụng Gemini API hoặc bật billing.

Đây là bản thử nghiệm kết nối bằng thao tác trình duyệt của trợ lý, chưa phải
tính năng web LẶNG tự chạy độc lập.

## Thời gian

Các mốc được tính từ clip có giọng đọc thực tế của video
`241b6683f6e04d5a9c0838468d20fec1`, không do mô hình đoán.

| Cảnh | Bắt đầu | Kết thúc | Hình ảnh |
| --- | --- | --- | --- |
| 1 | 0,00s | 9,17s | Lan ở lại văn phòng làm báo cáo |
| 2 | 9,17s | 17,59s | Túi cọ vẽ bị bỏ quên dưới bàn |
| 3 | 17,59s | 28,27s | Lan nhẹ nhàng từ chối đồng nghiệp |
| 4 | 28,27s | 37,20s | Lan trở lại vẽ tranh |

Container MP4 cuối có thể dài hơn tổng clip một chút do đóng gói âm thanh.

## Quy tắc hình ảnh chung

Ảnh dọc 9:16. Nhân vật hư cấu: Lan, nữ Việt Nam khoảng 27 tuổi, tóc đen thẳng
dài ngang vai, mặt trái xoan, áo sơ mi kem, quần tối màu. Phong cách ảnh điện ảnh
chân thực, cảm xúc kín đáo, màu phim tự nhiên. Không chữ, không logo do mô hình
thêm vào. Chừa vùng dưới thoáng cho phụ đề. Giữ nguyên các dấu hiệu nguồn gốc
mà dịch vụ tạo ảnh tự thêm.

Tạo các cảnh trong cùng cuộc trò chuyện. Dùng ảnh đầu làm tham chiếu và kiểm tra
ngoại hình sau từng ảnh; chỉ nhắc lại prompt không bảo đảm nhân vật đồng nhất.

## Prompt từng cảnh

### Cảnh 1

Tạo một ảnh dọc 9:16 cho cảnh đầu của video kể chuyện đời thường Việt Nam.
Nhân vật hư cấu: Lan, nữ Việt Nam khoảng 27 tuổi, tóc đen thẳng dài ngang vai,
mặt trái xoan, áo sơ mi màu kem, quần tối màu. Cảnh: 11 giờ đêm, Lan ngồi một
mình bên bàn làm việc trong văn phòng gần như tắt đèn, mệt mỏi sau khi nhận
làm báo cáo giúp đồng nghiệp. Cốc cà phê nguội, laptop sáng, túi vải có vài
cây cọ vẽ lộ ra dưới bàn gợi ước mơ bị bỏ quên. Góc máy trung rộng từ chéo
phía trước, nhân vật ở giữa khung hình, ánh đèn bàn vàng ấm tương phản màu
xanh đêm ngoài cửa sổ. Cinematic realistic photography, tinh tế, cảm xúc
kín đáo, màu phim tự nhiên. Chừa vùng phía dưới thoáng để ghép phụ đề.
Không chèn chữ, không logo. Hãy tạo ảnh thực sự, không chỉ trả lại prompt.

### Cảnh 2

Tạo ảnh tiếp theo trong cùng câu chuyện. Giữ nguyên Lan, quần áo, túi vải,
bàn làm việc và tông màu của ảnh trước. Góc máy thấp nhìn chéo dưới bàn:
túi vải chứa cọ vẽ và sổ phác thảo nằm im cạnh chân ghế. Lan cúi xuống nhìn
túi, một tay chạm nhẹ vào quai túi, nét mặt tiếc nuối. Ánh laptop xanh nhạt
và đèn bàn vàng tạo một vùng sáng nhỏ giữa văn phòng tối. Ý nghĩa: sở thích
của cô bị bỏ quên vì luôn chiều lòng người khác. Ảnh điện ảnh chân thực,
dọc 9:16, không chèn chữ; vùng phụ đề phía dưới không chứa chi tiết quan trọng.

### Cảnh 3

Tạo ảnh tiếp theo, giữ đúng khuôn mặt, tóc và áo sơ mi kem của Lan trong
ảnh đầu. Sáng hôm sau trong cùng văn phòng, ánh nắng dịu xuyên cửa kính.
Lan đứng đối diện một đồng nghiệp bên bàn làm việc, bình tĩnh lắc đầu nhẹ
và đưa tay ra cử chỉ từ chối lịch sự. Đồng nghiệp đang gật đầu thông cảm,
không có xung đột. Trung cảnh hai người, nét mặt Lan nhẹ nhõm nhưng còn
chút ngập ngừng. Tông phim chuyển sáng và ấm hơn. Ảnh dọc 9:16,
chân thực, không chữ, giữ vùng dưới thoáng cho phụ đề.

### Cảnh 4

Tạo ảnh kết thúc với đúng nhân vật Lan của ảnh đầu. Buổi tối trong một
góc học vẽ nhỏ ấm áp, Lan ngồi trước giá vẽ, tay cầm cây cọ từ túi vải đã
xuất hiện ở cảnh trước, đặt nét màu đầu tiên lên tranh. Gương mặt nhẹ nhõm,
nụ cười rất nhỏ. Áo sơ mi kem, tóc đen ngang vai không đổi. Ánh đèn vàng,
bảng màu và một chậu cây làm nền. Góc máy chéo qua vai thấy cả nét mặt và
tay vẽ. Cảm giác tìm lại bản thân, không phô trương. Dọc 9:16, ảnh điện
ảnh chân thực, không chữ, chừa không gian dưới cho phụ đề.
