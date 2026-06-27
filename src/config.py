from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VideoConfig:
    resolution: tuple[int, int]
    fps: int
    music_volume: float
    ken_burns_scale: float
    fade_duration: float


@dataclass
class SubtitleConfig:
    font: str
    font_size: int
    color: str
    outline_color: str
    outline_width: int


@dataclass
class OllamaConfig:
    base_url: str
    timeout_first: int
    timeout_retry: int


@dataclass
class Config:
    providers: dict[str, str]
    models: dict[str, str]
    voices: dict[str, dict]
    image_styles: dict[str, str]
    video: VideoConfig
    subtitle: SubtitleConfig
    ollama: OllamaConfig

    @classmethod
    def load(cls, path: Path = Path("config.yaml")) -> "Config":
        with open(path) as f:
            raw = yaml.safe_load(f)
        v = raw["video"]
        s = raw["subtitle"]
        o = raw.get("ollama", {})
        return cls(
            providers=raw["providers"],
            models=raw["models"],
            voices=raw["voices"],
            image_styles=raw["image_styles"],
            video=VideoConfig(
                resolution=tuple(v["resolution"]),
                fps=v["fps"],
                music_volume=v["music_volume"],
                ken_burns_scale=v["ken_burns_scale"],
                fade_duration=v["fade_duration"],
            ),
            subtitle=SubtitleConfig(
                font=s["font"],
                font_size=s["font_size"],
                color=s["color"],
                outline_color=s["outline_color"],
                outline_width=s["outline_width"],
            ),
            ollama=OllamaConfig(
                base_url=o.get("base_url", "http://localhost:11434"),
                timeout_first=o.get("timeout_first", 10),
                timeout_retry=o.get("timeout_retry", 30),
            ),
        )
