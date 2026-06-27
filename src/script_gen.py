from __future__ import annotations
import re
import requests
from dataclasses import dataclass, field
from pathlib import Path

from src.config import Config


@dataclass
class Scene:
    id: int
    text: str
    image_prompt: str = ""


def parse_script(path: Path) -> tuple[str, str, list[Scene]]:
    """Parse .txt file into (title, style, scenes). image_prompt filled from [image:] tags only."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    title = ""
    style = "cinematic"
    for line in lines:
        if m := re.match(r"\[title:\s*(.+?)\]", line):
            title = m.group(1).strip()
        if m := re.match(r"\[style:\s*(.+?)\]", line):
            style = m.group(1).strip()

    if not title:
        raise ValueError("Script must contain [title: ...] header")

    # Split into blocks by blank lines, skip header lines
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"\[(title|style):", line):
            continue
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    scenes: list[Scene] = []
    scene_id = 1
    for block in blocks:
        block_lines = block.splitlines()
        image_prompt = ""
        text_lines = []
        for line in block_lines:
            if m := re.match(r"\[image:\s*(.+?)\]", line):
                image_prompt = m.group(1).strip()
            else:
                text_lines.append(line)
        text = " ".join(text_lines).strip()
        if text:
            scenes.append(Scene(id=scene_id, text=text, image_prompt=image_prompt))
            scene_id += 1

    return title, style, scenes


def _rule_based_prompt(text: str) -> str:
    """Extract key nouns/verbs as a fallback image prompt."""
    stop = {"là", "và", "của", "có", "không", "để", "cho", "với", "một", "những", "các", "được", "trong", "khi"}
    words = [w for w in re.findall(r"\w+", text.lower()) if w not in stop and len(w) > 3]
    return ", ".join(words[:5]) if words else text[:50]


def _call_ollama(text: str, cfg: Config, timeout: int) -> str:
    payload = {
        "model": cfg.models["ollama"],
        "prompt": (
            f"Mô tả ngắn gọn (5-10 từ tiếng Anh) một hình ảnh ẩn dụ, cinematic cho câu sau. "
            f"Chỉ trả về mô tả hình ảnh, không giải thích:\n{text}"
        ),
        "stream": False,
    }
    resp = requests.post(
        f"{cfg.ollama.base_url}/api/generate",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def generate_image_prompts(
    scenes: list[Scene], style: str, cfg: Config, warnings: list[str]
) -> list[Scene]:
    """Fill in image_prompt for scenes that don't have a manual [image:] override."""
    use_ollama = cfg.providers.get("script_prompt") == "ollama"
    style_suffix = cfg.image_styles.get(style, "")

    for scene in scenes:
        if scene.image_prompt:
            # Manual override — just append style suffix
            scene.image_prompt = f"{scene.image_prompt}, {style_suffix}"
            continue

        content_prompt = ""
        if use_ollama:
            try:
                content_prompt = _call_ollama(scene.text, cfg, cfg.ollama.timeout_first)
            except Exception:
                try:
                    content_prompt = _call_ollama(scene.text, cfg, cfg.ollama.timeout_retry)
                except Exception:
                    warnings.append(f"scene {scene.id}: used rule-based image_prompt (Ollama unavailable)")
                    content_prompt = _rule_based_prompt(scene.text)
        else:
            content_prompt = _rule_based_prompt(scene.text)

        scene.image_prompt = f"{content_prompt}, {style_suffix}"

    return scenes
