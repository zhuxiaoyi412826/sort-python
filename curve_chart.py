# -*- coding: utf-8 -*-
"""
算法复杂度曲线对比
==================
使用 Matplotlib + Tkinter 展示多种排序算法在不同数据规模下的性能曲线。
功能：
  - 选择 2~9 种算法
  - 横轴：数据规模 n（10~10000，对数刻度）
  - 纵轴：比较次数 / 交换次数 / 耗时（可切换）
  - 多条曲线对比 O(n) 增长趋势
  - 鼠标悬停显示具体数值
  - 算法信息表格
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
import numpy as np
import threading
import time
import random
import os

from sorting_algos import BASIC_ALGOS, FUN_ALGOS, ALGO_DISPATCH

ALL_ALGOS = BASIC_ALGOS  # 仅使用10种标准排序算法

# 中文字体
_CN_FONT = None
for _name in ['Microsoft YaHei', 'SimHei', 'SimSun', 'DengXian']:
    if any(_name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        _CN_FONT = _name
        break
if _CN_FONT:
    plt.rcParams['font.sans-serif'] = [_CN_FONT, 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

# 算法复杂度元数据
ALGO_META = {
    "冒泡排序":   ("Bubble Sort",       "O(n²)",      "O(1)"),
    "选择排序":   ("Selection Sort",    "O(n²)",      "O(1)"),
    "插入排序":   ("Insertion Sort",    "O(n²)",      "O(1)"),
    "快速排序":   ("Quick Sort",        "O(n log n)", "O(log n)"),
    "归并排序":   ("Merge Sort",        "O(n log n)", "O(n)"),
    "希尔排序":   ("Shell Sort",        "O(n^1.3)",   "O(1)"),
    "堆排序":     ("Heap Sort",         "O(n log n)", "O(1)"),
    "桶排序":     ("Bucket Sort",       "O(n+k)",     "O(n+k)"),
    "计数排序":   ("Counting Sort",     "O(n+k)",     "O(k)"),
    "基数排序":   ("Radix Sort",        "O(d·(n+k))", "O(n+k)"),
    "猴子排序":   ("Bogo Sort",         "O(∞)",       "O(1)"),
    "睡眠排序":   ("Sleep Sort",        "O(n+max)",   "O(n)"),
    "面条排序":   ("Spaghetti Sort",    "O(n²)",      "O(n)"),
    "斯大林排序": ("Stalin Sort",       "O(n)",       "O(1)"),
    "鸡尾酒排序": ("Cocktail Sort",     "O(n²)",      "O(1)"),
    "慢排序":     ("Slow Sort",         "O(n^log n)", "O(log n)"),
    "煎饼排序":   ("Pancake Sort",      "O(n²)",      "O(1)"),
    "珠排序":     ("Bead Sort",         "O(n·max)",   "O(n·max)"),
    "鸽巢排序":   ("Pigeonhole Sort",   "O(n+k)",     "O(n+k)"),
}

# 超过此规模跳过超慢算法
SKIP_ABOVE = {
    "猴子排序": 8,
    "慢排序": 25,
    "睡眠排序": 50,
    "面条排序": 200,
    "珠排序": 200,
    "桶排序": 2000,
    "计数排序": 5000,
    "鸽巢排序": 5000,
    "基数排序": 5000,
}

# 曲线颜色
CURVE_COLORS = ['#4169E1', '#FF6347', '#32CD32', '#FF8C00',
                '#9932CC', '#00CED1', '#FF69B4', '#FFD700', '#20B2AA', '#8B4513']

# 数据规模采样点
DATA_SIZES = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]


# ============================================================
#  基准测试
# ============================================================

def _benchmark_algo(algo_name, n):
    """对指定算法在数据规模 n 下进行基准测试
    返回 (cmp_count, swap_count, elapsed_ms)
    """
    # 检查是否跳过
    limit = SKIP_ABOVE.get(algo_name)
    if limit and n > limit:
        return None, None, None

    arr = [random.randint(1, max(10, n * 2)) for _ in range(n)]
    func = ALGO_DISPATCH[algo_name]

    t0 = time.perf_counter()
    gen = func(arr.copy())
    cmp_count = 0
    swap_count = 0
    try:
        for result in gen:
            if len(result) >= 4:
                _, _, swap_count, cmp_count = result[:4]
    except StopIteration:
        pass
    t1 = time.perf_counter()

    return cmp_count, swap_count, (t1 - t0) * 1000  # ms


# ============================================================
#  配置弹窗（无数据规模滑块）
# ============================================================

class CurveConfigDialog(tk.Toplevel):
    """算法选择弹窗 - 选择 2~10 种算法"""

    def __init__(self, parent, on_confirm):
        super().__init__(parent)
        self.title("算法曲线表 - 配置")
        self.geometry("520x500")
        self.resizable(False, False)

        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        self.grab_set()

        self._parent_root = parent
        self._on_confirm = on_confirm
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="选择对比算法（2~10种）", font=("Microsoft YaHei", 12, "bold"),
                 fg="#2266aa").pack(pady=(14, 6))

        frame = tk.Frame(self)
        frame.pack(fill="x", padx=20)

        self._vars = {}
        cols = 3
        for i, name in enumerate(ALL_ALGOS):
            var = tk.BooleanVar(value=False)
            self._vars[name] = var
            cb = tk.Checkbutton(frame, text=name, variable=var,
                                font=("Microsoft YaHei", 10), anchor="w",
                                command=self._update_count)
            cb.grid(row=i // cols, column=i % cols, sticky="w", pady=2)

        self._count_label = tk.Label(self, text="已选择 0 种算法",
                                     font=("Microsoft YaHei", 10, "bold"), fg="#2266aa")
        self._count_label.pack(pady=(12, 0))
        tk.Label(self, text="最多选择 10 种算法",
                 font=("Microsoft YaHei", 9), fg="#999").pack(pady=(0, 4))

        # 全选/全部清除按钮
        sel_frame = tk.Frame(self)
        sel_frame.pack(pady=(6, 2))
        tk.Button(sel_frame, text="全选", font=("Microsoft YaHei", 10),
                  bg="#32CD32", fg="white", width=8, command=self._select_all
                  ).pack(side="left", padx=8)
        tk.Button(sel_frame, text="全部清除", font=("Microsoft YaHei", 10),
                  bg="#cc4444", fg="white", width=8, command=self._clear_all
                  ).pack(side="left", padx=8)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=14)
        tk.Button(btn_frame, text="确定", font=("Microsoft YaHei", 11, "bold"),
                  bg="#2266aa", fg="white", width=12, command=self._confirm
                  ).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", font=("Microsoft YaHei", 11),
                  width=12, command=self.destroy
                  ).pack(side="left", padx=10)

    def _update_count(self):
        count = sum(1 for var in self._vars.values() if var.get())
        self._count_label.config(text=f"已选择 {count} 种算法")
        if count < 2 or count > 10:
            self._count_label.config(fg="#cc0000")
        else:
            self._count_label.config(fg="#2266aa")
        if count > 10:
            self._show_limit_popup()

    def _select_all(self):
        """全选所有算法"""
        for var in self._vars.values():
            var.set(True)
        self._update_count()

    def _clear_all(self):
        """全部清除选择"""
        for var in self._vars.values():
            var.set(False)
        self._update_count()

    def _show_limit_popup(self):
        popup = tk.Toplevel(self)
        popup.title("提示")
        popup.geometry("320x120")
        popup.resizable(False, False)
        popup.transient(self)
        popup.attributes('-topmost', True)
        popup.lift()
        popup.focus_force()
        popup.grab_set()

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 320) // 2
        py = self.winfo_y() + (self.winfo_height() - 120) // 2
        popup.geometry(f"+{px}+{py}")

        tk.Label(popup, text="⚠", font=("Microsoft YaHei", 24), fg="#e67e22").pack(pady=(8, 2))
        tk.Label(popup, text="最多选择 10 种算法！",
                 font=("Microsoft YaHei", 12, "bold"), fg="#cc0000").pack()
        tk.Button(popup, text="确定", font=("Microsoft YaHei", 10),
                  bg="#cc0000", fg="white", width=10,
                  command=popup.destroy).pack(pady=8)

    def _confirm(self):
        selected = [name for name, var in self._vars.items() if var.get()]
        if len(selected) < 2:
            messagebox.showwarning("提示", "请至少选择 2 种算法！")
            return
        if len(selected) > 10:
            messagebox.showwarning("提示", "最多选择 10 种算法！")
            return
        self.destroy()
        self._on_confirm(selected)


# ============================================================
#  曲线图表窗口
# ============================================================

class CurveChartWindow:
    """算法复杂度曲线对比窗口"""

    def __init__(self, algos, parent_root=None):
        self.algos = algos
        self.n_algos = len(algos)
        self._metrics = {}  # {algo: {n: (cmp, swap, ms)}}

        # 构建窗口
        if parent_root is not None:
            self.root = parent_root
            self.root.attributes('-alpha', 1)
            self.root.attributes('-topmost', True)
        else:
            self.root = tk.Tk()
            self.root.attributes('-topmost', True)

        self.root.title(f"算法复杂度曲线对比 - {self.n_algos} 种算法")
        self.root.geometry("1280x850")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.lift()
        self.root.focus_force()
        self.root.after(300, lambda: self.root.attributes('-topmost', False))
        self.root.update_idletasks()

        self._build_ui()
        self._setup_hover()
        self._run_benchmarks()

    def _build_ui(self):
        # 顶部控制栏
        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(ctrl, text="纵轴指标:", font=("Microsoft YaHei", 10)).pack(side="left")

        self._metric_var = tk.StringVar(value="comparisons")
        metrics = [("比较次数", "comparisons"), ("交换次数", "swaps"), ("耗时(ms)", "time")]
        for text, val in metrics:
            tk.Radiobutton(ctrl, text=text, variable=self._metric_var, value=val,
                           font=("Microsoft YaHei", 10), command=self._update_chart
                           ).pack(side="left", padx=8)

        # 对数刻度开关
        self._log_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="对数刻度", variable=self._log_var,
                       font=("Microsoft YaHei", 10), command=self._update_chart
                       ).pack(side="right", padx=8)

        # 进度提示
        self._progress_label = tk.Label(self.root, text="正在计算...",
                                        font=("Microsoft YaHei", 11, "bold"), fg="#cc6600")
        self._progress_label.pack(pady=4)

        # Matplotlib 图表区
        chart_frame = tk.Frame(self.root)
        chart_frame.pack(fill="both", expand=True, padx=10)

        self._fig = Figure(figsize=(12, 5), dpi=100)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=chart_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        # 算法信息表格
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="x", padx=10, pady=(4, 8))

        tk.Label(table_frame, text="算法详细信息", font=("Microsoft YaHei", 11, "bold"),
                 fg="#2266aa").pack(anchor="w")

        cols = ("算法", "英文名", "时间复杂度", "空间复杂度", "类型")
        self._tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=5)
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=160, anchor="center")
        self._tree.column("算法", width=100)
        self._tree.column("类型", width=120)
        self._tree.pack(fill="x", pady=(4, 0))

        # 填充表格
        type_map = {
            "O(n²)": "二次方", "O(n log n)": "线性对数", "O(n)": "线性",
            "O(1)": "常数", "O(n+k)": "线性", "O(d·(n+k))": "线性",
            "O(n^1.3)": "次二次", "O(∞)": "不确定", "O(n+max)": "特殊",
            "O(n^log n)": "超指数", "O(n·max)": "特殊",
        }
        for algo in self.algos:
            meta = ALGO_META.get(algo, ("?", "?", "?"))
            eng, tc, sc = meta
            algo_type = type_map.get(tc, tc)
            self._tree.insert("", "end", values=(algo, eng, tc, sc, algo_type))

    def _run_benchmarks(self):
        """在后台线程运行基准测试"""
        def _worker():
            sizes = DATA_SIZES
            total = len(self.algos) * len(sizes)
            done = 0
            for algo in self.algos:
                self._metrics[algo] = {}
                for n in sizes:
                    cmp, swap, ms = _benchmark_algo(algo, n)
                    self._metrics[algo][n] = (cmp, swap, ms)
                    done += 1
                    pct = int(done / total * 100)
                    try:
                        self._progress_label.config(
                            text=f"正在计算... {pct}%  ({algo}, n={n})")
                        self.root.update_idletasks()
                    except Exception:
                        return  # 窗口已关闭

            try:
                self._progress_label.config(text="✓ 计算完成", fg="#00aa44")
                self._update_chart()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _update_chart(self):
        """根据选择的指标更新图表"""
        self._ax.clear()
        metric = self._metric_var.get()
        use_log = self._log_var.get()

        ylabel_map = {
            "comparisons": "比较次数",
            "swaps": "交换次数",
            "time": "耗时 (ms)",
        }
        ylabel = ylabel_map.get(metric, "比较次数")

        sizes = DATA_SIZES
        self._line_data = []  # 每次更新图表时重置
        for idx, algo in enumerate(self.algos):
            color = CURVE_COLORS[idx % len(CURVE_COLORS)]
            xs, ys = [], []
            data = self._metrics.get(algo, {})
            for n in sizes:
                vals = data.get(n)
                if vals is None or vals[0] is None:
                    continue
                cmp, swap, ms = vals
                if metric == "comparisons":
                    y = cmp
                elif metric == "swaps":
                    y = swap
                else:
                    y = ms
                xs.append(n)
                ys.append(y)

            if xs:
                lines = self._ax.plot(xs, ys, 'o-', color=color, label=algo,
                                      linewidth=2, markersize=5, picker=True)
                self._line_data.append((lines[0], algo, xs, ys, data))
                # 标注数值
                for x, y in zip(xs, ys):
                    if y > 0:
                        self._ax.annotate(f'{y:,.0f}', (x, y),
                                          textcoords="offset points",
                                          xytext=(0, 8), fontsize=7,
                                          color=color, ha='center')

        # 轴设置
        if use_log:
            self._ax.set_xscale('log')
            self._ax.set_yscale('log')

        self._ax.set_xlabel("数据规模 n", fontsize=12)
        self._ax.set_ylabel(ylabel, fontsize=12)
        self._ax.set_title(f"算法复杂度曲线对比 - {ylabel}", fontsize=14, fontweight='bold')
        self._ax.legend(fontsize=9, loc='upper left', framealpha=0.9)
        self._ax.grid(True, alpha=0.3, linestyle='--')

        # 设置 x 轴刻度标签
        self._ax.set_xticks([10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000])
        self._ax.set_xticklabels(['10', '20', '50', '100', '200', '500',
                                  '1K', '2K', '5K', '10K'], fontsize=8)

        self._fig.tight_layout()
        self._canvas.draw()

    # ----------------------------------------------------------
    #  悬停交互
    # ----------------------------------------------------------
    def _setup_hover(self):
        """初始化悬停提示相关状态并绑定鼠标事件"""
        self._hover_annot = None   # 悬停注释对象
        self._line_data = []       # [(line, algo_name, xs, ys, full_data), ...]
        self._cid = self._canvas.mpl_connect('motion_notify_event', self._on_hover)

    def _on_hover(self, event):
        """鼠标移动时检测最近的曲线并显示详细信息浮窗"""
        if event.inaxes != self._ax or not self._line_data:
            if self._hover_annot is not None:
                self._hover_annot.set_visible(False)
                self._hover_annot = None
                self._canvas.draw_idle()
            return

        # 找到距离鼠标最近的点
        best_dist = float('inf')
        best_info = None
        for line_obj, algo_name, xs, ys, full_data in self._line_data:
            if not xs:
                continue
            for i, (px, py) in enumerate(zip(xs, ys)):
                # 将数据坐标转换为显示坐标来计算距离
                disp_x, disp_y = self._ax.transData.transform((px, py))
                mouse_x, mouse_y = event.x, event.y
                dist = ((disp_x - mouse_x) ** 2 + (disp_y - mouse_y) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    n_val = xs[i]
                    best_info = (algo_name, n_val, full_data.get(n_val), px, py)

        THRESHOLD = 40  # 像素距离阈值
        if best_info and best_dist < THRESHOLD:
            algo_name, n_val, vals, px, py = best_info
            if vals and vals[0] is not None:
                cmp, swap, ms = vals
            else:
                cmp, swap, ms = 'N/A', 'N/A', 'N/A'

            meta = ALGO_META.get(algo_name, ('?', '?', '?'))
            eng, tc, sc = meta

            text = (
                f"{algo_name} ({eng})\n"
                f"───────────────\n"
                f"数据规模: n = {n_val:,}\n"
                f"比较次数: {cmp:,}\n"
                f"交换次数: {swap:,}\n"
                f"耗时: {ms:.2f} ms\n"
                f"───────────────\n"
                f"时间复杂度: {tc}\n"
                f"空间复杂度: {sc}"
            )

            if self._hover_annot is not None:
                self._hover_annot.remove()

            # 根据鼠标位置决定提示框偏移方向，避免超出边界
            xoff = 15 if event.xdata < (self._ax.get_xlim()[0] + self._ax.get_xlim()[1]) / 1.5 else -15
            ha = 'left' if xoff > 0 else 'right'

            self._hover_annot = self._ax.annotate(
                text, xy=(px, py), xytext=(xoff, 15),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='#FFFFCC', ec='#666666', alpha=0.95),
                fontsize=9, fontfamily='Microsoft YaHei',
                ha=ha, va='bottom',
                arrowprops=dict(arrowstyle='->', color='#666666', lw=1.2)
            )
            self._canvas.draw_idle()
        else:
            if self._hover_annot is not None:
                self._hover_annot.set_visible(False)
                self._hover_annot = None
                self._canvas.draw_idle()

    def _on_close(self):
        try:
            if hasattr(self, '_cid'):
                self._canvas.mpl_disconnect(self._cid)
            self.root.destroy()
        except Exception:
            pass


# ============================================================
#  入口函数
# ============================================================

def launch_curve_chart():
    """启动算法曲线表功能"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-alpha', 0)

    def _on_confirm(algos):
        root.deiconify()          # 先恢复窗口显示（withdraw 的反操作）
        root.attributes('-alpha', 1)
        root.attributes('-topmost', False)
        CurveChartWindow(algos, parent_root=root)

    dialog = CurveConfigDialog(root, _on_confirm)

    def _cancel():
        dialog.destroy()
        root.destroy()

    dialog.protocol("WM_DELETE_WINDOW", _cancel)
    root.mainloop()


if __name__ == "__main__":
    launch_curve_chart()
