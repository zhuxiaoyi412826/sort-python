# -*- mode: python ; coding: utf-8 -*-
"""
排序算法可视化工具 - PyInstaller 打包配置
"""

import os
import sys

block_cipher = None
this_dir = SPECPATH  # PyInstaller 自动设置为 spec 文件所在目录

# 数据文件
datas = [
    (os.path.join(this_dir, 'avi', '11.wav'), 'avi'),
    (os.path.join(this_dir, 'brightness.cfg'), '.'),
    (os.path.join(this_dir, 'darkmode.cfg'), '.'),
    # 子模块脚本（用于 subprocess 调用）
    (os.path.join(this_dir, 'algo_detail.py'), '.'),
    (os.path.join(this_dir, 'curve_chart.py'), '.'),
    (os.path.join(this_dir, 'record_replay.py'), '.'),
    (os.path.join(this_dir, 'sorting_algos.py'), '.'),
    (os.path.join(this_dir, 'audio_manager.py'), '.'),
    (os.path.join(this_dir, 'data_generator.py'), '.'),
    (os.path.join(this_dir, 'rendering.py'), '.'),
]

a = Analysis(
    [os.path.join(this_dir, 'sorting_visualizer.py')],
    pathex=[this_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'algo_detail',
        'curve_chart',
        'record_replay',
        'compare_mode',
        'sorting_algos',
        'audio_manager',
        'data_generator',
        'rendering',
        'pygame',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'numpy',
        'tkinter',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'scipy', 'pandas', 'sympy',
        'pytest', 'pygments',
        'IPython', 'jupyter',
        'notebook',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='排序算法可视化',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台（subprocess 输出可见）
    disable_windowed=False,
    argv_emulation=False,
    icon=None,
)
