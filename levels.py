# -*- coding: utf-8 -*-
"""
levels.py —— 关卡数据（全部 6×6）
"""

import random


LEVELS = [
    # 第 1 关：6×6 新手引导
    {
        "name": "第 1 关 · 新手引导",
        "grid": [
            "······",
            "·→·↑··",
            "··→···",
            "·↓·←··",
            "······",
            "······",
        ],
        "hearts": 3,
    },
    # 第 2 关：6×6
    {
        "name": "第 2 关",
        "grid": [
            "······",
            "·→→·↑·",
            "······",
            "·←·↓·→",
            "······",
            "······",
        ],
        "hearts": 3,
    },
    # 第 3 关：6×6
    {
        "name": "第 3 关",
        "grid": [
            "······",
            "·→→·↑·",
            "··↓···",
            "·←·→·→",
            "······",
            "······",
        ],
        "hearts": 3,
    },
    # 第 4 关：6×6
    {
        "name": "第 4 关",
        "grid": [
            "······",
            "·→→→↑·",
            "··↑·↓·",
            "······",
            "···←←←",
            "······",
        ],
        "hearts": 3,
    },
    # 第 5 关：6×6
    {
        "name": "第 5 关",
        "grid": [
            "←···→·",
            "·↑↑···",
            "←·····",
            "··←···",
            "·↑→··↓",
            "·←↓·→·",
        ],
        "hearts": 3,
    },
]


def _is_solvable(grid_str):
    """用贪心验证一个字符网格是否可以通关"""
    rows = len(grid_str)
    cols = len(grid_str[0]) if rows else 0
    dir_map = {'↑': (-1, 0), '↓': (1, 0), '←': (0, -1), '→': (0, 1)}
    arrows = []
    for r in range(rows):
        for c in range(cols):
            ch = grid_str[r][c]
            if ch in dir_map:
                arrows.append((r, c, ch))
    remaining = list(arrows)
    changed = True
    while remaining and changed:
        changed = False
        for arrow in list(remaining):
            r, c, ch = arrow
            dr, dc = dir_map[ch]
            occupied = {(a[0], a[1]) for a in remaining if (a[0], a[1]) != (r, c)}
            rr, cc = r + dr, c + dc
            blocked = False
            while 0 <= rr < rows and 0 <= cc < cols:
                if (rr, cc) in occupied:
                    blocked = True
                    break
                rr += dr
                cc += dc
            if not blocked:
                remaining.remove(arrow)
                changed = True
    return not remaining


def generate_random_level(rows=6, cols=6, arrow_count=10, hearts=3, seed=None, level_num=1):
    """随机生成一个 6×6 的可通关关卡"""
    rng = random.Random(seed)
    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    rng.shuffle(all_cells)
    chosen = all_cells[:arrow_count]
    dirs = ['↑', '↓', '←', '→']
    for _ in range(200):
        grid = [['·'] * cols for _ in range(rows)]
        for (r, c) in chosen:
            grid[r][c] = rng.choice(dirs)
        grid_str = [''.join(row) for row in grid]
        if _is_solvable(grid_str):
            return {
                "name": f"无尽模式 · 第 {level_num} 关",
                "grid": grid_str,
                "hearts": hearts,
            }
    # 保底布局（保证可通关）
    return {
        "name": f"无尽模式 · 第 {level_num} 关",
        "grid": [
            "······",
            "·→→·↑·",
            "··↓···",
            "·←·→·→",
            "······",
            "······",
        ],
        "hearts": hearts,
    }