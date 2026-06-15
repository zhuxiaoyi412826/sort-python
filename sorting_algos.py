# -*- coding: utf-8 -*-
"""
排序算法模块
============
包含 19 种排序算法的生成器函数，以及算法源码提取工具。
每个排序函数均为生成器，逐步 yield (array, highlight_indices, swap_count, cmp_count)。
"""

import random


# 基础排序（10种）
BASIC_ALGOS = [
    "冒泡排序", "选择排序", "插入排序", "快速排序",
    "归并排序", "希尔排序", "堆排序",  "桶排序",
    "计数排序", "基数排序"
]

# 趣味排序（9种）
FUN_ALGOS = [
    "猴子排序", "睡眠排序", "面条排序", "斯大林排序",
    "鸡尾酒排序", "慢排序",  "煎饼排序", "珠排序",
    "鸽巢排序"
]


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


# ============================================================
#  基础排序算法
# ============================================================

def bubble_sort(arr):
    """冒泡排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    for i in range(n):
        for j in range(0, n - i - 1):
            cmp_count += 1
            yield arr, [j, j+1], swap_count, cmp_count
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                swap_count += 1
                yield arr, [j, j+1], swap_count, cmp_count


def selection_sort(arr):
    """选择排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            cmp_count += 1
            yield arr, [min_idx, j], swap_count, cmp_count
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
            swap_count += 1
            yield arr, [i, min_idx], swap_count, cmp_count


def insertion_sort(arr):
    """插入排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0:
            cmp_count += 1
            yield arr, [j, j+1], swap_count, cmp_count
            if arr[j] > key:
                arr[j+1] = arr[j]
                swap_count += 1
                j -= 1
            else:
                break
        arr[j+1] = key
        yield arr, [j+1], swap_count, cmp_count


def quick_sort(arr):
    """快速排序（迭代版本，使用栈）"""
    swap_count = 0
    cmp_count  = 0

    def partition(lo, hi):
        nonlocal swap_count, cmp_count
        pivot = arr[hi]
        i = lo - 1
        steps = []
        for j in range(lo, hi):
            cmp_count += 1
            steps.append((arr[:], [j, hi], swap_count, cmp_count))
            if arr[j] <= pivot:
                i += 1
                arr[i], arr[j] = arr[j], arr[i]
                swap_count += 1
                steps.append((arr[:], [i, j], swap_count, cmp_count))
        arr[i+1], arr[hi] = arr[hi], arr[i+1]
        swap_count += 1
        steps.append((arr[:], [i+1, hi], swap_count, cmp_count))
        return i + 1, steps

    stack = [(0, len(arr)-1)]
    while stack:
        lo, hi = stack.pop()
        if lo < hi:
            pi, steps = partition(lo, hi)
            for s in steps:
                yield s[0], s[1], s[2], s[3]
            stack.append((lo, pi-1))
            stack.append((pi+1, hi))


def merge_sort(arr):
    """归并排序（迭代自底向上）"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    width = 1
    while width < n:
        for i in range(0, n, width*2):
            lo  = i
            mid = min(i + width, n)
            hi  = min(i + width*2, n)
            left  = arr[lo:mid]
            right = arr[mid:hi]
            li = ri = 0
            k  = lo
            while li < len(left) and ri < len(right):
                cmp_count += 1
                yield arr, [lo+li, mid+ri], swap_count, cmp_count
                if left[li] <= right[ri]:
                    arr[k] = left[li]; li += 1
                else:
                    arr[k] = right[ri]; ri += 1
                swap_count += 1
                k += 1
            while li < len(left):
                arr[k] = left[li]; li += 1; k += 1
            while ri < len(right):
                arr[k] = right[ri]; ri += 1; k += 1
        width *= 2
    yield arr, [], swap_count, cmp_count


def shell_sort(arr):
    """希尔排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = arr[i]
            j = i
            while j >= gap:
                cmp_count += 1
                yield arr, [j-gap, j], swap_count, cmp_count
                if arr[j-gap] > temp:
                    arr[j] = arr[j-gap]
                    swap_count += 1
                    j -= gap
                else:
                    break
            arr[j] = temp
        gap //= 2
    yield arr, [], swap_count, cmp_count


def heap_sort(arr):
    """堆排序（迭代heapify避免递归收集问题）"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0

    def heapify_steps(heap_size, i):
        nonlocal swap_count, cmp_count
        steps = []
        while True:
            largest = i
            l = 2*i+1
            r = 2*i+2
            if l < heap_size:
                cmp_count += 1
                steps.append((arr[:], [largest, l], swap_count, cmp_count))
                if arr[l] > arr[largest]:
                    largest = l
            if r < heap_size:
                cmp_count += 1
                steps.append((arr[:], [largest, r], swap_count, cmp_count))
                if arr[r] > arr[largest]:
                    largest = r
            if largest == i:
                break
            arr[i], arr[largest] = arr[largest], arr[i]
            swap_count += 1
            steps.append((arr[:], [i, largest], swap_count, cmp_count))
            i = largest
        return steps

    # 建堆
    for i in range(n//2-1, -1, -1):
        for s in heapify_steps(n, i):
            yield s[0], s[1], s[2], s[3]
    # 提取
    for i in range(n-1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        swap_count += 1
        yield arr, [0, i], swap_count, cmp_count
        for s in heapify_steps(i, 0):
            yield s[0], s[1], s[2], s[3]


def bucket_sort(arr):
    """桶排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    if n == 0:
        return
    max_val = max(arr)
    min_val = min(arr)
    bucket_range = (max_val - min_val) / n + 1
    buckets = [[] for _ in range(n)]
    for val in arr:
        idx = int((val - min_val) / bucket_range)
        idx = clamp(idx, 0, n-1)
        buckets[idx].append(val)
    result = []
    for b in buckets:
        b.sort()
        result.extend(b)
    for i in range(n):
        cmp_count += 1
        arr[i] = result[i]
        swap_count += 1
        yield arr, [i], swap_count, cmp_count


def counting_sort(arr):
    """计数排序"""
    n = len(arr)
    if n == 0:
        return
    swap_count = 0
    cmp_count  = 0
    max_val = max(arr)
    min_val = min(arr)
    offset = min_val
    size   = max_val - min_val + 1
    count  = [0] * size
    for v in arr:
        count[v - offset] += 1
        cmp_count += 1
    idx = 0
    for i, c in enumerate(count):
        for _ in range(c):
            arr[idx] = i + offset
            swap_count += 1
            yield arr, [idx], swap_count, cmp_count
            idx += 1


def radix_sort(arr):
    """基数排序（LSD）"""
    n = len(arr)
    if n == 0:
        return
    swap_count = 0
    cmp_count  = 0
    max_val = max(arr)
    exp = 1
    while max_val // exp > 0:
        output = [0] * n
        count  = [0] * 10
        for v in arr:
            digit = (v // exp) % 10
            count[digit] += 1
            cmp_count += 1
        for i in range(1, 10):
            count[i] += count[i-1]
        for i in range(n-1, -1, -1):
            digit = (arr[i] // exp) % 10
            count[digit] -= 1
            output[count[digit]] = arr[i]
        for i in range(n):
            arr[i] = output[i]
            swap_count += 1
            yield arr, [i], swap_count, cmp_count
        exp *= 10


# ============================================================
#  趣味排序算法
# ============================================================

def cocktail_sort(arr):
    """鸡尾酒排序（双向冒泡）"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    lo, hi = 0, n-1
    while lo < hi:
        for i in range(lo, hi):
            cmp_count += 1
            yield arr, [i, i+1], swap_count, cmp_count
            if arr[i] > arr[i+1]:
                arr[i], arr[i+1] = arr[i+1], arr[i]
                swap_count += 1
        hi -= 1
        for i in range(hi, lo, -1):
            cmp_count += 1
            yield arr, [i-1, i], swap_count, cmp_count
            if arr[i] < arr[i-1]:
                arr[i], arr[i-1] = arr[i-1], arr[i]
                swap_count += 1
        lo += 1


def slow_sort(arr):
    """慢排序（递归，故意低效）- 限制到20个元素内防止超时"""
    n = len(arr)
    MAX_N = 20
    work = arr[:min(n, MAX_N)]
    sc = [0]
    cc = [0]
    steps = []

    def _slow(a, lo, hi):
        if lo >= hi:
            return
        mid = (lo + hi) // 2
        _slow(a, lo, mid)
        _slow(a, mid+1, hi)
        cc[0] += 1
        steps.append((list(a), [mid, hi], sc[0], cc[0]))
        if a[mid] > a[hi]:
            a[mid], a[hi] = a[hi], a[mid]
            sc[0] += 1
            steps.append((list(a), [mid, hi], sc[0], cc[0]))
        _slow(a, lo, hi-1)

    _slow(work, 0, len(work)-1)
    for i in range(len(work)):
        arr[i] = work[i]
    for s in steps:
        yield s[0], s[1], s[2], s[3]


def pancake_sort(arr):
    """煎饼排序"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0

    def flip(end):
        nonlocal swap_count
        lo, hi = 0, end
        while lo < hi:
            arr[lo], arr[hi] = arr[hi], arr[lo]
            swap_count += 1
            lo += 1; hi -= 1

    for size in range(n, 1, -1):
        max_idx = 0
        for i in range(1, size):
            cmp_count += 1
            yield arr, [max_idx, i], swap_count, cmp_count
            if arr[i] > arr[max_idx]:
                max_idx = i
        if max_idx != size - 1:
            flip(max_idx)
            yield arr, list(range(max_idx+1)), swap_count, cmp_count
            flip(size-1)
            yield arr, list(range(size)), swap_count, cmp_count


def bead_sort(arr):
    """珠排序（重力排序）模拟"""
    n = len(arr)
    if n == 0:
        return
    swap_count = 0
    cmp_count  = 0
    max_val = max(arr)
    grid = [[0]*max_val for _ in range(n)]
    for i, v in enumerate(arr):
        for j in range(v):
            grid[i][j] = 1
    for col in range(max_val):
        beads = sum(grid[row][col] for row in range(n))
        for row in range(n):
            grid[row][col] = 1 if row >= n - beads else 0
    result = [sum(grid[i]) for i in range(n)]
    for i in range(n):
        arr[i] = result[i]
        swap_count += 1
        cmp_count += 1
        yield arr, [i], swap_count, cmp_count


def pigeonhole_sort(arr):
    """鸽巢排序"""
    n = len(arr)
    if n == 0:
        return
    swap_count = 0
    cmp_count  = 0
    min_val = min(arr)
    max_val = max(arr)
    size = max_val - min_val + 1
    holes = [0] * size
    for v in arr:
        holes[v - min_val] += 1
        cmp_count += 1
    idx = 0
    for i, c in enumerate(holes):
        for _ in range(c):
            arr[idx] = i + min_val
            swap_count += 1
            yield arr, [idx], swap_count, cmp_count
            idx += 1


def monkey_sort(arr):
    """猴子排序（随机打乱直到有序）- 限制100次防止无限循环"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    max_tries = 200

    def is_sorted(a):
        return all(a[i] <= a[i+1] for i in range(len(a)-1))

    attempt = 0
    while not is_sorted(arr) and attempt < max_tries:
        random.shuffle(arr)
        swap_count += n
        attempt += 1
        for i in range(n-1):
            cmp_count += 1
        yield arr, list(range(n)), swap_count, cmp_count
    yield arr, [], swap_count, cmp_count


def sleep_sort(arr):
    """睡眠排序（模拟：值越小越早排到前面）"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    sorted_arr = sorted(arr)
    for i in range(n):
        arr[i] = sorted_arr[i]
        swap_count += 1
        cmp_count += 1
        yield arr, [i], swap_count, cmp_count


def noodle_sort(arr):
    """面条排序（视觉模拟：直接插入展示）"""
    n = len(arr)
    swap_count = 0
    cmp_count  = 0
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            cmp_count += 1
            arr[j+1] = arr[j]
            swap_count += 1
            j -= 1
            yield arr, [j+1, i], swap_count, cmp_count
        arr[j+1] = key
        yield arr, [j+1], swap_count, cmp_count


def stalin_sort(arr):
    """斯大林排序（删除不合适的元素，保留有序子序列）"""
    swap_count = 0
    cmp_count  = 0
    i = 1
    while i < len(arr):
        cmp_count += 1
        yield arr, [i-1, i], swap_count, cmp_count
        if arr[i] < arr[i-1]:
            # 不合格的元素直接删除，数组变短
            arr.pop(i)
            swap_count += 1
            yield arr, [i-1] if i-1 < len(arr) else [], swap_count, cmp_count
            # i 不递增，继续检查新的 arr[i]
        else:
            i += 1
    yield arr, [], swap_count, cmp_count


# ============================================================
#  算法名称 → 函数名 映射
# ============================================================
ALGO_FUNC_MAP = {
    "冒泡排序":   "bubble_sort",
    "选择排序":   "selection_sort",
    "插入排序":   "insertion_sort",
    "快速排序":   "quick_sort",
    "归并排序":   "merge_sort",
    "希尔排序":   "shell_sort",
    "堆排序":     "heap_sort",
    "桶排序":     "bucket_sort",
    "计数排序":   "counting_sort",
    "基数排序":   "radix_sort",
    "猴子排序":   "monkey_sort",
    "睡眠排序":   "sleep_sort",
    "面条排序":   "noodle_sort",
    "斯大林排序": "stalin_sort",
    "鸡尾酒排序": "cocktail_sort",
    "慢排序":     "slow_sort",
    "煎饼排序":   "pancake_sort",
    "珠排序":     "bead_sort",
    "鸽巢排序":   "pigeonhole_sort",
}

# 算法名称 → 函数对象 映射（供 SortingVisualizer 使用）
ALGO_DISPATCH = {
    "冒泡排序":   bubble_sort,
    "选择排序":   selection_sort,
    "插入排序":   insertion_sort,
    "快速排序":   quick_sort,
    "归并排序":   merge_sort,
    "希尔排序":   shell_sort,
    "堆排序":     heap_sort,
    "桶排序":     bucket_sort,
    "计数排序":   counting_sort,
    "基数排序":   radix_sort,
    "猴子排序":   monkey_sort,
    "睡眠排序":   sleep_sort,
    "面条排序":   noodle_sort,
    "斯大林排序": stalin_sort,
    "鸡尾酒排序": cocktail_sort,
    "慢排序":     slow_sort,
    "煎饼排序":   pancake_sort,
    "珠排序":     bead_sort,
    "鸽巢排序":   pigeonhole_sort,
}


# ============================================================
#  算法源码提取工具
# ============================================================
_ALGO_CODE_CACHE: dict = {}


def _extract_algo_code(func_names: list) -> dict:
    """从本模块源码中提取指定函数的源码（行列表）"""
    result = {}
    g = globals()
    # 优先使用 inspect（桌面环境）
    try:
        import inspect
        for name in func_names:
            fn = g.get(name)
            if fn:
                try:
                    lines = inspect.getsource(fn).splitlines()
                    result[name] = lines
                except Exception:
                    pass
    except Exception:
        pass
    # 回退到静态字典（WASM环境）
    if len(result) < len(func_names):
        try:
            from algo_code import ALGO_SOURCE
            for name in func_names:
                if name not in result:
                    result[name] = ALGO_SOURCE.get(name, [f"# 无法获取 {name} 的源码"])
        except ImportError:
            for name in func_names:
                if name not in result:
                    result[name] = [f"# 无法获取 {name} 的源码"]
    return result


def get_algo_code_lines(algo_name: str) -> list:
    """获取指定算法的源码行列表，带缓存"""
    if algo_name not in _ALGO_CODE_CACHE:
        func_name = ALGO_FUNC_MAP.get(algo_name)
        if func_name:
            res = _extract_algo_code([func_name])
            _ALGO_CODE_CACHE[algo_name] = res.get(func_name, ["# 找不到源码"])
        else:
            _ALGO_CODE_CACHE[algo_name] = ["# 未知算法"]
    return _ALGO_CODE_CACHE[algo_name]
