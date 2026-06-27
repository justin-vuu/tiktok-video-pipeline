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
