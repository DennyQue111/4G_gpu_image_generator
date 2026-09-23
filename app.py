from __future__ import annotations

import os
import queue
import random
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from inference_engine import DEFAULT_NEGATIVE, Generation, SIZES, generate_batch
from model_manager import component_paths, import_model, install_components, remove_components

APP_NAME = "4G 显存 AI 背景图生成器"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("940x720")
        self.minsize(820, 650)
        self.configure(bg="#111827")
        self.events = queue.Queue()
        self.components = component_paths()
        self._build()
        self.after(120, self._poll)
        self._refresh_model_status()

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#111827")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 19, "bold"), foreground="#f8fafc")
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=9)
        style.configure("Accent.TButton", background="#2563eb", foreground="white", padding=11)
        style.configure("TCombobox", padding=6)

        root = ttk.Frame(self, padding=24)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="Stable Diffusion 1.5 · 本地离线 · 无需 ComfyUI",
                  foreground="#94a3b8").pack(anchor="w", pady=(2, 18))

        model_box = tk.Frame(root, bg="#182235", highlightthickness=1, highlightbackground="#334155")
        model_box.pack(fill="x", pady=(0, 15))
        self.model_status = tk.Label(model_box, bg="#182235", fg="#fbbf24", anchor="w",
                                     font=("Microsoft YaHei UI", 10), padx=12, pady=11)
        self.model_status.pack(side="left", fill="x", expand=True)
        self.install_button = ttk.Button(model_box, text="下载 AI 组件", command=self.install)
        self.install_button.pack(side="right", padx=8, pady=7)
        self.import_button = ttk.Button(model_box, text="导入本地模型", command=self.import_local)
        self.import_button.pack(side="right", pady=7)
        self.remove_button = ttk.Button(model_box, text="删除组件", command=self.remove)
        self.remove_button.pack(side="right", padx=(0, 6), pady=7)

        ttk.Label(root, text="描述你想生成的背景").pack(anchor="w")
        self.prompt = tk.Text(root, height=5, wrap="word", font=("Microsoft YaHei UI", 11),
                              bg="#0b1220", fg="#f8fafc", insertbackground="white",
                              relief="flat", padx=10, pady=9)
        self.prompt.pack(fill="x", pady=(5, 13))
        self.prompt.insert("1.0", "古风山水背景，远山与湖面，水墨画意境，宁静，柔和光线，画面中央简洁留白")

        options = ttk.Frame(root)
        options.pack(fill="x")
        self.ratio = tk.StringVar(value="9:16")
        self.count = tk.IntVar(value=4)
        self.text_area = tk.StringVar(value="居中")
        self.seed = tk.StringVar()
        self.output = tk.StringVar(value=str(Path.home() / "Pictures" / "4G_AI_Backgrounds"))

        self._combo(options, "画面比例", self.ratio, tuple(SIZES), 0)
        self._combo(options, "文字区域", self.text_area, ("居中", "左侧", "右侧", "无"), 1)

        count_frame = ttk.Frame(options)
        count_frame.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        ttk.Label(count_frame, text="生成数量").pack(anchor="w")
        tk.Spinbox(count_frame, from_=1, to=20, textvariable=self.count, width=10).pack(fill="x", pady=(5, 0))
        for column in range(3):
            options.columnconfigure(column, weight=1)

        advanced = ttk.LabelFrame(root, text="高级选项", padding=10)
        advanced.pack(fill="x", pady=(13, 0))
        ttk.Label(advanced, text="排除内容").grid(row=0, column=0, sticky="w")
        self.negative = tk.StringVar(value=DEFAULT_NEGATIVE)
        ttk.Entry(advanced, textvariable=self.negative).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        ttk.Label(advanced, text="随机种子（留空则随机）").grid(row=2, column=0, sticky="w")
        ttk.Entry(advanced, textvariable=self.seed).grid(row=3, column=0, sticky="ew", pady=(4, 0), padx=(0, 8))
        ttk.Label(advanced, text="保存位置").grid(row=2, column=1, sticky="w")
        output_row = ttk.Frame(advanced)
        output_row.grid(row=3, column=1, sticky="ew", pady=(4, 0))
        ttk.Entry(output_row, textvariable=self.output).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="浏览", command=self._choose_output).pack(side="right", padx=(6, 0))
        advanced.columnconfigure(0, weight=1)
        advanced.columnconfigure(1, weight=2)

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", pady=(18, 4))
        self.status = ttk.Label(root, text="就绪", foreground="#94a3b8")
        self.status.pack(anchor="w")
        self.generate_button = ttk.Button(root, text="开始 AI 批量生成", style="Accent.TButton", command=self.generate)
        self.generate_button.pack(fill="x", pady=(13, 0))

        ttk.Label(root, text="模型优先走国内镜像并支持断点续传；也可以手动导入 GGUF 文件。",
                  foreground="#64748b").pack(anchor="center", pady=(9, 0))

    @staticmethod
    def _combo(parent, label, variable, values, column):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column < 2 else 0)
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Combobox(frame, textvariable=variable, values=values, state="readonly").pack(fill="x", pady=(5, 0))

    def _choose_output(self):
        chosen = filedialog.askdirectory(initialdir=self.output.get())
        if chosen:
            self.output.set(chosen)

    def _refresh_model_status(self):
        self.components = component_paths()
        if self.components.ready:
            size = self.components.model.stat().st_size / 1024**3
            self.model_status.configure(text=f"AI组件已就绪 · SD 1.5 Q4 · {size:.1f} GB", fg="#4ade80")
            self.install_button.configure(text="重新检查", state="normal")
            self.import_button.configure(state="normal")
            self.remove_button.configure(state="normal")
            self.generate_button.configure(state="normal")
        else:
            self.model_status.configure(text="尚未安装 AI 推理引擎和模型", fg="#fbbf24")
            self.install_button.configure(text="下载 AI 组件", state="normal")
            self.import_button.configure(state="normal")
            self.remove_button.configure(state="disabled")
            self.generate_button.configure(state="disabled")

    def install(self):
        if self.components.ready:
            self._refresh_model_status()
            return
        if not messagebox.askyesno(APP_NAME, "将下载推理引擎和约3GB的模型。是否继续？"):
            return
        self.install_button.configure(state="disabled")
        self.progress.configure(mode="determinate", value=0, maximum=100)
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            components = install_components(progress=lambda label, done, total:
                self.events.put(("download", label, done, total)))
            self.events.put(("installed", components))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def import_local(self):
        selected = filedialog.askopenfilename(
            title="选择已下载的 SD 1.5 Q4 GGUF 模型",
            filetypes=(("GGUF 模型", "*.gguf"), ("所有文件", "*.*")),
        )
        if not selected:
            return
        self.install_button.configure(state="disabled")
        self.import_button.configure(state="disabled")
        self.status.configure(text="正在导入本地模型，请稍候…")
        threading.Thread(target=self._import_worker, args=(Path(selected),), daemon=True).start()

    def _import_worker(self, source):
        try:
            components = import_model(source)
            self.events.put(("installed", components))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def remove(self):
        if messagebox.askyesno(APP_NAME, "确定删除已下载的推理引擎和模型吗？"):
            try:
                remove_components()
                self._refresh_model_status()
            except Exception as exc:
                messagebox.showerror(APP_NAME, str(exc))

    def generate(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showerror(APP_NAME, "请输入图片描述。")
            return
        try:
            seed = int(self.seed.get()) if self.seed.get().strip() else random.SystemRandom().randrange(1, 2**31)
            count = max(1, min(20, int(self.count.get())))
            job = Generation(prompt, self.negative.get(), self.ratio.get(), count, seed,
                             self.text_area.get(), Path(self.output.get()))
        except ValueError:
            messagebox.showerror(APP_NAME, "随机种子和数量必须是整数。")
            return
        self.generate_button.configure(state="disabled")
        self.install_button.configure(state="disabled")
        self.progress.configure(value=0, maximum=count)
        threading.Thread(target=self._generate_worker, args=(job,), daemon=True).start()

    def _generate_worker(self, job):
        try:
            outputs = generate_batch(self.components, job, lambda done, total, text:
                                     self.events.put(("generation", done, total, text)))
            self.events.put(("done", outputs))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "download":
                    _, label, done, total = event
                    if total:
                        percent = done * 100 / total
                        self.progress.configure(value=percent)
                        self.status.configure(text=f"{label}：{percent:.1f}%")
                    else:
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(10)
                        self.status.configure(text=f"{label}：{done / 1024**2:.1f} MB")
                elif event[0] == "installed":
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=100)
                    self.status.configure(text="AI组件安装完成")
                    self._refresh_model_status()
                elif event[0] == "generation":
                    _, done, total, text = event
                    self.progress.configure(value=done, maximum=total)
                    self.status.configure(text=text)
                elif event[0] == "done":
                    self.generate_button.configure(state="normal")
                    self.install_button.configure(state="normal")
                    self.import_button.configure(state="normal")
                    self.status.configure(text=f"完成：{len(event[1])} 张")
                    if messagebox.askyesno(APP_NAME, "图片生成完成。是否打开保存文件夹？"):
                        os.startfile(str(event[1][0].parent))
                elif event[0] == "error":
                    self.install_button.configure(state="normal")
                    self.import_button.configure(state="normal")
                    if self.components.ready:
                        self.generate_button.configure(state="normal")
                    self.progress.stop()
                    self.status.configure(text="操作失败")
                    messagebox.showerror(APP_NAME, event[1])
        except queue.Empty:
            pass
        self.after(120, self._poll)


if __name__ == "__main__":
    App().mainloop()
