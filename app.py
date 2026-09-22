from __future__ import annotations

import os
import queue
import random
import threading
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import ImageTk
from background_engine import STYLES, Settings, make_background, save_batch

APP_NAME = "4G 显存背景图生成器"
DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1080x720")
        self.minsize(940, 640)
        self.configure(bg="#111827")
        self.events = queue.Queue()
        self.preview_image = None
        self._build()
        self.after(120, self._poll)
        self.after(250, self.preview)

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#111827")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=8)
        style.configure("Accent.TButton", background="#2563eb", foreground="white", padding=11)
        style.configure("TCombobox", padding=6)

        root = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)
        controls = ttk.Frame(root, width=370)
        controls.pack(side="left", fill="y", padx=(0, 20))
        preview = ttk.Frame(root)
        preview.pack(side="right", fill="both", expand=True)

        ttk.Label(controls, text=APP_NAME, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w")
        ttk.Label(controls, text="Lite 程序化引擎 · 关键词驱动 · 无需模型", foreground="#94a3b8").pack(anchor="w", pady=(2, 16))

        self.description = tk.StringVar(value="深蓝色科技感，柔和光线，简洁低对比度")
        self.style = tk.StringVar(value="自动匹配")
        self.ratio = tk.StringVar(value="9:16")
        self.count = tk.IntVar(value=8)
        self.color = tk.StringVar(value="#173b72")
        self.darkness = tk.IntVar(value=28)
        self.safe_zone = tk.StringVar(value="居中")
        self.image_format = tk.StringVar(value="JPG")
        self.seed = tk.StringVar()
        self.output = tk.StringVar(value=str(Path.home() / "Pictures" / "4GImageGenerator"))

        self._field(controls, "风格关键词（例：古风，有山有水）", ttk.Entry(controls, textvariable=self.description))
        self._field(controls, "基础风格", ttk.Combobox(controls, textvariable=self.style, state="readonly", values=STYLES))
        self._field(controls, "画面比例", ttk.Combobox(controls, textvariable=self.ratio, state="readonly", values=tuple(DIMENSIONS)))

        row = ttk.Frame(controls); row.pack(fill="x", pady=5)
        ttk.Label(row, text="主题颜色").pack(anchor="w")
        ttk.Entry(row, textvariable=self.color).pack(side="left", fill="x", expand=True, pady=(4, 0))
        ttk.Button(row, text="选择", command=self._pick_color).pack(side="right", padx=(6, 0), pady=(4, 0))

        self._field(controls, "文字安全区", ttk.Combobox(controls, textvariable=self.safe_zone, state="readonly",
                                                     values=("居中", "左侧", "右侧", "无")))
        self._field(controls, "输出格式", ttk.Combobox(controls, textvariable=self.image_format, state="readonly",
                                                   values=("JPG", "PNG")))

        row = ttk.Frame(controls); row.pack(fill="x", pady=5)
        ttk.Label(row, text="生成数量").pack(side="left")
        tk.Spinbox(row, from_=1, to=100, textvariable=self.count, width=7).pack(side="right")

        row = ttk.Frame(controls); row.pack(fill="x", pady=5)
        ttk.Label(row, text="压暗程度").pack(anchor="w")
        ttk.Scale(row, from_=0, to=70, variable=self.darkness).pack(fill="x")

        self._field(controls, "随机种子（留空则随机）", ttk.Entry(controls, textvariable=self.seed))

        row = ttk.Frame(controls); row.pack(fill="x", pady=5)
        ttk.Label(row, text="保存位置").pack(anchor="w")
        ttk.Entry(row, textvariable=self.output).pack(side="left", fill="x", expand=True, pady=(4, 0))
        ttk.Button(row, text="浏览", command=self._pick_folder).pack(side="right", padx=(6, 0), pady=(4, 0))

        row = ttk.Frame(controls); row.pack(fill="x", pady=(15, 6))
        ttk.Button(row, text="刷新预览", command=self.preview).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.generate_button = ttk.Button(row, text="批量生成", style="Accent.TButton", command=self.generate)
        self.generate_button.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self.progress = ttk.Progressbar(controls)
        self.progress.pack(fill="x", pady=(8, 3))
        self.status = ttk.Label(controls, text="就绪", foreground="#94a3b8")
        self.status.pack(anchor="w")

        box = tk.Frame(preview, bg="#0b1220", highlightthickness=1, highlightbackground="#263244")
        box.pack(fill="both", expand=True)
        self.preview_label = tk.Label(box, bg="#0b1220", fg="#64748b", text="正在生成预览…",
                                      font=("Microsoft YaHei UI", 12))
        self.preview_label.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(preview, text="预览为缩略图；导出使用完整分辨率。", foreground="#64748b").pack(anchor="e", pady=(7, 0))

    @staticmethod
    def _field(parent, label, widget):
        row = ttk.Frame(parent); row.pack(fill="x", pady=5)
        ttk.Label(row, text=label).pack(anchor="w")
        widget.pack(fill="x", pady=(4, 0))

    def _pick_color(self):
        selected = colorchooser.askcolor(self.color.get(), title="选择主题颜色")[1]
        if selected:
            self.color.set(selected)
            self.preview()

    def _pick_folder(self):
        selected = filedialog.askdirectory(initialdir=self.output.get())
        if selected:
            self.output.set(selected)

    def _settings(self, small=False):
        width, height = DIMENSIONS[self.ratio.get()]
        if small:
            scale = min(620 / width, 550 / height)
            width, height = max(200, int(width * scale)), max(200, int(height * scale))
        seed_text = self.seed.get().strip()
        try:
            seed = int(seed_text) if seed_text else random.SystemRandom().randrange(1, 2**31)
        except ValueError as exc:
            raise ValueError("随机种子必须是整数，或保持为空。") from exc
        return Settings(width, height, self.style.get(), self.description.get(), self.color.get(),
                        int(self.darkness.get()), self.safe_zone.get(), seed)

    def preview(self):
        try:
            image = make_background(self._settings(small=True))
            image.thumbnail((650, 570))
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_image, text="")
        except Exception as exc:
            self.preview_label.configure(image="", text=f"预览失败：{exc}")

    def generate(self):
        try:
            settings = self._settings()
            count = max(1, min(100, int(self.count.get())))
            output = Path(self.output.get())
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        self.generate_button.configure(state="disabled")
        self.progress.configure(maximum=count, value=0)
        self.status.configure(text="正在生成…")
        threading.Thread(target=self._worker, args=(settings, count, output), daemon=True).start()

    def _worker(self, settings, count, output):
        try:
            save_batch(settings, count, output, self.image_format.get(),
                       lambda index, path: self.events.put(("progress", index)))
            self.events.put(("done", str(output), count))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    self.progress.configure(value=event[1])
                    self.status.configure(text=f"已生成 {event[1]} 张")
                elif event[0] == "done":
                    self.generate_button.configure(state="normal")
                    self.status.configure(text=f"完成：{event[2]} 张")
                    if messagebox.askyesno(APP_NAME, f"已生成 {event[2]} 张。是否打开输出文件夹？"):
                        os.startfile(event[1])
                elif event[0] == "error":
                    self.generate_button.configure(state="normal")
                    self.status.configure(text="生成失败")
                    messagebox.showerror(APP_NAME, event[1])
        except queue.Empty:
            pass
        self.after(120, self._poll)


if __name__ == "__main__":
    App().mainloop()
