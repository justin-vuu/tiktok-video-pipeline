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
