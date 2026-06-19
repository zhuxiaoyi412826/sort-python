# -*- coding: utf-8 -*-
"""
排序过程录制与回放
==================
功能：
  - 加载录制文件（JSON帧序列）
  - 回放、暂停、倒放
  - 调速（0.25x ~ 8x）
  - 导出为 GIF 动图（需要 Pillow 库）
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import time
import threading

# Pillow 用于 GIF 导出（可选）
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# 尝试加载 matplotlib 用于嵌入图表
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ============================================================
#  回放窗口
# ============================================================

class ReplayWindow:
    """排序录制回放窗口"""

    COLORS = {
        'normal': '#4169E1',
        'highlight': '#FF4500',
        'bg': '#F8F8F8',
        'bar_border': '#333333',
        'text': '#333333',
        'progress_bg': '#E0E0E0',
        'progress_fill': '#4CAF50',
    }

    def __init__(self, record_file=None, parent_root=None):
        self.record_file = record_file
        self.frames = []
        self.meta = {}
        self.current_frame = 0
        self._playing = False
        self._reverse = False
        self._speed = 1.0
        self._thread = None

        # 构建窗口
        if parent_root is not None:
            self.root = parent_root
            self.root.deiconify()
            self.root.attributes('-alpha', 1)
        else:
            self.root = tk.Tk()

        self.root.title("排序过程录制与回放")
        self.root.geometry("900x680")
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, lambda: self.root.attributes('-topmost', False))

        self._build_ui()

        # 如果提供了文件，自动加载
        if record_file and os.path.exists(record_file):
            self._load_file(record_file)

    def _build_ui(self):
        # 文件选择区
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(file_frame, text="录制文件:", font=("Microsoft YaHei", 10)).pack(side="left")
        self._file_label = tk.Label(file_frame, text="(未加载)", font=("Microsoft YaHei", 9),
                                    fg="#999", wraplength=500, justify="left")
        self._file_label.pack(side="left", padx=8, fill="x", expand=True)

        tk.Button(file_frame, text="打开", font=("Microsoft YaHei", 9),
                  command=self._open_file).pack(side="right", padx=4)

        # 可视化区域（使用 Canvas）
        self._canvas = tk.Canvas(self.root, bg=self.COLORS['bg'], highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=10, pady=(4, 4))

        # 进度条
        prog_frame = tk.Frame(self.root)
        prog_frame.pack(fill="x", padx=10)

        self._frame_label = tk.Label(prog_frame, text="帧: 0/0", font=("Microsoft YaHei", 9),
                                     fg=self.COLORS['text'])
        self._frame_label.pack(side="left")

        self._scale = tk.Scale(prog_frame, from_=0, to=1, orient="horizontal",
                               length=600, showvalue=False, command=self._on_scale_change)
        self._scale.pack(side="left", fill="x", expand=True, padx=8)

        self._time_label = tk.Label(prog_frame, text="", font=("Microsoft YaHei", 9),
                                    fg="#666")
        self._time_label.pack(side="right")

        # 控制按钮区
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill="x", padx=10, pady=(4, 8))

        self._btn_reverse = tk.Button(ctrl_frame, text="⏪ 倒放", font=("Microsoft YaHei", 10),
                                     command=self._toggle_reverse)
        self._btn_reverse.pack(side="left", padx=4)

        self._btn_play = tk.Button(ctrl_frame, text="▶ 播放", font=("Microsoft YaHei", 10, "bold"),
                                    bg="#4CAF50", fg="white", command=self._toggle_play)
        self._btn_play.pack(side="left", padx=4)

        self._btn_step_back = tk.Button(ctrl_frame, text="◀ 上一步", font=("Microsoft YaHei", 10),
                                         command=self._step_back)
        self._btn_step_back.pack(side="left", padx=4)

        self._btn_step_fwd = tk.Button(ctrl_frame, text="下一步 ▶", font=("Microsoft YaHei", 10),
                                        command=self._step_forward)
        self._btn_step_fwd.pack(side="left", padx=4)

        self._btn_reset = tk.Button(ctrl_frame, text="⏮ 重置", font=("Microsoft YaHei", 10),
                                     command=self._reset_frame)
        self._btn_reset.pack(side="left", padx=4)

        # 速度控制
        tk.Label(ctrl_frame, text="速度:", font=("Microsoft YaHei", 10)).pack(side="left", padx=(20, 4))
        self._speed_var = tk.DoubleVar(value=1.0)
        self._speed_scale = tk.Scale(ctrl_frame, from_=0.25, to=8, resolution=0.25,
                                      orient="horizontal", length=120, variable=self._speed_var,
                                      command=self._on_speed_change, font=("Microsoft YaHei", 9))
        self._speed_scale.pack(side="left")

        self._speed_label = tk.Label(ctrl_frame, text="1.0x", font=("Microsoft YaHei", 10, "bold"),
                                     fg="#2266aa", width=5)
        self._speed_label.pack(side="left")

        # 导出按钮
        self._btn_export = tk.Button(ctrl_frame, text="导出 GIF", font=("Microsoft YaHei", 10, "bold"),
                                      bg="#9C27B0", fg="white", command=self._export_gif)
        self._btn_export.pack(side="right", padx=4)

        if not HAS_PILLOW:
            self._btn_export.config(state="disabled", text="导出GIF(需Pillow)")

    def _open_file(self):
        filepath = filedialog.askopenfilename(
            title="选择录制文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        if filepath:
            self._load_file(filepath)

    def _load_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.meta = data.get('meta', {})
            self.frames = data.get('frames', [])
            self.record_file = filepath

            filename = os.path.basename(filepath)
            algo = self.meta.get('algo', '未知')
            n = self.meta.get('n', '?')
            self._file_label.config(text=f"{filename} | 算法: {algo} | 数据量: {n} | 帧数: {len(self.frames)}",
                                    fg="#333")
            self.root.title(f"排序回放 - {algo} (n={n})")

            if self.frames:
                self._scale.config(from_=0, to=len(self.frames) - 1)
                self.current_frame = 0
                self._draw_frame()

        except Exception as e:
            messagebox.showerror("加载失败", f"无法加载文件:\n{e}")

    def _draw_frame(self):
        """绘制当前帧"""
        if not self.frames or self.current_frame < 0 or self.current_frame >= len(self.frames):
            return

        self._canvas.delete("all")
        frame = self.frames[self.current_frame]
        array = frame.get('array', [])
        highlight = frame.get('highlight', [])

        if not array:
            return

        # 计算布局
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 10 or h < 10:
            self.root.after(50, self._draw_frame)
            return

        n = len(array)
        max_val = max(array) if array else 1
        margin = 40
        bar_area_w = w - margin * 2
        bar_area_h = h - margin * 2 - 30  # 留30给顶部信息

        bar_w = max(1, bar_area_w / n - 1)
        gap = 1 if n > 20 else 2

        # 顶部信息
        algo = self.meta.get('algo', '未知')
        info_text = f"算法: {algo}  |  帧 {self.current_frame + 1}/{len(self.frames)}"
        if highlight:
            info_text += f"  |  比较位置: {highlight}"
        self._canvas.create_text(w // 2, 15, text=info_text,
                                  font=("Microsoft YaHei", 11), fill=self.COLORS['text'])

        # 绘制柱子
        for i, val in enumerate(array):
            x = margin + i * (bar_w + gap)
            bar_h = max(1, (val / max_val) * bar_area_h)
            y = h - margin - bar_h

            if i in highlight:
                color = self.COLORS['highlight']
            else:
                color = self.COLORS['normal']

            self._canvas.create_rectangle(x, y, x + bar_w, h - margin,
                                           fill=color, outline=self.COLORS['bar_border'], width=0.5)

            # 数据量小时显示数字
            if n <= 30 and bar_w > 15:
                self._canvas.create_text(x + bar_w // 2, y - 8,
                                          text=str(val), font=("Microsoft YaHei", 8),
                                          fill=self.COLORS['text'])

        # 更新进度标签
        self._frame_label.config(text=f"帧: {self.current_frame + 1}/{len(self.frames)}")

    def _on_scale_change(self, val):
        idx = int(float(val))
        if idx != self.current_frame:
            self.current_frame = idx
            self._draw_frame()

    def _on_speed_change(self, val):
        self._speed = float(val)
        self._speed_label.config(text=f"{self._speed:.2f}x")

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self._btn_play.config(text="▶ 播放", bg="#4CAF50")
        else:
            if not self.frames:
                messagebox.showinfo("提示", "请先加载录制文件！")
                return
            self._playing = True
            self._btn_play.config(text="⏸ 暂停", bg="#FF9800")
            self._play_loop()

    def _toggle_reverse(self):
        self._reverse = not self._reverse
        if self._reverse:
            self._btn_reverse.config(text="⏪ 倒放中", bg="#FF5722", fg="white")
        else:
            self._btn_reverse.config(text="⏪ 倒放", bg="SystemButtonFace", fg="SystemButtonText")

    def _play_loop(self):
        if not self._playing or not self.frames:
            return

        if self._reverse:
            self.current_frame -= 1
            if self.current_frame < 0:
                self.current_frame = len(self.frames) - 1
        else:
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.current_frame = 0

        self._scale.set(self.current_frame)
        self._draw_frame()

        # 根据速度调整延迟
        delay = int(100 / self._speed)
        self.root.after(max(10, delay), self._play_loop)

    def _step_forward(self):
        if not self.frames:
            return
        self.current_frame = min(self.current_frame + 1, len(self.frames) - 1)
        self._scale.set(self.current_frame)
        self._draw_frame()

    def _step_back(self):
        if not self.frames:
            return
        self.current_frame = max(self.current_frame - 1, 0)
        self._scale.set(self.current_frame)
        self._draw_frame()

    def _reset_frame(self):
        self.current_frame = 0
        self._playing = False
        self._btn_play.config(text="▶ 播放", bg="#4CAF50")
        if self.frames:
            self._scale.set(0)
            self._draw_frame()

    def _export_gif(self):
        """导出当前录制为 GIF 动图"""
        if not HAS_PILLOW:
            messagebox.showwarning("提示", "需要安装 Pillow 库才能导出 GIF：\npip install Pillow")
            return

        if not self.frames:
            messagebox.showinfo("提示", "请先加载录制文件！")
            return

        filepath = filedialog.asksaveasfilename(
            title="保存 GIF 文件",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif")],
            initialfile=f"sort_replay_{self.meta.get('algo', 'unknown')}.gif"
        )
        if not filepath:
            return

        self._btn_export.config(state="disabled", text="导出中...")
        self.root.update()

        def _do_export():
            try:
                images = []
                w, h = 800, 400
                for i, frame in enumerate(self.frames):
                    img = Image.new('RGB', (w, h), self.COLORS['bg'])
                    draw = ImageDraw.Draw(img)

                    array = frame.get('array', [])
                    highlight = frame.get('highlight', [])
                    if not array:
                        continue

                    n = len(array)
                    max_val = max(array) if array else 1
                    margin = 20
                    bar_area_w = w - margin * 2
                    bar_area_h = h - margin * 2 - 30

                    bar_w = max(1, bar_area_w / n - 1)
                    gap = 1 if n > 20 else 2

                    # 绘制柱子
                    for j, val in enumerate(array):
                        x = margin + j * (bar_w + gap)
                        bar_h = max(1, (val / max_val) * bar_area_h)
                        y = h - margin - bar_h

                        color = self.COLORS['highlight'] if j in highlight else self.COLORS['normal']
                        draw.rectangle([x, y, x + bar_w, h - margin], fill=color, outline='#333')

                    # 帧信息
                    try:
                        font = ImageFont.truetype("msyh.ttc", 14)
                    except Exception:
                        font = ImageFont.load_default()
                    draw.text((w // 2 - 100, 8), f"帧 {i + 1}/{len(self.frames)}",
                              fill=self.COLORS['text'], font=font)

                    images.append(img)

                if images:
                    duration = int(100 / max(0.25, self._speed))
                    images[0].save(filepath, save_all=True, append_images=images[1:],
                                    duration=duration, loop=0, optimize=True)

                self.root.after(0, lambda: self._export_done(filepath))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("导出失败", str(e)))
                self.root.after(0, lambda: self._btn_export.config(state="normal", text="导出 GIF"))

        threading.Thread(target=_do_export, daemon=True).start()

    def _export_done(self, filepath):
        self._btn_export.config(state="normal", text="导出 GIF")
        messagebox.showinfo("导出成功", f"GIF 已保存到:\n{filepath}")

    def _on_close(self):
        self._playing = False
        try:
            self.root.destroy()
        except Exception:
            pass


# ============================================================
#  入口函数
# ============================================================

def launch_replay(record_file=None):
    """启动回放窗口"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-alpha', 0)

    ReplayWindow(record_file=record_file, parent_root=root)
    root.mainloop()


if __name__ == "__main__":
    import sys
    record_file = sys.argv[1] if len(sys.argv) > 1 else None
    launch_replay(record_file)
