import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.subtitle_gen import run_subtitle_gen, _segments_to_srt, _format_timestamp


def test_format_timestamp():
    assert _format_timestamp(0.0) == "00:00:00,000"
    assert _format_timestamp(61.5) == "00:01:01,500"
    assert _format_timestamp(3661.123) == "01:01:01,123"


def test_segments_to_srt_basic():
    segments = [
        MagicMock(start=0.0, end=2.5, text=" Xin chào"),
        MagicMock(start=2.5, end=5.0, text=" thế giới"),
    ]
    srt = _segments_to_srt(segments, offset=0.0)
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "Xin chào" in srt
    assert "00:00:02,500 --> 00:00:05,000" in srt


def test_segments_to_srt_applies_offset():
    segments = [MagicMock(start=1.0, end=3.0, text=" text")]
    srt = _segments_to_srt(segments, offset=10.0)
    assert "00:00:11,000 --> 00:00:13,000" in srt


def test_run_subtitle_gen_creates_srt(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

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
