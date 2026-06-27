from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> float:
        """Synthesize text to audio file. Returns duration in seconds."""

    def unload(self) -> None:
        """Release model from memory. Override in subclasses that hold model state."""
