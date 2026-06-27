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
