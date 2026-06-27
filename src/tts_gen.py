from __future__ import annotations
import logging
from pathlib import Path

from src.providers.tts.base import TTSProvider
from src.script_gen import Scene

log = logging.getLogger(__name__)


def run_tts(
    scenes: list[Scene],
    provider: TTSProvider,
    audio_dir: Path,
    voice: str | None = None,
) -> list[float]:
    """Synthesize all scenes. Returns list of durations (seconds) per scene."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []

    for scene in scenes:
        out = audio_dir / f"scene_{scene.id:03d}.wav"
        log.info("[TTS] Scene %d/%d → %s", scene.id, len(scenes), out.name)
        duration = provider.synthesize(text=scene.text, output_path=out, voice=voice)
        durations.append(duration)
        log.info("[TTS] Scene %d done (%.1fs)", scene.id, duration)

    return durations


def get_tts_provider(cfg) -> TTSProvider:
    name = cfg.providers.get("tts", "xtts")
    if name == "xtts":
        from src.providers.tts.xtts import XTTSProvider
        return XTTSProvider(cfg)
    if name == "elevenlabs":
        from src.providers.tts.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider(cfg)
    raise ValueError(f"Unknown TTS provider: {name}")
