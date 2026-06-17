# -*- coding: utf-8 -*-
"""
多算法对比模式
==============
使用 Matplotlib + Tkinter 实现多排序算法并行对比可视化。
功能：
  - 选择 2~9 种算法进行对比
  - 选择数据规模 (10~100)
  - 实时 matplotlib 柱状图动画
  - 排行榜面板（耗时/比较次数/交换次数）
  - JSON / 图片导出
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
import numpy as np
import threading
import time
import json
import random
import os

# 导入排序算法
from sorting_algos import BASIC_ALGOS, FUN_ALGOS, ALGO_DISPATCH

ALL_ALGOS = BASIC_ALGOS + FUN_ALGOS


def _read_brightness():
    """从 brightness.cfg 读取亮度值 (20~100)"""
    try:
        bri_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brightness.cfg")
        with open(bri_file, "r") as f:
            val = int(f.read().strip())
            return max(20, min(100, val))
    except Exception:
        return 100


def _read_dark_mode():
    """从 darkmode.cfg 读取深色模式设置 (True=深色, False=浅色)"""
    try:
        dark_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "darkmode.cfg")
        with open(dark_file, "r") as f:
            val = f.read().strip()
            return val == "1"
    except Exception:
        return True  # 默认深色模式

# ---------- 算法复杂度信息 ----------
ALGO_COMPLEXITY = {
    "冒泡排序":   ("O(n²)",      "O(1)"),
    "选择排序":   ("O(n²)",      "O(1)"),
    "插入排序":   ("O(n²)",      "O(1)"),
    "快速排序":   ("O(n log n)", "O(log n)"),
    "归并排序":   ("O(n log n)", "O(n)"),
    "希尔排序":   ("O(n^1.3)",   "O(1)"),
    "堆排序":     ("O(n log n)", "O(1)"),
    "桶排序":     ("O(n+k)",     "O(n+k)"),
    "计数排序":   ("O(n+k)",     "O(k)"),
    "基数排序":   ("O(d·n)",     "O(n+d)"),
    "猴子排序":   ("O(∞)",       "O(1)"),
    "睡眠排序":   ("O(n+max)",   "O(n)"),
    "面条排序":   ("O(n)",       "O(n)"),
    "斯大林排序": ("O(n)",       "O(1)"),
    "鸡尾酒排序": ("O(n²)",      "O(1)"),
    "慢排序":     ("O(n^2.7)",   "O(n)"),
    "煎饼排序":   ("O(n²)",      "O(1)"),
    "珠排序":     ("O(n·m)",     "O(n·m)"),
    "鸽巢排序":   ("O(n+k)",     "O(k)"),
}

# ---------- 倍速档位 ----------
SPEED_LEVELS = [0.25, 0.5, 1, 2, 4, 8,16,32]

# ---------- 中文字体设置 ----------
_CN_FONT = None
for _name in ['Microsoft YaHei', 'SimHei', 'SimSun', 'DengXian', 'FangSong']:
    if any(_name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        _CN_FONT = _name
        break
if _CN_FONT:
    plt.rcParams['font.sans-serif'] = [_CN_FONT, 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False


# ============================================================
#  配置对话框
# ============================================================
class ConfigDialog(tk.Toplevel):
    """算法选择 + 数据规模配置弹窗"""

    def __init__(self, parent, on_confirm):
        super().__init__(parent)
        self.title("多算法对比 - 配置")
        self.geometry("520x500")
        self.resizable(False, False)
        # 不使用 transient(parent)，因为父窗口已 withdraw，会导致子窗口不可见

        # 强制前台显示
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        self.grab_set()

        self._parent_root = parent
        self._on_confirm = on_confirm
        self._selected = []
        self._scale = 50

        self._build_ui()

    def _build_ui(self):
        # 算法选择区
        tk.Label(self, text="选择对比算法（2~9种）", font=("Microsoft YaHei", 12, "bold"),
                 fg="#2266aa").pack(pady=(12, 4))

        frame_algo = tk.Frame(self)
        frame_algo.pack(fill="x", padx=20)

        self._vars = {}
        cols = 3
        for i, name in enumerate(ALL_ALGOS):
            var = tk.BooleanVar(value=False)
            self._vars[name] = var
            cb = tk.Checkbutton(frame_algo, text=name, variable=var,
                                font=("Microsoft YaHei", 10), anchor="w",
                                command=self._update_count)
            cb.grid(row=i // cols, column=i % cols, sticky="w", pady=2)

        # 数据规模
        tk.Label(self, text="数据规模（10~100）", font=("Microsoft YaHei", 11),
                 fg="#333").pack(pady=(16, 4))

        scale_frame = tk.Frame(self)
        scale_frame.pack()
        self._scale_var = tk.IntVar(value=50)
        self._scale_label = tk.Label(scale_frame, text="50", font=("Microsoft YaHei", 11, "bold"),
                                     width=4, fg="#aa3300")
        self._scale_label.pack(side="right", padx=10)
        tk.Scale(scale_frame, from_=10, to=100, orient="horizontal",
                 length=300, variable=self._scale_var,
                 command=self._on_scale_change,
                 font=("Microsoft YaHei", 9)).pack(side="left")

        # 已选数量提示（动态更新）
        self._count_label = tk.Label(self, text="已选择 0 种算法",
                                     font=("Microsoft YaHei", 10, "bold"), fg="#2266aa")
        self._count_label.pack(pady=(8, 0))
        # 最大限制提示
        tk.Label(self, text="最多选择 9 种算法",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 4))

        # 按钮区
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=16)
        tk.Button(btn_frame, text="确定", font=("Microsoft YaHei", 11, "bold"),
                  bg="#2266aa", fg="white", width=12, command=self._confirm
                  ).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", font=("Microsoft YaHei", 11),
                  width=12, command=self.destroy
                  ).pack(side="left", padx=10)

    def _on_scale_change(self, val):
        self._scale = int(float(val))
        self._scale_label.config(text=str(self._scale))

    def _update_count(self):
        """动态更新已选算法数量，超出9种时弹出警告"""
        count = sum(1 for var in self._vars.values() if var.get())
        self._count_label.config(text=f"已选择 {count} 种算法")
        # 颜色反馈
        if count < 2:
            self._count_label.config(fg="#cc0000")   # 不足时红色
        elif count > 9:
            self._count_label.config(fg="#cc0000")   # 超出时红色
            self._show_limit_popup()
        else:
            self._count_label.config(fg="#2266aa")   # 正常时蓝色

    def _show_limit_popup(self):
        """弹出模态提示框：超出9种算法时强制用户确认"""
        popup = tk.Toplevel(self)
        popup.title("提示")
        popup.geometry("320x130")
        popup.resizable(False, False)
        popup.transient(self)
        popup.attributes('-topmost', True)
        popup.lift()
        popup.focus_force()
        popup.grab_set()

        # 居中显示在父窗口上方
        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 320) // 2
        py = self.winfo_y() + (self.winfo_height() - 130) // 2
        popup.geometry(f"+{px}+{py}")

        tk.Label(popup, text="⚠", font=("Microsoft YaHei", 24),
                 fg="#e67e22").pack(pady=(10, 2))
        tk.Label(popup, text="最多选择 9 种算法！",
                 font=("Microsoft YaHei", 12, "bold"), fg="#cc0000").pack()
        tk.Button(popup, text="取消", font=("Microsoft YaHei", 10),
                  bg="#cc0000", fg="white", width=10,
                  command=popup.destroy).pack(pady=10)

    def _confirm(self):
        selected = [name for name, var in self._vars.items() if var.get()]
        if len(selected) < 2:
            messagebox.showwarning("提示", "请至少选择 2 种算法！")
            return
        if len(selected) > 9:
            messagebox.showwarning("提示", "最多选择 9 种算法！")
            return
        algos = selected
        scale = self._scale
        self.destroy()  # 先关闭，释放 grab_set
        self._on_confirm(algos, scale)


# ============================================================
#  对比主窗口
# ============================================================
class CompareWindow:
    """多算法对比可视化窗口（Matplotlib + Tkinter）"""

    # 最多 9 个子图颜色
    COLORS = ['#4169E1', '#FF6347', '#32CD32', '#FF8C00',
              '#9932CC', '#00CED1', '#FF69B4', '#FFD700', '#20B2AA']

    @staticmethod
    def _dim_color(hex_color, ratio):
        """将 hex 颜色按比例变暗，ratio: 0.0~1.0"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
        r, g, b = int(r * ratio), int(g * ratio), int(b * ratio)
        return f'#{r:02x}{g:02x}{b:02x}'

    def __init__(self, algos, scale, parent_root=None):
        self.algos = algos
        self.scale = scale
        self.n_algos = len(algos)

        # 数据与状态
        self.arrays = {}        # 每种算法的数组副本
        self.generators = {}    # 排序生成器
        self.stats = {}         # {algo: {cmp, swap, time, done}}
        self._running = False
        self._paused = False
        self._all_done = False
        self._thread = None

        self._init_data()

        # 倍速状态
        self._speed_idx = 2  # 默认 1x (SPEED_LEVELS[2])

        # 亮度 (0.2~1.0)
        self._brightness = _read_brightness()
        self._bri_ratio = self._brightness / 100.0

        # 深色/浅色模式
        self._dark_mode = _read_dark_mode()

        # 构建窗口（复用父窗口或创建新窗口）
        if parent_root is not None:
            self.root = parent_root
            # 恢复可见并重置属性
            self.root.attributes('-alpha', 1)
            self.root.attributes('-topmost', True)
        else:
            self.root = tk.Tk()
            self.root.attributes('-topmost', True)

        self.root.title(f"多算法对比 - {self.n_algos} 种算法 | 数据规模: {self.scale}")
        self.root.geometry("1200x750")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.lift()
        self.root.focus_force()
        self.root.after(300, lambda: self.root.attributes('-topmost', False))

        # 先让窗口完成布局再构建图表，避免在极小窗口中渲染导致卡死
        self.root.update_idletasks()

        self._build_ui()
        self._draw_initial()

    # ----------------------------------------------------------
    #  初始化数据
    # ----------------------------------------------------------

    def _init_data(self):
        """生成随机数据并初始化每种算法的生成器"""
        base = [random.randint(1, 1000) for _ in range(self.scale)]
        for algo in self.algos:
            arr = base.copy()
            self.arrays[algo] = arr
            self.generators[algo] = ALGO_DISPATCH[algo](arr)
            self.stats[algo] = {
                'cmp': 0, 'swap': 0, 'time': 0.0, 'done': False
            }

    def _randomize(self):
        """重新生成随机数据"""
        for algo in self.algos:
            self.stats[algo] = {'cmp': 0, 'swap': 0, 'time': 0.0, 'done': False}
        self._all_done = False
        self._running = False
        self._paused = False
        base = [random.randint(1, 1000) for _ in range(self.scale)]
        for algo in self.algos:
            arr = base.copy()
            self.arrays[algo] = arr
            self.generators[algo] = ALGO_DISPATCH[algo](arr)
        self._draw_initial()
        self._update_ranking()

    # ----------------------------------------------------------
    #  UI 构建
    # ----------------------------------------------------------

    def _build_ui(self):
        # 亮度调节后的背景色
        r = self._bri_ratio
        if self._dark_mode:
            ctrl_bg = self._dim_color('#1a1a2e', r)
            fig_bg = self._dim_color('#0d1117', r)
            ax_bg = self._dim_color('#161b22', r)
            text_fg = "white"
            accent_fg = "#00ff88"
            spine_color = '#333333'
            tree_bg = "#161b22"
            tree_fg = "white"
            tree_head_bg = "#2a2a4e"
        else:
            ctrl_bg = self._dim_color('#e8ecf1', r)
            fig_bg = self._dim_color('#f0f2f5', r)
            ax_bg = self._dim_color('#ffffff', r)
            text_fg = "#222222"
            accent_fg = "#00884a"
            spine_color = '#aaaaaa'
            tree_bg = "#ffffff"
            tree_fg = "#222222"
            tree_head_bg = "#dde0e4"
        self._fig_bg = fig_bg
        self._ax_bg = ax_bg
        self._text_fg = text_fg
        self._spine_color = spine_color

        # 顶部控制栏
        ctrl = tk.Frame(self.root, bg=ctrl_bg, height=50)
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)

        btn_style = {"font": ("Microsoft YaHei", 10, "bold"), "width": 10, "bd": 0}
        tk.Button(ctrl, text="▶ 开始", bg="#28a745", fg="white",
                  command=self._start, **btn_style).pack(side="left", padx=8, pady=10)
        tk.Button(ctrl, text="⏸ 暂停", bg="#ffc107", fg="black",
                  command=self._pause, **btn_style).pack(side="left", padx=8, pady=10)
        tk.Button(ctrl, text="🔀 随机", bg="#17a2b8", fg="white",
                  command=self._randomize, **btn_style).pack(side="left", padx=8, pady=10)

        # 倍速控制按钮
        speed_btn_style = {"font": ("Microsoft YaHei", 10, "bold"), "width": 6, "bd": 0}
        tk.Button(ctrl, text="⏪ 减速", bg="#e67e22", fg="white",
                  command=self._speed_down, **speed_btn_style
                  ).pack(side="left", padx=4, pady=10)
        self._speed_var = tk.StringVar(value="1x")
        tk.Label(ctrl, textvariable=self._speed_var,
                 font=("Microsoft YaHei", 11, "bold"), bg=ctrl_bg, fg="#ffd700",
                 width=5).pack(side="left", padx=2, pady=10)
        tk.Button(ctrl, text="加速 ⏩", bg="#e67e22", fg="white",
                  command=self._speed_up, **speed_btn_style
                  ).pack(side="left", padx=4, pady=10)

        # 状态标签
        self._status_var = tk.StringVar(value="就绪")
        tk.Label(ctrl, textvariable=self._status_var,
                 font=("Microsoft YaHei", 11), bg=ctrl_bg, fg=accent_fg
                 ).pack(side="left", padx=20, pady=10)

        # 导出按钮区（右侧）
        tk.Button(ctrl, text="📷 导出图片", bg="#6c757d", fg="white",
                  font=("Microsoft YaHei", 9), width=12, bd=0,
                  command=self._export_image).pack(side="right", padx=8, pady=10)
        tk.Button(ctrl, text="📄 导出JSON", bg="#6c757d", fg="white",
                  font=("Microsoft YaHei", 9), width=12, bd=0,
                  command=self._export_json).pack(side="right", padx=8, pady=10)

        # 主体区域（左图表 + 右排行）
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        # matplotlib 图表区
        chart_frame = tk.Frame(main_frame)
        chart_frame.pack(side="left", fill="both", expand=True)

        # 计算子图布局（动态调整画布大小）
        ncols = min(3, self.n_algos)
        nrows = (self.n_algos + ncols - 1) // ncols
        fig_w = 9 if nrows <= 2 else 10
        fig_h = 4.5 * nrows

        self.fig = Figure(figsize=(fig_w, fig_h), dpi=90, facecolor=fig_bg)
        self.fig.subplots_adjust(hspace=0.35, wspace=0.25)
        self.axes = []
        for i in range(self.n_algos):
            ax = self.fig.add_subplot(nrows, ncols, i + 1)
            ax.set_facecolor(ax_bg)
            ax.tick_params(colors='#888888' if self._dark_mode else '#444444', labelsize=7)
            # 图表标题: 算法名 + 时间复杂度 + 空间复杂度
            tc, sc = ALGO_COMPLEXITY.get(self.algos[i], ("?", "?"))
            ax.set_title(f"{self.algos[i]}  |  时间:{tc}  空间:{sc}",
                         fontsize=9, color=self.COLORS[i % len(self.COLORS)],
                         pad=4, loc='left')
            ax.title.set_color(self.COLORS[i % len(self.COLORS)])
            for spine in ax.spines.values():
                spine.set_color(spine_color)
            self.axes.append(ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # 排行榜区（右侧）
        rank_frame = tk.Frame(main_frame, bg=ctrl_bg, width=320)
        rank_frame.pack(side="right", fill="y")
        rank_frame.pack_propagate(False)

        tk.Label(rank_frame, text="📊 排行榜", font=("Microsoft YaHei", 12, "bold"),
                 fg=accent_fg, bg=ctrl_bg).pack(pady=(10, 6))

        # 表格
        cols = ("算法", "比较", "交换", "耗时")
        self.tree = ttk.Treeview(rank_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=75 if c != "算法" else 100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        # 配置行颜色
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=tree_bg, foreground=tree_fg,
                        fieldbackground=tree_bg, font=("Microsoft YaHei", 9))
        style.configure("Treeview.Heading", background=tree_head_bg, foreground=text_fg,
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("Treeview", background=[("selected", "#3a3a6e" if self._dark_mode else "#b0c4de")])

        # 初始化表格行
        for algo in self.algos:
            self.tree.insert("", "end", iid=algo,
                             values=(algo, "0", "0", "0.000s"))

    def _draw_initial(self):
        """绘制初始柱状图"""
        tick_c = '#888888' if self._dark_mode else '#444444'
        for i, algo in enumerate(self.algos):
            ax = self.axes[i]
            ax.clear()
            ax.set_facecolor(self._ax_bg)
            tc, sc = ALGO_COMPLEXITY.get(algo, ("?", "?"))
            ax.set_title(f"{algo}  |  时间:{tc}  空间:{sc}",
                         fontsize=9, color=self.COLORS[i % len(self.COLORS)],
                         pad=4, loc='left')
            ax.tick_params(colors=tick_c, labelsize=7)
            for spine in ax.spines.values():
                spine.set_color(self._spine_color)
            bars = ax.bar(range(len(self.arrays[algo])), self.arrays[algo],
                          color=self.COLORS[i % len(self.COLORS)], alpha=0.8)
            ax.set_ylim(0, 1100)
        self.canvas.draw()

    # ----------------------------------------------------------
    #  排序控制
    # ----------------------------------------------------------

    def _start(self):
        if self._all_done:
            return
        if self._paused:
            self._paused = False
            self._running = True
            self._status_var.set("排序中...")
            self._sort_loop()
            return
        if self._running:
            return
        self._running = True
        self._paused = False
        self._all_done = False
        for algo in self.algos:
            self.stats[algo]['time'] = 0.0
        self._status_var.set("排序中...")
        self._sort_loop()

    def _pause(self):
        if self._running:
            self._paused = True
            self._running = False
            self._status_var.set("已暂停")

    def _speed_up(self):
        if self._speed_idx < len(SPEED_LEVELS) - 1:
            self._speed_idx += 1
            spd = SPEED_LEVELS[self._speed_idx]
            self._speed_var.set(f"{spd:g}x")

    def _speed_down(self):
        if self._speed_idx > 0:
            self._speed_idx -= 1
            spd = SPEED_LEVELS[self._speed_idx]
            self._speed_var.set(f"{spd:g}x")

    def _sort_loop(self):
        """在后台线程推进排序"""
        if self._thread and self._thread.is_alive():
            return

        def worker():
            start_t = time.time()
            while self._running and not self._paused:
                any_active = False
                for algo in self.algos:
                    if self.stats[algo]['done']:
                        continue
                    any_active = True
                    # 每帧推进多步（根据数据量和倍速调节）
                    speed = SPEED_LEVELS[self._speed_idx]
                    steps = max(1, int((50 // self.scale) * speed))
                    for _ in range(steps):
                        try:
                            result = next(self.generators[algo])
                            if result:
                                self.arrays[algo] = list(result[0])
                                self.stats[algo]['swap'] = result[2]
                                self.stats[algo]['cmp'] = result[3]
                        except StopIteration:
                            self.stats[algo]['done'] = True
                            self.stats[algo]['time'] = time.time() - start_t
                            break

                if not any_active:
                    self._all_done = True
                    self._running = False
                    self.root.after(0, self._on_all_done)
                    return

                elapsed = time.time() - start_t
                for algo in self.algos:
                    if not self.stats[algo]['done']:
                        self.stats[algo]['time'] = elapsed

                # 更新 UI（主线程）
                self.root.after(0, self._update_charts)
                self.root.after(0, self._update_ranking)
                time.sleep(max(0.001, 0.03 / speed))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _on_all_done(self):
        """所有算法排序完成"""
        self._status_var.set("✓ 全部完成!")
        self._update_charts()
        self._update_ranking()

    # ----------------------------------------------------------
    #  图表 & 排行更新
    # ----------------------------------------------------------

    def _update_charts(self):
        """刷新所有子图"""
        tick_c = '#888888' if self._dark_mode else '#444444'
        info_c = '#aaaaaa' if self._dark_mode else '#666666'
        for i, algo in enumerate(self.algos):
            ax = self.axes[i]
            ax.clear()
            ax.set_facecolor(self._ax_bg)
            tc, sc = ALGO_COMPLEXITY.get(algo, ("?", "?"))
            ax.set_title(f"{algo}  |  时间:{tc}  空间:{sc}",
                         fontsize=9,
                         color=self.COLORS[i % len(self.COLORS)], pad=4, loc='left')
            ax.tick_params(colors=tick_c, labelsize=7)
            for spine in ax.spines.values():
                spine.set_color(self._spine_color)

            arr = self.arrays[algo]
            if len(arr) <= 100:
                ax.bar(range(len(arr)), arr,
                       color=self.COLORS[i % len(self.COLORS)], alpha=0.8)
            else:
                ax.plot(arr, color=self.COLORS[i % len(self.COLORS)], linewidth=0.8)
            ax.set_ylim(0, 1100)

            # 状态标注
            stat = self.stats[algo]
            info = f"比较:{stat['cmp']} 交换:{stat['swap']}"
            ax.text(0.5, 0.95, info, transform=ax.transAxes,
                    fontsize=7, color=info_c, ha='center', va='top')

        self.canvas.draw_idle()  # draw_idle 比 draw 更快，不阻塞UI

    def _update_ranking(self):
        """更新排行榜表格（按耗时排序）"""
        # 收集数据
        rows = []
        for algo in self.algos:
            s = self.stats[algo]
            rows.append((algo, s['cmp'], s['swap'], s['time'], s['done']))

        # 按耗时升序排列
        rows.sort(key=lambda r: r[3])

        # 更新表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        for rank, (algo, cmp, swap, t, done) in enumerate(rows):
            tag = ""
            if rank == 0:
                tag = "best"
            elif rank == len(rows) - 1 and len(rows) > 2:
                tag = "worst"
            time_str = f"{t:.3f}s"
            suffix = " ✓" if done else " ..."
            self.tree.insert("", "end", iid=algo,
                             values=(algo, cmp, swap, time_str + suffix))

        # 高亮最优/最差（浅色模式用深色文字）
        best_c = "#00ff88" if self._dark_mode else "#008844"
        worst_c = "#ff6666" if self._dark_mode else "#cc2222"
        self.tree.tag_configure("best", foreground=best_c)
        self.tree.tag_configure("worst", foreground=worst_c)

    # ----------------------------------------------------------
    #  导出
    # ----------------------------------------------------------

    def _export_json(self):
        """导出排行数据为 JSON"""
        rows = []
        for algo in self.algos:
            s = self.stats[algo]
            rows.append({
                "algorithm": algo,
                "comparisons": s['cmp'],
                "swaps": s['swap'],
                "time_seconds": round(s['time'], 4),
                "completed": s['done']
            })
        rows.sort(key=lambda r: r['time_seconds'])
        data = {"data_scale": self.scale, "results": rows}

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")],
            title="导出排行榜")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("导出成功", f"已保存到:\n{path}")

    def _export_image(self):
        """导出当前图表为图片"""
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png"), ("所有文件", "*.*")],
            title="导出图表")
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches='tight',
                             facecolor=self.fig.get_facecolor())
            messagebox.showinfo("导出成功", f"已保存到:\n{path}")

    # ----------------------------------------------------------
    #  窗口管理
    # ----------------------------------------------------------

    def _on_close(self):
        self._running = False
        self._paused = False
        self.root.destroy()

    def run(self):
        """启动主循环（阻塞）"""
        self.root.mainloop()


# ============================================================
#  入口函数（供主程序调用）
# ============================================================
def launch_compare(parent_tk=None):
    """
    打开多算法对比配置对话框。
    可从主程序线程调用，也可以独立运行。
    """
    root = tk.Tk()
    root.title("多算法对比")
    root.geometry("1x1+0+0")   # 最小化
    root.attributes('-alpha', 0)  # 透明不可见

    def on_confirm(algos, scale):
        # 复用同一个 root，避免多 Tk 实例冲突
        win = CompareWindow(algos, scale, parent_root=root)
        win.run()  # 嵌套 mainloop，用户关闭后返回

    dialog = ConfigDialog(root, on_confirm)

    def on_cancel():
        dialog.destroy()
        root.destroy()

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()


if __name__ == "__main__":
    launch_compare()
