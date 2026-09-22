from __future__ import annotations

import colorsys
import hashlib
import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


STYLES = ("自动匹配", "柔光渐变", "流体光带", "几何科技", "纸张颗粒", "水墨留白", "星尘夜空")


@dataclass(frozen=True)
class Settings:
    width: int
    height: int
    style: str
    description: str
    color: str
    darkness: int
    safe_zone: str
    seed: int


def _rgb(value: str) -> tuple[int, int, int]:
    try:
        value = value.strip().lstrip("#")
        if len(value) != 6:
            raise ValueError
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except (TypeError, ValueError):
        return 25, 55, 95


def _shift(color, hue=0.0, saturation=0.0, value=0.0):
    h, s, v = colorsys.rgb_to_hsv(*(part / 255 for part in color))
    h = (h + hue) % 1.0
    s = max(0.0, min(1.0, s + saturation))
    v = max(0.0, min(1.0, v + value))
    return tuple(int(part * 255) for part in colorsys.hsv_to_rgb(h, s, v))


def _gradient(size, start, end, diagonal=False):
    width, height = size
    small_w, small_h = (256, 256) if diagonal else (1, 256)
    ramp = Image.new("RGB", (small_w, small_h))
    pixels = ramp.load()
    denominator = max(1, small_w + small_h - 2 if diagonal else small_h - 1)
    for y in range(small_h):
        for x in range(small_w):
            t = ((x + y) if diagonal else y) / denominator
            t = t * t * (3 - 2 * t)
            pixels[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(start, end))
    return ramp.resize((width, height), Image.Resampling.BICUBIC)


def _choose_style(style: str, description: str) -> str:
    if style != "自动匹配":
        return style
    text = description.lower()
    mapping = (
        (("水墨", "国风", "山水", "ink"), "水墨留白"),
        (("纸", "复古", "羊皮", "paper"), "纸张颗粒"),
        (("科技", "赛博", "网格", "tech", "cyber"), "几何科技"),
        (("星", "宇宙", "夜空", "space"), "星尘夜空"),
        (("流体", "光带", "波浪", "wave"), "流体光带"),
    )
    for words, selected in mapping:
        if any(word in text for word in words):
            return selected
    return "柔光渐变"


def _description_color(base, description: str):
    text = description.lower()
    colors = {
        ("红", "red"): (122, 32, 42),
        ("橙", "orange"): (149, 73, 27),
        ("黄", "gold", "金"): (133, 105, 33),
        ("绿", "green", "森林"): (28, 91, 67),
        ("紫", "purple"): (82, 49, 128),
        ("粉", "pink"): (137, 65, 104),
        ("黑", "black"): (30, 34, 42),
        ("蓝", "blue", "科技"): (23, 59, 114),
    }
    for words, color in colors.items():
        if any(word in text for word in words):
            return color
    return base


def make_background(settings: Settings, variant: int = 0) -> Image.Image:
    salt = int.from_bytes(hashlib.sha256(settings.description.encode("utf-8")).digest()[:4], "big")
    rng = random.Random(settings.seed + variant * 104729 + salt)
    size = settings.width, settings.height
    width, height = size
    base = _description_color(_rgb(settings.color), settings.description)
    style = _choose_style(settings.style, settings.description)

    image = _gradient(
        size,
        _shift(base, rng.uniform(-0.04, 0.04), -0.10, -0.36),
        _shift(base, rng.uniform(-0.08, 0.08), 0.04, 0.06),
        diagonal=rng.choice((True, False)),
    ).convert("RGBA")
    layer = Image.new("RGBA", size)
    draw = ImageDraw.Draw(layer, "RGBA")

    for _ in range(5):
        radius = rng.randint(max(40, min(size) // 8), max(60, min(size) // 2))
        x, y = rng.randint(-radius, width + radius), rng.randint(-radius, height + radius)
        color = _shift(base, rng.uniform(-0.12, 0.12), 0.14, 0.24)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*color, rng.randint(20, 65)))
    layer = layer.filter(ImageFilter.GaussianBlur(max(18, min(size) // 17)))
    image = Image.alpha_composite(image, layer)

    art = Image.new("RGBA", size)
    draw = ImageDraw.Draw(art, "RGBA")
    if style == "流体光带":
        for line in range(7):
            center = height * (0.14 + line * 0.12) + rng.randint(-height // 20, height // 20)
            amplitude = rng.randint(max(15, height // 55), max(30, height // 13))
            frequency, phase = rng.uniform(1.0, 2.7), rng.uniform(0, math.tau)
            points = [(x, center + math.sin(x / width * math.tau * frequency + phase) * amplitude)
                      for x in range(-40, width + 50, max(8, width // 90))]
            draw.line(points, fill=(*_shift(base, line * 0.025, 0.15, 0.28), rng.randint(30, 80)),
                      width=max(3, width // 130))
        art = art.filter(ImageFilter.GaussianBlur(max(4, width // 180)))
    elif style == "几何科技":
        step = max(36, width // 11)
        color = _shift(base, 0.07, 0.25, 0.25)
        for x in range(-height, width + height, step):
            draw.line((x, 0, x-height//3, height), fill=(*color, 28))
        for y in range(0, height, step):
            draw.line((0, y, width, y), fill=(*color, 22))
    elif style == "纸张颗粒":
        image = _gradient(size, (86, 72, 50), _shift(base, 0, -0.35, -0.08)).convert("RGBA")
        for _ in range(max(900, width * height // 900)):
            draw.point((rng.randrange(width), rng.randrange(height)), fill=(255, 245, 220, rng.randint(8, 35)))
    elif style == "水墨留白":
        image = _gradient(size, (226, 228, 220), _shift(base, 0, -0.55, 0.35)).convert("RGBA")
        for _ in range(14):
            x = rng.choice((rng.randint(-width//5, width//3), rng.randint(2*width//3, 6*width//5)))
            y = rng.randint(-height//10, height)
            rx, ry = rng.randint(width//8, width//2), rng.randint(height//20, height//5)
            draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill=(*_shift(base, 0, -0.25, -0.28), rng.randint(12, 42)))
        art = art.filter(ImageFilter.GaussianBlur(max(16, width // 28)))
    elif style == "星尘夜空":
        for _ in range(max(90, width * height // 8000)):
            x, y = rng.randrange(width), rng.randrange(height)
            radius = rng.choice((1, 1, 1, 2, 3))
            draw.ellipse((x-radius, y-radius, x+radius, y+radius),
                         fill=(210, 230, 255, rng.randint(55, 180)))
    image = Image.alpha_composite(image, art)

    # Pillow's effect_noise uses an internal random source and is slow on some
    # Windows machines. randbytes is deterministic, fast and seed-controlled.
    noise = Image.frombytes("L", size, rng.randbytes(width * height))
    noise = ImageEnhance.Contrast(noise).enhance(0.10)
    grain = Image.merge("RGBA", (noise, noise, noise, noise.point(lambda p: p // 16)))
    image = Image.alpha_composite(image, grain)

    if settings.safe_zone != "无":
        mask = Image.new("L", size)
        mask_draw = ImageDraw.Draw(mask)
        band_width = int(width * 0.58)
        x = {"左侧": int(width * 0.05), "右侧": width-int(width * 0.05)-band_width}.get(
            settings.safe_zone, (width-band_width)//2)
        mask_draw.rounded_rectangle((x, int(height*.04), x+band_width, int(height*.96)),
                                    radius=max(20, width//16), fill=165)
        calm = image.filter(ImageFilter.GaussianBlur(max(6, width//90)))
        calm = Image.alpha_composite(calm, Image.new("RGBA", size, (0, 0, 0, 42)))
        image = Image.composite(calm, image, mask.filter(ImageFilter.GaussianBlur(max(15, width//25))))

    if settings.darkness:
        alpha = int(max(0, min(70, settings.darkness)) * 1.65)
        image = Image.alpha_composite(image, Image.new("RGBA", size, (0, 0, 0, alpha)))
    return image.convert("RGB")


def save_batch(settings: Settings, count: int, output: Path, image_format: str, progress=None):
    output.mkdir(parents=True, exist_ok=True)
    extension = ".jpg" if image_format.upper() == "JPG" else ".png"
    paths = []
    for index in range(count):
        image = make_background(settings, index)
        path = output / f"backdrop_{settings.seed}_{index + 1:03d}{extension}"
        if extension == ".jpg":
            image.save(path, quality=94, optimize=True, subsampling=0)
        else:
            image.save(path, optimize=True)
        paths.append(path)
        if progress:
            progress(index + 1, path)
    return paths
