import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from main import main


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_help_shows_all_options(cli_runner):
    """Verify `python main.py --help` exits with code 0 and shows expected options."""
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--script" in result.output
    assert "--style" in result.output
    assert "--voice" in result.output
    assert "--music" in result.output
    assert "--output-name" in result.output
    assert "--output-dir" in result.output
    assert "--skip-tts" in result.output
    assert "--skip-image" in result.output
    assert "--config" in result.output
    assert "Path to .txt script file" in result.output


def test_script_option_is_required(cli_runner):
    """Verify --script is required."""
    result = cli_runner.invoke(main, [])
    assert result.exit_code != 0
    assert "Missing option '--script'" in result.output


def test_cli_wires_script_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI wires --script to run_pipeline correctly (mock run_pipeline)."""
    # Create a test script file
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        # Mock run_pipeline to return a Path
        final_video = tmp_path / "output" / "test-video-0000" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        assert f"✓ Video ready: {final_video}" in result.output
        mock_run_pipeline.assert_called_once()
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["script_path"] == script_file


def test_cli_passes_style_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --style option to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--style", "painterly",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["style"] == "painterly"


def test_cli_passes_voice_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --voice option to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--voice", "vi-female",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["voice"] == "vi-female"


def test_cli_passes_music_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --music option to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--music", "track.mp3",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["music_override"] == "track.mp3"


def test_cli_passes_output_name_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --output-name option to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--output-name", "my-video",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["output_name"] == "my-video"


def test_cli_passes_skip_tts_flag_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --skip-tts flag to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--skip-tts",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["skip_tts"] is True


def test_cli_passes_skip_image_flag_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --skip-image flag to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = tmp_path / "output" / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--skip-image",
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["skip_image"] is True


def test_cli_passes_output_dir_to_run_pipeline(cli_runner, config_path, tmp_path):
    """Verify CLI passes --output-dir option to run_pipeline."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    custom_output_dir = tmp_path / "custom_output"
    custom_output_dir.mkdir()

    with patch("main.run_pipeline") as mock_run_pipeline:
        final_video = custom_output_dir / "final.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.touch()
        mock_run_pipeline.return_value = final_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--output-dir", str(custom_output_dir),
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        call_args = mock_run_pipeline.call_args
        assert call_args.kwargs["output_base"] == custom_output_dir


def test_cli_loads_config_from_path(cli_runner, config_path, tmp_path):
    """Verify CLI loads config from specified path."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.Config.load") as mock_load:
        mock_cfg = MagicMock()
        mock_load.return_value = mock_cfg

        with patch("main.run_pipeline") as mock_run_pipeline:
            final_video = tmp_path / "output" / "final.mp4"
            final_video.parent.mkdir(parents=True, exist_ok=True)
            final_video.touch()
            mock_run_pipeline.return_value = final_video

            result = cli_runner.invoke(main, [
                "--script", str(script_file),
                "--config", str(config_path),
            ])

            assert result.exit_code == 0
            mock_load.assert_called_once_with(config_path)


def test_cli_output_message_format(cli_runner, config_path, tmp_path):
    """Verify CLI prints the expected video ready message."""
    script_file = tmp_path / "test_script.txt"
    script_file.write_text("[title: Test Script]\n\nTest content.")

    with patch("main.run_pipeline") as mock_run_pipeline:
        expected_video = tmp_path / "output" / "test-video-0000" / "final.mp4"
        expected_video.parent.mkdir(parents=True, exist_ok=True)
        expected_video.touch()
        mock_run_pipeline.return_value = expected_video

        result = cli_runner.invoke(main, [
            "--script", str(script_file),
            "--config", str(config_path),
        ])

        assert result.exit_code == 0
        assert "✓ Video ready:" in result.output
        assert str(expected_video) in result.output
