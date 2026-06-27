# TikTok AI Video Pipeline — Design Spec
Date: 2026-06-27

## Overview

A Python pipeline that takes a manually written Vietnamese philosophy script (`.txt`), generates AI voiceover, AI images, subtitles, and assembles a 9:16 TikTok-ready `.mp4` — all running locally on Apple Silicon M1 Max (32GB), zero paid APIs required by default.

Single command: `python main.py --script my_script.txt`

---

## Goals & Non-Goals

**Goals:**
- 100% local, free-to-run pipeline (Ollama + XTTS-v2 + SDXL + faster-whisper + ffmpeg)
- Modular: each step independently testable, skip-able via `--skip-*` flags
- Adapter pattern: swap providers (ElevenLabs, Claude API, Replicate) by changing `config.yaml`
- Resume logic: re-run skips already-completed steps based on file existence
- Correct from the start — no prototype shortcuts

**Non-Goals (v1):**
- Auto-posting to TikTok/Facebook
- Hash-based resume invalidation (v2)
- Ollama/Claude API for script generation (added later — v1 uses manual `.txt` input)

---

## Architecture

```
[1] script_gen.py   — parse .txt → scenes JSON + Ollama image_prompt generation
[2] tts_gen.py      — XTTS-v2 (MPS) → per-scene .wav files
[3] image_gen.py    — SDXL Turbo (MPS) → per-scene .png files
[4] subtitle_gen.py — faster-whisper → subtitle.srt
[5] video_assembler.py — ffmpeg: Ken Burns + fade + subtitle burn-in + music → final.mp4
[6] pipeline.py     — orchestrator with resume logic, sequential RAM management
[7] main.py         — CLI entry point
```

RAM management: each heavy module loads model → generates → unloads + `torch.mps.empty_cache()` before the next module loads. Never two heavy models in memory simultaneously.

---

## File & Folder Structure

```
tiktok-pipeline/
├── main.py
├── config.yaml
├── .env.example
├── requirements.txt
├── assets/
│   ├── music/              # user drops .mp3 files here
│   ├── fonts/              # NotoSans-Bold.ttf etc.
│   └── fallback/           # 2-3 generic landscape images for image fallback
├── src/
│   ├── providers/
│   │   ├── tts/
│   │   │   ├── base.py     # abstract TTSProvider
│   │   │   ├── xtts.py     # XTTS-v2 on MPS
│   │   │   └── elevenlabs.py  # optional, reads ELEVENLABS_API_KEY from .env
│   │   └── image/
│   │       ├── base.py     # abstract ImageProvider
│   │       ├── sdxl.py     # SDXL Turbo on MPS
│   │       └── replicate.py   # optional, reads REPLICATE_API_TOKEN from .env
│   ├── script_gen.py
│   ├── tts_gen.py
│   ├── image_gen.py
│   ├── subtitle_gen.py
│   ├── video_assembler.py
│   └── pipeline.py
└── output/
    └── <video_id>/
        ├── script.json
        ├── audio/
        ├── images/
        ├── subtitle.srt
        ├── pipeline.log
        └── final.mp4
```

---

## Data Formats

### Input: `.txt` script file

```
[title: Bài học về sự kiên trì]
[style: cinematic]

Cuộc đời không bao giờ cho bạn những gì bạn muốn...

Nhưng nó luôn cho bạn những gì bạn cần để trưởng thành.
[image: solitary figure walking through fog toward distant light, cinematic]

Kiên trì không phải là không ngã...
```

**Parsing rules:**
- Blank line separates scenes (one scene = one block of text)
- `[title: ...]` and `[style: ...]` are header metadata, not scenes
- `[image: ...]` overrides the image_prompt for the scene **immediately above** it
- Without `[image: ...]`, Ollama generates the image_prompt from the scene text

### Output: `script.json`

```json
{
  "title": "Bài học về sự kiên trì",
  "style": "cinematic",
  "music_file": "lofi_rain.mp3",
  "video_id": "bai-hoc-kien-tri-a1b2",
  "scenes": [
    {
      "id": 1,
      "text": "Cuộc đời không bao giờ cho bạn những gì bạn muốn...",
      "image_prompt": "lone tree in storm, moody sky"
    }
  ]
}
```

`music_file` is saved on first run (random selection) and reused on subsequent re-renders unless `--music` is passed.

### `video_id` format
`slugify(title) + "-" + uuid4()[:4]` → e.g. `bai-hoc-kien-tri-a1b2`
Override with `--output-name`.

---

## Provider Interfaces

### TTSProvider

```python
class TTSProvider(ABC):
    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        """Generate audio file. Returns duration in seconds."""
```

`voice` is a key from `config.yaml > voices`. Each provider resolves it differently:
- XTTS-v2: maps to `speaker_wav` path (voice cloning sample)
- ElevenLabs: maps to `voice_id` string

### ImageProvider

```python
class ImageProvider(ABC):
    def generate(self, prompt: str, style: str, output_path: Path,
                 resolution: tuple[int, int] = (1080, 1920)) -> Path:
        """Generate image. Provider handles resize/crop to target resolution."""
```

Provider generates at native size → center-crop to 9:16 aspect ratio → resize to `resolution` using Pillow.

### Image prompt construction

```python
final_prompt = f"{ollama_content_prompt}, {image_styles[style]}"
```

- Ollama only generates the **content description** (short, concrete, no style words — e.g. `"lone tree in storm, man walking alone"`)
- Rule-based fallback: extract 3-5 key nouns/verbs from scene text, join as comma-separated phrase
- `image_styles[style]` suffix is always appended by code — never included in Ollama output
- This separation allows style to be changed independently of content

---

## config.yaml

```yaml
providers:
  tts: xtts           # xtts | elevenlabs
  image: sdxl         # sdxl | replicate
  script_prompt: ollama  # ollama | none (falls back to rule-based)

models:
  xtts: xtts_v2
  ollama: qwen2.5:14b
  sdxl: stabilityai/sdxl-turbo

voices:
  default: vi-female
  vi-female:
    xtts: assets/voices/vi_female_sample.wav
    elevenlabs: "Rachel"

image_styles:
  cinematic: "cinematic lighting, moody atmosphere, symbolic, no text, no watermark, 9:16 aspect ratio"
  painterly: "watercolor painting, artistic, emotional, no text, 9:16 aspect ratio"
  abstract: "abstract symbolic, geometric, minimalist, moody, no text, 9:16 aspect ratio"

video:
  resolution: [1080, 1920]
  fps: 30
  music_volume: 0.15
  ken_burns_scale: 1.08
  fade_duration: 0.3

subtitle:
  font: assets/fonts/NotoSans-Bold.ttf
  font_size: 52
  color: white
  outline_color: black
  outline_width: 3
```

---

## CLI Interface

```bash
python main.py --script my_script.txt
python main.py --script my_script.txt \
               --style cinematic \
               --voice vi-female \
               --music lofi_rain.mp3 \
               --output-name "kien-tri-v2" \
               --skip-image \
               --skip-tts
```

All `--skip-*` flags are for debugging individual steps.

---

## Error Handling

| Module | Error | Handling |
|---|---|---|
| `script_gen.py` | Ollama timeout/unavailable | Retry once (10s → 30s timeout), then fallback to rule-based; log warning |
| `tts_gen.py` | XTTS OOM / model error | Raise immediately — hard stop, no retry |
| `image_gen.py` | SDXL NSFW block / error | Retry up to 2× with shortened prompt; if still fails → fallback image (see below) |
| `subtitle_gen.py` | faster-whisper error | Raise immediately — subtitle missing = broken video |
| `video_assembler.py` | ffmpeg missing / file missing | Raise with specific file path in message |

### Image fallback strategy

Responsibility contained entirely in `image_gen.py`. `video_assembler.py` only reads files by scene name — no fallback awareness needed.

- **Scene 1 fails:** copy a random image from `assets/fallback/` to `images/scene_001.png`
- **Scene N>1 fails:** copy `images/scene_00(N-1).png` to `images/scene_00N.png` (extend previous scene visually)

### Pipeline summary warning

After all steps complete, if any warnings were collected:
```
[PIPELINE] Done with 2 warnings:
  - scene 3: used fallback image (SDXL failed after 2 retries)
  - scene 5: used rule-based image_prompt (Ollama timeout)
→ output/bai-hoc-kien-tri-a1b2/final.mp4
```

---

## Resume Logic

In `pipeline.py`, check file existence before each step:

| Step | Skip condition |
|---|---|
| script_gen | `script.json` exists |
| tts_gen | `audio/scene_001.wav` exists |
| image_gen | `images/scene_001.png` exists |
| subtitle_gen | `subtitle.srt` exists |
| video_assembler | always re-runs (fast, safe to redo) |

Full log is appended to `output/<video_id>/pipeline.log` on each run.

---

## RAM Management Order

```python
# pipeline.py execution order
script_gen.run(scenes)       # Ollama (CPU) — unload after
tts_gen.run(scenes)          # XTTS-v2 (MPS) — load → generate → unload → empty_cache()
image_gen.run(scenes)        # SDXL (MPS) — load → generate → unload → empty_cache()
subtitle_gen.run(scenes)     # faster-whisper (CPU/ANE) — load → generate → unload
video_assembler.run()        # ffmpeg only, no GPU
```

Never load two heavy models simultaneously.

---

## Future Extensions (out of scope for v1)

- Ollama/Claude API for script generation (provider already stubbed in `script_gen.py`)
- ElevenLabs / Replicate providers (adapter already in place)
- Hash-based resume invalidation when `.txt` changes
- Auto-post to TikTok via TikTok API
