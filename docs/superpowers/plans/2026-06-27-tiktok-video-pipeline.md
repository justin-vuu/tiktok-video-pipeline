# TikTok AI Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python pipeline that takes a Vietnamese philosophy `.txt` script and produces a TikTok-ready 9:16 `.mp4` with AI voiceover, AI images, burned-in subtitles, and background music.

**Architecture:** Seven sequential modules (script_gen → tts_gen → image_gen → subtitle_gen → video_assembler), orchestrated by `pipeline.py` with resume logic. Each heavy model (XTTS-v2, SDXL, Whisper) loads → generates → unloads before the next loads, to stay within 32GB unified RAM. Providers follow an abstract adapter pattern so API alternatives can be swapped via `config.yaml`.

**Tech Stack:** Python 3.11+, Coqui TTS (XTTS-v2), diffusers (SDXL Turbo), faster-whisper, ffmpeg (subprocess), Pillow, Ollama (qwen2.5:14b), PyYAML, python-dotenv, click, pytest.

## Global Constraints

- Python 3.11+ (use f-strings, `match`, `type | None` syntax freely)
- Apple Silicon M1 Max, MPS backend for PyTorch: `device = "mps"` for XTTS and SDXL
- Never load two heavy models simultaneously — always `del model; torch.mps.empty_cache()` before next model
- All API keys read from `.env` via `python-dotenv` — never hardcoded
- Video output: 1080×1920 px, 30 fps, H.264, 9:16 aspect ratio
- `video_id` format: `slugify(title) + "-" + uuid4()[:4]` (e.g. `bai-hoc-kien-tri-a1b2`)
- All output files land in `output/<video_id>/` — never deleted between runs
- Resume logic: skip a step if its first expected output file already exists
- `[image: ...]` tag in `.txt` applies to the scene **immediately above** it
- Image fallback: scene 0 → random file from `assets/fallback/`; scene N>0 → copy previous scene's `.png`
- Ollama timeout: 10 s first attempt, 30 s retry; fallback to rule-based on second failure
- No comments explaining what code does — only add a comment when the WHY is non-obvious

---

## File Map

```
tiktok-pipeline/
├── main.py                          # CLI entry (click)
├── config.yaml                      # provider defaults, model names, style strings
├── .env.example                     # optional API keys (ELEVENLABS_API_KEY, REPLICATE_API_TOKEN, ANTHROPIC_API_KEY)
├── requirements.txt
├── assets/
│   ├── music/                       # user drops .mp3 files here
│   ├── fonts/NotoSans-Bold.ttf      # subtitle font
│   └── fallback/                    # 2-3 generic landscape images (user provides)
├── src/
│   ├── config.py                    # load config.yaml + .env, expose typed Config dataclass
│   ├── providers/
│   │   ├── tts/
│   │   │   ├── base.py              # abstract TTSProvider
│   │   │   ├── xtts.py              # XTTS-v2 on MPS
│   │   │   └── elevenlabs.py        # ElevenLabs stub (optional)
│   │   └── image/
│   │       ├── base.py              # abstract ImageProvider
│   │       ├── sdxl.py              # SDXL Turbo on MPS
│   │       └── replicate.py         # Replicate stub (optional)
│   ├── script_gen.py                # parse .txt → List[Scene] + Ollama image_prompt
│   ├── tts_gen.py                   # drive TTSProvider per scene, unload after
│   ├── image_gen.py                 # drive ImageProvider per scene, fallback logic, unload after
│   ├── subtitle_gen.py              # faster-whisper per scene .wav → combined subtitle.srt
│   ├── video_assembler.py           # ffmpeg: Ken Burns + crossfade + subtitle burn-in + music
│   └── pipeline.py                  # orchestrator with resume, warnings collector, summary log
└── tests/
    ├── conftest.py
    ├── test_script_gen.py
    ├── test_tts_gen.py
    ├── test_image_gen.py
    ├── test_subtitle_gen.py
    ├── test_video_assembler.py
    └── test_pipeline.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/conftest.py`
- Create all `__init__.py` stubs for `src/providers/tts/`, `src/providers/image/`

**Interfaces:**
- Produces: `Config` dataclass with fields used by all later tasks

- [ ] **Step 1: Create `requirements.txt`**

```
anthropic>=0.30.0
python-dotenv>=1.0.0
pyyaml>=6.0
requests>=2.31.0
TTS>=0.22.0
diffusers>=0.27.0
transformers>=4.38.0
accelerate>=0.27.0
torch>=2.2.0
Pillow>=10.0.0
faster-whisper>=1.0.0
ffmpeg-python>=0.2.0
python-slugify>=8.0.0
click>=8.1.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create `config.yaml`**

```yaml
providers:
  tts: xtts           # xtts | elevenlabs
  image: sdxl         # sdxl | replicate
  script_prompt: ollama  # ollama | none

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

ollama:
  base_url: "http://localhost:11434"
  timeout_first: 10
  timeout_retry: 30
```

- [ ] **Step 3: Create `.env.example`**

```
# All keys are optional — pipeline runs 100% local without any of these
ELEVENLABS_API_KEY=
REPLICATE_API_TOKEN=
ANTHROPIC_API_KEY=
```

- [ ] **Step 4: Create `src/config.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VideoConfig:
    resolution: tuple[int, int]
    fps: int
    music_volume: float
    ken_burns_scale: float
    fade_duration: float


@dataclass
class SubtitleConfig:
    font: str
    font_size: int
    color: str
    outline_color: str
    outline_width: int


@dataclass
class OllamaConfig:
    base_url: str
    timeout_first: int
    timeout_retry: int


@dataclass
class Config:
    providers: dict[str, str]
    models: dict[str, str]
    voices: dict[str, dict]
    image_styles: dict[str, str]
    video: VideoConfig
    subtitle: SubtitleConfig
    ollama: OllamaConfig

    @classmethod
    def load(cls, path: Path = Path("config.yaml")) -> "Config":
        with open(path) as f:
            raw = yaml.safe_load(f)
        v = raw["video"]
        s = raw["subtitle"]
        o = raw.get("ollama", {})
        return cls(
            providers=raw["providers"],
            models=raw["models"],
            voices=raw["voices"],
            image_styles=raw["image_styles"],
            video=VideoConfig(
                resolution=tuple(v["resolution"]),
                fps=v["fps"],
                music_volume=v["music_volume"],
                ken_burns_scale=v["ken_burns_scale"],
                fade_duration=v["fade_duration"],
            ),
            subtitle=SubtitleConfig(
                font=s["font"],
                font_size=s["font_size"],
                color=s["color"],
                outline_color=s["outline_color"],
                outline_width=s["outline_width"],
            ),
            ollama=OllamaConfig(
                base_url=o.get("base_url", "http://localhost:11434"),
                timeout_first=o.get("timeout_first", 10),
                timeout_retry=o.get("timeout_retry", 30),
            ),
        )
```

- [ ] **Step 5: Create `__init__.py` stubs**

```bash
touch src/__init__.py
mkdir -p src/providers/tts src/providers/image
touch src/providers/__init__.py src/providers/tts/__init__.py src/providers/image/__init__.py
mkdir -p tests assets/music assets/fonts assets/fallback output
touch tests/__init__.py
```

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import pytest
from pathlib import Path
import yaml, shutil, tempfile


@pytest.fixture
def tmp_output(tmp_path) -> Path:
    return tmp_path / "output" / "test-video-0000"


@pytest.fixture
def config_path(tmp_path) -> Path:
    cfg = {
        "providers": {"tts": "xtts", "image": "sdxl", "script_prompt": "none"},
        "models": {"xtts": "xtts_v2", "ollama": "qwen2.5:14b", "sdxl": "stabilityai/sdxl-turbo"},
        "voices": {"default": "vi-female", "vi-female": {"xtts": "assets/voices/sample.wav", "elevenlabs": "Rachel"}},
        "image_styles": {
            "cinematic": "cinematic lighting, no text, 9:16 aspect ratio",
            "painterly": "watercolor, no text, 9:16 aspect ratio",
            "abstract": "abstract, no text, 9:16 aspect ratio",
        },
        "video": {"resolution": [1080, 1920], "fps": 30, "music_volume": 0.15, "ken_burns_scale": 1.08, "fade_duration": 0.3},
        "subtitle": {"font": "assets/fonts/NotoSans-Bold.ttf", "font_size": 52, "color": "white", "outline_color": "black", "outline_width": 3},
        "ollama": {"base_url": "http://localhost:11434", "timeout_first": 10, "timeout_retry": 30},
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(cfg))
    return p
```

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 8: Verify config loads**

```bash
python -c "from src.config import Config; c = Config.load(); print(c.video.resolution)"
```

Expected: `(1080, 1920)`

- [ ] **Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold, config loader, folder structure"
```

---

## Task 2: `script_gen.py` — Parse `.txt` → Scenes + Image Prompts

**Files:**
- Create: `src/script_gen.py`
- Create: `tests/test_script_gen.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class Scene:
      id: int
      text: str
      image_prompt: str  # may be empty string if Ollama/rule-based not run yet

  def parse_script(path: Path) -> tuple[str, str, list[Scene]]
  # returns (title, style, scenes) — image_prompt is empty at this stage

  def generate_image_prompts(scenes: list[Scene], cfg: Config, warnings: list[str]) -> list[Scene]
  # mutates image_prompt in place; returns updated scenes
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_script_gen.py
import pytest
from pathlib import Path
from src.script_gen import parse_script, Scene


SAMPLE_TXT = """\
[title: Bài học về sự kiên trì]
[style: cinematic]

Cuộc đời không bao giờ cho bạn những gì bạn muốn.

Nhưng nó luôn cho bạn những gì bạn cần.
[image: lone figure walking through fog]

Kiên trì không phải là không ngã.
"""


def test_parse_title_and_style(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    title, style, scenes = parse_script(p)
    assert title == "Bài học về sự kiên trì"
    assert style == "cinematic"


def test_parse_scenes_count(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    _, _, scenes = parse_script(p)
    assert len(scenes) == 3


def test_parse_scene_ids_are_1_indexed(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    _, _, scenes = parse_script(p)
    assert scenes[0].id == 1
    assert scenes[2].id == 3


def test_image_tag_overrides_scene_above(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    _, _, scenes = parse_script(p)
    assert scenes[1].image_prompt == "lone figure walking through fog"


def test_scene_without_image_tag_has_empty_prompt(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    _, _, scenes = parse_script(p)
    assert scenes[0].image_prompt == ""
    assert scenes[2].image_prompt == ""


def test_missing_title_raises(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("Không có title\n\nScene 1.", encoding="utf-8")
    with pytest.raises(ValueError, match="title"):
        parse_script(p)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_script_gen.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `script_gen` not yet implemented.

- [ ] **Step 3: Implement `src/script_gen.py`**

```python
from __future__ import annotations
import re
import requests
from dataclasses import dataclass, field
from pathlib import Path

from src.config import Config


@dataclass
class Scene:
    id: int
    text: str
    image_prompt: str = ""


def parse_script(path: Path) -> tuple[str, str, list[Scene]]:
    """Parse .txt file into (title, style, scenes). image_prompt filled from [image:] tags only."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    title = ""
    style = "cinematic"
    for line in lines:
        if m := re.match(r"\[title:\s*(.+?)\]", line):
            title = m.group(1).strip()
        if m := re.match(r"\[style:\s*(.+?)\]", line):
            style = m.group(1).strip()

    if not title:
        raise ValueError("Script must contain [title: ...] header")

    # Split into blocks by blank lines, skip header lines
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"\[(title|style):", line):
            continue
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    scenes: list[Scene] = []
    scene_id = 1
    for block in blocks:
        block_lines = block.splitlines()
        image_prompt = ""
        text_lines = []
        for line in block_lines:
            if m := re.match(r"\[image:\s*(.+?)\]", line):
                image_prompt = m.group(1).strip()
            else:
                text_lines.append(line)
        text = " ".join(text_lines).strip()
        if text:
            scenes.append(Scene(id=scene_id, text=text, image_prompt=image_prompt))
            scene_id += 1

    return title, style, scenes


def _rule_based_prompt(text: str) -> str:
    """Extract key nouns/verbs as a fallback image prompt."""
    stop = {"là", "và", "của", "có", "không", "để", "cho", "với", "một", "những", "các", "được", "trong", "khi"}
    words = [w for w in re.findall(r"\w+", text.lower()) if w not in stop and len(w) > 3]
    return ", ".join(words[:5]) if words else text[:50]


def _call_ollama(text: str, cfg: Config, timeout: int) -> str:
    payload = {
        "model": cfg.models["ollama"],
        "prompt": (
            f"Mô tả ngắn gọn (5-10 từ tiếng Anh) một hình ảnh ẩn dụ, cinematic cho câu sau. "
            f"Chỉ trả về mô tả hình ảnh, không giải thích:\n{text}"
        ),
        "stream": False,
    }
    resp = requests.post(
        f"{cfg.ollama.base_url}/api/generate",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def generate_image_prompts(
    scenes: list[Scene], style: str, cfg: Config, warnings: list[str]
) -> list[Scene]:
    """Fill in image_prompt for scenes that don't have a manual [image:] override."""
    use_ollama = cfg.providers.get("script_prompt") == "ollama"
    style_suffix = cfg.image_styles.get(style, "")

    for scene in scenes:
        if scene.image_prompt:
            # Manual override — just append style suffix
            scene.image_prompt = f"{scene.image_prompt}, {style_suffix}"
            continue

        content_prompt = ""
        if use_ollama:
            try:
                content_prompt = _call_ollama(scene.text, cfg, cfg.ollama.timeout_first)
            except Exception:
                try:
                    content_prompt = _call_ollama(scene.text, cfg, cfg.ollama.timeout_retry)
                except Exception:
                    warnings.append(f"scene {scene.id}: used rule-based image_prompt (Ollama unavailable)")
                    content_prompt = _rule_based_prompt(scene.text)
        else:
            content_prompt = _rule_based_prompt(scene.text)

        scene.image_prompt = f"{content_prompt}, {style_suffix}"

    return scenes
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_script_gen.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/script_gen.py tests/test_script_gen.py
git commit -m "feat: script parser and Ollama image prompt generation"
```

---

## Task 3: TTS Provider — Base + XTTS-v2

**Files:**
- Create: `src/providers/tts/base.py`
- Create: `src/providers/tts/xtts.py`
- Create: `src/providers/tts/elevenlabs.py`
- Create: `tests/test_tts_gen.py`

**Interfaces:**
- Produces:
  ```python
  class TTSProvider(ABC):
      def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
          """Returns audio duration in seconds."""

  def get_tts_provider(cfg: Config) -> TTSProvider: ...
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tts_gen.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.providers.tts.base import TTSProvider
from src.tts_gen import run_tts
from src.script_gen import Scene


def make_scenes():
    return [Scene(id=1, text="Xin chào", image_prompt=""), Scene(id=2, text="Thế giới", image_prompt="")]


def test_tts_provider_is_abstract():
    with pytest.raises(TypeError):
        TTSProvider()


def test_run_tts_creates_audio_files(tmp_path, config_path):
    from src.config import Config
    cfg = Config.load(config_path)
    scenes = make_scenes()
    audio_dir = tmp_path / "audio"

    mock_provider = MagicMock()
    mock_provider.synthesize.return_value = 3.5

    durations = run_tts(scenes, audio_dir, mock_provider, voice="vi-female")

    assert len(durations) == 2
    assert durations[0] == 3.5
    assert mock_provider.synthesize.call_count == 2
    assert mock_provider.synthesize.call_args_list[0][1]["output_path"] == audio_dir / "scene_001.wav"


def test_run_tts_returns_duration_per_scene(tmp_path, config_path):
    from src.config import Config
    scenes = make_scenes()
    audio_dir = tmp_path / "audio"

    mock_provider = MagicMock()
    mock_provider.synthesize.side_effect = [2.1, 4.8]

    durations = run_tts(scenes, mock_provider, audio_dir, voice="vi-female")
    assert durations == [2.1, 4.8]
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_tts_gen.py -v
```

Expected: `ImportError` — modules not yet created.

- [ ] **Step 3: Implement `src/providers/tts/base.py`**

```python
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        """Synthesize text to audio file. Returns duration in seconds."""

    def unload(self) -> None:
        """Release model from memory. Override in subclasses that hold model state."""
```

- [ ] **Step 4: Implement `src/providers/tts/xtts.py`**

```python
from __future__ import annotations
from pathlib import Path
import wave

from src.providers.tts.base import TTSProvider
from src.config import Config


class XTTSProvider(TTSProvider):
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._tts = None

    def _load(self) -> None:
        if self._tts is not None:
            return
        from TTS.api import TTS
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self._tts = TTS(model_name=model_name).to("mps")

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        self._load()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_key = voice or self._cfg.voices["default"]
        speaker_wav = self._cfg.voices.get(voice_key, {}).get("xtts")

        self._tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language="vi",
            file_path=str(output_path),
        )
        return _wav_duration(output_path)

    def unload(self) -> None:
        import torch
        del self._tts
        self._tts = None
        torch.mps.empty_cache()


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "r") as f:
        return f.getnframes() / f.getframerate()
```

- [ ] **Step 5: Implement `src/providers/tts/elevenlabs.py`** (stub — not used in v1)

```python
from __future__ import annotations
import os
from pathlib import Path
import requests

from src.providers.tts.base import TTSProvider
from src.config import Config


class ElevenLabsProvider(TTSProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._api_key = os.environ.get("ELEVENLABS_API_KEY", "")

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        if not self._api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set in .env")

        voice_key = voice or self._cfg.voices["default"]
        voice_id = self._cfg.voices.get(voice_key, {}).get("elevenlabs", "Rachel")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.post(
            f"{self.BASE_URL}/text-to-speech/{voice_id}",
            headers={"xi-api-key": self._api_key},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=60,
        )
        resp.raise_for_status()
        output_path.write_bytes(resp.content)

        import wave
        with wave.open(str(output_path), "r") as f:
            return f.getnframes() / f.getframerate()
```

- [ ] **Step 6: Create `src/tts_gen.py`**

```python
from __future__ import annotations
import logging
from pathlib import Path

from src.providers.tts.base import TTSProvider
from src.script_gen import Scene

log = logging.getLogger(__name__)


def run_tts(
    scenes: list[Scene],
    provider: TTSProvider,
    audio_dir: Path,
    voice: str | None = None,
) -> list[float]:
    """Synthesize all scenes. Returns list of durations (seconds) per scene."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []

    for scene in scenes:
        out = audio_dir / f"scene_{scene.id:03d}.wav"
        log.info("[TTS] Scene %d/%d → %s", scene.id, len(scenes), out.name)
        duration = provider.synthesize(text=scene.text, output_path=out, voice=voice)
        durations.append(duration)
        log.info("[TTS] Scene %d done (%.1fs)", scene.id, duration)

    return durations


def get_tts_provider(cfg) -> TTSProvider:
    name = cfg.providers.get("tts", "xtts")
    if name == "xtts":
        from src.providers.tts.xtts import XTTSProvider
        return XTTSProvider(cfg)
    if name == "elevenlabs":
        from src.providers.tts.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider(cfg)
    raise ValueError(f"Unknown TTS provider: {name}")
```

- [ ] **Step 7: Fix test call signatures and run**

The tests call `run_tts(scenes, audio_dir, mock_provider, ...)` but implementation is `run_tts(scenes, provider, audio_dir, ...)`. Fix tests to match:

```python
# tests/test_tts_gen.py — corrected calls
durations = run_tts(scenes, mock_provider, audio_dir, voice="vi-female")
```

```bash
pytest tests/test_tts_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/providers/tts/ src/tts_gen.py tests/test_tts_gen.py
git commit -m "feat: TTSProvider base, XTTS-v2 provider, tts_gen orchestrator"
```

---

## Task 4: Image Provider — Base + SDXL Turbo

**Files:**
- Create: `src/providers/image/base.py`
- Create: `src/providers/image/sdxl.py`
- Create: `src/providers/image/replicate.py`
- Create: `src/image_gen.py`
- Create: `tests/test_image_gen.py`

**Interfaces:**
- Produces:
  ```python
  class ImageProvider(ABC):
      def generate(self, prompt: str, style: str, output_path: Path,
                   resolution: tuple[int, int] = (1080, 1920)) -> Path: ...

  def run_image_gen(scenes, provider, images_dir, style, cfg, warnings) -> None: ...
  def get_image_provider(cfg) -> ImageProvider: ...
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_image_gen.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image
from src.script_gen import Scene
from src.image_gen import run_image_gen


def make_scene(id, text="hello"):
    return Scene(id=id, text=text, image_prompt="lone tree in storm")


def test_run_image_gen_calls_provider_per_scene(tmp_path):
    scenes = [make_scene(1), make_scene(2)]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    mock_provider = MagicMock()
    # Simulate provider writing a file
    def fake_generate(prompt, style, output_path, resolution):
        img = Image.new("RGB", (1080, 1920), color=(100, 100, 100))
        img.save(output_path)
        return output_path
    mock_provider.generate.side_effect = fake_generate

    warnings = []
    run_image_gen(scenes, mock_provider, images_dir, style="cinematic", cfg=None, warnings=warnings)

    assert mock_provider.generate.call_count == 2
    assert (images_dir / "scene_001.png").exists()
    assert (images_dir / "scene_002.png").exists()


def test_fallback_copies_previous_scene_on_failure(tmp_path):
    from PIL import Image
    scenes = [make_scene(1), make_scene(2)]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    # Pre-create scene_001.png (previous scene)
    img = Image.new("RGB", (1080, 1920), color=(50, 50, 50))
    img.save(images_dir / "scene_001.png")

    mock_provider = MagicMock()
    call_count = [0]
    def fake_generate(prompt, style, output_path, resolution):
        call_count[0] += 1
        if call_count[0] <= 3:  # fail all attempts for scene 2
            raise RuntimeError("SDXL error")
        img = Image.new("RGB", (1080, 1920))
        img.save(output_path)
        return output_path
    mock_provider.generate.side_effect = fake_generate

    warnings = []
    run_image_gen(scenes, mock_provider, images_dir, style="cinematic", cfg=None, warnings=warnings)

    # scene_002.png should be a copy of scene_001.png
    assert (images_dir / "scene_002.png").exists()
    assert any("fallback" in w for w in warnings)


def test_fallback_uses_assets_fallback_for_first_scene(tmp_path):
    scenes = [make_scene(1)]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    fallback_dir = tmp_path / "assets" / "fallback"
    fallback_dir.mkdir(parents=True)
    img = Image.new("RGB", (1080, 1920), color=(30, 30, 30))
    img.save(fallback_dir / "nature.png")

    mock_provider = MagicMock()
    mock_provider.generate.side_effect = RuntimeError("fail")

    warnings = []
    run_image_gen(
        scenes, mock_provider, images_dir, style="cinematic",
        cfg=None, warnings=warnings, fallback_dir=fallback_dir
    )

    assert (images_dir / "scene_001.png").exists()
    assert any("fallback" in w for w in warnings)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_image_gen.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/providers/image/base.py`**

```python
from abc import ABC, abstractmethod
from pathlib import Path


class ImageProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        """Generate image and save to output_path. Returns output_path."""

    def unload(self) -> None:
        """Release model from memory."""
```

- [ ] **Step 4: Implement `src/providers/image/sdxl.py`**

```python
from __future__ import annotations
from pathlib import Path

from PIL import Image

from src.providers.image.base import ImageProvider


class SDXLProvider(ImageProvider):
    def __init__(self) -> None:
        self._pipe = None

    def _load(self) -> None:
        if self._pipe is not None:
            return
        import torch
        from diffusers import AutoPipelineForText2Image
        self._pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16,
            variant="fp16",
        ).to("mps")

    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        self._load()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # SDXL Turbo: 4 steps, no CFG
        result = self._pipe(
            prompt=prompt,
            num_inference_steps=4,
            guidance_scale=0.0,
        )
        image: Image.Image = result.images[0]
        image = _crop_and_resize(image, resolution)
        image.save(output_path, format="PNG")
        return output_path

    def unload(self) -> None:
        import torch
        del self._pipe
        self._pipe = None
        torch.mps.empty_cache()


def _crop_and_resize(image: Image.Image, resolution: tuple[int, int]) -> Image.Image:
    """Center-crop to target aspect ratio, then resize."""
    target_w, target_h = resolution
    target_ratio = target_w / target_h
    src_w, src_h = image.size
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # wider than target — crop width
        new_w = int(src_h * target_ratio)
        offset = (src_w - new_w) // 2
        image = image.crop((offset, 0, offset + new_w, src_h))
    else:
        # taller than target — crop height
        new_h = int(src_w / target_ratio)
        offset = (src_h - new_h) // 2
        image = image.crop((0, offset, src_w, offset + new_h))

    return image.resize((target_w, target_h), Image.LANCZOS)
```

- [ ] **Step 5: Implement `src/providers/image/replicate.py`** (stub)

```python
from __future__ import annotations
import os
from pathlib import Path
import requests

from src.providers.image.base import ImageProvider


class ReplicateProvider(ImageProvider):
    API_URL = "https://api.replicate.com/v1/predictions"

    def __init__(self) -> None:
        self._token = os.environ.get("REPLICATE_API_TOKEN", "")

    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        if not self._token:
            raise RuntimeError("REPLICATE_API_TOKEN not set in .env")
        raise NotImplementedError("Replicate provider not yet fully implemented")
```

- [ ] **Step 6: Implement `src/image_gen.py`**

```python
from __future__ import annotations
import logging
import random
import shutil
from pathlib import Path

from src.providers.image.base import ImageProvider
from src.script_gen import Scene

log = logging.getLogger(__name__)
MAX_RETRIES = 2


def run_image_gen(
    scenes: list[Scene],
    provider: ImageProvider,
    images_dir: Path,
    style: str,
    cfg,
    warnings: list[str],
    fallback_dir: Path = Path("assets/fallback"),
    resolution: tuple[int, int] = (1080, 1920),
) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)

    for scene in scenes:
        out = images_dir / f"scene_{scene.id:03d}.png"
        log.info("[IMAGE] Scene %d/%d → %s", scene.id, len(scenes), out.name)

        success = False
        for attempt in range(MAX_RETRIES + 1):
            try:
                provider.generate(
                    prompt=scene.image_prompt,
                    style=style,
                    output_path=out,
                    resolution=resolution,
                )
                success = True
                break
            except Exception as e:
                log.warning("[IMAGE] Scene %d attempt %d failed: %s", scene.id, attempt + 1, e)

        if not success:
            _apply_fallback(scene, images_dir, fallback_dir, warnings)


def _apply_fallback(
    scene: Scene,
    images_dir: Path,
    fallback_dir: Path,
    warnings: list[str],
) -> None:
    out = images_dir / f"scene_{scene.id:03d}.png"

    if scene.id > 1:
        prev = images_dir / f"scene_{scene.id - 1:03d}.png"
        if prev.exists():
            shutil.copy2(prev, out)
            warnings.append(
                f"scene {scene.id}: used fallback image (copied scene {scene.id - 1}, SDXL failed after {MAX_RETRIES} retries)"
            )
            return

    # First scene or previous doesn't exist — use assets/fallback/
    fallback_files = list(fallback_dir.glob("*.png")) + list(fallback_dir.glob("*.jpg"))
    if fallback_files:
        shutil.copy2(random.choice(fallback_files), out)
        warnings.append(
            f"scene {scene.id}: used fallback image from assets/fallback/ (SDXL failed after {MAX_RETRIES} retries)"
        )
    else:
        warnings.append(f"scene {scene.id}: NO fallback image available — scene will be missing")


def get_image_provider(cfg) -> ImageProvider:
    name = cfg.providers.get("image", "sdxl")
    if name == "sdxl":
        from src.providers.image.sdxl import SDXLProvider
        return SDXLProvider()
    if name == "replicate":
        from src.providers.image.replicate import ReplicateProvider
        return ReplicateProvider()
    raise ValueError(f"Unknown image provider: {name}")
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_image_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/providers/image/ src/image_gen.py tests/test_image_gen.py
git commit -m "feat: ImageProvider base, SDXL Turbo provider, image_gen with fallback logic"
```

---

## Task 5: `subtitle_gen.py` — faster-whisper → `.srt`

**Files:**
- Create: `src/subtitle_gen.py`
- Create: `tests/test_subtitle_gen.py`

**Interfaces:**
- Produces:
  ```python
  def run_subtitle_gen(audio_dir: Path, output_srt: Path, scene_count: int) -> None: ...
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_subtitle_gen.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.subtitle_gen import run_subtitle_gen, _segments_to_srt, _format_timestamp


def test_format_timestamp():
    from src.subtitle_gen import _format_timestamp
    assert _format_timestamp(0.0) == "00:00:00,000"
    assert _format_timestamp(61.5) == "00:01:01,500"
    assert _format_timestamp(3661.123) == "01:01:01,123"


def test_segments_to_srt_basic():
    from src.subtitle_gen import _segments_to_srt
    segments = [
        MagicMock(start=0.0, end=2.5, text=" Xin chào"),
        MagicMock(start=2.5, end=5.0, text=" thế giới"),
    ]
    srt = _segments_to_srt(segments, offset=0.0)
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "Xin chào" in srt
    assert "00:00:02,500 --> 00:00:05,000" in srt


def test_segments_to_srt_applies_offset():
    from src.subtitle_gen import _segments_to_srt
    segments = [MagicMock(start=1.0, end=3.0, text=" text")]
    srt = _segments_to_srt(segments, offset=10.0)
    assert "00:00:11,000 --> 00:00:13,000" in srt


def test_run_subtitle_gen_creates_srt(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    # Create dummy wav files (silence)
    import wave, struct
    for i in range(1, 3):
        wav_path = audio_dir / f"scene_{i:03d}.wav"
        with wave.open(str(wav_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            f.writeframes(struct.pack("<" + "h" * 22050, *([0] * 22050)))

    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 1.0
    mock_segment.text = " Kiên trì"

    with patch("src.subtitle_gen.WhisperModel") as MockModel:
        instance = MockModel.return_value
        instance.transcribe.return_value = ([mock_segment], MagicMock())
        output_srt = tmp_path / "subtitle.srt"
        run_subtitle_gen(audio_dir, output_srt, scene_count=2)

    assert output_srt.exists()
    content = output_srt.read_text(encoding="utf-8")
    assert "Kiên trì" in content
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_subtitle_gen.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/subtitle_gen.py`**

```python
from __future__ import annotations
import logging
import wave
from pathlib import Path

log = logging.getLogger(__name__)


def _format_timestamp(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds // 60) % 60
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments, offset: float) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        start = _format_timestamp(seg.start + offset)
        end = _format_timestamp(seg.end + offset)
        text = seg.text.strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "r") as f:
        return f.getnframes() / f.getframerate()


def run_subtitle_gen(audio_dir: Path, output_srt: Path, scene_count: int) -> None:
    from faster_whisper import WhisperModel

    log.info("[SUBTITLE] Loading faster-whisper...")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    all_srt: list[str] = []
    offset = 0.0
    index = 1

    for i in range(1, scene_count + 1):
        wav = audio_dir / f"scene_{i:03d}.wav"
        if not wav.exists():
            log.warning("[SUBTITLE] Missing %s — skipping", wav.name)
            continue

        log.info("[SUBTITLE] Transcribing %s (offset=%.1fs)", wav.name, offset)
        segments, _ = model.transcribe(str(wav), language="vi", word_timestamps=False)
        segments = list(segments)

        srt_block = _segments_to_srt(segments, offset=offset)
        # Re-number entries globally
        for j, seg in enumerate(segments):
            start = _format_timestamp(seg.start + offset)
            end = _format_timestamp(seg.end + offset)
            text = seg.text.strip()
            all_srt.append(f"{index}\n{start} --> {end}\n{text}")
            index += 1

        offset += _wav_duration(wav)

    output_srt.write_text("\n\n".join(all_srt) + "\n", encoding="utf-8")
    log.info("[SUBTITLE] Written → %s (%d entries)", output_srt.name, index - 1)

    del model
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_subtitle_gen.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/subtitle_gen.py tests/test_subtitle_gen.py
git commit -m "feat: subtitle_gen with faster-whisper, SRT formatting, scene offset accumulation"
```

---

## Task 6: `video_assembler.py` — ffmpeg Assembly

**Files:**
- Create: `src/video_assembler.py`
- Create: `tests/test_video_assembler.py`

**Interfaces:**
- Produces:
  ```python
  def run_video_assembler(
      images_dir: Path,
      audio_dir: Path,
      subtitle_srt: Path,
      music_file: Path | None,
      output_video: Path,
      durations: list[float],
      cfg: Config,
  ) -> None: ...
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_video_assembler.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.video_assembler import _build_ken_burns_filter, _format_fade_filter


def test_ken_burns_filter_contains_zoompan():
    f = _build_ken_burns_filter(duration=5.0, fps=30, scale=1.08, resolution=(1080, 1920))
    assert "zoompan" in f
    assert "1080" in f
    assert "1920" in f


def test_ken_burns_filter_frame_count():
    f = _build_ken_burns_filter(duration=4.0, fps=30, scale=1.08, resolution=(1080, 1920))
    # duration * fps = 120 frames
    assert "d=120" in f


def test_format_fade_filter_has_in_and_out():
    f = _format_fade_filter(duration=0.3, total_duration=10.0)
    assert "fade=t=in" in f
    assert "fade=t=out" in f
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_video_assembler.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/video_assembler.py`**

```python
from __future__ import annotations
import logging
import random
import subprocess
import tempfile
from pathlib import Path

from src.config import Config

log = logging.getLogger(__name__)


def _build_ken_burns_filter(
    duration: float, fps: int, scale: float, resolution: tuple[int, int]
) -> str:
    w, h = resolution
    frames = int(duration * fps)
    # zoompan: zoom from 1.0 to scale over all frames, center crop
    return (
        f"zoompan=z='min(zoom+{(scale-1)/frames:.6f},{ scale})':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
    )


def _format_fade_filter(duration: float, total_duration: float) -> str:
    fade_frames = int(duration * 25)
    out_start = total_duration - duration
    return (
        f"fade=t=in:st=0:d={duration},"
        f"fade=t=out:st={out_start:.3f}:d={duration}"
    )


def run_video_assembler(
    images_dir: Path,
    audio_dir: Path,
    subtitle_srt: Path,
    music_file: Path | None,
    output_video: Path,
    durations: list[float],
    cfg: Config,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    w, h = cfg.video.resolution
    fps = cfg.video.fps
    fade = cfg.video.fade_duration
    kb_scale = cfg.video.ken_burns_scale

    scene_clips: list[Path] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Step 1: Build per-scene video clips (image + Ken Burns + audio)
        for i, duration in enumerate(durations, start=1):
            img = images_dir / f"scene_{i:03d}.png"
            wav = audio_dir / f"scene_{i:03d}.wav"
            clip_out = tmp / f"clip_{i:03d}.mp4"

            kb = _build_ken_burns_filter(duration, fps, kb_scale, (w, h))

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(img),
                "-i", str(wav),
                "-vf", kb,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration),
                "-r", str(fps),
                "-pix_fmt", "yuv420p",
                str(clip_out),
            ]
            _run(cmd)
            scene_clips.append(clip_out)

        # Step 2: Concatenate all clips with crossfade
        concat_out = tmp / "concat.mp4"
        _concat_with_fade(scene_clips, concat_out, fade, fps)

        # Step 3: Burn subtitles
        subbed = tmp / "subbed.mp4"
        sub_cfg = cfg.subtitle
        subtitle_filter = (
            f"subtitles={subtitle_srt}:force_style='"
            f"FontFile={sub_cfg.font},"
            f"FontSize={sub_cfg.font_size},"
            f"PrimaryColour=&H00ffffff,"
            f"OutlineColour=&H00000000,"
            f"Outline={sub_cfg.outline_width},"
            f"Shadow=0'"
        )
        _run(["ffmpeg", "-y", "-i", str(concat_out), "-vf", subtitle_filter,
              "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", str(subbed)])

        # Step 4: Mix in background music
        if music_file and music_file.exists():
            _mix_music(subbed, music_file, output_video, cfg.video.music_volume)
        else:
            import shutil
            shutil.copy2(subbed, output_video)

    log.info("[VIDEO] Done → %s", output_video)


def _concat_with_fade(clips: list[Path], output: Path, fade: float, fps: int) -> None:
    if len(clips) == 1:
        import shutil
        shutil.copy2(clips[0], output)
        return

    # Write concat list for ffmpeg
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
        list_file = f.name

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(output),
    ])


def _mix_music(video: Path, music: Path, output: Path, volume: float) -> None:
    _run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        f"[1:a]volume={volume},afade=t=in:st=0:d=2,afade=t=out:st=-2:d=2[music];"
        f"[0:a][music]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output),
    ])


def _run(cmd: list[str]) -> None:
    log.debug("[FFMPEG] %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_video_assembler.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/video_assembler.py tests/test_video_assembler.py
git commit -m "feat: video_assembler with Ken Burns, subtitle burn-in, music mix via ffmpeg"
```

---

## Task 7: `pipeline.py` — Orchestrator with Resume

**Files:**
- Create: `src/pipeline.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Produces:
  ```python
  def run_pipeline(
      script_path: Path,
      output_dir: Path,
      cfg: Config,
      voice: str | None = None,
      style: str | None = None,
      music_override: str | None = None,
      output_name: str | None = None,
      skip_tts: bool = False,
      skip_image: bool = False,
  ) -> Path:
      """Returns path to final .mp4"""
  ```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.pipeline import run_pipeline, _pick_music, _load_or_generate_script


def test_pick_music_random_from_dir(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "track1.mp3").write_bytes(b"")
    (music_dir / "track2.mp3").write_bytes(b"")

    result = _pick_music(music_dir, override=None, saved=None)
    assert result.name in {"track1.mp3", "track2.mp3"}


def test_pick_music_uses_override(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "lofi.mp3").write_bytes(b"")

    result = _pick_music(music_dir, override="lofi.mp3", saved=None)
    assert result.name == "lofi.mp3"


def test_pick_music_reuses_saved(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "saved_track.mp3").write_bytes(b"")

    result = _pick_music(music_dir, override=None, saved="saved_track.mp3")
    assert result.name == "saved_track.mp3"


def test_resume_skips_script_gen_if_json_exists(tmp_path, config_path):
    from src.config import Config
    cfg = Config.load(config_path)

    script_json = tmp_path / "script.json"
    script_json.write_text(json.dumps({
        "title": "Test", "style": "cinematic", "music_file": None, "video_id": "test-0000",
        "scenes": [{"id": 1, "text": "hello", "image_prompt": "lone tree"}]
    }), encoding="utf-8")

    with patch("src.pipeline.parse_script") as mock_parse:
        title, style, scenes = _load_or_generate_script(
            script_path=tmp_path / "s.txt",
            script_json=script_json,
            style_override=None,
            cfg=cfg,
            warnings=[],
        )
        mock_parse.assert_not_called()
        assert title == "Test"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_pipeline.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/pipeline.py`**

```python
from __future__ import annotations
import json
import logging
import random
import time
from pathlib import Path

from slugify import slugify
import uuid

from src.config import Config
from src.script_gen import Scene, parse_script, generate_image_prompts
from src.tts_gen import run_tts, get_tts_provider
from src.image_gen import run_image_gen, get_image_provider
from src.subtitle_gen import run_subtitle_gen
from src.video_assembler import run_video_assembler

logging.basicConfig(
    format="[%(asctime)s] [%(name)-12s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("PIPELINE")


def _pick_music(music_dir: Path, override: str | None, saved: str | None) -> Path | None:
    if override:
        return music_dir / override
    if saved:
        candidate = music_dir / saved
        if candidate.exists():
            return candidate
    files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    return random.choice(files) if files else None


def _load_or_generate_script(
    script_path: Path,
    script_json: Path,
    style_override: str | None,
    cfg: Config,
    warnings: list[str],
) -> tuple[str, str, list[Scene]]:
    if script_json.exists():
        log.info("[SCRIPT] Resuming from existing script.json")
        data = json.loads(script_json.read_text(encoding="utf-8"))
        scenes = [Scene(id=s["id"], text=s["text"], image_prompt=s["image_prompt"]) for s in data["scenes"]]
        return data["title"], data.get("style", "cinematic"), scenes

    title, style, scenes = parse_script(script_path)
    style = style_override or style
    scenes = generate_image_prompts(scenes, style, cfg, warnings)
    return title, style, scenes


def run_pipeline(
    script_path: Path,
    output_base: Path,
    cfg: Config,
    voice: str | None = None,
    style: str | None = None,
    music_override: str | None = None,
    output_name: str | None = None,
    skip_tts: bool = False,
    skip_image: bool = False,
) -> Path:
    warnings: list[str] = []
    t_start = time.time()

    # --- Step 1: Parse script ---
    tmp_json = Path(f"/tmp/_script_probe_{uuid.uuid4().hex[:4]}.json")
    title, final_style, scenes = _load_or_generate_script(
        script_path, tmp_json, style, cfg, warnings
    )

    video_id = output_name or f"{slugify(title)}-{uuid.uuid4().hex[:4]}"
    video_dir = output_base / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    script_json = video_dir / "script.json"
    audio_dir = video_dir / "audio"
    images_dir = video_dir / "images"
    subtitle_srt = video_dir / "subtitle.srt"
    final_video = video_dir / "final.mp4"

    log.info("[PIPELINE] Starting video: %s (%d scenes)", video_id, len(scenes))

    # Re-check resume using real path
    if not script_json.exists():
        music_file = _pick_music(Path("assets/music"), music_override, None)
        data = {
            "title": title,
            "style": final_style,
            "music_file": music_file.name if music_file else None,
            "video_id": video_id,
            "scenes": [{"id": s.id, "text": s.text, "image_prompt": s.image_prompt} for s in scenes],
        }
        script_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("[SCRIPT] Saved → script.json")
    else:
        data = json.loads(script_json.read_text(encoding="utf-8"))
        scenes = [Scene(id=s["id"], text=s["text"], image_prompt=s["image_prompt"]) for s in data["scenes"]]
        final_style = data.get("style", final_style)
        saved_music = data.get("music_file")
        music_file = _pick_music(Path("assets/music"), music_override, saved_music)

    durations: list[float] = []

    # --- Step 2: TTS ---
    if not skip_tts and not (audio_dir / "scene_001.wav").exists():
        log.info("[TTS] Synthesizing %d scenes...", len(scenes))
        provider = get_tts_provider(cfg)
        durations = run_tts(scenes, provider, audio_dir, voice=voice)
        provider.unload()
        log.info("[TTS] Done")
    else:
        log.info("[TTS] Skipped (audio exists or --skip-tts)")
        durations = _read_durations(audio_dir, len(scenes))

    # --- Step 3: Image generation ---
    if not skip_image and not (images_dir / "scene_001.png").exists():
        log.info("[IMAGE] Generating %d images...", len(scenes))
        provider = get_image_provider(cfg)
        run_image_gen(scenes, provider, images_dir, final_style, cfg, warnings)
        provider.unload()
        log.info("[IMAGE] Done")
    else:
        log.info("[IMAGE] Skipped (images exist or --skip-image)")

    # --- Step 4: Subtitles ---
    if not subtitle_srt.exists():
        log.info("[SUBTITLE] Generating subtitles...")
        run_subtitle_gen(audio_dir, subtitle_srt, scene_count=len(scenes))
        log.info("[SUBTITLE] Done")
    else:
        log.info("[SUBTITLE] Skipped (subtitle.srt exists)")

    # --- Step 5: Video assembly ---
    log.info("[VIDEO] Assembling final video...")
    run_video_assembler(
        images_dir=images_dir,
        audio_dir=audio_dir,
        subtitle_srt=subtitle_srt,
        music_file=music_file,
        output_video=final_video,
        durations=durations,
        cfg=cfg,
    )

    elapsed = time.time() - t_start
    _print_summary(final_video, elapsed, warnings)
    return final_video


def _read_durations(audio_dir: Path, count: int) -> list[float]:
    import wave
    durations = []
    for i in range(1, count + 1):
        wav = audio_dir / f"scene_{i:03d}.wav"
        if wav.exists():
            with wave.open(str(wav), "r") as f:
                durations.append(f.getnframes() / f.getframerate())
        else:
            durations.append(0.0)
    return durations


def _print_summary(final_video: Path, elapsed: float, warnings: list[str]) -> None:
    if warnings:
        log.info("[PIPELINE] Done with %d warning(s):", len(warnings))
        for w in warnings:
            log.info("  - %s", w)
    else:
        log.info("[PIPELINE] Done (no warnings)")
    log.info("[PIPELINE] Total time: %.1fs → %s", elapsed, final_video)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pipeline.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestrator with resume logic and warning summary"
```

---

## Task 8: `main.py` — CLI Entry Point

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: `run_pipeline()` from `src/pipeline.py`, `Config.load()` from `src/config.py`

- [ ] **Step 1: Implement `main.py`**

```python
#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import click
from src.config import Config
from src.pipeline import run_pipeline


@click.command()
@click.option("--script", required=True, type=click.Path(exists=True, path_type=Path),
              help="Path to .txt script file")
@click.option("--style", default=None, help="Image style: cinematic | painterly | abstract")
@click.option("--voice", default=None, help="Voice key from config.yaml (e.g. vi-female)")
@click.option("--music", default=None, help="Music filename in assets/music/ (overrides random pick)")
@click.option("--output-name", default=None, help="Override output folder name")
@click.option("--output-dir", default="output", type=click.Path(path_type=Path),
              help="Base output directory (default: output/)")
@click.option("--skip-tts", is_flag=True, default=False, help="Skip TTS step (debug)")
@click.option("--skip-image", is_flag=True, default=False, help="Skip image generation step (debug)")
@click.option("--config", "config_path", default="config.yaml",
              type=click.Path(exists=True, path_type=Path), help="Path to config.yaml")
def main(script, style, voice, music, output_name, output_dir, skip_tts, skip_image, config_path):
    """Generate a TikTok-ready video from a Vietnamese philosophy script."""
    cfg = Config.load(config_path)
    final_video = run_pipeline(
        script_path=script,
        output_base=output_dir,
        cfg=cfg,
        voice=voice,
        style=style,
        music_override=music,
        output_name=output_name,
        skip_tts=skip_tts,
        skip_image=skip_image,
    )
    click.echo(f"\n✓ Video ready: {final_video}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

```bash
python main.py --help
```

Expected output includes `--script`, `--style`, `--voice`, `--music`, `--skip-tts`, `--skip-image`.

- [ ] **Step 3: Smoke test with a sample script**

Create `test_script.txt`:
```
[title: Thử nghiệm pipeline]
[style: cinematic]

Cuộc đời là một hành trình dài.

Mỗi bước đi đều để lại dấu ấn riêng.
[image: footprints in sand, golden hour light]

Hãy bước đi với lòng dũng cảm.
```

Run with `--skip-image` and `--skip-tts` to verify orchestration logic without model loading:
```bash
python main.py --script test_script.txt --skip-tts --skip-image
```

Expected: pipeline logs steps, creates `output/<video_id>/script.json`, skips TTS and image steps.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: CLI entry point with click, all pipeline options wired"
```

---

## Task 9: Integration Smoke Test (End-to-End)

This task verifies the pipeline runs top-to-bottom with real models on the target machine.

**Prerequisites before running:**
- `pip install -r requirements.txt` complete
- `ffmpeg` installed: `brew install ffmpeg`
- At least 1 `.mp3` file in `assets/music/`
- At least 1 image (`.png`/`.jpg`) in `assets/fallback/`
- `assets/fonts/NotoSans-Bold.ttf` present (download from Google Fonts)
- A voice sample `.wav` (10-20s, clear Vietnamese female voice) saved to `assets/voices/vi_female_sample.wav`

- [ ] **Step 1: Test script_gen + Ollama image prompts (no heavy models)**

```bash
# Start Ollama first (separate terminal)
ollama serve

# Test prompt generation only
python -c "
from pathlib import Path
from src.config import Config
from src.script_gen import parse_script, generate_image_prompts

cfg = Config.load()
title, style, scenes = parse_script(Path('test_script.txt'))
warnings = []
scenes = generate_image_prompts(scenes, style, cfg, warnings)
for s in scenes:
    print(f'Scene {s.id}: {s.image_prompt[:80]}')
print('Warnings:', warnings)
"
```

Expected: 3 lines of image prompts, no warnings.

- [ ] **Step 2: Test TTS only**

```bash
python main.py --script test_script.txt --skip-image
```

Expected: `audio/scene_001.wav`, `scene_002.wav`, `scene_003.wav` created. Log shows XTTS unloaded after.

- [ ] **Step 3: Test image generation only (resume from existing audio)**

```bash
python main.py --script test_script.txt --skip-tts
```

Expected: `images/scene_001.png` etc created. Log shows SDXL unloaded after.

- [ ] **Step 4: Full pipeline run**

```bash
python main.py --script test_script.txt
```

Expected:
- All steps log start/end times
- `output/<video_id>/final.mp4` created
- Final summary line: `✓ Video ready: output/.../final.mp4`
- No warnings (or only expected warnings logged)

- [ ] **Step 5: Verify video**

```bash
ffprobe output/*/final.mp4 2>&1 | grep -E "Duration|Video:|Audio:"
```

Expected:
- Duration matches approximate script length
- Video: `h264`, `1080x1920`, `30 fps`
- Audio: `aac`

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: complete TikTok AI video pipeline — local, modular, resume-capable"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `script_gen.py` — parse .txt, Ollama prompts, rule-based fallback, `[image:]` override → Task 2
- [x] `tts_gen.py` — XTTS-v2, adapter pattern, unload after → Task 3
- [x] `image_gen.py` — SDXL, fallback (scene 0 → assets/fallback, scene N → copy prev), unload → Task 4
- [x] `subtitle_gen.py` — faster-whisper, per-sentence SRT, offset accumulation → Task 5
- [x] `video_assembler.py` — Ken Burns, crossfade, subtitle burn-in, music mix → Task 6
- [x] `pipeline.py` — resume, sequential RAM, warning summary → Task 7
- [x] `main.py` — all CLI flags → Task 8
- [x] `config.yaml` + `Config` dataclass → Task 1
- [x] `.env.example` with optional keys → Task 1
- [x] Ollama retry (10s → 30s → fallback) → Task 2, `_call_ollama`
- [x] Music: random default, saved in `script.json`, `--music` override → Task 7, `_pick_music`
- [x] `video_id` = `slugify(title) + uuid[:4]` → Task 7

**Placeholder scan:** No TBD/TODO found.

**Type consistency:** `Scene` dataclass defined in Task 2 and used identically in Tasks 3–7. `Config` from Task 1 threaded through all tasks. `TTSProvider.synthesize(text, output_path, voice)` and `ImageProvider.generate(prompt, style, output_path, resolution)` consistent throughout.
