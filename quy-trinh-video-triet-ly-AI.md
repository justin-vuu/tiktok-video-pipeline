# Quy trình End-to-End: Video Triết Lý Nhân Sinh bằng AI

## 1. Tổng quan kiến trúc

```
[1] Script Generator (LLM)
      ↓ (text triết lý + chia đoạn/scene)
[2] TTS Engine (giọng đọc AI)
      ↓ (file audio .mp3/.wav + timestamps)
[3] Image Generator (AI ảnh theo từng scene)
      ↓ (ảnh .png/.jpg theo prompt)
[4] Forced Alignment / Subtitle (khớp phụ đề với audio)
      ↓ (file .srt hoặc .ass)
[5] Video Assembler (ffmpeg/moviepy)
      ↓ ghép ảnh + audio + phụ đề + nhạc nền + hiệu ứng Ken Burns
[6] Output: video .mp4 hoàn chỉnh (9:16, 1080x1920)
```

Toàn bộ pipeline chạy bằng 1 lệnh CLI, input là 1 "chủ đề" hoặc 1 script có sẵn, output là file video sẵn sàng đăng.

---

## 2. Danh sách API cần đăng ký

| Bước | Dịch vụ | API cần lấy | Ghi chú |
|---|---|---|---|
| Viết script | **Anthropic API** (Claude) | `ANTHROPIC_API_KEY` tại console.anthropic.com | Bạn dùng Claude Code nên có thể tận dụng sẵn key này |
| Giọng đọc AI (tiếng Việt) | **ElevenLabs** | `ELEVENLABS_API_KEY` tại elevenlabs.io | Hỗ trợ tiếng Việt khá tốt, có voice cloning, trả phí theo ký tự |
| Giọng đọc AI (thay thế rẻ hơn) | **FPT.AI TTS** hoặc **VBee** | API key qua đăng ký doanh nghiệp/cá nhân tại fpt.ai hoặc vbee.vn | Giọng Việt tự nhiên, giá rẻ hơn ElevenLabs, phù hợp scale nhiều video |
| Ảnh AI | **OpenAI Images API (gpt-image-1)** hoặc **Replicate** (chạy model Flux/SDXL) | `OPENAI_API_KEY` hoặc `REPLICATE_API_TOKEN` | Replicate linh hoạt hơn, nhiều style model để chọn |
| Ảnh AI (thay thế) | **Leonardo AI API** | API key tại leonardo.ai | Có style "cinematic" sẵn, hợp nội dung triết lý |
| Forced alignment / phụ đề | **OpenAI Whisper API** | dùng chung `OPENAI_API_KEY` | Dùng để tạo timestamp chính xác từng từ, khớp phụ đề với giọng đọc |
| Nhạc nền | Không cần API | Lấy từ thư viện free: Pixabay Music, YouTube Audio Library, CapCut sound library | Tránh bản quyền |
| Ghép video | Không cần API | `ffmpeg` (cài local) + Python `moviepy` hoặc `ffmpeg-python` | Chạy hoàn toàn local |

**Gợi ý tiết kiệm chi phí khi mới bắt đầu:**
- Script: Claude API (rẻ, chất lượng tốt cho tiếng Việt)
- TTS: thử free tier ElevenLabs trước, nếu cần scale nhiều video/ngày thì chuyển qua FPT.AI/VBee
- Ảnh: Replicate (trả theo giây compute, khá rẻ với SDXL/Flux)

---

## 2.5. Phiên bản 100% LOCAL / MIỄN PHÍ — chạy trên M1 Max 32GB

Máy của bạn (Apple Silicon, 32GB unified memory) đủ mạnh để chạy toàn bộ pipeline không cần trả phí API nào, đổi lại tốc độ chậm hơn và chất lượng ảnh/giọng đọc có thể không bằng bản trả phí. Nhờ pipeline đã thiết kế theo **adapter pattern** ở phần 4, bạn chỉ cần viết thêm 1 provider "local" cho mỗi bước mà không phải sửa code các module khác.

| Bước | Công cụ local | Cách chạy trên M1 Max | Ghi chú thực tế |
|---|---|---|---|
| Script (LLM) | **Ollama** + model `qwen2.5:14b` hoặc `llama3.1:8b` | `ollama run qwen2.5:14b`, expose API local tại `localhost:11434` (OpenAI-compatible) | Qwen2.5 viết tiếng Việt khá tốt, 14B chạy ổn trong 32GB RAM. Free, không cần internet sau khi tải model |
| Giọng đọc AI (TTS tiếng Việt) | **F5-TTS** hoặc **XTTS-v2 (Coqui)** fine-tune tiếng Việt, hoặc **viXTTS** | Chạy bằng Python + PyTorch với backend `mps` (Metal) | Đây là điểm yếu nhất: TTS tiếng Việt mã nguồn mở chưa tự nhiên bằng ElevenLabs/FPT.AI. XTTS-v2 hỗ trợ voice cloning nếu bạn có sẵn 1 đoạn mẫu giọng Việt 10-20s |
| Ảnh AI | **Stable Diffusion (SDXL Turbo)** hoặc **Flux Schnell** qua `diffusers` (MPS) hoặc **ComfyUI** (có hỗ trợ Mac native) | `pip install diffusers torch accelerate`, set device `mps` | SDXL Turbo cho ảnh 1024x1024 trong ~5-15s/ảnh trên M1 Max. Flux Schnell chất lượng cao hơn nhưng nặng hơn, nên dùng bản quantize (GGUF/Q8) để đỡ tốn RAM |
| Phụ đề / forced alignment | **faster-whisper** hoặc **whisper.cpp** | Chạy local, có bản tối ưu cho Apple Silicon (Core ML) | Nhanh và chính xác, không thua bản API của OpenAI |
| Ghép video | `ffmpeg` (đã free từ đầu) | không đổi | — |
| Nhạc nền | Pixabay/YouTube Audio Library | không đổi | — |

**Cài đặt nhanh:**
```bash
# LLM
brew install ollama
ollama pull qwen2.5:14b

# TTS + Image gen (trong virtualenv riêng vì hay xung đột dependency)
pip install torch torchvision torchaudio   # bản có hỗ trợ MPS
pip install TTS                             # Coqui TTS (XTTS-v2)
pip install diffusers transformers accelerate

# Whisper
pip install faster-whisper
```

**Lưu ý quan trọng:**
- Lần đầu chạy mỗi model sẽ tải vài GB (SDXL ~6-7GB, XTTS-v2 ~2GB, Qwen2.5 14B ~9GB) — cần ổ đĩa trống và internet để tải 1 lần, sau đó chạy hoàn toàn offline.
- RAM 32GB là unified (CPU+GPU dùng chung), nên tránh chạy đồng thời LLM 14B + SDXL cùng lúc — pipeline nên chạy **tuần tự** (sinh script xong mới load model ảnh, sinh ảnh xong mới giải phóng để chạy TTS) để không bị tràn RAM.
- Có thể bắt đầu mix: dùng Claude API (rẻ) cho script vì chất lượng văn rất quan trọng, còn ảnh + TTS chạy local để tiết kiệm — đây là điểm cân bằng tốt giữa chi phí và chất lượng.

---

## 3. Tech stack đề xuất

- **Ngôn ngữ:** Python 3.11+ (dễ dùng cho cả gọi API, xử lý audio, ffmpeg wrapper)
- **Thư viện chính:**
  - `anthropic` — gọi Claude để viết script
  - `requests` — gọi ElevenLabs/Replicate/OpenAI
  - `moviepy` hoặc `ffmpeg-python` — ghép video
  - `pillow` — xử lý/resize ảnh, thêm hiệu ứng
  - `pysrt` hoặc tự build — xử lý file phụ đề
- **Cấu trúc project:**
```
video-pipeline/
├── config.yaml          # cấu hình voice, style ảnh, độ dài video...
├── .env                 # các API key
├── src/
│   ├── script_gen.py    # gọi Claude sinh script + chia scene
│   ├── tts_gen.py        # gọi TTS sinh audio
│   ├── image_gen.py      # gọi image API sinh ảnh từng scene
│   ├── subtitle_gen.py   # forced alignment, tạo .srt
│   ├── video_assembler.py # ghép tất cả bằng ffmpeg
│   └── pipeline.py       # orchestrator, chạy toàn bộ luồng
├── assets/
│   ├── music/            # nhạc nền free-copyright
│   └── fonts/            # font cho phụ đề
├── output/               # video hoàn chỉnh
└── main.py               # entry point CLI
```

---

## 4. Prompt siêu chi tiết để đưa vào Claude Code (chạy Opus ở mode Plan)

Dán nguyên đoạn dưới đây vào Claude Code. Vì bạn dùng Plan mode trước, Opus sẽ tự lên kế hoạch chi tiết (file structure, thứ tự implement, edge cases) trước khi viết code.

```
Tôi muốn bạn xây dựng một pipeline Python end-to-end để tự động tạo video ngắn
(dạng Reels/Shorts, tỉ lệ 9:16, 1080x1920) có nội dung "triết lý nhân sinh / đạo lý
cuộc sống", với giọng đọc AI và ảnh minh họa AI, hoàn toàn tự động từ 1 chủ đề đầu vào.

## Yêu cầu tổng quan
- Input: một chủ đề hoặc ý tưởng ngắn (ví dụ: "bài học về sự kiên trì")
- Output: 1 file .mp4 hoàn chỉnh, có giọng đọc, ảnh AI đổi theo từng đoạn, phụ đề
  burn-in đồng bộ với giọng đọc, nhạc nền nhẹ, hiệu ứng zoom nhẹ (Ken Burns) trên ảnh tĩnh.
- Toàn bộ chạy qua 1 lệnh CLI duy nhất: `python main.py --topic "chủ đề" --voice "ten_voice"`
- Code phải modular, mỗi bước là 1 module riêng, có thể test độc lập (ví dụ chỉ test
  bước sinh ảnh mà không cần chạy lại TTS).
- ƯU TIÊN 100% LOCAL, KHÔNG TRẢ PHÍ: chạy trên máy Mac M1 Max 32GB RAM (Apple Silicon,
  Metal/MPS). Mọi model nặng (LLM, TTS, image gen, whisper) phải chạy local, không gọi
  API trả phí nào, trừ khi tôi chủ động bật flag để dùng Claude API cho bước sinh script
  (vì chất lượng văn quan trọng và chi phí rất thấp).
- Vì RAM là unified memory dùng chung CPU/GPU, pipeline phải chạy TUẦN TỰ giữa các bước
  nặng (load model → dùng → giải phóng/unload trước khi load model tiếp theo), không
  load đồng thời LLM 14B + SDXL + TTS cùng lúc để tránh tràn RAM.
- Toàn bộ API key (nếu có dùng Claude API cho script) đọc từ file .env, không hardcode.

## Chi tiết từng bước (modules)

### 1. script_gen.py — Sinh script bằng Anthropic API
- Input: chủ đề (string)
- Gọi Claude (model claude-opus-4-7 hoặc claude-sonnet-4-6) với system prompt yêu cầu:
  - Viết bằng tiếng Việt, giọng văn trầm, suy ngẫm, độ dài 150-220 từ
  - Cấu trúc: 1 câu mở đầu gây chú ý/đặt câu hỏi → 3-4 đoạn triển khai ý → 1 câu kết
    đọng lại, dễ nhớ, có thể trích dẫn
  - Output PHẢI là JSON với schema:
    {
      "title": "tên ngắn cho video",
      "scenes": [
        {"text": "đoạn text của scene 1", "image_prompt": "prompt mô tả ảnh minh hoạ,
         phong cách cinematic, ẩn dụ, không có chữ trong ảnh"},
        ...
      ]
    }
  - Mỗi scene khoảng 2-3 câu để dễ chia ảnh, tổng 6-10 scenes cho 60-90 giây video
  - Nội dung phải là sáng tác mới, không sao chép nguyên văn quote/bài viết có sẵn
- Parse JSON output, validate schema, retry nếu Claude trả về không đúng format
- Lưu kết quả vào output/<video_id>/script.json

### 2. tts_gen.py — Sinh giọng đọc
- Input: full text (ghép toàn bộ scenes) hoặc sinh riêng từng scene (cân nhắc trade-off:
  sinh riêng từng scene giúp dễ đồng bộ ảnh với audio hơn — ưu tiên cách này)
- Viết theo adapter pattern (TTSProvider abstract class), implement TRƯỚC TIÊN 1 provider
  local: dùng Coqui TTS (XTTS-v2) hoặc F5-TTS chạy trên thiết bị `mps`, có thể clone giọng
  từ 1 file mẫu tiếng Việt 10-20s nếu tôi cung cấp. Để sẵn 1 provider ElevenLabs làm
  phương án dự phòng (đọc API key từ .env nếu có, optional, không bắt buộc).
- Trả về: file .mp3/.wav cho từng scene + tổng thời lượng từng file (dùng để tính thời gian
  hiển thị ảnh tương ứng)
- Lưu vào output/<video_id>/audio/scene_001.wav, scene_002.wav...
- Sau khi dùng xong, giải phóng model TTS khỏi RAM (del model, torch.mps.empty_cache())
  trước khi pipeline chuyển sang bước sinh ảnh

### 3. image_gen.py — Sinh ảnh AI cho từng scene
- Input: image_prompt của từng scene (lấy từ script.json)
- Viết theo adapter pattern tương tự TTS. Provider local mặc định: Stable Diffusion
  (SDXL Turbo, ít bước inference, nhanh) chạy qua `diffusers` với device `mps`. Cho phép
  cấu hình đổi sang Flux Schnell (bản quantize) nếu muốn chất lượng cao hơn, chấp nhận
  chậm hơn. Để sẵn 1 provider Replicate/OpenAI Images làm phương án dự phòng (optional,
  đọc API key từ .env nếu có).
- Thêm style cố định vào mọi prompt: "cinematic lighting, moody atmosphere, symbolic,
  no text, no watermark, 9:16 aspect ratio"
- Output: ảnh .png độ phân giải tối thiểu 1080x1920 (upscale nếu model native ra ảnh nhỏ
  hơn, dùng Pillow resize hoặc model upscaler nếu cần), lưu vào
  output/<video_id>/images/scene_001.png...
- Xử lý lỗi: nếu ảnh bị NSFW-block hoặc lỗi, tự động thử lại với prompt rút gọn (tối đa 2 lần)
- Sau khi sinh xong toàn bộ ảnh, giải phóng model khỏi RAM trước khi chuyển bước tiếp theo

### 4. subtitle_gen.py — Tạo phụ đề khớp giọng đọc
- Dùng `faster-whisper` (chạy local, có tối ưu cho Apple Silicon) để chạy forced alignment
  trên từng file audio, lấy timestamp theo từng từ/cụm từ. Không cần API key, không cần
  internet sau khi đã tải model lần đầu.
- Sinh ra file .srt cho từng scene, style phụ đề dạng "từng câu ngắn xuất hiện đúng nhịp đọc"
- Gộp lại thành 1 file subtitle.srt cho toàn video (cộng dồn timestamp theo thứ tự scene)

### 5. video_assembler.py — Ghép video cuối cùng bằng ffmpeg/moviepy
- Với mỗi scene: lấy ảnh tĩnh, áp Ken Burns effect (zoom in nhẹ 1.0 → 1.08 trong suốt
  thời gian audio của scene đó), độ dài clip = độ dài audio tương ứng
- Nối tất cả scene clips lại theo thứ tự, có transition fade nhẹ (0.3s) giữa các scene
- Overlay nhạc nền (từ assets/music/, chọn random hoặc theo config), giảm âm lượng nhạc
  xuống ~15-20% so với giọng đọc, fade-in/fade-out đầu cuối
- Burn-in phụ đề từ subtitle.srt, font dễ đọc, có outline/shadow để nổi trên mọi nền ảnh
- Export ra output/<video_id>/final_video.mp4, codec H.264, 1080x1920, 30fps

### 6. pipeline.py — Orchestrator
- Chạy lần lượt 5 bước trên, log rõ từng bước (bắt đầu/kết thúc/lỗi)
- Cho phép resume: nếu script.json đã tồn tại thì skip bước 1, nếu audio đã tồn tại thì
  skip bước 2, v.v. (check theo file tồn tại trong thư mục output/<video_id>/)
- Lưu toàn bộ intermediate files để debug, không tự xoá

### 7. main.py — CLI entry point
- Dùng argparse hoặc click
- Args: --topic (bắt buộc), --voice (optional, mặc định lấy từ config.yaml),
  --image-style (optional), --output-name (optional)
- In ra đường dẫn video cuối cùng khi xong

## Cấu hình
- Tạo config.yaml chứa: provider mặc định cho mỗi bước (local/api), tên model local
  (ví dụ "qwen2.5:14b", "xtts-v2", "sdxl-turbo"), voice_id/sample giọng mẫu, image style
  mặc định, thư mục nhạc nền, font phụ đề, số scenes mặc định
- Tạo .env.example liệt kê các API key OPTIONAL (chỉ cần nếu bật provider trả phí):
  ANTHROPIC_API_KEY (cho bước script nếu không dùng Ollama local), ELEVENLABS_API_KEY,
  REPLICATE_API_TOKEN, OPENAI_API_KEY — tất cả đều optional, mặc định pipeline chạy
  không cần key nào

## Yêu cầu phi chức năng
- Xử lý lỗi rõ ràng ở mỗi bước gọi API (timeout, rate limit, retry với backoff)
- Viết log ra console rõ ràng từng bước đang chạy, thời gian mỗi bước
- Code có docstring và type hints đầy đủ
- Viết kèm README.md hướng dẫn cài đặt (requirements.txt), cấu hình .env, và cách chạy

## Việc cần làm trước khi code (ở Plan mode)
Trước khi viết bất kỳ dòng code nào, hãy:
1. Đề xuất cấu trúc file/folder chi tiết
2. Liệt kê các package cần cài (requirements.txt)
3. Chỉ ra các điểm rủi ro/edge case cần xử lý (ví dụ: ảnh bị filter, audio quá ngắn/dài
   so với dự kiến, API rate limit)
4. Hỏi lại tôi nếu có quyết định kiến trúc nào cần tôi xác nhận trước
Sau khi tôi duyệt plan, mới bắt đầu implement từng module theo đúng thứ tự 1→7 ở trên.
```

---

## 5. Lưu ý khi triển khai thực tế

- **Bản quyền:** script phải là nội dung tự sinh/tự viết, không copy nguyên văn từ nguồn khác; nhạc nền dùng nguồn free-copyright.
- **Chi phí ước tính/video** (tham khảo, có thể thay đổi theo provider): script ~vài cent, TTS ~vài nghìn-vài chục nghìn đồng tuỳ độ dài, ảnh AI ~vài nghìn đồng/ảnh x 6-10 ảnh. Nên test với 1-2 video trước khi chạy batch lớn.
- **Tốc độ:** bước sinh ảnh AI thường là bottleneck (vài giây - vài chục giây/ảnh), có thể chạy song song (async) để rút ngắn thời gian tổng.
- **Mở rộng sau này:** có thể thêm bước tự động đăng lên Facebook/TikTok qua Graph API/TikTok API khi pipeline ổn định.
