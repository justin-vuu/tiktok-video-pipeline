# TikTok AI Video Pipeline

## LẶNG Studio — web tạo video trên Mac

Mở **`Mo Lang Studio.command`** bằng cách nhấp đúp, rồi truy cập
**http://127.0.0.1:7860**. Giữ cửa sổ Terminal của studio mở trong lúc sử dụng.

Nhập chủ đề → chọn Chuyện đời / Chữa lành / Triết lý & cổ phong → bấm tạo →
tạo ảnh từng cảnh trên Gemini → bấm **Dựng video** → xem và tải MP4. Có giọng nam/nữ, thời lượng mục tiêu 30/45/60 giây,
nhạc nền, phụ đề, thư viện và tiếp tục sau khi gián đoạn.

### Cài thủ công

```bash
python3 -m venv .venv-web
.venv-web/bin/python -m pip install -r requirements-web.txt
.venv-web/bin/python -m studio.server
```

Cần Python 3.11+, `ffmpeg` và `ffprobe` (`brew install ffmpeg`), font
`/System/Library/Fonts/Supplemental/Arial Bold.ttf`, cùng Claude Code hoặc
Codex CLI đã đăng nhập. Môi trường web tách biệt với các model nặng của CLI cũ.

- **Kịch bản:** gọi `claude -p` (mặc định) hoặc `codex exec` bằng phiên đăng nhập
  trên máy; sử dụng hạn mức của tài khoản đó. Không trích xuất cookie hay token.
  Claude không được cấp công cụ; Codex chạy trong thư mục tạm, sandbox read-only,
  không nạp cấu hình người dùng.
- **Ảnh — Gemini theo từng cảnh (mặc định):** AI viết kèm phong cách chung, ngoại hình
  nhân vật và mô tả khung hình cho từng cảnh. Sau khi có giọng đọc, studio tính mốc
  giây thật của mỗi cảnh, ghép thành prompt riêng rồi dừng ở trạng thái **Chờ ảnh Gemini**.
  Bạn dán prompt vào Gemini trên trình duyệt bằng tài khoản của mình, không dùng
  Gemini API hay billing. Ảnh tải về có tên `Gemini_Generated_Image_*` trong `~/Downloads`
  (tạo sau khi bảng cảnh sẵn sàng) được tự xếp vào cảnh trống đầu tiên. Cũng có thể
  kéo thả, dán ⌘V hoặc chọn file. Đổi ảnh sau khi xong rồi bấm **Dựng lại với ảnh mới**,
  chỉ cảnh đổi ảnh được dựng lại. Nếu macOS chưa cấp quyền đọc Downloads cho Terminal,
  web báo và bạn kéo thả thay thế.
- **Ảnh — thư viện (tự động hoàn toàn):** AI chọn từ thư viện ảnh Unsplash giới hạn
  trong `studio/catalog.py`, theo mô tả hình ảnh ẩn dụ; không phải ảnh AI tạo riêng.
  Nguồn từng cảnh có trong `sources.json`.
- **Giọng:** Edge TTS trực tuyến, Nam Minh / Hoài My, có mốc từng từ cho phụ đề.
  Kết nối Internet là bắt buộc và dịch vụ có thể gián đoạn.
- **Nhạc:** ambient tổng hợp trên máy, không tải bài hát thương mại.
- **Video:** H.264/AAC, 720 × 1280, 24 fps, chuyển động zoom nhẹ, fade từng cảnh.
  Phụ đề vẽ bằng Pillow nên không cần bản FFmpeg có libass.
  Thời lượng thực tế tùy số chữ và tốc độ đọc, không cam kết khớp tuyệt đối mục tiêu.
- **Bố cục "Khung giấy":** nền giấy, tít vàng cố định ở trên (lấy từ trường `hook`),
  logo tròn ghi tên kênh nếu nhập, ảnh ngang 16:9 ở giữa, phụ đề 2–3 chữ viết hoa,
  bướm bay ở dưới. Nền, bướm, tít đều vẽ bằng Pillow (`frame_loop`, vòng lặp 4 giây),
  ảnh cảnh được yêu cầu khung ngang. Sắc thái **Tâm sự đời** tự chọn bố cục này,
  viết kiểu lời bình hai vế đối lập, kết bằng câu hỏi mời bình luận.

Gói ChatGPT/Claude/Gemini trong ứng dụng không được coi là API key tạo ảnh
hoặc giọng đọc. Studio gọi **Claude Code/Codex** để viết kịch bản; Gemini Pro được dùng
qua trình duyệt do bạn tự thao tác, studio không điều khiển hay đăng nhập Gemini. Tham khảo cơ chế CLI chính thức:
[Claude print mode](https://code.claude.com/docs/en/headless),
[Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode).

### Dữ liệu và xử lý lỗi

Video nằm trong `.studio/jobs/<id>/final.mp4`, cùng kịch bản, phụ đề SRT và nguồn ảnh.
`.studio/` được bỏ qua bởi Git. Chủ đề/lời đọc được gửi tới AI và dịch vụ giọng đọc
để tạo nội dung; bản dựng được lưu trên máy, không tự đăng lên TikTok.

Chỉ một video chạy mỗi lần. Có thể bấm **Dừng**, sau đó **Thử lại từ bước đã lưu**.
Nếu tắt server, khởi động lại rồi vào Thư viện để tiếp tục. Những bước hoàn tất
(kịch bản, âm thanh, clip) được giữ lại; không tự đổi AI hoặc dùng nội dung mẫu
khi nhà cung cấp lỗi. Khi hết quota, tạo video mới và chọn AI khác trong Tùy chỉnh thêm.

Nếu hết cổng, dùng `STUDIO_PORT=7861 .venv-web/bin/python -m studio.server`.
Server chỉ lắng nghe `127.0.0.1`, không có tính năng truy cập từ mạng LAN.

### Kiểm tra web

```bash
.venv-web/bin/python -m pip install pytest
.venv-web/bin/python -m pytest studio/tests -q
node --check studio/static/app.js
```

Các kiểm thử web không gọi AI/Edge TTS và không động đến thư viện video thật;
hai bài kiểm thử dựng media dùng FFmpeg thực với âm thanh thử một giây.

---

## CLI pipeline gốc

Generate TikTok-ready vertical videos (1080x1920) from Vietnamese philosophy scripts using local AI models (XTTS-v2, SDXL) with optional cloud fallbacks.

## Features

- Parse structured `.txt` scripts into scenes
- Generate image prompts via Ollama (local LLM) or rule-based fallback
- Synthesize Vietnamese TTS audio via XTTS-v2 or ElevenLabs
- Generate scene images via SDXL-Turbo or Replicate
- Transcribe audio to SRT subtitles via faster-whisper
- Assemble final video with Ken Burns effect, crossfades, subtitle burn-in, and background music
- Resume-capable: re-run after interruption, completed steps are skipped
- Sequential RAM management: models are loaded and unloaded one at a time

## Prerequisites

- Python 3.11+
- ffmpeg: `brew install ffmpeg`
- Ollama (optional, for AI image prompts): `brew install ollama`

## Installation

```bash
pip install -r requirements.txt
```

## Directory Setup

Create these directories and add assets before running:

```
assets/
  music/         # Add .mp3 or .wav background music files (at least one)
  fallback/      # Add at least one .png or .jpg as fallback image
  fonts/         # Download NotoSans-Bold.ttf from Google Fonts
    NotoSans-Bold.ttf
  voices/        # Add a 10-20s clear Vietnamese female voice sample
    vi_female_sample.wav
```

## Input Script Format

Create a `.txt` file with the following structure:

```
[title: My Video Title]
[style: cinematic]

First scene text here. This becomes the TTS narration.

Second scene text here.
[image: custom image prompt for this scene, optional override]

Third scene text here.
```

- `[title: ...]` — required, sets the video title and output folder name
- `[style: ...]` — optional, one of `cinematic` | `painterly` | `abstract` (default: `cinematic`)
- `[image: ...]` — optional per-scene, overrides AI-generated image prompt
- Blank lines separate scenes
- Each non-empty, non-header block becomes one scene

**Example (`test_script.txt`):**

```
[title: Thử nghiệm pipeline]
[style: cinematic]

Cuộc đời là một hành trình dài đầy thử thách và bài học.

Mỗi bước đi đều để lại dấu ấn riêng trong tâm hồn ta.
[image: footprints in sand, golden hour light, cinematic]

Hãy bước đi với lòng dũng cảm và sự tin tưởng vào bản thân.
```

## Running the Pipeline

```bash
# Basic run
python main.py --script my_script.txt

# With overrides
python main.py --script my_script.txt --style painterly --voice vi-female

# Debug: skip heavy model steps (for testing parse/structure only)
python main.py --script my_script.txt --skip-tts --skip-image
```

Output is saved to `output/<video-id>/final.mp4`.

## CLI Options

| Option | Description |
|---|---|
| `--script PATH` | Path to .txt script file (required) |
| `--style TEXT` | Image style: `cinematic` \| `painterly` \| `abstract` |
| `--voice TEXT` | Voice key from config.yaml (e.g. `vi-female`) |
| `--music TEXT` | Music filename in `assets/music/` (overrides random pick) |
| `--output-name TEXT` | Override the output folder name |
| `--output-dir PATH` | Base output directory (default: `output/`) |
| `--skip-tts` | Skip TTS synthesis step (debug/resume) |
| `--skip-image` | Skip image generation step (debug/resume) |
| `--config PATH` | Path to config.yaml (default: `config.yaml`) |

## Configuration (`config.yaml`)

### Provider Options

```yaml
providers:
  tts: xtts           # xtts | elevenlabs
  image: sdxl         # sdxl | replicate
  script_prompt: ollama  # ollama | none
```

| Provider | Setting | Description |
|---|---|---|
| `xtts` | `tts: xtts` | Local XTTS-v2 model (requires voice sample WAV) |
| `elevenlabs` | `tts: elevenlabs` | ElevenLabs cloud API (set `ELEVENLABS_API_KEY` in `.env`) |
| `sdxl` | `image: sdxl` | Local SDXL-Turbo via diffusers |
| `replicate` | `image: replicate` | Replicate cloud API (set `REPLICATE_API_TOKEN` in `.env`) |
| `ollama` | `script_prompt: ollama` | Use local Ollama LLM to generate image prompts |
| `none` | `script_prompt: none` | Use rule-based fallback for image prompts |

### Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in cloud API keys if using cloud providers:

```bash
cp .env.example .env
```

```
ELEVENLABS_API_KEY=your_key_here   # Required for tts: elevenlabs
REPLICATE_API_TOKEN=your_key_here  # Required for image: replicate
```

## Running Tests

```bash
pytest tests/ -v
```

All 38 unit tests should pass without any heavy models loaded.

## Pipeline Architecture

```
parse_script()          # .txt -> title, style, scenes
generate_image_prompts() # scenes -> scenes with image_prompt (Ollama or rule-based)
run_tts()               # scenes -> audio/scene_001.wav ... (XTTS or ElevenLabs)
run_image_gen()         # scenes -> images/scene_001.png ... (SDXL or Replicate)
run_subtitle_gen()      # audio/ -> subtitle.srt (faster-whisper)
run_video_assembler()   # images/ + audio/ + srt -> final.mp4 (ffmpeg)
```

Each step checks for existing outputs and skips if already complete (resume support).
