from __future__ import annotations
from pathlib import Path

from PIL import Image

from src.providers.image.base import ImageProvider


class SDXLProvider(ImageProvider):
    def __init__(self) -> None:
        self._pipe = None

    def _load(self) -> None:
        if self._pipe is not None:
            return
        import torch
        from diffusers import AutoPipelineForText2Image
        self._pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16,
            variant="fp16",
        ).to("mps")

    def generate(
        self,
        prompt: str,
        style: str,
        output_path: Path,
        resolution: tuple[int, int] = (1080, 1920),
    ) -> Path:
        self._load()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = self._pipe(
            prompt=prompt,
            num_inference_steps=4,
            guidance_scale=0.0,
        )
        image: Image.Image = result.images[0]
        image = _crop_and_resize(image, resolution)
        image.save(output_path, format="PNG")
        return output_path

    def unload(self) -> None:
        import torch
        del self._pipe
        self._pipe = None
        torch.mps.empty_cache()


def _crop_and_resize(image: Image.Image, resolution: tuple[int, int]) -> Image.Image:
    """Center-crop to target aspect ratio, then resize."""
    target_w, target_h = resolution
    target_ratio = target_w / target_h
    src_w, src_h = image.size
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        offset = (src_w - new_w) // 2
        image = image.crop((offset, 0, offset + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        offset = (src_h - new_h) // 2
        image = image.crop((0, offset, src_w, offset + new_h))

    return image.resize((target_w, target_h), Image.LANCZOS)
