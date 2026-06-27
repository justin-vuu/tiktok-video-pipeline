from __future__ import annotations
import os
import wave
from pathlib import Path

import requests

from src.providers.tts.base import TTSProvider
from src.config import Config


class ElevenLabsProvider(TTSProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._api_key = os.environ.get("ELEVENLABS_API_KEY", "")

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        if not self._api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set in .env")

        voice_key = voice or self._cfg.voices["default"]
        voice_id = self._cfg.voices.get(voice_key, {}).get("elevenlabs", "Rachel")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.post(
            f"{self.BASE_URL}/text-to-speech/{voice_id}",
            headers={"xi-api-key": self._api_key, "Accept": "audio/wav"},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=60,
        )
        resp.raise_for_status()
        output_path.write_bytes(resp.content)

        with wave.open(str(output_path), "r") as f:
            return f.getnframes() / f.getframerate()
