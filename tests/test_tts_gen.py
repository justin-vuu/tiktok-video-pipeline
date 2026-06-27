import pytest
from pathlib import Path
from unittest.mock import MagicMock
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

    durations = run_tts(scenes, mock_provider, audio_dir, voice="vi-female")

    assert len(durations) == 2
    assert durations[0] == 3.5
    assert mock_provider.synthesize.call_count == 2
    assert mock_provider.synthesize.call_args_list[0][1]["output_path"] == audio_dir / "scene_001.wav"


def test_run_tts_returns_duration_per_scene(tmp_path, config_path):
    scenes = make_scenes()
    audio_dir = tmp_path / "audio"

    mock_provider = MagicMock()
    mock_provider.synthesize.side_effect = [2.1, 4.8]

    durations = run_tts(scenes, mock_provider, audio_dir, voice="vi-female")
    assert durations == [2.1, 4.8]
