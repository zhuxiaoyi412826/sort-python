# -*- coding: utf-8 -*-
"""
算法详解页面模块
================
步进调试模式：左侧可视化 + 右侧代码展示 + 顶部控制栏
支持单步执行、快进、代码高亮同步跟随
"""

import pygame
import random
import os
import sys

# 颜色常量
BLACK = (12, 14, 20)
WHITE = (240, 240, 245)
CYAN = (0, 210, 220)
YELLOW = (255, 220, 60)
GREEN = (60, 220, 120)
RED = (220, 70, 70)
ORANGE = (230, 140, 40)
LGRAY = (160, 165, 180)
DGRAY = (30, 34, 48)
CTRL_BG = (22, 28, 42)
VIZ_BG = (8, 10, 18)
CODE_BG = (14, 18, 28)
BAR_NORMAL = (55, 100, 220)
BAR_HIGHLIGHT = (255, 220, 60)
BAR_SORTED = (60, 220, 120)

CTRL_H = 55  # 控制栏高度（单行）
STATUS_H = 36


class AlgoDetailPage:
    """算法详解页面 - 步进调试模式"""

    def __init__(self, screen, font_lg, font_md, font_sm, font_code=None):
        self.screen = screen
        self.font_lg = font_lg
        self.font_md = font_md
        self.font_sm = font_sm
        self.font_code = font_code or font_sm

        self.screen_w, self.screen_h = screen.get_size()

        # 导入算法模块
        from sorting_algos import (ALGO_DISPATCH, BASIC_ALGOS, FUN_ALGOS,
                                   get_algo_code_lines)
        self.ALGO_DISPATCH = ALGO_DISPATCH
        self.ALL_ALGOS = BASIC_ALGOS + FUN_ALGOS
        self.get_algo_code_lines = get_algo_code_lines

        # 当前状态
        self.algo_name = "冒泡排序"
        self.array = []
        self.generator = None
        self.highlight = []
        self.cmp_count = 0
        self.swap_count = 0
        self.sorted_done = False
        self.running = False
        self.step_count = 0

        # 上一步的计数（用于判断变化）
        self._prev_cmp = 0
        self._prev_swap = 0

        # 代码
        self.code_scroll = 0
        self.code_lines = []
        self.code_categories = {}  # 行号 -> 类别
        self.highlight_line = -1

        # 分割线
        self.split_ratio = 0.50
        self.dragging_split = False

        # 构建按钮
        self._build_buttons()

        # 初始化数据
        self._init_data()

    def _build_buttons(self):
        """构建控制按钮 - 单行居中布局"""
        btn_h = 30
        gap = 6

        self.buttons = []
        self.size_buttons = []

        # ---- 先计算总宽度用于居中 ----
        # 数据量标签
        size_label = "数据量:"
        size_label_w = self.font_sm.size(size_label)[0] + 6

        # 数据量按钮
        self._size_label_text = size_label
        size_defs = [("10", 10), ("20", 20), ("50", 50), ("100", 100)]
        size_btn_widths = []
        for text, _ in size_defs:
            w = max(36, self.font_sm.size(text)[0] + 16)
            size_btn_widths.append(w)

        # 下拉框
        dd_w = 120

        # 主按钮
        btn_defs = [
            ("◀ 单步", self._step_once, (50, 110, 180)),
            ("⏩ 快进10", self._fast_forward_10, (120, 70, 170)),
            ("⏩⏩ 快进100", self._fast_forward_100, (160, 50, 150)),
            ("▶ 自动", self._toggle_auto, (40, 150, 80)),
            ("🔀 重置", self._reset, (180, 110, 40)),
            ("← 返回", self._go_back, (170, 55, 55)),
        ]
        main_btn_widths = []
        for text, _, _ in btn_defs:
            w = self.font_md.size(text)[0] + 24
            main_btn_widths.append(w)

        # 总宽度
        total_w = (size_label_w + sum(size_btn_widths) + len(size_defs) * 4
                   + gap * 2 + dd_w + gap
                   + sum(main_btn_widths) + (len(btn_defs) - 1) * gap)
        start_x = max(10, (self.screen_w - total_w) // 2)

        btn_y = (CTRL_H - btn_h) // 2
        x = start_x

        # 数据量标签
        self._size_label_rect = pygame.Rect(x, btn_y + 2, size_label_w, btn_h - 4)
        x += size_label_w

        # 数据量按钮
        for i, (text, val) in enumerate(size_defs):
            w = size_btn_widths[i]
            rect = pygame.Rect(x, btn_y + 2, w, btn_h - 4)
            self.size_buttons.append({"rect": rect, "text": text, "value": val})
            x += w + 4
        x += gap * 2

        # 下拉框
        self.algo_dd_rect = pygame.Rect(x, btn_y, dd_w, btn_h)
        self.dd_expanded = False
        self.dd_hover_idx = -1
        x += dd_w + gap

        # 主控制按钮
        for i, (text, callback, color) in enumerate(btn_defs):
            w = main_btn_widths[i]
            rect = pygame.Rect(x, btn_y, w, btn_h)
            self.buttons.append({"rect": rect, "text": text, "callback": callback, "color": color})
            x += w + gap

        self.data_size = 20

    def _init_data(self):
        self.array = [random.randint(10, 500) for _ in range(self.data_size)]
        self._start_algo()

    def _start_algo(self):
        """启动当前算法"""
        self.generator = self.ALGO_DISPATCH[self.algo_name](self.array.copy())
        self.highlight = []
        self.cmp_count = 0
        self.swap_count = 0
        self._prev_cmp = 0
        self._prev_swap = 0
        self.sorted_done = False
        self.running = False
        self.step_count = 0
        self.code_scroll = 0
        self.highlight_line = 0

        # 获取源码并分类
        self.code_lines = self.get_algo_code_lines(self.algo_name)
        self._categorize_code_lines()

    def _categorize_code_lines(self):
        """对源码行进行分类标注"""
        self.code_categories = {}
        for i, line in enumerate(self.code_lines):
            stripped = line.lstrip()
            if stripped.startswith("yield"):
                self.code_categories[i] = "yield"
            elif any(kw in stripped for kw in [">", "<", ">=", "<=", "=="]):
                if "if " in stripped or "cmp_count" in stripped or stripped.startswith("if"):
                    self.code_categories[i] = "compare"
            elif "swap_count" in stripped and "+=" in stripped:
                self.code_categories[i] = "swap"
            elif stripped.startswith("def "):
                self.code_categories[i] = "def"
            elif stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                self.code_categories[i] = "comment"
            elif stripped.startswith("for ") or stripped.startswith("while "):
                self.code_categories[i] = "loop"
            elif stripped.startswith("if ") or stripped.startswith("elif "):
                self.code_categories[i] = "if"
            elif stripped.startswith("else"):
                self.code_categories[i] = "else"
            elif stripped.startswith("return"):
                self.code_categories[i] = "return"
            else:
                self.code_categories[i] = "other"

    def _find_highlight_line(self):
        """根据排序步骤状态，智能匹配当前应高亮的代码行"""
        if not self.code_lines:
            return 0

        # 判断本步发生了什么变化
        cmp_changed = self.cmp_count > self._prev_cmp
        swap_changed = self.swap_count > self._prev_swap

        # 查找对应类别的行
        compare_lines = [i for i, c in self.code_categories.items() if c == "compare"]
        swap_lines = [i for i, c in self.code_categories.items() if c == "swap"]
        yield_lines = [i for i, c in self.code_categories.items() if c == "yield"]

        if self.sorted_done:
            # 排序完成 -> 最后一个 yield 或 return
            ret = [i for i, c in self.code_categories.items() if c == "return"]
            return ret[-1] if ret else (yield_lines[-1] if yield_lines else len(self.code_lines) - 1)

        if swap_changed and cmp_changed:
            # 既有比较又有交换 -> 交换 yield 行（通常在后面）
            if len(yield_lines) >= 2:
                return yield_lines[-1]
            if swap_lines:
                return swap_lines[-1]
        elif cmp_changed and not swap_changed:
            # 仅比较 -> 比较 yield 行
            if yield_lines:
                return yield_lines[0]
            if compare_lines:
                return compare_lines[-1]
        elif swap_changed and not cmp_changed:
            # 仅交换 -> 交换 yield 行
            if len(yield_lines) >= 2:
                return yield_lines[-1]
            if swap_lines:
                return swap_lines[-1]

        # 无变化（可能是初始化等）
        return self.highlight_line if self.highlight_line >= 0 else 0

    def _auto_scroll_to_line(self, line_idx):
        """自动滚动使高亮行居中显示"""
        line_h = 17
        visible_area_h = self.screen_h - CTRL_H - STATUS_H - 80
        visible_lines = max(1, visible_area_h // line_h)
        half = visible_lines // 2

        # 如果高亮行在当前可视范围内，不滚动
        if self.code_scroll <= line_idx < self.code_scroll + visible_lines:
            return

        # 让高亮行居中
        self.code_scroll = max(0, min(len(self.code_lines) - visible_lines, line_idx - half))

    def _step_once(self):
        """执行单步"""
        if self.sorted_done:
            return
        try:
            self._prev_cmp = self.cmp_count
            self._prev_swap = self.swap_count
            result = next(self.generator)
            if len(result) >= 4:
                self.array, self.highlight, self.swap_count, self.cmp_count = result[:4]
            elif len(result) >= 2:
                self.array, self.highlight = result[:2]
            self.step_count += 1

            # 智能代码高亮 + 自动滚动
            self.highlight_line = self._find_highlight_line()
            self._auto_scroll_to_line(self.highlight_line)
        except StopIteration:
            self.sorted_done = True
            self.highlight = []
            self.highlight_line = self._find_highlight_line()

    def _fast_forward_10(self):
        for _ in range(10):
            if not self.sorted_done:
                self._step_once()

    def _fast_forward_100(self):
        for _ in range(100):
            if not self.sorted_done:
                self._step_once()

    def _toggle_auto(self):
        self.running = not self.running

    def _reset(self):
        self._init_data()

    def _go_back(self):
        return "BACK"

    def _set_size(self, size):
        self.data_size = size
        self._init_data()

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.QUIT:
            return "QUIT"

        if event.type == pygame.VIDEORESIZE:
            self.screen_w, self.screen_h = event.w, event.h
            self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.RESIZABLE)
            self._build_buttons()
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            for btn in self.buttons:
                if btn["rect"].collidepoint(mx, my):
                    result = btn["callback"]()
                    if result == "BACK":
                        return "BACK"
                    return None

            for btn in self.size_buttons:
                if btn["rect"].collidepoint(mx, my):
                    self._set_size(btn["value"])
                    return None

            if self.algo_dd_rect.collidepoint(mx, my):
                self.dd_expanded = not self.dd_expanded
                return None

            if self.dd_expanded:
                dd_bottom = self.algo_dd_rect.bottom
                dd_items_h = len(self.ALL_ALGOS) * 26
                if (self.algo_dd_rect.x <= mx <= self.algo_dd_rect.right and
                        dd_bottom <= my <= dd_bottom + dd_items_h):
                    idx = (my - dd_bottom) // 26
                    if 0 <= idx < len(self.ALL_ALGOS):
                        self.algo_name = self.ALL_ALGOS[idx]
                        self.dd_expanded = False
                        self._start_algo()
                    return None
                else:
                    self.dd_expanded = False

            # 分割线拖动
            split_x = int(self.screen_w * self.split_ratio)
            if abs(mx - split_x) < 12 and CTRL_H < my < self.screen_h - STATUS_H:
                self.dragging_split = True
                return None

            # 代码区域滚轮
            code_x = int(self.screen_w * self.split_ratio) + 10
            if mx > code_x:
                if event.button == 4:
                    self.code_scroll = max(0, self.code_scroll - 3)
                elif event.button == 5:
                    self.code_scroll = min(max(0, len(self.code_lines) - 10), self.code_scroll + 3)

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_split = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_split:
                self.split_ratio = max(0.3, min(0.8, event.pos[0] / self.screen_w))
            if self.dd_expanded:
                mx, my = event.pos
                dd_bottom = self.algo_dd_rect.bottom
                if my > dd_bottom:
                    idx = (my - dd_bottom) // 26
                    self.dd_hover_idx = idx if 0 <= idx < len(self.ALL_ALGOS) else -1
                else:
                    self.dd_hover_idx = -1

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "BACK"
            elif event.key == pygame.K_SPACE:
                self._step_once()
            elif event.key == pygame.K_RIGHT:
                self._fast_forward_10()
            elif event.key == pygame.K_r:
                self._reset()

        return None

    def update(self):
        if self.running and not self.sorted_done:
            self._step_once()

    def draw(self):
        """绘制页面"""
        self.screen_w, self.screen_h = self.screen.get_size()
        self.screen.fill(BLACK)

        # 控制栏
        self._draw_ctrl()

        # 分割位置
        split_x = int(self.screen_w * self.split_ratio)
        content_top = CTRL_H + 4
        content_h = self.screen_h - CTRL_H - STATUS_H - 8

        # 左侧可视化
        viz_rect = pygame.Rect(6, content_top, split_x - 10, content_h)
        pygame.draw.rect(self.screen, VIZ_BG, viz_rect, border_radius=4)
        pygame.draw.rect(self.screen, (30, 40, 60), viz_rect, 1, border_radius=4)

        # 右侧代码
        code_rect = pygame.Rect(split_x + 4, content_top,
                                self.screen_w - split_x - 10, content_h)
        pygame.draw.rect(self.screen, CODE_BG, code_rect, border_radius=4)
        pygame.draw.rect(self.screen, (30, 40, 60), code_rect, 1, border_radius=4)

        # 分割线
        pygame.draw.line(self.screen, (40, 50, 70),
                         (split_x, content_top), (split_x, content_top + content_h), 2)
        mid_y = (content_top + content_top + content_h) // 2
        pygame.draw.rect(self.screen, CYAN,
                         pygame.Rect(split_x - 3, mid_y - 15, 6, 30), border_radius=3)

        # 绘制内容
        self._draw_viz(viz_rect.x + 10, viz_rect.y + 8,
                       viz_rect.width - 20, viz_rect.height - 16)
        self._draw_code(code_rect.x + 8, code_rect.y + 6,
                        code_rect.width - 16, code_rect.height - 12)
        self._draw_status()

        # 下拉列表最后绘制
        if self.dd_expanded:
            self._draw_dropdown()

        pygame.display.flip()

    def _draw_ctrl(self):
        """绘制控制栏"""
        pygame.draw.rect(self.screen, CTRL_BG, pygame.Rect(0, 0, self.screen_w, CTRL_H))
        pygame.draw.line(self.screen, (40, 55, 80), (0, CTRL_H), (self.screen_w, CTRL_H), 2)

        mx, my = pygame.mouse.get_pos()

        # 数据量标签
        self._draw_text(self._size_label_text, self.font_sm, LGRAY,
                        self._size_label_rect.centerx, self._size_label_rect.centery, "center")

        # 数据量按钮
        for btn in self.size_buttons:
            is_current = btn["value"] == self.data_size
            if is_current:
                bg, border, bw = (40, 120, 180), CYAN, 2
            else:
                bg, border, bw = (35, 42, 58), (70, 80, 100), 1
            hover = btn["rect"].collidepoint(mx, my)
            if hover:
                bg = tuple(min(255, c + 20) for c in bg)
            pygame.draw.rect(self.screen, bg, btn["rect"], border_radius=5)
            pygame.draw.rect(self.screen, border, btn["rect"], bw, border_radius=5)
            self._draw_text(btn["text"], self.font_sm, WHITE,
                            btn["rect"].centerx, btn["rect"].centery, "center")

        # 下拉框
        pygame.draw.rect(self.screen, (35, 45, 65), self.algo_dd_rect, border_radius=6)
        pygame.draw.rect(self.screen, CYAN, self.algo_dd_rect, 2, border_radius=6)
        self._draw_text(self.algo_name + " ▼", self.font_md, WHITE,
                        self.algo_dd_rect.centerx, self.algo_dd_rect.centery, "center")

        # 主按钮
        for btn in self.buttons:
            color = btn["color"]
            hover = btn["rect"].collidepoint(mx, my)
            if hover:
                color = tuple(min(255, c + 35) for c in color)
            shadow = btn["rect"].move(2, 2)
            pygame.draw.rect(self.screen, (10, 12, 18), shadow, border_radius=6)
            pygame.draw.rect(self.screen, color, btn["rect"], border_radius=6)
            pygame.draw.rect(self.screen,
                             WHITE if hover else (80, 90, 110),
                             btn["rect"], 2 if hover else 1, border_radius=6)
            self._draw_text(btn["text"], self.font_md, WHITE,
                            btn["rect"].centerx, btn["rect"].centery, "center")

    def _draw_dropdown(self):
        """绘制下拉列表"""
        dd_bottom = self.algo_dd_rect.bottom
        item_h = 26
        total_h = len(self.ALL_ALGOS) * item_h

        overlay = pygame.Surface((self.algo_dd_rect.width + 4, total_h + 4), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (self.algo_dd_rect.x - 2, dd_bottom - 2))

        for i, name in enumerate(self.ALL_ALGOS):
            rect = pygame.Rect(self.algo_dd_rect.x, dd_bottom + i * item_h,
                               self.algo_dd_rect.width, item_h)
            if i == self.dd_hover_idx:
                bg = (50, 70, 110)
            elif name == self.algo_name:
                bg = (35, 55, 85)
            else:
                bg = (22, 30, 48)
            pygame.draw.rect(self.screen, bg, rect)
            pygame.draw.line(self.screen, (40, 50, 70),
                             (rect.x, rect.bottom), (rect.right, rect.bottom))
            color = CYAN if name == self.algo_name else WHITE
            self._draw_text(name, self.font_sm, color, rect.x + 12, rect.centery, "midleft")

    def _draw_viz(self, x, y, w, h):
        """绘制可视化区域"""
        if not self.array:
            return

        n = len(self.array)
        max_val = max(self.array) if self.array else 1

        padding = 10
        avail_w = w - padding * 2
        avail_h = h - 40
        bar_w = max(2, avail_w // n - 2)
        gap = max(1, (avail_w - bar_w * n) // max(1, n - 1)) if n > 1 else 0

        # 标题
        self._draw_text(f"可视化: {self.algo_name}", self.font_sm, CYAN,
                        x + padding, y + 2, "topleft")

        for i, val in enumerate(self.array):
            bar_h = max(2, int((val / max_val) * avail_h))
            bx = x + padding + i * (bar_w + gap)
            by = y + h - 5 - bar_h

            if self.sorted_done:
                color = BAR_SORTED
            elif i in self.highlight:
                color = BAR_HIGHLIGHT
            else:
                color = BAR_NORMAL

            bar_rect = pygame.Rect(bx, by, bar_w, bar_h)
            pygame.draw.rect(self.screen, color, bar_rect)
            if bar_w > 4:
                light = tuple(min(255, c + 40) for c in color)
                pygame.draw.line(self.screen, light, (bx + 1, by), (bx + 1, by + bar_h - 1))

            if i in self.highlight and len(self.highlight) >= 2:
                arrow_y = by - 20
                if arrow_y > y + 15:
                    c = YELLOW if i == self.highlight[0] else RED
                    self._draw_text("▲", self.font_md, c, bx + bar_w // 2, arrow_y, "center")

        if self.sorted_done:
            self._draw_text("✓ 排序完成!", self.font_lg, GREEN,
                            x + w // 2, y + 25, "center")

    def _draw_code(self, x, y, w, h):
        """绘制代码区域"""
        title_h = 26
        pygame.draw.rect(self.screen, (25, 32, 50), pygame.Rect(x, y, w, title_h), border_radius=4)
        self._draw_text(f"源码: {self.algo_name}  ({len(self.code_lines)}行)",
                        self.font_md, CYAN, x + 10, y + title_h // 2, "midleft")

        code_y = y + title_h + 4
        line_h = 17
        visible_lines = max(1, (h - title_h - 8) // line_h)
        num_w = 36

        # 行号背景
        pygame.draw.rect(self.screen, (16, 20, 30),
                         pygame.Rect(x, code_y, num_w, h - title_h - 4))

        for i in range(visible_lines):
            line_idx = self.code_scroll + i
            if line_idx >= len(self.code_lines):
                break

            line = self.code_lines[line_idx]
            ly = code_y + i * line_h
            highlighted = line_idx == self.highlight_line

            # 行号
            self._draw_text(f"{line_idx + 1:>3}", self.font_code,
                            (60, 65, 85) if not highlighted else YELLOW,
                            x + 5, ly, "topleft")

            # 高亮背景
            if highlighted:
                hl_rect = pygame.Rect(x + num_w, ly - 1, w - num_w - 2, line_h)
                pygame.draw.rect(self.screen, (55, 55, 15), hl_rect)
                # 左侧指示条
                pygame.draw.line(self.screen, YELLOW,
                                 (x + num_w, ly - 1), (x + num_w, ly + line_h - 1), 2)

            # 语法高亮
            color = (195, 200, 210)
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                color = (90, 145, 90)
            elif stripped.startswith("def "):
                color = (100, 170, 255)
            elif any(stripped.startswith(kw) for kw in ["for ", "while "]):
                color = (255, 170, 90)
            elif any(stripped.startswith(kw) for kw in ["if ", "elif ", "else:"]):
                color = (255, 140, 100)
            elif stripped.startswith("yield") or stripped.startswith("return"):
                color = (255, 110, 160)
            elif "yield" in line or "return" in line:
                color = (190, 170, 240)

            if highlighted:
                color = YELLOW

            self._draw_text(line, self.font_code, color, x + num_w + 5, ly, "topleft")

        # 滚动条
        if len(self.code_lines) > visible_lines:
            sb_x = x + w - 8
            sb_track_h = h - title_h - 4
            sb_h = max(20, int(sb_track_h * visible_lines / len(self.code_lines)))
            max_scroll = len(self.code_lines) - visible_lines
            sb_y = code_y + int((sb_track_h - sb_h) * self.code_scroll / max(1, max_scroll))
            pygame.draw.rect(self.screen, (22, 28, 40),
                             pygame.Rect(sb_x, code_y, 5, sb_track_h), border_radius=2)
            pygame.draw.rect(self.screen, (65, 80, 115),
                             pygame.Rect(sb_x, sb_y, 5, sb_h), border_radius=2)

    def _draw_status(self):
        """绘制底部状态栏"""
        y = self.screen_h - STATUS_H
        pygame.draw.rect(self.screen, CTRL_BG, pygame.Rect(0, y, self.screen_w, STATUS_H))
        pygame.draw.line(self.screen, (40, 55, 80), (0, y), (self.screen_w, y), 1)

        parts = [f"比较: {self.cmp_count}", f"交换: {self.swap_count}", f"步数: {self.step_count}"]
        info = "  |  ".join(parts)

        if self.sorted_done:
            info += "  |  ✓ 排序完成!"
            color = GREEN
        elif self.running:
            info += "  |  ▶ 自动运行中..."
            color = CYAN
        else:
            info += "  |  ⏸ 步进模式"
            color = YELLOW

        self._draw_text(info, self.font_md, color, 15, y + STATUS_H // 2, "midleft")

        if self.highlight and len(self.highlight) >= 2:
            i, j = self.highlight[0], self.highlight[1]
            if 0 <= i < len(self.array) and 0 <= j < len(self.array):
                info2 = f"arr[{i}]={self.array[i]}  arr[{j}]={self.array[j]}"
                self._draw_text(info2, self.font_sm, LGRAY,
                                self.screen_w - 15, y + STATUS_H // 2, "midright")

        self._draw_text("空格=单步  →=快进10  R=重置  ESC=返回",
                        self.font_sm, (80, 85, 100),
                        self.screen_w // 2, y + STATUS_H // 2, "center")

    def _draw_text(self, text, font, color, x, y, anchor="topleft"):
        try:
            surface = font.render(str(text), True, color)
        except Exception:
            return
        rect = surface.get_rect()
        setattr(rect, anchor, (x, y))
        self.screen.blit(surface, rect)


def run_algo_detail():
    """独立运行算法详解页面"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 700), pygame.RESIZABLE)
    pygame.display.set_caption("算法详解 - 步进调试模式")

    font_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = None
    for name in ["msyh.ttc", "simhei.ttf",
                 "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        path = os.path.join(font_dir, name) if not os.path.isabs(name) else name
        if os.path.isfile(path):
            font_path = path
            break

    code_font_path = None
    for name in ["consola.ttf", "C:/Windows/Fonts/consola.ttf",
                 "C:/Windows/Fonts/cour.ttf"]:
        path = os.path.join(font_dir, name) if not os.path.isabs(name) else name
        if os.path.isfile(path):
            code_font_path = path
            break

    if font_path:
        font_lg = pygame.font.Font(font_path, 20)
        font_md = pygame.font.Font(font_path, 14)
        font_sm = pygame.font.Font(font_path, 12)
    else:
        font_lg = pygame.font.SysFont("Microsoft YaHei", 20)
        font_md = pygame.font.SysFont("Microsoft YaHei", 14)
        font_sm = pygame.font.SysFont("Microsoft YaHei", 12)

    font_code = pygame.font.Font(code_font_path, 13) if code_font_path else pygame.font.SysFont("Consolas", 13)

    page = AlgoDetailPage(screen, font_lg, font_md, font_sm, font_code)
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            result = page.handle_event(event)
            if result == "BACK" or result == "QUIT":
                running = False
        page.update()
        page.draw()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    run_algo_detail()
