from __future__ import annotations
from pathlib import Path
import wave

from src.providers.tts.base import TTSProvider
from src.config import Config


class XTTSProvider(TTSProvider):
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._tts = None

    def _load(self) -> None:
        if self._tts is not None:
            return
        from TTS.api import TTS
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self._tts = TTS(model_name=model_name).to("mps")

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        self._load()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_key = voice or self._cfg.voices["default"]
        speaker_wav = self._cfg.voices.get(voice_key, {}).get("xtts")

        self._tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language="vi",
            file_path=str(output_path),
        )
        return _wav_duration(output_path)

    def unload(self) -> None:
        import torch
        del self._tts
        self._tts = None
        torch.mps.empty_cache()


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "r") as f:
        return f.getnframes() / f.getframerate()
