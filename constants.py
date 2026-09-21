# -*- coding: utf-8 -*-
"""
constants.py —— 全局常量：窗口、棋盘、颜色、帧率
"""

# ---- 窗口 ----
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 620

# ---- 棋盘 ----
GRID_SIZE = 80          # 每格边长（像素）
BOARD_TOP = 160         # 棋盘区域顶部留白（放标题与状态栏）

# ---- 颜色 (R, G, B) ----
BG_COLOR = (245, 247, 250)          # 背景
CELL_COLOR = (255, 255, 255)        # 空格底色
GRID_LINE = (205, 210, 220)         # 网格线
ARROW_COLOR = (45, 120, 235)        # 箭头正常颜色（蓝）
ARROW_BLOCKED = (230, 60, 60)       # 碰撞反馈颜色（红）
TEXT_COLOR = (40, 45, 55)           # 正文
TITLE_COLOR = (30, 60, 120)         # 标题
MISTAKE_COLOR = (230, 60, 60)       # 剩余失误文字

FPS = 60
