from __future__ import annotations
import logging
import random
import shutil
from pathlib import Path

from src.providers.image.base import ImageProvider
from src.script_gen import Scene

log = logging.getLogger(__name__)
MAX_RETRIES = 2


def run_image_gen(
    scenes: list[Scene],
    provider: ImageProvider,
    images_dir: Path,
    style: str,
    cfg,
    warnings: list[str],
    fallback_dir: Path = Path("assets/fallback"),
    resolution: tuple[int, int] = (1080, 1920),
) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)

    for scene in scenes:
        out = images_dir / f"scene_{scene.id:03d}.png"
        log.info("[IMAGE] Scene %d/%d → %s", scene.id, len(scenes), out.name)

        success = False
        for attempt in range(MAX_RETRIES + 1):
            try:
                provider.generate(
                    prompt=scene.image_prompt,
                    style=style,
                    output_path=out,
                    resolution=resolution,
                )
                success = True
                break
            except Exception as e:
                log.warning("[IMAGE] Scene %d attempt %d failed: %s", scene.id, attempt + 1, e)

        if not success:
            _apply_fallback(scene, images_dir, fallback_dir, warnings)


def _apply_fallback(
    scene: Scene,
    images_dir: Path,
    fallback_dir: Path,
    warnings: list[str],
) -> None:
    out = images_dir / f"scene_{scene.id:03d}.png"

    if scene.id > 1:
        prev = images_dir / f"scene_{scene.id - 1:03d}.png"
        if prev.exists():
            shutil.copy2(prev, out)
            warnings.append(
                f"scene {scene.id}: used fallback image (copied scene {scene.id - 1}, SDXL failed after {MAX_RETRIES} retries)"
            )
            return

    # First scene or previous doesn't exist — use assets/fallback/
    fallback_files = list(fallback_dir.glob("*.png")) + list(fallback_dir.glob("*.jpg"))
    if fallback_files:
        shutil.copy2(random.choice(fallback_files), out)
        warnings.append(
            f"scene {scene.id}: used fallback image from assets/fallback/ (SDXL failed after {MAX_RETRIES} retries)"
        )
    else:
        warnings.append(f"scene {scene.id}: NO fallback image available — scene will be missing")


def get_image_provider(cfg) -> ImageProvider:
    name = cfg.providers.get("image", "sdxl")
    if name == "sdxl":
        from src.providers.image.sdxl import SDXLProvider
        return SDXLProvider()
    if name == "replicate":
        from src.providers.image.replicate import ReplicateProvider
        return ReplicateProvider()
    raise ValueError(f"Unknown image provider: {name}")
