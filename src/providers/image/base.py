from abc import ABC, abstractmethod
from pathlib import Path


class ImageProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        """Generate image and save to output_path. Returns output_path."""

    def unload(self) -> None:
        """Release model from memory."""
