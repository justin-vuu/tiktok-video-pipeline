from __future__ import annotations
import json
import logging
import random
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

    # Probe parse to get title for video_id (before we know video_dir)
    # We use a dummy json path that won't exist to force fresh parse for title
    _dummy_json = Path(f"/nonexistent/_probe_{uuid.uuid4().hex}.json")
    title, final_style, scenes = _load_or_generate_script(
        script_path, _dummy_json, style, cfg, warnings
    )

    video_id = output_name or f"{slugify(title)}-{uuid.uuid4().hex[:4]}"
    video_dir = output_base / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    script_json = video_dir / "script.json"
    audio_dir = video_dir / "audio"
    images_dir = video_dir / "images"
    subtitle_srt = video_dir / "subtitle.srt"
    final_video = video_dir / "final.mp4"

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
        scenes = [Scene(id=s["id"], text=s["text"], image_prompt=s["image_prompt"]) for s in data["scenes"]]
        final_style = data.get("style", final_style)
        saved_music = data.get("music_file")
        music_file = _pick_music(music_dir, music_override, saved_music) if music_dir.exists() else None

    durations: list[float] = []

    # Step 2: TTS
    if not skip_tts and not (audio_dir / "scene_001.wav").exists():
        log.info("[TTS] Synthesizing %d scenes...", len(scenes))
        provider = get_tts_provider(cfg)
        durations = run_tts(scenes, provider, audio_dir, voice=voice)
        provider.unload()
        log.info("[TTS] Done")
    else:
        log.info("[TTS] Skipped (audio exists or --skip-tts)")
        durations = _read_durations(audio_dir, len(scenes))

    # Step 3: Image generation
    if not skip_image and not (images_dir / "scene_001.png").exists():
        log.info("[IMAGE] Generating %d images...", len(scenes))
        provider = get_image_provider(cfg)
        run_image_gen(scenes, provider, images_dir, final_style, cfg, warnings)
        provider.unload()
        log.info("[IMAGE] Done")
    else:
        log.info("[IMAGE] Skipped (images exist or --skip-image)")

    # Step 4: Subtitles
    if not subtitle_srt.exists():
        log.info("[SUBTITLE] Generating subtitles...")
        run_subtitle_gen(audio_dir, subtitle_srt, scene_count=len(scenes))
        log.info("[SUBTITLE] Done")
    else:
        log.info("[SUBTITLE] Skipped (subtitle.srt exists)")

    # Step 5: Video assembly
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
