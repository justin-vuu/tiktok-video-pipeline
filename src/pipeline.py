from __future__ import annotations
import json
import logging
import random
import re
import time
import uuid
import wave
from pathlib import Path

from slugify import slugify

from src.config import Config
from src.script_gen import Scene, parse_script, generate_image_prompts
from src.tts_gen import run_tts, get_tts_provider
from src.image_gen import run_image_gen, get_image_provider
from src.subtitle_gen import run_subtitle_gen
from src.video_assembler import run_video_assembler

logging.basicConfig(
    format="[%(asctime)s] [%(name)-12s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("PIPELINE")


def _pick_music(music_dir: Path, override: str | None, saved: str | None) -> Path | None:
    if override:
        return music_dir / override
    if saved:
        candidate = music_dir / saved
        if candidate.exists():
            return candidate
    files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    return random.choice(files) if files else None


def _extract_title(script_path: Path) -> str:
    """Read [title:] from .txt without parsing scenes or calling any LLM."""
    for line in script_path.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\[title:\s*(.+?)\]", line):
            return m.group(1).strip()
    return "untitled"


def _load_or_generate_script(
    script_path: Path,
    script_json: Path,
    style_override: str | None,
    cfg: Config,
    warnings: list[str],
) -> tuple[str, str, list[Scene]]:
    if script_json.exists():
        log.info("[SCRIPT] Resuming from existing script.json")
        data = json.loads(script_json.read_text(encoding="utf-8"))
        scenes = [Scene(id=s["id"], text=s["text"], image_prompt=s["image_prompt"]) for s in data["scenes"]]
        return data["title"], data.get("style", "cinematic"), scenes

    title, style, scenes = parse_script(script_path)
    style = style_override or style
    scenes = generate_image_prompts(scenes, style, cfg, warnings)
    return title, style, scenes


def _read_durations(audio_dir: Path, count: int) -> list[float]:
    durations = []
    for i in range(1, count + 1):
        wav = audio_dir / f"scene_{i:03d}.wav"
        if wav.exists():
            with wave.open(str(wav), "r") as f:
                durations.append(f.getnframes() / f.getframerate())
        else:
            durations.append(0.0)
    return durations


def _print_summary(final_video: Path, elapsed: float, warnings: list[str]) -> None:
    if warnings:
        log.info("[PIPELINE] Done with %d warning(s):", len(warnings))
        for w in warnings:
            log.info("  - %s", w)
    else:
        log.info("[PIPELINE] Done (no warnings)")
    log.info("[PIPELINE] Total time: %.1fs -> %s", elapsed, final_video)


def run_pipeline(
    script_path: Path,
    output_base: Path,
    cfg: Config,
    voice: str | None = None,
    style: str | None = None,
    music_override: str | None = None,
    output_name: str | None = None,
    skip_tts: bool = False,
    skip_image: bool = False,
) -> Path:
    warnings: list[str] = []
    t_start = time.time()

    # Cheaply extract title from script text without calling any LLM
    title_for_id = _extract_title(script_path)
    video_id = output_name or f"{slugify(title_for_id)}-{uuid.uuid4().hex[:4]}"
    video_dir = output_base / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    script_json = video_dir / "script.json"
    audio_dir = video_dir / "audio"
    images_dir = video_dir / "images"
    subtitle_srt = video_dir / "subtitle.srt"
    final_video = video_dir / "final.mp4"

    # Add file handler for this run
    file_handler = logging.FileHandler(video_dir / "pipeline.log", mode="a")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)-12s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(file_handler)

    # Now parse/load the script (resumes from script.json if it exists)
    title, final_style, scenes = _load_or_generate_script(
        script_path, script_json, style, cfg, warnings
    )

    log.info("[PIPELINE] Starting video: %s (%d scenes)", video_id, len(scenes))

    music_file: Path | None = None
    music_dir = Path("assets/music")

    if not script_json.exists():
        music_file = _pick_music(music_dir, music_override, None) if music_dir.exists() else None
        data = {
            "title": title,
            "style": final_style,
            "music_file": music_file.name if music_file else None,
            "video_id": video_id,
            "scenes": [{"id": s.id, "text": s.text, "image_prompt": s.image_prompt} for s in scenes],
        }
        script_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("[SCRIPT] Saved -> script.json")
    else:
        data = json.loads(script_json.read_text(encoding="utf-8"))
        saved_music = data.get("music_file")
        music_file = _pick_music(music_dir, music_override, saved_music) if music_dir.exists() else None

    durations: list[float] = []

    # Step 2: TTS
    last_audio = audio_dir / f"scene_{len(scenes):03d}.wav"
    if not skip_tts and not last_audio.exists():
        log.info("[TTS] Synthesizing %d scenes...", len(scenes))
        provider = get_tts_provider(cfg)
        durations = run_tts(scenes, provider, audio_dir, voice=voice)
        provider.unload()
        log.info("[TTS] Done")
    else:
        log.info("[TTS] Skipped (audio exists or --skip-tts)")
        durations = _read_durations(audio_dir, len(scenes))

    # Step 3: Image generation
    last_image = images_dir / f"scene_{len(scenes):03d}.png"
    if not skip_image and not last_image.exists():
        log.info("[IMAGE] Generating %d images...", len(scenes))
        provider = get_image_provider(cfg)
        run_image_gen(scenes, provider, images_dir, final_style, cfg, warnings)
        provider.unload()
        log.info("[IMAGE] Done")
    else:
        log.info("[IMAGE] Skipped (images exist or --skip-image)")

    # Step 4: Subtitles
    audio_files_exist = list(audio_dir.glob("scene_*.wav")) if audio_dir.exists() else []
    if not subtitle_srt.exists():
        if not audio_files_exist:
            log.info("[SUBTITLE] Skipped (no audio files — run without --skip-tts to generate)")
        else:
            log.info("[SUBTITLE] Generating subtitles...")
            run_subtitle_gen(audio_dir, subtitle_srt, scene_count=len(scenes))
            log.info("[SUBTITLE] Done")
    else:
        log.info("[SUBTITLE] Skipped (subtitle.srt exists)")

    # Step 5: Video assembly
    images_exist = list(images_dir.glob("scene_*.png")) if images_dir.exists() else []
    if not audio_files_exist or not images_exist:
        log.info(
            "[VIDEO] Skipped (missing %s%s— provide audio and images to assemble video)",
            "audio " if not audio_files_exist else "",
            "images " if not images_exist else "",
        )
        _print_summary(final_video, time.time() - t_start, warnings)
        return final_video
    log.info("[VIDEO] Assembling final video...")
    run_video_assembler(
        images_dir=images_dir,
        audio_dir=audio_dir,
        subtitle_srt=subtitle_srt,
        music_file=music_file,
        output_video=final_video,
        durations=durations,
        cfg=cfg,
    )

    elapsed = time.time() - t_start
    _print_summary(final_video, elapsed, warnings)
    return final_video
