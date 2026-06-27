import pytest
from pathlib import Path
import yaml


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
