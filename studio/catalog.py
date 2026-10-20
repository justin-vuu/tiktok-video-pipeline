STYLES = {
    "story": {
        "name": "Chuyện đời",
        "direction": "Kể chuyện đời thường hư cấu, cụ thể, có nhân vật và bước ngoặt nhỏ. Giọng chân thành, không lên lớp.",
        "visual": "ảnh điện ảnh chân thực, màu phim tự nhiên, ánh sáng có chủ đích, bối cảnh đời thường Việt Nam",
        "voice": "male",
    },
    "healing": {
        "name": "Chữa lành",
        "direction": "Tâm sự nhẹ nhàng, cho phép người nghe nghỉ ngơi, có hình ảnh cụ thể. Không hứa chữa bệnh, không sáo rỗng.",
        "visual": "tranh minh họa kỹ thuật số mềm mại, màu pastel ấm, ánh sáng dịu, nhiều khoảng trống, cảm giác an yên",
        "voice": "female",
    },
    "talk": {
        "name": "Tâm sự đời",
        "direction": (
            "Lời bình tâm sự về một nghịch lý trong gia đình, hôn nhân, tình thân hay phận người: đặt hai vế đối lập "
            "cạnh nhau, dùng hình ảnh đời thường cụ thể, nói thẳng với người xem bằng 'bạn', không kể chuyện một "
            "nhân vật có tên. Kết bằng một câu chốt thấm thía và một câu hỏi ngắn mời người xem bình luận. "
            "Không quy chụp, không xúc phạm giới nào."
        ),
        "visual": (
            "tranh hoạt hình nét mực đen trắng đơn giản kiểu truyện tranh tô màu, chỉ thang xám, nhân vật đầu tròn "
            "mắt to hiền lành, nền phòng tối xanh đen, nét viền sạch rõ"
        ),
        "voice": "female",
    },
    "wisdom": {
        "name": "Chiêm nghiệm",
        "direction": "Chiêm nghiệm theo tinh thần phương Đông, dùng ẩn dụ thiên nhiên. Không bịa danh ngôn hay gán lời cho cổ nhân.",
        "visual": "cổ phong phương Đông, nét thủy mặc kết hợp ánh sáng điện ảnh, sương núi, tre, trà, gam màu trầm",
        "voice": "male",
    },
}

PHOTOS = {
    "forest": ("photo-1441974231531-c6227db76b6e", "Nắng xuyên qua rừng xanh; bình yên, trưởng thành"),
    "lake": ("photo-1470770841072-f978cf4d019e", "Núi và mặt hồ tĩnh lặng; suy ngẫm, cô độc"),
    "mountain": ("photo-1464822759023-fed622ff2c3b", "Đỉnh núi cao; thử thách, kiên trì"),
    "journey": ("photo-1501785888041-af3ef285b470", "Hồ giữa núi, con thuyền; hành trình, buông bỏ"),
    "ocean": ("photo-1518837695005-2083093ee35b", "Sóng biển và bầu trời; cảm xúc, thay đổi"),
    "road": ("photo-1476231682828-37e571bc172f", "Con đường uốn lượn giữa rừng; lựa chọn, đi tiếp"),
    "desk": ("photo-1499750310107-5fef28a66643", "Bàn làm việc và sổ tay; công việc, viết, suy tư"),
    "city": ("photo-1519608487953-e999c86e7455", "Phố vắng và ánh đèn ban đêm; làm việc muộn, cô đơn"),
    "leaves": ("photo-1448375240586-882707db888b", "Rừng cây xanh; chữa lành, thời gian"),
}


def photo_url(key: str, width: int = 1200) -> str:
    return f"https://images.unsplash.com/{PHOTOS[key][0]}?auto=format&fit=crop&w={width}&q=85"
