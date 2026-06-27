from pathlib import Path
from src.config import Config


def test_config_load_from_fixture(config_path: Path):
    """Test that Config.load() works with the fixture"""
    cfg = Config.load(config_path)
    assert cfg.video.resolution == (1080, 1920)
    assert cfg.video.fps == 30
    assert cfg.video.music_volume == 0.15
    assert cfg.subtitle.font_size == 52
    assert cfg.ollama.base_url == "http://localhost:11434"
    assert cfg.providers["tts"] == "xtts"


def test_config_load_default():
    """Test that Config.load() works with default path"""
    cfg = Config.load()
    assert cfg.video.resolution == (1080, 1920)
    assert cfg.subtitle.font == "assets/fonts/NotoSans-Bold.ttf"


def test_tmp_output_fixture(tmp_output: Path):
    """Test that tmp_output fixture works"""
    assert str(tmp_output).endswith("test-video-0000")
