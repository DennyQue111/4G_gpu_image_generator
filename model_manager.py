from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


RUNTIME_TAG = "master-890-74988b2"
RUNTIME_FILE = "sd-master-74988b2-bin-win-vulkan-x64.zip"
RUNTIME_URL = f"https://github.com/leejet/stable-diffusion.cpp/releases/download/{RUNTIME_TAG}/{RUNTIME_FILE}"
RUNTIME_SHA256 = "744c8f817c66ecfd02fbb9dc8b122e1f29f7240db1f6086dfde2669403c5d896"

MODEL_FILE = "v1-5-pruned_Q4_0.gguf"
MODEL_URL = (
    "https://huggingface.co/kostakoff/stable-diffusion-v1-5-GGUF/"
    f"resolve/main/{MODEL_FILE}?download=true"
)
MODEL_MIN_BYTES = 1_000_000_000


@dataclass(frozen=True)
class Components:
    root: Path
    cli: Path
    model: Path

    @property
    def ready(self) -> bool:
        return self.cli.is_file() and self.model.is_file() and self.model.stat().st_size >= MODEL_MIN_BYTES


def component_paths(root: Path | None = None) -> Components:
    if root is None:
        local = os.environ.get("LOCALAPPDATA")
        root = Path(local) / "4GImageGenerator" if local else Path.home() / ".4g_image_generator"
    root = Path(root)
    return Components(root, root / "runtime" / "sd-cli.exe", root / "models" / MODEL_FILE)


def _sha256(path: Path, block_size=1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path, label: str, progress: Callable[[str, int, int], None] | None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "4GImageGenerator/0.2"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if progress:
                progress(label, downloaded, total)
    partial.replace(destination)


def install_components(
    root: Path | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> Components:
    components = component_paths(root)
    components.root.mkdir(parents=True, exist_ok=True)

    if not components.cli.is_file():
        with tempfile.TemporaryDirectory(prefix="4gimg-") as temp:
            archive = Path(temp) / RUNTIME_FILE
            _download(RUNTIME_URL, archive, "下载推理引擎", progress)
            if _sha256(archive) != RUNTIME_SHA256:
                raise RuntimeError("推理引擎校验失败，下载文件可能已损坏。")
            extract = Path(temp) / "runtime"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extract)
            cli_candidates = list(extract.rglob("sd-cli.exe"))
            if not cli_candidates:
                raise RuntimeError("推理引擎压缩包中没有找到 sd-cli.exe。")
            source_dir = cli_candidates[0].parent
            destination = components.cli.parent
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source_dir, destination)

    if not components.model.is_file() or components.model.stat().st_size < MODEL_MIN_BYTES:
        _download(MODEL_URL, components.model, "下载 SD 1.5 Q4 模型", progress)
        if components.model.stat().st_size < MODEL_MIN_BYTES:
            components.model.unlink(missing_ok=True)
            raise RuntimeError("模型文件尺寸异常，下载可能未完成。")

    if not components.ready:
        raise RuntimeError("组件安装没有完成。")
    return components


def remove_components(root: Path | None = None):
    components = component_paths(root)
    if components.root.exists():
        shutil.rmtree(components.root)
