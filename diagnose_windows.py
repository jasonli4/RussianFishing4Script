#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""窗口诊断脚本 - 用于查找所有 Russian Fishing 4 相关的窗口"""

import win32gui
import win32con

def enum_all_windows_callback(hwnd, windows):
    """枚举所有可见窗口回调函数"""
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:  # 只要有标题的窗口
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            windows.append({
                'hwnd': hwnd,
                'title': title,
                'class_name': class_name,
                'rect': rect,
                'width': width,
                'height': height
            })

def main():
    import sys
    import io

    # 设置控制台输出编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("正在搜索所有可见窗口...\n")

    all_windows = []
    win32gui.EnumWindows(enum_all_windows_callback, all_windows)

    # 查找标题完全匹配或包含 "Russian Fishing 4" 的窗口
    fishing_windows = [w for w in all_windows if 'Russian Fishing 4' in w['title']]

    if fishing_windows:
        print(f"找到 {len(fishing_windows)} 个与游戏相关的窗口:\n")
        for i, win in enumerate(fishing_windows):
            print(f"窗口 #{i+1}:")
            print(f"  标题: {win['title']}")
            print(f"  类名: {win['class_name']}")
            print(f"  窗口句柄: {win['hwnd']}")
            print(f"  位置: ({win['rect'][0]}, {win['rect'][1]})")
            print(f"  大小: {win['width']}x{win['height']}")
            print()

        # 推荐最可能是游戏主窗口的窗口
        candidates = [w for w in fishing_windows if w['width'] >= 800 and w['height'] >= 600]

        if candidates:
            print("\n推荐的游戏主窗口候选:")
            for c in candidates:
                print(f"  - {c['title']} (大小: {c['width']}x{c['height']}, 类名: {c['class_name']})")

            # 找到最大的窗口
            main_window = max(candidates, key=lambda w: w['width'] * w['height'])
            print(f"\n最可能的游戏主窗口:")
            print(f"  标题: {main_window['title']}")
            print(f"  大小: {main_window['width']}x{main_window['height']}")
            print(f"  类名: {main_window['class_name']}")
            print(f"  窗口句柄: {main_window['hwnd']}")
    else:
        print("未找到任何与 'Russian Fishing 4' 相关的窗口")
        print("\n显示所有可见窗口 (前50个):")
        print(f"总共找到 {len(all_windows)} 个可见窗口\n")
        for i, win in enumerate(all_windows[:50]):
            print(f"{i+1:3d}. [{win['class_name']}] {win['title'][:60]} "
                  f"({win['width']}x{win['height']})")

    print("\n提示：请确保游戏已启动并显示在屏幕上")

if __name__ == "__main__":
    main()
