# 可选 AI 模式（Stable Diffusion 1.5）

Lite EXE 使用程序化绘图，不需要显卡、模型或 ComfyUI。AI 模式目前从源码运行，原因是 PyTorch 和模型权重合计数 GB，不适合捆绑进单文件 EXE。

## 推荐硬件

- NVIDIA 显卡，4 GB 显存
- 16 GB 系统内存（8 GB 可能很慢）
- 至少 12 GB 可用磁盘空间
- Windows 10/11，Python 3.10–3.12

## 安装

先根据显卡驱动，从 PyTorch 官方安装适合的 CUDA 版本，然后：

```powershell
python -m venv .venv-ai
.\.venv-ai\Scripts\python.exe -m pip install -r requirements-ai.txt
```

首次运行会从 Hugging Face 下载 Stable Diffusion 1.5 权重。模型不会由本仓库重新分发，使用前请阅读模型许可证。

## 4 GB 显存策略

`ai_engine.py` 已启用：

- FP16
- attention slicing
- VAE slicing
- model CPU offload
- 逐张生成而非 GPU batch
- 默认 512×768

CPU 卸载会减少显存占用，但速度会变慢。不要直接尝试 1080×1920；先生成较低分辨率，再使用普通插值放大。
