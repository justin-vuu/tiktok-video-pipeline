from __future__ import annotations
import os
from pathlib import Path

from src.providers.image.base import ImageProvider


class ReplicateProvider(ImageProvider):
    API_URL = "https://api.replicate.com/v1/predictions"

    def __init__(self) -> None:
        self._token = os.environ.get("REPLICATE_API_TOKEN", "")

    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        if not self._token:
            raise RuntimeError("REPLICATE_API_TOKEN not set in .env")
        raise NotImplementedError("Replicate provider not yet fully implemented")
