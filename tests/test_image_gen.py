import pytest
from pathlib import Path
from unittest.mock import MagicMock
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
    scenes = [make_scene(1), make_scene(2)]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

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
