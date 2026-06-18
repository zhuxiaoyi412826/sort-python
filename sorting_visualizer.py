# -*- coding: utf-8 -*-
"""
排序算法可视化工具 - 主程序
============================
从拆分后的模块导入各组件，组装并运行可视化界面。

模块拆分：
  - sorting_algos.py   排序算法（19种生成器）+ 源码提取
  - rendering.py       颜色常量、绘制函数、UI组件（按钮/菜单/对话框/代码面板）
  - data_generator.py  随机数据生成

运行方式：
  pip install pygame
  python sorting_visualizer.py
"""

import pygame
import sys
import os
import time
import math
import random
import threading
import asyncio
import subprocess

# 浏览器环境（pygbag WASM）检测
try:
    import platform as _platform_mod
    _IS_WASM = _platform_mod.system() == 'Emscripten'
except Exception:
    _IS_WASM = False

if not _IS_WASM:
    import subprocess

# 从拆分模块导入
from sorting_algos import (
    BASIC_ALGOS, FUN_ALGOS, ALGO_DISPATCH,
)
from rendering import (
    # 颜色
    BLACK, WHITE, BLUE, YELLOW, GREEN, RED, CYAN, DKBLUE, LGRAY,
    # 常量
    CTRL_H,
    # 工具
    draw_text, clamp,
    # UI 组件
    DropDown, Button, CountDialog, CodePanel, HoverDropDown, SettingsPanel,
)
from data_generator import generate_random_array
from audio_manager import SoundManager

# ============================================================
#  全局常量
# ============================================================
WIN_WIDTH  = 1280
WIN_HEIGHT = 720
FPS        = 60
DEFAULT_COUNT = 100
SPEED_LEVELS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]

# 数据分布选项
DATA_DIST_OPTIONS = ["随机分布", "近乎有序", "完全逆序", "少量唯一值", "正弦波形"]

# 算法元数据：英文名、时间复杂度、空间复杂度、复杂度类型
ALGO_META = {
    "冒泡排序":   ("Bubble Sort",       "O(n²)",       "O(1)",       "quadratic"),
    "选择排序":   ("Selection Sort",    "O(n²)",       "O(1)",       "quadratic"),
    "插入排序":   ("Insertion Sort",    "O(n²)",       "O(1)",       "quadratic"),
    "快速排序":   ("Quick Sort",        "O(n log n)",  "O(log n)",   "linearithmic"),
    "归并排序":   ("Merge Sort",        "O(n log n)",  "O(n)",       "linearithmic"),
    "希尔排序":   ("Shell Sort",        "O(n^1.3)",    "O(1)",       "sub_quadratic"),
    "堆排序":     ("Heap Sort",         "O(n log n)",  "O(1)",       "linearithmic"),
    "桶排序":     ("Bucket Sort",       "O(n+k)",      "O(n+k)",     "linear"),
    "计数排序":   ("Counting Sort",     "O(n+k)",      "O(k)",       "linear"),
    "基数排序":   ("Radix Sort",        "O(d·(n+k))",  "O(n+k)",     "linear"),
    "猴子排序":   ("Bogo Sort",         "O((n+1)!)",   "O(1)",       "factorial"),
    "睡眠排序":   ("Sleep Sort",        "O(n+max)",    "O(n)",       "special"),
    "面条排序":   ("Spaghetti Sort",    "O(n²)",       "O(n)",       "quadratic"),
    "斯大林排序": ("Stalin Sort",       "O(n)",        "O(1)",       "linear"),
    "鸡尾酒排序": ("Cocktail Sort",     "O(n²)",       "O(1)",       "quadratic"),
    "慢排序":     ("Slow Sort",         "O(n^log n)",  "O(log n)",   "super_exp"),
    "煎饼排序":   ("Pancake Sort",      "O(n²)",       "O(1)",       "quadratic"),
    "珠排序":     ("Bead Sort",         "O(n·max)",    "O(n·max)",   "special"),
    "鸽巢排序":   ("Pigeonhole Sort",   "O(n+k)",      "O(n+k)",     "linear"),
}


# ============================================================
#  主可视化器类
# ============================================================
class SortingVisualizer:
    def __init__(self, wasm_size=None):
        """
        wasm_size: (w, h) 浏览器固定画布大小，None 时使用桌面模式
        """
        pygame.init()
        pygame.display.set_caption("排序算法可视化 - Pygame")

        self.is_wasm = _IS_WASM

        # 屏幕信息
        if wasm_size:
            self.screen_w, self.screen_h = wasm_size
            self.screen = pygame.display.set_mode(wasm_size)
        elif self.is_wasm:
            self.screen_w, self.screen_h = 1280, 720
            self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        else:
            info = pygame.display.Info()
            self.screen_w = int(info.current_w * 0.75)
            self.screen_h = int(info.current_h * 0.75)
            self.screen = pygame.display.set_mode(
                (self.screen_w, self.screen_h), pygame.RESIZABLE
            )

        self.is_fullscreen = False
        self.clock = pygame.time.Clock()

        # 字体
        self._init_fonts()

        # 状态
        self.count        = DEFAULT_COUNT
        self.array        = []
        self.highlight    = []
        self.sorted_done  = False
        self.cmp_count    = 0
        self.swap_count   = 0
        self.speed_idx    = 2          # 对应 SPEED_LEVELS[2] = 1.0x
        self.running      = False
        self.paused       = False
        self.generator    = None
        self.algo_type    = "basic"
        self.algo_name    = BASIC_ALGOS[0]

        # 帧计时
        self.frame_acc   = 0.0
        self.steps_done  = 0

        # 数据分布类型（仅通过数据分布下拉框改变）
        self.data_dist   = 0

        # 排序计时
        self._sort_start_time = 0.0
        self._sort_elapsed    = 0.0
        self._sort_end_time   = 0.0

        self._generate_random()
        self.sound_mgr = SoundManager()   # 音效管理器
        self._build_ui()

    # ----------------------------------------------------------
    def _init_fonts(self):
        """初始化字体（优先使用捆绑字体，其次系统字体）"""
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        bundled = [
            os.path.join(_this_dir, "msyh.ttc"),
            os.path.join(_this_dir, "simhei.ttf"),
        ]
        system = [
            "microsoftyahei", "simhei", "simsun",
            "dengxian", "fangsong",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        ]
        candidates = bundled + system
        self.font_sm = None
        self.font_md = None
        self.font_lg = None
        for name in candidates:
            try:
                self.font_sm = pygame.font.Font(name, 16)
                self.font_md = pygame.font.Font(name, 20)
                self.font_lg = pygame.font.Font(name, 28)
                break
            except:
                pass
        if self.font_sm is None:
            self.font_sm = pygame.font.SysFont(None, 18)
            self.font_md = pygame.font.SysFont(None, 22)
            self.font_lg = pygame.font.SysFont(None, 32)

    # ----------------------------------------------------------
    def _build_ui(self):
        """根据当前窗口大小构建UI控件"""
        w = self.screen_w
        dd_w, dd_h, dd_y = 160, 38, 90
        self.dd_basic = DropDown(10,  dd_y, dd_w, dd_h, BASIC_ALGOS, self.font_md, "基础")
        self.dd_fun   = DropDown(180, dd_y, dd_w, dd_h, FUN_ALGOS,   self.font_md, "趣味")

        bw, bh, bx, by, gap = 90, 38, 355, 90, 8
        self.btn_start   = Button(bx,                 by, bw, bh, "开始",    (0,160,50),   font=self.font_md)
        self.btn_pause   = Button(bx+bw+gap,          by, bw, bh, "暂停",    (180,130,0),  font=self.font_md)
        self.btn_reset   = Button(bx+(bw+gap)*2,      by, bw, bh, "重置",    (180,40,40),  font=self.font_md)
        self.btn_faster  = Button(bx+(bw+gap)*3,      by, bw, bh, "加速",    (0,120,180),  font=self.font_md)
        self.btn_slower  = Button(bx+(bw+gap)*4,      by, bw, bh, "减速",    (0,80,140),   font=self.font_md)
        self.dd_data     = HoverDropDown(
            bx+(bw+gap)*5, by, bw+20, bh, DATA_DIST_OPTIONS, self.font_md,
            on_select=self._on_distribution_change)
        self.btn_setcnt  = Button(bx+(bw+gap)*5+bw+20+gap, by, bw+20, bh, "设置数量", (140,80,0), font=self.font_md)
        self.btn_full    = Button(w-220,              by, 100, bh, "全屏",    (0,160,160),  font=self.font_md)
        self.btn_srccode = Button(w-110, by, 100, bh, "算法代码", (40,100,60), font=self.font_md)
        self.btn_settings = Button(w-55, 8, 46, 28, "⚙", (30,35,65), font=self.font_md)

        self.btn_basic_tab = Button(10,  45, 150, 36, "基础排序", (0,80,160),  font=self.font_md)
        self.btn_fun_tab   = Button(170, 45, 150, 36, "趣味排序", (80,40,120), font=self.font_md)
        self.btn_compare   = Button(350, 45, 140, 36, "多算法对比", (180,80,0), font=self.font_md)

        self.all_buttons = [
            self.btn_start, self.btn_pause, self.btn_reset,
            self.btn_faster, self.btn_slower,
            self.btn_setcnt, self.btn_full, self.btn_srccode, self.btn_settings,
            self.btn_basic_tab, self.btn_fun_tab, self.btn_compare
        ]

        self.count_dialog = CountDialog(self.screen_w, self.screen_h, self.font_md, self.font_sm,
                                        on_change=self._on_count_change)
        self.settings_panel = SettingsPanel(self.screen_w, self.screen_h, self.font_md)
        self.code_panel = CodePanel()
        self._code_panel_font_ready = False

    # ----------------------------------------------------------
    def _on_count_change(self, new_count):
        """滑块拖动时实时回调：立即更新数据量并重新生成数组"""
        if new_count != self.count:
            self.count = new_count
            self._generate_distribution()

    def _on_distribution_change(self, idx):
        """数据分布下拉选择回调：立即用新分布重新生成数据"""
        self.data_dist = idx
        self._generate_distribution()

    def _generate_distribution(self):
        """根据当前 data_dist 生成对应分布的数组"""
        n = self.count
        dist = self.data_dist
        if dist == 1:   # 近乎有序
            arr = list(range(1, n + 1))
            swaps = max(1, int(n * 0.05))
            for _ in range(swaps):
                i, j = random.sample(range(n), 2)
                arr[i], arr[j] = arr[j], arr[i]
        elif dist == 2:  # 完全逆序
            arr = list(range(n, 0, -1))
        elif dist == 3:  # 少量唯一值
            unique = sorted(random.sample(range(1, 1001), min(8, max(5, n // 10))))
            arr = [random.choice(unique) for _ in range(n)]
        elif dist == 4:  # 正弦波形
            arr = [int(500 + 499 * math.sin(2 * math.pi * i / n)) for i in range(n)]
        else:            # 随机分布
            arr = generate_random_array(n)
        self.array       = arr
        self.highlight   = []
        self.sorted_done = False
        self.cmp_count   = 0
        self.swap_count  = 0
        self.generator   = None
        self.running     = False
        self.paused      = False
        self._sort_start_time = 0.0
        self._sort_elapsed    = 0.0
        self._sort_end_time   = 0.0

    def _generate_random(self):
        """生成随机数组（兼容入口，始终使用当前分布）"""
        self._generate_distribution()

    # ----------------------------------------------------------
    def _get_generator(self):
        """根据当前算法名返回对应生成器"""
        arr = self.array[:]
        self.array = arr
        fn = ALGO_DISPATCH.get(self.algo_name)
        if fn:
            return fn(self.array)
        return None

    # ----------------------------------------------------------
    def _estimated_comps(self):
        """估算算法总比较次数（用于进度百分比）"""
        n = len(self.array)
        if n <= 1:
            return max(1, n)
        meta = ALGO_META.get(self.algo_name)
        ctype = meta[3] if meta else "quadratic"
        if ctype == "quadratic":
            return max(1, n * n // 2)
        if ctype == "linearithmic":
            return max(1, int(n * math.log2(max(2, n)) * 1.5))
        if ctype == "sub_quadratic":
            return max(1, int(n ** 1.3))
        if ctype == "linear":
            return max(1, n * 3)
        return max(1, n * n // 2)

    def _start_sort(self):
        if self.running and not self.paused:
            return
        if self.paused:
            self.paused  = False
            self.running = True
            self._sort_start_time = time.time() - self._sort_elapsed
            return
        self.cmp_count   = 0
        self.swap_count  = 0
        self.sorted_done = False
        self.highlight   = []
        self.generator   = self._get_generator()
        self.running     = True
        self.paused      = False
        self._sort_start_time = time.time()
        self._sort_elapsed    = 0.0
        self._sort_end_time   = 0.0

    def _pause_sort(self):
        if self.running:
            self.paused = not self.paused

    def _reset(self):
        """重置排序状态，保留当前数据不变"""
        self.highlight   = []
        self.sorted_done = False
        self.cmp_count   = 0
        self.swap_count  = 0
        self.generator   = None
        self.running     = False
        self.paused      = False
        self._sort_start_time = 0.0
        self._sort_elapsed    = 0.0
        self._sort_end_time   = 0.0
        self.sound_mgr.stop_all()   # 停止正在播放的音效
        if hasattr(self, 'code_panel') and self.code_panel.visible:
            self.code_panel.show(self.algo_name, self.screen_w, self.screen_h)

    def _change_speed(self, delta):
        self.speed_idx = clamp(self.speed_idx + delta, 0, len(SPEED_LEVELS)-1)

    def _open_source_page(self):
        """在独立线程中启动源码页面，不阻塞主窗口"""
        if self.is_wasm:
            return
        def _run():
            src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_page.py")
            if os.path.isfile(src):
                subprocess.Popen([sys.executable, src])
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_fullscreen(self):
        if self.is_wasm:
            return
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.screen_w = info.current_w
            self.screen_h = info.current_h
        else:
            info = pygame.display.Info()
            self.screen_w = int(info.current_w * 0.75)
            self.screen_h = int(info.current_h * 0.75)
            self.screen = pygame.display.set_mode(
                (self.screen_w, self.screen_h), pygame.RESIZABLE
            )
        self._build_ui()

    def _handle_resize(self, w, h):
        self.screen_w = w
        self.screen_h = h
        self._build_ui()

    # ----------------------------------------------------------
    def _advance_generator(self):
        """推进排序生成器若干步（根据速度倍率），并触发音效"""
        if not self.running or self.paused or self.generator is None:
            return
        speed = SPEED_LEVELS[self.speed_idx]
        steps = max(1, int(speed))
        for _ in range(steps):
            try:
                result = next(self.generator)
                old_swaps = self.swap_count
                self.array      = list(result[0])
                self.highlight  = list(result[1])
                self.swap_count = result[2]
                self.cmp_count  = result[3]

                # 音效：比较音（音高与柱高成正比）
                if self.highlight and self.array:
                    idx = self.highlight[0]
                    if 0 <= idx < len(self.array):
                        self.sound_mgr.play_compare(self.array[idx])

                # 音效：交换咔嗒声（swap_count 增加时）
                if self.swap_count > old_swaps:
                    self.sound_mgr.play_swap()

            except StopIteration:
                self.running     = False
                self.sorted_done = True
                self.highlight   = []
                self._sort_end_time = time.time()
                self._sort_elapsed  = self._sort_end_time - self._sort_start_time
                self.sound_mgr.play_complete()   # 完成扫弦音效
                break

    # ----------------------------------------------------------
    def _draw_bars(self):
        """绘制可视化区域的竖条"""
        w = self.screen_w
        h = self.screen_h
        vis_top    = CTRL_H
        vis_height = h - vis_top
        n          = len(self.array)
        if n == 0:
            return
        bar_w    = max(1, (w - 10) / n)
        max_val  = max(self.array) if self.array else 1
        for i, val in enumerate(self.array):
            bar_h = int(val / max_val * (vis_height - 5))
            x     = int(10 + i * bar_w)
            y     = h - bar_h
            if self.sorted_done:
                color = self.settings_panel.get_sorted_color()
            elif i in self.highlight:
                color = self.settings_panel.get_highlight_color()
            else:
                color = self.settings_panel.get_normal_color()
            bar_rect = pygame.Rect(x, y, max(1, int(bar_w)-1), bar_h)
            pygame.draw.rect(self.screen, color, bar_rect)

    def _draw_ctrl(self):
        """绘制控制栏"""
        w = self.screen_w
        dark = self.settings_panel.get_dark_mode()
        # 根据深色/浅色模式选择控制栏背景
        ctrl_bg = (10, 15, 35) if dark else (220, 225, 235)
        pygame.draw.rect(self.screen, ctrl_bg, pygame.Rect(0, 0, w, CTRL_H))
        pygame.draw.line(self.screen, CYAN if dark else (0, 120, 180), (0, CTRL_H), (w, CTRL_H), 2)

        # 标题向右偏移，为设置按钮腾出空间
        title_color = WHITE if dark else (20, 30, 60)
        draw_text(self.screen, "排序算法可视化", self.font_lg, title_color,
                  w//2 + 60, 10, anchor="midtop")

        speed = SPEED_LEVELS[self.speed_idx]
        speed_str = f"{speed:g}x"
        status_parts = [
            f"当前算法：{self.algo_name}",
            f"比较次数：{self.cmp_count}",
            f"交换次数：{self.swap_count}",
            f"速度：{speed_str}",
            f"数据量：{self.count}",
        ]
        STATUS_COLOR = (0, 255, 127) if dark else (0, 120, 60)
        GAP = 28
        state_y = 15
        sx = 10
        for part in status_parts:
            draw_text(self.screen, part, self.font_sm, STATUS_COLOR, sx, state_y)
            text_w, _ = self.font_sm.size(part)
            sx += text_w + GAP

        if self.algo_type == "basic":
            pygame.draw.rect(self.screen, CYAN, self.btn_basic_tab.rect, 2, border_radius=6)
        else:
            pygame.draw.rect(self.screen, CYAN, self.btn_fun_tab.rect,   2, border_radius=6)

        for btn in self.all_buttons:
            btn.draw(self.screen)

        if self.algo_type == "basic":
            self.dd_basic.draw(self.screen)
        else:
            self.dd_fun.draw(self.screen)

        # 数据分布下拉框（悬停展开）
        self.dd_data.draw(self.screen)

        # 状态提示（位置/字体与排序完成一致）
        if self.sorted_done:
            st_color = GREEN if dark else (0, 140, 60)
            draw_text(self.screen, "✓ 排序完成!", self.font_md, st_color,
                      w//2, CTRL_H-4, anchor="midbottom")
        elif self.running:
            st_color = YELLOW if dark else (180, 130, 0)
            draw_text(self.screen, "▶ 排序中...", self.font_md, st_color,
                      w//2, CTRL_H-4, anchor="midbottom")
        else:
            st_color = LGRAY if dark else (100, 100, 110)
            draw_text(self.screen, "● 就绪中", self.font_md, st_color,
                      w//2, CTRL_H-4, anchor="midbottom")

    # ----------------------------------------------------------
    def _draw_info(self):
        """在控制栏下方左侧绘制算法信息面板（4行）"""
        meta = ALGO_META.get(self.algo_name)
        if not meta:
            return
        en_name, time_c, space_c, _ = meta
        LH   = 22
        x    = 12
        y    = CTRL_H + 8
        font = self.font_sm
        dark = self.settings_panel.get_dark_mode()

        # 浅色模式文字颜色
        c_accent  = CYAN if dark else (0, 100, 180)
        c_normal  = LGRAY if dark else (80, 80, 90)
        c_text    = WHITE if dark else (30, 30, 40)

        # 更新排序耗时
        if self.running and not self.paused:
            self._sort_elapsed = time.time() - self._sort_start_time

        # 第1行：英文名称 + 时间复杂度 + 空间复杂度
        draw_text(self.screen, en_name, font, c_accent, x, y)
        en_w, _ = font.size(en_name)
        draw_text(self.screen, f"  Time: {time_c}  |  Space: {space_c}",
                  font, c_normal, x + en_w, y)

        # 第2行：排序耗时
        if self.sorted_done:
            t_str = f"{self._sort_elapsed:.3f}s"
        elif self.running:
            t_str = f"{self._sort_elapsed:.3f}s"
        else:
            t_str = "0.000s"
        draw_text(self.screen, f"Sort Time: {t_str}", font, c_text, x, y + LH)

        # 第3行：数据规模
        draw_text(self.screen, f"Data Size: {self.count}", font, c_text, x, y + LH*2)

        # 第4行：排序完成度
        if self.sorted_done:
            pct = 100.0
        elif self.running:
            est = self._estimated_comps()
            pct = min(99.9, self.cmp_count / est * 100)
        else:
            pct = 0.0
        if pct >= 100:
            pct_color = GREEN if dark else (0, 140, 60)
        elif pct > 0:
            pct_color = YELLOW if dark else (180, 130, 0)
        else:
            pct_color = LGRAY if dark else (130, 130, 140)
        draw_text(self.screen, f"Progress: {pct:.1f}%", font, pct_color, x, y + LH*3)

    # ----------------------------------------------------------
    def _draw(self):
        # 根据深色/浅色模式选择背景色
        bg_color = BLACK if self.settings_panel.get_dark_mode() else (240, 240, 245)
        self.screen.fill(bg_color)
        self._draw_bars()
        self._draw_ctrl()
        self._draw_info()
        self.count_dialog.draw(self.screen)

        # 亮度覆盖层（设置面板之前绘制，确保面板始终清晰）
        bri = self.settings_panel.get_brightness()
        if bri < 100:
            alpha = int((100 - bri) * 2.0)  # 20%亮度 -> alpha≈160
            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            self.screen.blit(overlay, (0, 0))

        self.settings_panel.draw(self.screen)
        if not self._code_panel_font_ready:
            _this_dir = os.path.dirname(os.path.abspath(__file__))
            _code_font = None
            for _name in [
                os.path.join(_this_dir, "msyh.ttc"),
                os.path.join(_this_dir, "simhei.ttf"),
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/msyhbd.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "C:/Windows/Fonts/simhei.ttf",
            ]:
                try:
                    _code_font = pygame.font.Font(_name, 15)
                    break
                except Exception:
                    pass
            if _code_font is None:
                _code_font = self.font_sm
            self.code_panel.setup_fonts(_code_font, self.font_md, self.font_sm)
            self._code_panel_font_ready = True
        self.code_panel.draw(self.screen)
        pygame.display.flip()

    # ----------------------------------------------------------
    def _process_events(self):
        """处理一轮事件并渲染，供 run() 和 run_async() 共用"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if not self.is_wasm and event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self._handle_resize(event.w, event.h)
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE
                    )

            # 设置面板事件（优先处理，防止穿透）
            if self.settings_panel.handle_event(event):
                # 同步音效开关状态到 SoundManager
                self.sound_mgr.set_process(self.settings_panel.sound_process)
                self.sound_mgr.set_complete(self.settings_panel.sound_complete)
                if self.settings_panel.visible:
                    continue  # 面板展开时拦截下方事件

            if self.code_panel.handle_event(event, self.screen_w, self.screen_h):
                continue

            val = self.count_dialog.handle_event(event)
            if val is not None:
                if val >= 0:
                    # 确认按钮 / 回车：确定最终数量并重新生成数据
                    if val != self.count:
                        self.count = val
                        self._generate_distribution()  # 重新生成数组
                    else:
                        self._reset()  # 数量未变，只重置排序状态
                # val == -1: 取消或点击外部关闭，数量已通过滑块实时生效
                continue
            if self.count_dialog.visible:
                continue  # 弹窗打开时拦截下方控件事件

            changed = False
            if self.algo_type == "basic":
                changed = self.dd_basic.handle_event(event)
                if changed:
                    self.algo_name = BASIC_ALGOS[self.dd_basic.selected]
                    self._reset()
            else:
                changed = self.dd_fun.handle_event(event)
                if changed:
                    self.algo_name = FUN_ALGOS[self.dd_fun.selected]
                    self._reset()

            if self.btn_basic_tab.handle_event(event):
                self.algo_type = "basic"
                self.algo_name = BASIC_ALGOS[self.dd_basic.selected]
                self._reset()

            if self.btn_fun_tab.handle_event(event):
                self.algo_type = "fun"
                self.algo_name = FUN_ALGOS[self.dd_fun.selected]
                self._reset()

            if self.btn_start.handle_event(event):
                self._start_sort()
            if self.btn_pause.handle_event(event):
                self._pause_sort()
            if self.btn_reset.handle_event(event):
                self._reset()
            if self.btn_faster.handle_event(event):
                self._change_speed(+1)
            if self.btn_slower.handle_event(event):
                self._change_speed(-1)
            self.dd_data.handle_event(event)
            if self.btn_setcnt.handle_event(event):
                self.count_dialog.show(self.count)

            if self.btn_srccode.handle_event(event):
                if self.code_panel.visible and self.code_panel.algo_name == self.algo_name:
                    self.code_panel.hide()
                else:
                    self.code_panel.show(self.algo_name, self.screen_w, self.screen_h)

            if self.btn_full.handle_event(event):
                self._toggle_fullscreen()

            # 设置按钮
            if self.btn_settings.handle_event(event):
                self.settings_panel.toggle()

            # 多算法对比按钮（daemon线程启动，不弹黑窗）
            if self.btn_compare.handle_event(event):
                if not hasattr(self, '_compare_running') or not self._compare_running:
                    self._compare_running = True
                    def _run_compare():
                        try:
                            import compare_mode
                            compare_mode.launch_compare()
                        except Exception as e:
                            print(f"[Compare] 错误: {e}")
                        finally:
                            self._compare_running = False
                    threading.Thread(target=_run_compare, daemon=True).start()

        self._advance_generator()
        self._draw()
        return True

    # ----------------------------------------------------------
    def run(self):
        """桌面模式主循环（同步）"""
        while True:
            self.clock.tick(FPS)
            if not self._process_events():
                pygame.quit()
                raise SystemExit

    async def run_async(self):
        """浏览器 WASM 模式主循环（异步）"""
        while True:
            self.clock.tick(FPS)
            if not self._process_events():
                break
            await asyncio.sleep(0)


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    app = SortingVisualizer()
    if _IS_WASM:
        asyncio.run(app.run_async())
    else:
        app.run()
