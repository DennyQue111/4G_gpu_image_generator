# 4G GPU Image Generator

真正使用 Stable Diffusion 1.5 的本地 Windows AI 背景图生成器，面向 4 GB 显存电脑。

## 工作方式

应用本身是轻量单文件 EXE，不捆绑数 GB 模型。首次点击“下载 AI 组件”时，应用会下载：

- stable-diffusion.cpp Windows Vulkan 推理引擎
- Stable Diffusion 1.5 Q4 GGUF 模型

组件保存在 `%LOCALAPPDATA%\4GImageGenerator`。下载完成后可离线生成，不需要 ComfyUI，也不上传提示词或图片。

## 功能

- 自然语言描述背景，不再使用固定风格和颜色预设
- 同一描述批量生成多个随机变体
- 9:16、16:9、1:1、4:5
- 自动提示模型为滚动文字保留居中、左侧或右侧空间
- SD 1.5 Q4、Flash Attention、3.5GB VRAM预算
- 低分辨率逐张生成，再高质量放大导出
- 可删除模型释放磁盘空间

## 下载

在仓库 **Actions → Build Windows AI App** 中下载最新的 `4GImageGenerator-Windows-AI`。

## 首次运行

1. 运行 `4GImageGenerator.exe`。
2. 点击“下载 AI 组件”，准备约4GB磁盘空间。国内网络会优先使用镜像站。
3. 如果自动下载不稳定，也可手动下载 GGUF 文件后点击“导入本地模型”。
4. 下载或导入完成后输入描述并生成。
4. Windows Defender 可能对未签名的新 EXE 提示风险；可在 GitHub Actions 中核对构建来源。

## 4GB显存注意事项

- 生成时关闭游戏、视频剪辑和其他占用显卡的程序。
- 应用逐张生成，不能并行批量。
- 原始推理尺寸为512级，完成后放大至目标尺寸。
- Vulkan后端通常无需单独安装CUDA Toolkit，但显卡驱动应保持更新。
- 若显卡或驱动不支持Vulkan，当前版本不能使用GPU推理。

## 数据来源与许可

- 推理引擎：[stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp)，随其许可证发布。
- 模型：[kostakoff/stable-diffusion-v1-5-GGUF](https://huggingface.co/kostakoff/stable-diffusion-v1-5-GGUF)，继承 CreativeML OpenRAIL-M。
- 项目代码：MIT。

模型与引擎由应用从上游直接下载，本仓库不重新分发权重。
