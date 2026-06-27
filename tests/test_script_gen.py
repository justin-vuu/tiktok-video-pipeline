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
