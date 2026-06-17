# -*- coding: utf-8 -*-
"""
绘制与UI模块
============
包含颜色常量、绘制工具函数、UI组件（下拉菜单、按钮、对话框、代码面板）。
"""

import pygame
import math
import os
from sorting_algos import get_algo_code_lines


# ============================================================
#  颜色常量
# ============================================================
BLACK   = (0,   0,   0  )
WHITE   = (255, 255, 255)
BLUE    = (30,  100, 255)
YELLOW  = (255, 220, 0  )
GREEN   = (0,   220, 80 )
RED     = (220, 50,  50 )
CYAN    = (0,   220, 220)
ORANGE  = (255, 140, 0  )
PURPLE  = (160, 60,  200)
GRAY    = (80,  80,  80 )
LGRAY   = (140, 140, 140)
DKBLUE  = (10,  30,  80 )
TEAL    = (0,   180, 160)
PINK    = (220, 60,  120)

# 控制栏高度
CTRL_H = 160


# ============================================================
#  工具函数
# ============================================================
def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def draw_text(surface, text, font, color, x, y, anchor="topleft"):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    setattr(rect, anchor, (x, y))
    surface.blit(surf, rect)


# ============================================================
#  代码面板 - 语法高亮
# ============================================================
CODE_KEYWORDS = {
    "def","return","yield","if","else","elif","for","while",
    "in","not","and","or","True","False","None","import",
    "from","class","pass","break","continue","try","except",
    "with","as","global","nonlocal","lambda","raise",
}

def _tokenize_code_line(line: str):
    """返回 [(text, color), ...]"""
    KW      = (86,  156, 214)   # 蓝色关键字
    STR_C   = (206, 145, 120)   # 橙色字符串
    CMT     = (106, 153,  85)   # 绿色注释
    FN      = (220, 220, 170)   # 黄白函数名
    NUM     = (181, 206, 168)   # 浅绿数字
    NRM     = (212, 212, 212)   # 普通文本
    tokens  = []
    s       = line.lstrip()
    if s.startswith("#"):
        indent = len(line) - len(s)
        tokens.append((line[:indent], NRM))
        tokens.append((line[indent:], CMT))
        return tokens
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in ('"', "'"):
            j = i + 1
            while j < n and line[j] != ch:
                j += 1
            tokens.append((line[i:j+1], STR_C))
            i = j + 1
        elif ch == '#':
            tokens.append((line[i:], CMT))
            break
        elif ch in (' ', '\t'):
            j = i
            while j < n and line[j] in (' ','\t'): j += 1
            tokens.append((line[i:j], NRM)); i = j
        elif ch.isalpha() or ch == '_':
            j = i
            while j < n and (line[j].isalnum() or line[j] == '_'): j += 1
            w = line[i:j]
            if w in CODE_KEYWORDS:   tokens.append((w, KW))
            elif j < n and line[j] == '(': tokens.append((w, FN))
            else:                    tokens.append((w, NRM))
            i = j
        elif ch.isdigit():
            j = i
            while j < n and (line[j].isdigit() or line[j] == '.'): j += 1
            tokens.append((line[i:j], NUM)); i = j
        else:
            tokens.append((ch, NRM)); i += 1
    return tokens


# ============================================================
#  代码面板组件（右侧浮层显示算法源码）
# ============================================================
class CodePanel:
    """右侧浮层代码面板——叠加在可视化区上，不影响控制栏"""
    PANEL_W  = 420   # 面板宽度
    LNUM_W   = 40    # 行号宽
    LINE_H   = 20    # 行高
    PAD      = 6     # 内边距

    def __init__(self):
        self.visible    = False
        self.algo_name  = ""
        self.lines      = []
        self.tokens     = []
        self.scroll     = 0
        self.font_code  = None
        self.font_title = None
        self.font_sm    = None
        self._drag_sb   = False

    def setup_fonts(self, font_code, font_title, font_sm):
        self.font_code  = font_code
        self.font_title = font_title
        self.font_sm    = font_sm

    def show(self, algo_name: str, screen_w: int, screen_h: int):
        self.algo_name = algo_name
        self.lines     = get_algo_code_lines(algo_name)
        self.tokens    = [_tokenize_code_line(ln) for ln in self.lines]
        self.scroll    = 0
        self.visible   = True
        self._update_rect(screen_w, screen_h)

    def hide(self):
        self.visible = False

    def _update_rect(self, screen_w: int, screen_h: int):
        """根据窗口大小计算面板矩形"""
        pw = self.PANEL_W
        self.rect = pygame.Rect(screen_w - pw, CTRL_H, pw, screen_h - CTRL_H)
        self.btn_close = pygame.Rect(self.rect.right - 30, self.rect.y + 6, 24, 22)
        self.sb_track  = pygame.Rect(self.rect.right - 10, self.rect.y + 38,
                                     8, self.rect.height - 44)

    def _max_scroll(self):
        vis_h   = self.rect.height - 38
        total_h = len(self.lines) * self.LINE_H
        return max(0, total_h - vis_h)

    def _sb_rect(self):
        vis_h   = self.sb_track.height
        total_h = max(1, len(self.lines) * self.LINE_H)
        if total_h <= vis_h:
            return None
        sb_h = max(24, int(vis_h ** 2 / total_h))
        sb_y = int(self.scroll / (total_h - vis_h) * (vis_h - sb_h))
        return pygame.Rect(self.sb_track.x, self.sb_track.y + sb_y,
                           self.sb_track.width, sb_h)

    def draw(self, surface):
        if not self.visible or self.font_code is None:
            return

        r = self.rect

        # 面板背景（不透明深色）
        pygame.draw.rect(surface, (12, 16, 38), r)
        pygame.draw.line(surface, (0, 200, 220), (r.x, r.y), (r.x, r.bottom), 2)

        # 标题栏
        title_bg = pygame.Rect(r.x, r.y, r.width, 34)
        pygame.draw.rect(surface, (20, 28, 60), title_bg)
        pygame.draw.line(surface, (0,180,200), (r.x, r.y+34), (r.right, r.y+34))

        # 算法名称
        title = f"《 {self.algo_name} 》 源码"
        surf_t = self.font_title.render(title, True, (0, 220, 220))
        surface.blit(surf_t, (r.x + 8, r.y + 7))

        # 关闭按钮
        close_hov = self.btn_close.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (180,50,50) if close_hov else (120,40,40),
                         self.btn_close, border_radius=4)
        surf_x = self.font_sm.render("X", True, (255,255,255))
        surface.blit(surf_x, surf_x.get_rect(center=self.btn_close.center))

        # 代码区
        code_area_y = r.y + 38
        code_area_h = r.height - 44
        code_area_w = r.width - self.LNUM_W - 12
        code_area   = pygame.Rect(r.x + self.LNUM_W, code_area_y,
                                  code_area_w, code_area_h)
        lnum_area   = pygame.Rect(r.x, code_area_y,
                                  self.LNUM_W, code_area_h)

        try:
            lnum_sub = surface.subsurface(lnum_area)
            lnum_sub.fill((28, 32, 55))
        except Exception:
            lnum_sub = None

        try:
            code_sub = surface.subsurface(code_area)
            code_sub.fill((14, 18, 40))
        except Exception:
            code_sub = None

        lh         = self.LINE_H
        first      = int(self.scroll / lh)
        visible_n  = code_area_h // lh + 2
        for i in range(first, min(first + visible_n, len(self.lines))):
            y_off = i * lh - self.scroll
            if lnum_sub:
                ln_s = self.font_code.render(str(i+1), True, (80,85,110))
                lnum_sub.blit(ln_s, (self.LNUM_W - ln_s.get_width() - 5, y_off + 2))
            if code_sub:
                tx = 4
                for seg, col in self.tokens[i]:
                    if not seg: continue
                    try:
                        ts = self.font_code.render(seg, True, col)
                        if 0 <= y_off < code_area_h:
                            code_sub.blit(ts, (tx, y_off + 2))
                        tx += ts.get_width()
                    except Exception:
                        pass

        # 滚动条
        pygame.draw.rect(surface, (28,32,52), self.sb_track, border_radius=3)
        sb = self._sb_rect()
        if sb:
            pygame.draw.rect(surface, (70,85,130), sb, border_radius=3)

    def handle_event(self, event, screen_w, screen_h):
        """返回 True 表示事件被消耗"""
        if not self.visible:
            return False
        self._update_rect(screen_w, screen_h)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.btn_close.collidepoint(mx, my):
                self.hide()
                return True
            if self.rect.collidepoint(mx, my):
                sb = self._sb_rect()
                if sb and sb.collidepoint(mx, my):
                    self._drag_sb = True
                return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag_sb = False

        if event.type == pygame.MOUSEMOTION and self._drag_sb:
            vis_h   = self.sb_track.height
            total_h = max(1, len(self.lines) * self.LINE_H)
            rel_y   = event.pos[1] - self.sb_track.y
            ratio   = clamp(rel_y / vis_h, 0, 1)
            self.scroll = int(ratio * (total_h - vis_h))
            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll = clamp(
                    self.scroll - event.y * self.LINE_H * 3,
                    0, self._max_scroll()
                )
                return True

        return False


# ============================================================
#  下拉菜单
# ============================================================
class DropDown:
    def __init__(self, x, y, w, h, options, font, label=""):
        self.rect    = pygame.Rect(x, y, w, h)
        self.options = options
        self.font    = font
        self.label   = label
        self.selected = 0
        self.expanded = False
        self.hover_idx = -1

    def draw(self, surface):
        pygame.draw.rect(surface, DKBLUE, self.rect)
        pygame.draw.rect(surface, CYAN,   self.rect, 2)
        text = self.options[self.selected]
        draw_text(surface, text, self.font, WHITE,
                  self.rect.x+8, self.rect.centery, anchor="midleft")
        arrow = "▲" if self.expanded else "▼"
        draw_text(surface, arrow, self.font, CYAN,
                  self.rect.right-25, self.rect.centery, anchor="midleft")
        if self.expanded:
            for i, opt in enumerate(self.options):
                item_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.bottom + i * self.rect.height,
                    self.rect.width,
                    self.rect.height
                )
                bg = (50, 80, 150) if i == self.hover_idx else (20, 40, 90)
                pygame.draw.rect(surface, bg, item_rect)
                pygame.draw.rect(surface, CYAN, item_rect, 1)
                draw_text(surface, opt, self.font, WHITE,
                          item_rect.x+8, item_rect.centery, anchor="midleft")

    def handle_event(self, event):
        """返回是否选择了新选项"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
                return False
            if self.expanded:
                for i in range(len(self.options)):
                    item_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.bottom + i * self.rect.height,
                        self.rect.width,
                        self.rect.height
                    )
                    if item_rect.collidepoint(event.pos):
                        self.selected = i
                        self.expanded = False
                        return True
                self.expanded = False
        if event.type == pygame.MOUSEMOTION:
            if self.expanded:
                self.hover_idx = -1
                for i in range(len(self.options)):
                    item_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.bottom + i * self.rect.height,
                        self.rect.width,
                        self.rect.height
                    )
                    if item_rect.collidepoint(event.pos):
                        self.hover_idx = i
        return False


# ============================================================
#  按钮
# ============================================================
class Button:
    def __init__(self, x, y, w, h, text, color, text_color=WHITE, font=None):
        self.rect       = pygame.Rect(x, y, w, h)
        self.text       = text
        self.color      = color
        self.hover_color= tuple(min(255, c+50) for c in color)
        self.text_color = text_color
        self.font       = font
        self.hovered    = False

    def draw(self, surface):
        c = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, c, self.rect, border_radius=6)
        pygame.draw.rect(surface, WHITE, self.rect, 1, border_radius=6)
        if self.font:
            draw_text(surface, self.text, self.font, self.text_color,
                      self.rect.centerx, self.rect.centery, anchor="center")

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# ============================================================
#  数量设置对话框（滑动条 + 输入框双模式）
# ============================================================
class CountDialog:
    """设置数据量：拖动滑块 或 直接输入数字"""
    MIN_VAL = 1
    MAX_VAL = 1000

    def __init__(self, screen_w, screen_h, font_md, font_sm, on_change=None):
        self.visible   = False
        self.font      = font_md
        self.font_sm   = font_sm
        self.value     = 100
        self.text      = "100"
        self.dragging  = False
        self.input_active = False
        self._on_change = on_change   # 滑块实时回调
        self._just_opened = False     # 防止开启当帧误关闭
        self._layout(screen_w, screen_h)

    def _layout(self, sw, sh):
        dw, dh = 460, 200
        self.rect = pygame.Rect(sw//2 - dw//2, sh//2 - dh//2, dw, dh)
        self.track_rect = pygame.Rect(
            self.rect.x + 30, self.rect.y + 80, dw - 60, 8
        )
        self.input_rect = pygame.Rect(
            self.rect.x + dw//2 - 60, self.rect.y + 110, 120, 34
        )
        self.btn_ok = pygame.Rect(
            self.rect.x + dw//2 - 110, self.rect.y + dh - 50, 100, 34
        )
        self.btn_cancel = pygame.Rect(
            self.rect.x + dw//2 + 10, self.rect.y + dh - 50, 100, 34
        )

    def _val_to_x(self, val):
        ratio = (val - self.MIN_VAL) / (self.MAX_VAL - self.MIN_VAL)
        return int(self.track_rect.x + ratio * self.track_rect.width)

    def _x_to_val(self, x):
        ratio = (x - self.track_rect.x) / self.track_rect.width
        return clamp(int(ratio * (self.MAX_VAL - self.MIN_VAL) + self.MIN_VAL),
                     self.MIN_VAL, self.MAX_VAL)

    def show(self, current_val):
        self.visible = True
        self._just_opened = True
        self.value   = clamp(current_val, self.MIN_VAL, self.MAX_VAL)
        self.text    = str(self.value)
        self.input_active = False
        self.dragging = False

    def hide(self):
        self.visible = False

    def draw(self, surface):
        if not self.visible:
            return
        # 无全屏遮罩，仅绘制浮动对话框，可视化区域保持可见
        pygame.draw.rect(surface, (18, 28, 60), self.rect, border_radius=14)
        pygame.draw.rect(surface, CYAN,         self.rect, 2, border_radius=14)

        draw_text(surface, "设置数据量", self.font, WHITE,
                  self.rect.centerx, self.rect.y + 14, anchor="midtop")
        draw_text(surface, f"{self.value}  ITEMS", self.font,
                  CYAN, self.rect.centerx, self.rect.y + 48, anchor="midtop")

        pygame.draw.rect(surface, (50, 60, 100), self.track_rect, border_radius=4)
        filled_w = self._val_to_x(self.value) - self.track_rect.x
        filled_rect = pygame.Rect(self.track_rect.x, self.track_rect.y, filled_w, self.track_rect.height)
        pygame.draw.rect(surface, CYAN, filled_rect, border_radius=4)
        thumb_x = self._val_to_x(self.value)
        thumb_y = self.track_rect.centery
        pygame.draw.circle(surface, WHITE,  (thumb_x, thumb_y), 10)
        pygame.draw.circle(surface, CYAN,   (thumb_x, thumb_y), 10, 2)

        draw_text(surface, "1",    self.font_sm, LGRAY,
                  self.track_rect.x,           self.track_rect.y - 14, anchor="midtop")
        draw_text(surface, "1000", self.font_sm, LGRAY,
                  self.track_rect.right,        self.track_rect.y - 14, anchor="midtop")

        draw_text(surface, "或直接输入:", self.font_sm, LGRAY,
                  self.input_rect.x, self.input_rect.centery, anchor="midright")

        inp_border = YELLOW if self.input_active else LGRAY
        pygame.draw.rect(surface, (10, 18, 45), self.input_rect)
        pygame.draw.rect(surface, inp_border,   self.input_rect, 2, border_radius=4)
        cursor = "|" if self.input_active else ""
        draw_text(surface, self.text + cursor, self.font, YELLOW,
                  self.input_rect.centerx, self.input_rect.centery, anchor="center")

        pygame.draw.rect(surface, (0, 140, 60), self.btn_ok, border_radius=7)
        pygame.draw.rect(surface, WHITE, self.btn_ok, 1, border_radius=7)
        draw_text(surface, "确  认", self.font, WHITE,
                  self.btn_ok.centerx, self.btn_ok.centery, anchor="center")

        pygame.draw.rect(surface, (140, 40, 40), self.btn_cancel, border_radius=7)
        pygame.draw.rect(surface, WHITE, self.btn_cancel, 1, border_radius=7)
        draw_text(surface, "取  消", self.font, WHITE,
                  self.btn_cancel.centerx, self.btn_cancel.centery, anchor="center")

    def _commit_input(self):
        try:
            v = int(self.text)
            self.value = clamp(v, self.MIN_VAL, self.MAX_VAL)
            self.text  = str(self.value)
        except:
            self.text = str(self.value)

    def handle_event(self, event):
        """返回值: 正数=确认的数值, -1=关闭(取消/点外部), None=未关闭"""
        if not self.visible:
            return None
        # 跳过开启当帧的事件，防止触发开启的同一事件导致立即关闭
        if self._just_opened:
            self._just_opened = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # 点击对话框外部 → 关闭（数值已通过滑块实时生效）
            if not self.rect.collidepoint(mx, my):
                self.visible = False
                return -1
            if self.btn_ok.collidepoint(mx, my):
                self._commit_input()
                self.visible = False
                return self.value
            if self.btn_cancel.collidepoint(mx, my):
                self.visible = False
                return -1
            if self.input_rect.collidepoint(mx, my):
                self.input_active = True
                return None
            else:
                if self.input_active:
                    self._commit_input()
                self.input_active = False
            thumb_x = self._val_to_x(self.value)
            thumb_y = self.track_rect.centery
            dist = math.hypot(mx - thumb_x, my - thumb_y)
            if dist <= 14:
                self.dragging = True
                return None
            if self.track_rect.collidepoint(mx, my):
                self.value = self._x_to_val(mx)
                self.text  = str(self.value)
                self.dragging = True
                if self._on_change:
                    self._on_change(self.value)
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.value = self._x_to_val(event.pos[0])
                self.text  = str(self.value)
                if self._on_change:
                    self._on_change(self.value)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.visible = False
                return None
            if event.key == pygame.K_RETURN:
                self._commit_input()
                self.visible = False
                return self.value
            if self.input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.unicode.isdigit() and len(self.text) < 4:
                    self.text += event.unicode
                    try:
                        v = int(self.text)
                        self.value = clamp(v, self.MIN_VAL, self.MAX_VAL)
                    except:
                        pass

        return None


# ============================================================
#  悬停下拉菜单（鼠标移入展开，移出收起）
# ============================================================
class HoverDropDown:
    """悬停触发的下拉菜单——鼠标移入展开，移出自动收起"""

    def __init__(self, x, y, w, h, options, font, label="", on_select=None):
        self.rect      = pygame.Rect(x, y, w, h)
        self.options   = options
        self.font      = font
        self.label     = label
        self.selected  = 0
        self.expanded  = False
        self.hover_idx = -1
        self._on_select = on_select

    def _item_rect(self, i):
        return pygame.Rect(
            self.rect.x,
            self.rect.bottom + i * self.rect.height,
            self.rect.width,
            self.rect.height
        )

    def draw(self, surface):
        pygame.draw.rect(surface, (100, 0, 160), self.rect, border_radius=6)
        pygame.draw.rect(surface, WHITE, self.rect, 1, border_radius=6)
        text = self.options[self.selected]
        draw_text(surface, text, self.font, WHITE,
                  self.rect.x + 8, self.rect.centery, anchor="midleft")
        arrow = "▲" if self.expanded else "▼"
        draw_text(surface, arrow, self.font, CYAN,
                  self.rect.right - 22, self.rect.centery, anchor="midleft")
        if self.expanded:
            for i, opt in enumerate(self.options):
                item_rect = self._item_rect(i)
                bg = (80, 40, 160) if i == self.hover_idx else (60, 20, 120)
                pygame.draw.rect(surface, bg, item_rect)
                pygame.draw.rect(surface, CYAN, item_rect, 1)
                draw_text(surface, opt, self.font, WHITE,
                          item_rect.x + 8, item_rect.centery, anchor="midleft")

    def handle_event(self, event):
        """返回 True 表示选择了新选项"""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            on_main = self.rect.collidepoint(mx, my)
            if self.expanded:
                on_items = False
                self.hover_idx = -1
                for i in range(len(self.options)):
                    ir = self._item_rect(i)
                    if ir.collidepoint(mx, my):
                        self.hover_idx = i
                        on_items = True
                        break
                if not on_main and not on_items:
                    self.expanded = False
                    self.hover_idx = -1
            else:
                if on_main:
                    self.expanded = True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.expanded and self.hover_idx >= 0:
                self.selected = self.hover_idx
                # 始终触发回调（允许重复选择同一项重新生成数据）
                if self._on_select:
                    self._on_select(self.selected)
                return True
        return False


# ============================================================
#  设置面板（浮层）
# ============================================================
class SettingsPanel:
    """
    设置面板——点击齿轮按钮展开/收起浮层。
    功能：
      1. 自定义柱状图颜色（待排序/排序中/已完成 各 7 种常见色，下拉框选择）
      2. 排序音效 / 完成音效 独立开关
    """

    # 7 种常见颜色（统一调色板）
    COLORS = [
        ((220, 50, 50),   "红"),
        ((255, 140, 0),   "橙"),
        ((255, 230, 0),   "黄"),
        ((50, 200, 50),   "绿"),
        ((65, 105, 225),  "蓝"),
        ((148, 0, 211),   "紫"),
        ((0, 200, 200),   "青"),
    ]

    # 三个颜色分类的默认选项
    _DEFAULT_NORMAL    = 4   # 蓝
    _DEFAULT_HIGHLIGHT = 2   # 黄
    _DEFAULT_SORTED    = 3   # 绿

    def __init__(self, screen_w, screen_h, font):
        self.visible   = False
        self.font      = font
        self.screen_w  = screen_w
        self.screen_h  = screen_h

        # 当前选中色索引
        self.sel_normal    = self._DEFAULT_NORMAL
        self.sel_highlight = self._DEFAULT_HIGHLIGHT
        self.sel_sorted    = self._DEFAULT_SORTED

        # 音效开关
        self.sound_process  = True
        self.sound_complete = True

        # 明亮度 (20~100, 默认100)
        self.brightness = 100
        self._load_brightness()

        # 深色模式 (True=深色, False=浅色)
        self.dark_mode = True
        self._load_dark_mode()

        # 面板尺寸与位置（右对齐）
        self.pw, self.ph = 280, 390
        self._update_rect()

        # 下拉框布局参数
        self._dd_labels = ["柱状图颜色", "排序中颜色", "已完成颜色"]
        self._dd_sel_attrs = ["sel_normal", "sel_highlight", "sel_sorted"]
        self._dd_y_start = 48          # 第一个下拉框 y 偏移
        self._dd_row_h   = 42          # 行高
        self._dd_box_w   = 150         # 下拉框宽度
        self._dd_box_h   = 30          # 下拉框高度
        self._dd_item_h  = 28          # 展开项高度
        self._dd_open    = -1          # 当前展开的下拉框索引 (-1=无)

        # 音效区 y
        self._snd_y = self._dd_y_start + self._dd_row_h * 3 + 10

        # 明亮度区 y（音效区下方）
        self._bri_y = self._snd_y + 36 * 2 + 10

        # 深色模式区 y（明亮度区下方）
        self._dark_y = self._bri_y + 50

    def _update_rect(self):
        x = self.screen_w - self.pw - 10
        y = CTRL_H + 5
        self.rect = pygame.Rect(x, y, self.pw, self.ph)

    def _bri_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "brightness.cfg")

    def _dark_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "darkmode.cfg")

    def _save_brightness(self):
        try:
            with open(self._bri_file(), "w") as f:
                f.write(str(self.brightness))
        except Exception:
            pass

    def _load_brightness(self):
        try:
            with open(self._bri_file(), "r") as f:
                val = int(f.read().strip())
                self.brightness = max(20, min(100, val))
        except Exception:
            self.brightness = 100

    def _save_dark_mode(self):
        try:
            with open(self._dark_file(), "w") as f:
                f.write("1" if self.dark_mode else "0")
        except Exception:
            pass

    def _load_dark_mode(self):
        try:
            with open(self._dark_file(), "r") as f:
                val = f.read().strip()
                self.dark_mode = val == "1"
        except Exception:
            self.dark_mode = True

    def get_dark_mode(self):
        """返回是否深色模式"""
        return self.dark_mode

    def update_screen_size(self, w, h):
        self.screen_w, self.screen_h = w, h
        self._update_rect()

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def toggle(self):
        self.visible = not self.visible

    # 颜色访问接口
    def get_normal_color(self):
        return self.COLORS[self.sel_normal][0]

    def get_highlight_color(self):
        return self.COLORS[self.sel_highlight][0]

    def get_sorted_color(self):
        return self.COLORS[self.sel_sorted][0]

    def get_brightness(self):
        """返回亮度值 20~100"""
        return self.brightness

    # ----------------------------------------------------------
    #  下拉框区域计算
    # ----------------------------------------------------------

    def _dd_header_rect(self, index):
        """第 index 个下拉框的头部 Rect（关闭状态）"""
        x = self.rect.x + 120
        y = self.rect.y + self._dd_y_start + index * self._dd_row_h
        return pygame.Rect(x, y, self._dd_box_w, self._dd_box_h)

    def _dd_item_rect(self, dd_index, color_index):
        """第 dd_index 个下拉框的第 color_index 个选项 Rect"""
        hr = self._dd_header_rect(dd_index)
        x = hr.x
        y = hr.bottom + color_index * self._dd_item_h
        return pygame.Rect(x, y, self._dd_box_w, self._dd_item_h)

    def _toggle_rect(self, index):
        """获取音效开关方块的 Rect"""
        return pygame.Rect(self.rect.x + 238, self.rect.y + self._snd_y + index * 36 + 2,
                           24, 24)

    def _bri_minus_rect(self):
        return pygame.Rect(self.rect.x + 14, self.rect.y + self._bri_y + 18, 26, 26)

    def _bri_plus_rect(self):
        return pygame.Rect(self.rect.x + 240, self.rect.y + self._bri_y + 18, 26, 26)

    def _bri_bar_rect(self):
        return pygame.Rect(self.rect.x + 48, self.rect.y + self._bri_y + 26, 184, 12)

    def _dark_toggle_rect(self):
        return pygame.Rect(self.rect.x + 220, self.rect.y + self._dark_y + 10, 48, 28)

    # ----------------------------------------------------------
    #  绘制
    # ----------------------------------------------------------

    def draw(self, surface):
        if not self.visible:
            return

        # 面板背景（不透明）
        pygame.draw.rect(surface, (22, 28, 58), self.rect, border_radius=8)
        pygame.draw.rect(surface, CYAN, self.rect, 2, border_radius=8)

        # 标题
        draw_text(surface, "设置", self.font, WHITE,
                  self.rect.x + 14, self.rect.y + 14)

        # 关闭按钮
        pygame.draw.rect(surface, (80, 30, 30),
                         pygame.Rect(self.rect.right - 30, self.rect.y + 6, 22, 22),
                         border_radius=4)
        draw_text(surface, "×", self.font, WHITE,
                  self.rect.right - 19, self.rect.y + 17, anchor="center")

        # 三个颜色下拉框（仅绘制头部）
        for i, label in enumerate(self._dd_labels):
            sel_idx = getattr(self, self._dd_sel_attrs[i])
            sel_rgb, sel_name = self.COLORS[sel_idx]
            hr = self._dd_header_rect(i)

            # 标签
            draw_text(surface, label, self.font, CYAN,
                      self.rect.x + 14, hr.centery, anchor="midleft")

            # 下拉框主体
            pygame.draw.rect(surface, (40, 45, 75), hr, border_radius=4)
            pygame.draw.rect(surface, LGRAY, hr, 1, border_radius=4)

            # 色块预览（左侧小方块）
            preview = pygame.Rect(hr.x + 6, hr.y + 5, 20, 20)
            pygame.draw.rect(surface, sel_rgb, preview, border_radius=3)

            # 文字
            draw_text(surface, sel_name, self.font, WHITE,
                      hr.x + 32, hr.centery, anchor="midleft")

            # 箭头
            arrow = "▲" if self._dd_open == i else "▼"
            draw_text(surface, arrow, self.font, CYAN,
                      hr.right - 16, hr.centery, anchor="center")

        # 分隔线
        pygame.draw.line(surface, LGRAY,
                         (self.rect.x + 14, self.rect.y + self._snd_y - 6),
                         (self.rect.right - 14, self.rect.y + self._snd_y - 6))

        # 音效开关
        for i, (label, on) in enumerate([
            ("排序音效", self.sound_process),
            ("完成音效", self.sound_complete),
        ]):
            ty = self.rect.y + self._snd_y + i * 36
            draw_text(surface, label, self.font, WHITE,
                      self.rect.x + 14, ty + 12)
            tr = self._toggle_rect(i)
            bg = (0, 160, 60) if on else (100, 40, 40)
            pygame.draw.rect(surface, bg, tr, border_radius=4)
            pygame.draw.rect(surface, WHITE, tr, 1, border_radius=4)
            state = "开" if on else "关"
            draw_text(surface, state, self.font, WHITE,
                      tr.centerx, tr.centery, anchor="center")

        # 分隔线
        pygame.draw.line(surface, LGRAY,
                         (self.rect.x + 14, self.rect.y + self._bri_y - 4),
                         (self.rect.right - 14, self.rect.y + self._bri_y - 4))

        # 明亮度控制
        draw_text(surface, "明亮度", self.font, WHITE,
                  self.rect.x + 14, self.rect.y + self._bri_y + 8)
        draw_text(surface, f"{self.brightness}%", self.font, CYAN,
                  self.rect.right - 14, self.rect.y + self._bri_y + 8, anchor="topright")

        # 减号按钮
        mr = self._bri_minus_rect()
        pygame.draw.rect(surface, (60, 50, 100), mr, border_radius=4)
        pygame.draw.rect(surface, LGRAY, mr, 1, border_radius=4)
        draw_text(surface, "−", self.font, WHITE, mr.centerx, mr.centery, anchor="center")

        # 加号按钮
        pr = self._bri_plus_rect()
        pygame.draw.rect(surface, (60, 50, 100), pr, border_radius=4)
        pygame.draw.rect(surface, LGRAY, pr, 1, border_radius=4)
        draw_text(surface, "+", self.font, WHITE, pr.centerx, pr.centery, anchor="center")

        # 滑动条
        br = self._bri_bar_rect()
        pygame.draw.rect(surface, (40, 45, 75), br, border_radius=6)
        fill_w = int(br.width * (self.brightness - 20) / 80)
        if fill_w > 0:
            fill_r = pygame.Rect(br.x, br.y, fill_w, br.height)
            pygame.draw.rect(surface, (100, 180, 255), fill_r, border_radius=6)
        # 滑块手柄
        knob_x = br.x + fill_w
        knob_r = pygame.Rect(knob_x - 5, br.y - 4, 10, br.height + 8)
        pygame.draw.rect(surface, WHITE, knob_r, border_radius=5)

        # 分隔线
        pygame.draw.line(surface, LGRAY,
                         (self.rect.x + 14, self.rect.y + self._dark_y - 4),
                         (self.rect.right - 14, self.rect.y + self._dark_y - 4))

        # 深色/浅色模式切换
        draw_text(surface, "深色模式", self.font, WHITE,
                  self.rect.x + 14, self.rect.y + self._dark_y + 14)
        mode_text = "深色" if self.dark_mode else "浅色"
        draw_text(surface, mode_text, self.font, CYAN,
                  self.rect.x + 140, self.rect.y + self._dark_y + 14)
        # 开关按钮
        tr = self._dark_toggle_rect()
        bg = (0, 160, 60) if self.dark_mode else (200, 150, 50)
        pygame.draw.rect(surface, bg, tr, border_radius=14)
        pygame.draw.rect(surface, WHITE, tr, 1, border_radius=14)
        # 圆形滑块
        knob_x = tr.x + 34 if self.dark_mode else tr.x + 14
        pygame.draw.circle(surface, WHITE, (knob_x, tr.centery), 10)

        # ---- 展开的下拉列表最后绘制，确保不被其他元素遮挡 ----
        if self._dd_open >= 0:
            sel_idx = getattr(self, self._dd_sel_attrs[self._dd_open])
            for ci, (rgb, name) in enumerate(self.COLORS):
                ir = self._dd_item_rect(self._dd_open, ci)
                # 不透明背景
                pygame.draw.rect(surface, (30, 35, 65), ir)
                bg = (60, 50, 100) if ci == sel_idx else (35, 40, 70)
                pygame.draw.rect(surface, bg, ir.inflate(-2, -2))
                pygame.draw.rect(surface, LGRAY, ir, 1)
                # 色块预览
                ip = pygame.Rect(ir.x + 6, ir.y + 4, 20, 20)
                pygame.draw.rect(surface, rgb, ip, border_radius=3)
                draw_text(surface, name, self.font, WHITE,
                          ir.x + 32, ir.centery, anchor="midleft")

    # ----------------------------------------------------------
    #  事件
    # ----------------------------------------------------------

    def handle_event(self, event):
        """返回 True 表示事件已被消费（包括 MOUSEMOTION 悬停）"""
        if not self.visible:
            return False

        # 点击事件
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not self.rect.collidepoint(mx, my):
                self._dd_open = -1
                self.visible = False   # 点击面板外部关闭
                return True

            # 关闭按钮
            close_r = pygame.Rect(self.rect.right - 30, self.rect.y + 6, 22, 22)
            if close_r.collidepoint(mx, my):
                self._dd_open = -1
                self.visible = False
                return True

            # 下拉框选项点击
            if self._dd_open >= 0:
                for ci in range(len(self.COLORS)):
                    ir = self._dd_item_rect(self._dd_open, ci)
                    if ir.collidepoint(mx, my):
                        setattr(self, self._dd_sel_attrs[self._dd_open], ci)
                        self._dd_open = -1
                        return True
                # 点击了下拉列表外部，收起
                self._dd_open = -1
                return True

            # 下拉框头部点击（展开/收起）
            for i in range(3):
                hr = self._dd_header_rect(i)
                if hr.collidepoint(mx, my):
                    self._dd_open = i if self._dd_open != i else -1
                    return True

            # 音效开关
            for i, attr in enumerate(["sound_process", "sound_complete"]):
                tr = self._toggle_rect(i)
                if tr.collidepoint(mx, my):
                    setattr(self, attr, not getattr(self, attr))
                    return True

            # 明亮度减号
            if self._bri_minus_rect().collidepoint(mx, my):
                self.brightness = max(20, self.brightness - 10)
                self._save_brightness()
                return True

            # 明亮度加号
            if self._bri_plus_rect().collidepoint(mx, my):
                self.brightness = min(100, self.brightness + 10)
                self._save_brightness()
                return True

            # 明亮度滑动条点击
            br = self._bri_bar_rect()
            if br.inflate(0, 10).collidepoint(mx, my):
                ratio = max(0, min(1, (mx - br.x) / br.width))
                self.brightness = int(20 + ratio * 80)
                # 四舍五入到最接近的5
                self.brightness = round(self.brightness / 5) * 5
                self.brightness = max(20, min(100, self.brightness))
                self._save_brightness()
                return True

            # 深色模式切换
            if self._dark_toggle_rect().collidepoint(mx, my):
                self.dark_mode = not self.dark_mode
                self._save_dark_mode()
                return True

            return True  # 面板内部点击全部拦截

        # 鼠标在面板区域内则消费事件（防止穿透）
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            if self.rect.collidepoint(event.pos):
                return True

        return False
