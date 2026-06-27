from __future__ import annotations
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.config import Config

log = logging.getLogger(__name__)


def _build_ken_burns_filter(
    duration: float, fps: int, scale: float, resolution: tuple[int, int]
) -> str:
    w, h = resolution
    frames = int(duration * fps)
    return (
        f"zoompan=z='min(zoom+{(scale-1)/frames:.6f},{scale})':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
    )



def run_video_assembler(
    images_dir: Path,
    audio_dir: Path,
    subtitle_srt: Path,
    music_file: Path | None,
    output_video: Path,
    durations: list[float],
    cfg: Config,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    w, h = cfg.video.resolution
    fps = cfg.video.fps
    fade = cfg.video.fade_duration
    kb_scale = cfg.video.ken_burns_scale

    scene_clips: list[Path] = []

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)

        for i, duration in enumerate(durations, start=1):
            img = images_dir / f"scene_{i:03d}.png"
            wav = audio_dir / f"scene_{i:03d}.wav"
            clip_out = tmp / f"clip_{i:03d}.mp4"

            kb = _build_ken_burns_filter(duration, fps, kb_scale, (w, h))
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(img),
                "-i", str(wav),
                "-vf", kb,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration),
                "-r", str(fps),
                "-pix_fmt", "yuv420p",
                str(clip_out),
            ]
            _run(cmd)
            scene_clips.append(clip_out)

        concat_out = tmp / "concat.mp4"
        _concat_clips(scene_clips, concat_out, tmp)

        subbed = tmp / "subbed.mp4"
        sub_cfg = cfg.subtitle
        safe_sub_path = str(subtitle_srt).replace("\\", "/").replace(":", "\\:").replace(" ", "\\ ")
        subtitle_filter = (
            f"subtitles={safe_sub_path}:force_style='"
            f"FontFile={sub_cfg.font},"
            f"FontSize={sub_cfg.font_size},"
            f"PrimaryColour=&H00ffffff,"
            f"OutlineColour=&H00000000,"
            f"Outline={sub_cfg.outline_width},"
            f"Shadow=0'"
        )
        _run(["ffmpeg", "-y", "-i", str(concat_out), "-vf", subtitle_filter,
              "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", str(subbed)])

        if music_file and music_file.exists():
            _mix_music(subbed, music_file, output_video, cfg.video.music_volume)
        else:
            shutil.copy2(subbed, output_video)

    log.info("[VIDEO] Done → %s", output_video)


def _concat_clips(clips: list[Path], output: Path, tmp: Path) -> None:
    if len(clips) == 1:
        shutil.copy2(clips[0], output)
        return

    list_file = tmp / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{clip}'" for clip in clips))

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(output),
    ])


def _mix_music(video: Path, music: Path, output: Path, volume: float) -> None:
    _run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        f"[1:a]volume={volume},afade=t=in:st=0:d=2[music];"
        f"[0:a][music]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output),
    ])


def _run(cmd: list[str]) -> None:
    log.debug("[FFMPEG] %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")
