# -*- coding: utf-8 -*-
"""
数据生成模块
============
负责生成排序可视化所需的随机数组数据。
"""

import random


def generate_random_array(count, min_val=1, max_val=1000):
    """
    生成随机整数数组。

    参数:
        count:   数组长度
        min_val: 最小值（含）
        max_val: 最大值（含）

    返回:
        list[int]  长度为 count 的随机整数列表
    """
    return [random.randint(min_val, max_val) for _ in range(count)]


def create_sort_state():
    """
    创建排序初始状态字典，包含：
      - array:        空数组
      - highlight:    空高亮列表
      - sorted_done:  False
      - cmp_count:    0
      - swap_count:   0
      - generator:    None
      - running:      False
      - paused:       False
    """
    return {
        "array":       [],
        "highlight":   [],
        "sorted_done": False,
        "cmp_count":   0,
        "swap_count":  0,
        "generator":   None,
        "running":     False,
        "paused":      False,
    }
