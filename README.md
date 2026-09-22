# 4G GPU Image Generator

面向低配置 Windows 电脑的批量背景图生成器，适合短视频字幕、文字向上滚动、名言展示和信息卡片。

## 两种运行方式

### Lite EXE（推荐）

- 不需要 ComfyUI
- 不需要安装 Python
- 不需要显卡，也不占 GPU 显存
- 支持一句话描述风格并批量生成变体
- 通过 GitHub Actions 自动构建

### 可选 AI 模式

提供 Stable Diffusion 1.5 后端，使用 FP16、注意力切片、VAE 切片、CPU 卸载和逐张生成来适配 4 GB NVIDIA 显存。因为 PyTorch 与模型权重很大，AI 依赖不打包进 Lite EXE。参见 [AI 模式说明](docs/AI_MODE.md)。

## 功能

- 6 种基础风格和“自动匹配”
- 中文或英文自然语言风格描述
- 9:16、16:9、1:1、4:5
- 一次生成 1–100 张同风格变体
- 自选主题色、压暗程度与文字安全区
- JPG/PNG 输出
- 固定种子复现同一批结果

## 下载 Windows EXE

打开仓库的 **Actions → Build Windows EXE**，进入最新成功任务，在 **Artifacts** 下载 `4GImageGenerator-Windows`。创建 `v*` 标签时，EXE 也会自动附加到 GitHub Release。

## 从源码运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 测试与本地打包

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m PyInstaller --noconfirm --clean --onefile --windowed --name 4GImageGenerator --collect-all PIL app.py
```

生成的文件位于 `dist\4GImageGenerator.exe`。

## 许可

项目代码采用 MIT License。第三方库和 AI 模型遵循各自许可证。
