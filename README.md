# TikTok AI Video Pipeline

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
