from __future__ import annotations
import logging
import wave
from pathlib import Path

from faster_whisper import WhisperModel

log = logging.getLogger(__name__)


def _format_timestamp(seconds: float) -> str:
    ms = int(round((seconds % 1) * 1000))
    s = int(seconds) % 60
    m = int(seconds // 60) % 60
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments, offset: float) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        start = _format_timestamp(seg.start + offset)
        end = _format_timestamp(seg.end + offset)
        text = seg.text.strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}")
    return "\n\n".join(lines)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "r") as f:
        return f.getnframes() / f.getframerate()


def run_subtitle_gen(audio_dir: Path, output_srt: Path, scene_count: int) -> None:
    log.info("[SUBTITLE] Loading faster-whisper...")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    all_entries: list[str] = []
    offset = 0.0
    index = 1

    for i in range(1, scene_count + 1):
        wav = audio_dir / f"scene_{i:03d}.wav"
        if not wav.exists():
            log.warning("[SUBTITLE] Missing %s — skipping", wav.name)
            continue

        log.info("[SUBTITLE] Transcribing %s (offset=%.1fs)", wav.name, offset)
        segments, _ = model.transcribe(str(wav), language="vi", word_timestamps=False)
        segments = list(segments)

        for seg in segments:
            start = _format_timestamp(seg.start + offset)
            end = _format_timestamp(seg.end + offset)
            text = seg.text.strip()
            all_entries.append(f"{index}\n{start} --> {end}\n{text}")
            index += 1

        offset += _wav_duration(wav)

    output_srt.write_text("\n\n".join(all_entries) + "\n", encoding="utf-8")
    log.info("[SUBTITLE] Written → %s (%d entries)", output_srt.name, index - 1)

    del model
