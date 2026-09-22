"""Optional Stable Diffusion 1.5 backend for 4 GB NVIDIA GPUs.

This module is deliberately not bundled into the Lite EXE because PyTorch plus model
weights add several gigabytes. Run from source after following docs/AI_MODE.md.
"""
from __future__ import annotations

from pathlib import Path


class StableDiffusion15:
    def __init__(self, model_id="stable-diffusion-v1-5/stable-diffusion-v1-5"):
        try:
            import torch
            from diffusers import StableDiffusionPipeline
        except ImportError as exc:
            raise RuntimeError("AI 依赖未安装，请阅读 docs/AI_MODE.md。") from exc

        if not torch.cuda.is_available():
            raise RuntimeError("未检测到支持 CUDA 的 NVIDIA 显卡。")
        self.torch = torch
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            safety_checker=None,
        )
        self.pipe.enable_attention_slicing("max")
        self.pipe.enable_vae_slicing()
        self.pipe.enable_model_cpu_offload()

    def generate(self, prompt: str, output: Path, count=1, width=512, height=768, seed=None, progress=None):
        output.mkdir(parents=True, exist_ok=True)
        negative = "text, letters, words, logo, watermark, busy composition, high contrast"
        paths = []
        for index in range(count):  # Sequential generation is essential on 4 GB.
            current_seed = (seed or self.torch.seed()) + index
            generator = self.torch.Generator(device="cpu").manual_seed(current_seed)
            image = self.pipe(
                prompt=prompt + ", background image, simple composition, empty center area",
                negative_prompt=negative,
                width=width,
                height=height,
                num_inference_steps=20,
                guidance_scale=7.0,
                generator=generator,
            ).images[0]
            path = output / f"ai_backdrop_{current_seed}.png"
            image.save(path)
            paths.append(path)
            if progress:
                progress(index + 1, path)
        return paths
