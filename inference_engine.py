from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from model_manager import Components


SIZES = {
    "9:16": ((448, 768), (1080, 1920)),
    "16:9": ((768, 448), (1920, 1080)),
    "1:1": ((512, 512), (1080, 1080)),
    "4:5": ((512, 640), (1080, 1350)),
}

DEFAULT_NEGATIVE = (
    "text, letters, words, logo, watermark, signature, cluttered composition, "
    "busy background, high contrast, deformed, low quality, blurry"
)


@dataclass(frozen=True)
class Generation:
    prompt: str
    negative_prompt: str
    ratio: str
    count: int
    seed: int
    text_area: str
    output: Path


def enhanced_prompt(prompt: str, text_area: str) -> str:
    areas = {
        "居中": "calm empty negative space in the center for overlay text",
        "左侧": "calm empty negative space on the left for overlay text",
        "右侧": "calm empty negative space on the right for overlay text",
        "无": "",
    }
    suffix = areas.get(text_area, areas["居中"])
    parts = [
        prompt.strip(),
        "background image, no text, visually coherent, atmospheric, low contrast",
        suffix,
    ]
    return ", ".join(part for part in parts if part)


def build_command(components: Components, job: Generation, index: int, raw_output: Path) -> list[str]:
    if job.ratio not in SIZES:
        raise ValueError("不支持的画面比例。")
    width, height = SIZES[job.ratio][0]
    seed = job.seed + index
    return [
        str(components.cli),
        "-M", "img_gen",
        "-m", str(components.model),
        "-p", enhanced_prompt(job.prompt, job.text_area),
        "-n", job.negative_prompt.strip() or DEFAULT_NEGATIVE,
        "-W", str(width),
        "-H", str(height),
        "--steps", "20",
        "--cfg-scale", "7.0",
        "--sampling-method", "euler_a",
        "--diffusion-fa",
        "--backend", "gpu",
        "--max-vram", "3.5",
        "-s", str(seed),
        "-o", str(raw_output),
    ]


def generate_batch(
    components: Components,
    job: Generation,
    progress: Callable[[int, int, str], None] | None = None,
) -> list[Path]:
    if not components.ready:
        raise RuntimeError("AI组件尚未安装。")
    if not job.prompt.strip():
        raise ValueError("请输入图片描述。")
    job.output.mkdir(parents=True, exist_ok=True)
    outputs = []
    env = os.environ.copy()
    env["GGML_VK_VISIBLE_DEVICES"] = "0"

    for index in range(job.count):
        seed = job.seed + index
        raw_output = job.output / f".raw_{seed}.png"
        final_output = job.output / f"ai_background_{seed}.png"
        command = build_command(components, job, index, raw_output)
        if progress:
            progress(index, job.count, f"正在生成第 {index + 1}/{job.count} 张")
        process = subprocess.run(
            command,
            cwd=components.cli.parent,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if process.returncode != 0 or not raw_output.is_file():
            message = (process.stderr or process.stdout or "未知错误").strip()
            message = re.sub(r"\x1b\[[0-9;]*m", "", message)
            raise RuntimeError(f"AI生成失败：\n{message[-2500:]}")
        with Image.open(raw_output) as image:
            target = SIZES[job.ratio][1]
            image.convert("RGB").resize(target, Image.Resampling.LANCZOS).save(
                final_output, quality=95, optimize=True
            )
        raw_output.unlink(missing_ok=True)
        outputs.append(final_output)
        if progress:
            progress(index + 1, job.count, f"已完成 {index + 1}/{job.count} 张")
    return outputs
