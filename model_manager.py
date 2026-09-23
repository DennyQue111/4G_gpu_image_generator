from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.error
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
MODEL_PATH = f"kostakoff/stable-diffusion-v1-5-GGUF/resolve/main/{MODEL_FILE}?download=true"
MODEL_URLS = (
    ("国内镜像", f"https://hf-mirror.com/{MODEL_PATH}"),
    ("Hugging Face 官方", f"https://huggingface.co/{MODEL_PATH}"),
)
MODEL_MIN_BYTES = 1_000_000_000


@dataclass(frozen=True)
class Components:
    root: Path
    cli: Path
    model: Path

    @property
    def ready(self) -> bool:
        return self.cli.is_file() and valid_model(self.model)


def component_paths(root: Path | None = None) -> Components:
    if root is None:
        local = os.environ.get("LOCALAPPDATA")
        root = Path(local) / "4GImageGenerator" if local else Path.home() / ".4g_image_generator"
    root = Path(root)
    return Components(root, root / "runtime" / "sd-cli.exe", root / "models" / MODEL_FILE)


def valid_model(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < MODEL_MIN_BYTES:
        return False
    try:
        with path.open("rb") as stream:
            return stream.read(4) == b"GGUF"
    except OSError:
        return False


def _sha256(path: Path, block_size=1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _bundled_runtime() -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base / "runtime"
    return candidate if (candidate / "sd-cli.exe").is_file() else None


def _download(
    url: str,
    destination: Path,
    label: str,
    progress: Callable[[str, int, int], None] | None,
):
    """Download with HTTP Range resume. A .part file survives retries/restarts."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "4GImageGenerator/0.3"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        resumed = existing > 0 and getattr(response, "status", None) == 206
        mode = "ab" if resumed else "wb"
        downloaded = existing if resumed else 0
        remaining = int(response.headers.get("Content-Length") or 0)
        total = downloaded + remaining if remaining else 0
        with partial.open(mode) as output:
            while True:
                chunk = response.read(2 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(label, downloaded, total)
    partial.replace(destination)


def _download_from_sources(
    sources: tuple[tuple[str, str], ...],
    destination: Path,
    progress: Callable[[str, int, int], None] | None,
):
    errors = []
    for source_name, url in sources:
        try:
            _download(url, destination, f"从{source_name}下载模型", progress)
            if valid_model(destination):
                return
            destination.unlink(missing_ok=True)
            errors.append(f"{source_name}：文件格式或尺寸异常")
        except Exception as exc:
            errors.append(f"{source_name}：{exc}")
    raise RuntimeError("所有模型下载源均失败。\n" + "\n".join(errors))


def _install_runtime(components: Components, progress):
    bundled = _bundled_runtime()
    if bundled:
        components.cli.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundled, components.cli.parent, dirs_exist_ok=True)
        return

    # Source-mode fallback. Release EXEs already carry the verified runtime.
    with tempfile.TemporaryDirectory(prefix="4gimg-") as temp:
        archive = Path(temp) / RUNTIME_FILE
        _download(RUNTIME_URL, archive, "下载推理引擎", progress)
        if _sha256(archive) != RUNTIME_SHA256:
            raise RuntimeError("推理引擎校验失败，下载文件可能已损坏。")
        extract = Path(temp) / "runtime"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extract)
        candidates = list(extract.rglob("sd-cli.exe"))
        if not candidates:
            raise RuntimeError("推理引擎压缩包中没有找到 sd-cli.exe。")
        shutil.copytree(candidates[0].parent, components.cli.parent, dirs_exist_ok=True)


def install_components(
    root: Path | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> Components:
    components = component_paths(root)
    components.root.mkdir(parents=True, exist_ok=True)
    if not components.cli.is_file():
        _install_runtime(components, progress)
    if not valid_model(components.model):
        _download_from_sources(MODEL_URLS, components.model, progress)
    if not components.ready:
        raise RuntimeError("组件安装没有完成。")
    return components


def import_model(source: Path, root: Path | None = None) -> Components:
    components = component_paths(root)
    source = Path(source)
    if not valid_model(source):
        raise RuntimeError("所选文件不是有效的 GGUF 模型，或文件不完整。")
    components.model.parent.mkdir(parents=True, exist_ok=True)
    temporary = components.model.with_suffix(".gguf.importing")
    shutil.copy2(source, temporary)
    temporary.replace(components.model)
    if not components.cli.is_file():
        _install_runtime(components, None)
    return components


def remove_components(root: Path | None = None):
    components = component_paths(root)
    if components.root.exists():
        shutil.rmtree(components.root)
