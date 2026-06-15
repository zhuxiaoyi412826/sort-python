# -*- coding: utf-8 -*-
"""
音效管理模块
============
为排序可视化工具提供音效反馈：
- 比较音：正弦波音高与柱高成正比
- 交换音：短促咔嗒声
- 完成音：上升音阶扫弦
- 静音开关
"""

import math
import array
import pygame


class SoundManager:
    """排序音效管理器，自动生成并播放三种音效"""

    # 音频参数
    SAMPLE_RATE = 22050        # 采样率
    FREQ_MIN    = 200          # 最低音频率（对应最小值）
    FREQ_MAX    = 1200         # 最高音频率（对应最大值）

    def __init__(self):
        self.enabled = True
        self._mixer_ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16,
                                  channels=1, buffer=512)
            self._mixer_ok = True
            # 独立声道：避免互相干扰
            self._cmp_chan  = pygame.mixer.Channel(0)   # 比较音（每步中断重启）
            self._swap_chan = pygame.mixer.Channel(1)   # 交换咔嗒
            self._done_chan = pygame.mixer.Channel(2)   # 完成扫弦
            # 预生成音效
            self._build_sounds()
        except Exception as e:
            print(f"[SoundManager] 音频初始化失败: {e}")
            self._mixer_ok = False

    # ----------------------------------------------------------
    #  音效生成
    # ----------------------------------------------------------

    def _pluck_tone(self, freq, duration, volume=0.3):
        """
        生成拨弦音色（指数衰减 + 泛音）
        类似竖琴/吉他拨弦，比纯正弦波更温暖柔和
        """
        sr = self.SAMPLE_RATE
        n = int(sr * duration)
        amp = 24000 * volume
        buf = array.array('h')
        for i in range(n):
            t = i / sr
            # 快速起音 + 指数衰减（拨弦特征）
            env = math.exp(-t * 12.0)  # 衰减系数：越大音越短促
            if i < sr * 0.002:          # 2ms 起音淡入防爆音
                env *= i / (sr * 0.002)
            # 基频 + 泛音（2、3、4次谐波递减）—— 让音色更丰富温暖
            wave  = math.sin(2.0 * math.pi * freq * t)            # 基频
            wave += 0.4 * math.sin(2.0 * math.pi * freq * 2 * t)  # 二次泛音
            wave += 0.15 * math.sin(2.0 * math.pi * freq * 3 * t) # 三次泛音
            wave += 0.05 * math.sin(2.0 * math.pi * freq * 4 * t) # 四次泛音
            val = int(amp * env * wave * 0.5)  # 0.5 归一化（泛音叠加后振幅更大）
            buf.append(max(-32767, min(32767, val)))
        return buf

    def _ding_tone(self, freq, duration, volume=0.4):
        """
        生成清脆叮声（高频正弦 + 快速指数衰减）
        类似三角铁/风铃
        """
        sr = self.SAMPLE_RATE
        n = int(sr * duration)
        amp = 20000 * volume
        buf = array.array('h')
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 20.0)  # 快速衰减，短促清脆
            if i < sr * 0.001:          # 1ms 起音
                env *= i / (sr * 0.001)
            # 双频叠加产生"叮"的金属质感
            wave = math.sin(2.0 * math.pi * freq * t)
            wave += 0.3 * math.sin(2.0 * math.pi * freq * 2.76 * t)  # 非谐频泛音
            val = int(amp * env * wave)
            buf.append(max(-32767, min(32767, val)))
        return buf

    def _build_sounds(self):
        """预生成所有音效 Sound 对象"""
        # --- 比较音：拨弦音色，10 档频率，运行时选最近的 ---
        self._compare_tones = []
        # 五声音阶频率（C D E G A）跨两个八度，音程更和谐
        freqs = [262, 294, 330, 392, 440, 523, 587, 659, 784, 880]
        for f in freqs:
            buf = self._pluck_tone(f, 0.08, volume=0.25)
            snd = pygame.mixer.Sound(buffer=buf)
            snd.set_volume(0.25)
            self._compare_tones.append((f, snd))
    
        # --- 交换叮声（高频清脆短音）---
        buf = self._ding_tone(1200, 0.06, volume=0.35)
        self._swap_click = pygame.mixer.Sound(buffer=buf)
        self._swap_click.set_volume(0.35)
    
        # --- 完成竖琴琶音（C 大调分解和弦 + 余韵）---
        # C-E-G-C'-E'-G'-C''  每个音更长 + 余韵叠加
        notes = [262, 330, 392, 523, 659, 784, 1047, 1319]
        buf = array.array('h')
        for i, note in enumerate(notes):
            tone = self._pluck_tone(note, 0.25, volume=0.35)
            buf.extend(tone)
            # 音之间 12ms 间隔（竖琴拨弦间隔感）
            gap = array.array('h', [0] * int(self.SAMPLE_RATE * 0.012))
            buf.extend(gap)
        self._complete_snd = pygame.mixer.Sound(buffer=buf)
        self._complete_snd.set_volume(0.4)

    # ----------------------------------------------------------
    #  播放接口
    # ----------------------------------------------------------

    def _nearest_tone(self, freq):
        """找到最接近 freq 的预生成音调"""
        best = self._compare_tones[0]
        for t in self._compare_tones:
            if abs(t[0] - freq) < abs(best[0] - freq):
                best = t
        return best[1]

    def play_compare(self, value, max_value=1000):
        """
        播放比较音：音高与柱高（value）成正比
        value: 当前被比较的数值（1 ~ max_value）
        """
        if not self.enabled or not self._mixer_ok:
            return
        ratio = max(0.0, min(1.0, (value - 1) / max(1, max_value - 1)))
        freq = self.FREQ_MIN + ratio * (self.FREQ_MAX - self.FREQ_MIN)
        snd = self._nearest_tone(freq)
        self._cmp_chan.stop()
        self._cmp_chan.play(snd)

    def play_swap(self):
        """播放交换咔嗒声"""
        if not self.enabled or not self._mixer_ok:
            return
        self._swap_chan.play(self._swap_click)

    def play_complete(self):
        """播放完成扫弦音"""
        if not self.enabled or not self._mixer_ok:
            return
        self._done_chan.stop()
        self._done_chan.play(self._complete_snd)

    def stop_all(self):
        """停止所有正在播放的音效"""
        if self._mixer_ok:
            self._cmp_chan.stop()
            self._swap_chan.stop()
            self._done_chan.stop()

    def toggle(self):
        """切换静音状态，返回新的 enabled 值"""
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop_all()
        return self.enabled
