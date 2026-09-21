# -*- coding: utf-8 -*-
"""
main.py —— “一箭又一箭” 主程序（pygame 界面与主循环）

运行：python main.py
包含：开始界面 / 游戏界面 / 结果界面，以及飞出与碰撞动画。
"""

import os
import math
import pygame

from game import Game, UP, DOWN, LEFT, RIGHT, DIRS
from levels import LEVELS
import constants as C

# 飞出速度（像素/秒）
FLY_SPEED = C.GRID_SIZE * 7
# 碰撞抖动时长（秒）
BLOCK_TIME = 0.4


# 直接指定系统中文字体文件路径，避免 SysFont 在 Windows 上扫描注册表时报错
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
    "C:/Windows/Fonts/simsun.ttc",  # 宋体
    "C:/Windows/Fonts/Deng.ttf",    # 等线
]


def get_font(size, bold=False):
    """加载中文字体；粗体优先用粗体文件，找不到则用默认字体兜底"""
    if bold:
        for path in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf"):
            if os.path.exists(path):
                return pygame.font.Font(path, size)
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def arrow_points(cx, cy, d, r):
    """返回以 (cx, cy) 为中心、方向为 d 的等腰三角形顶点（r 为半径）"""
    if d == RIGHT:
        return [(cx + r, cy), (cx - r * 0.6, cy - r * 0.8), (cx - r * 0.6, cy + r * 0.8)]
    if d == LEFT:
        return [(cx - r, cy), (cx + r * 0.6, cy - r * 0.8), (cx + r * 0.6, cy + r * 0.8)]
    if d == UP:
        return [(cx, cy - r), (cx - r * 0.8, cy + r * 0.6), (cx + r * 0.8, cy + r * 0.6)]
    return [(cx, cy + r), (cx - r * 0.8, cy - r * 0.6), (cx + r * 0.8, cy - r * 0.6)]


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        self.game = Game(LEVELS)

        self.scene = "start"      # start / game / result
        self.result_kind = None   # win / game_over

        # 动画数据：飞出中的箭头、碰撞抖动的格子
        self.fly_anims = []       # [{r, c, d, t0, x, y}]
        self.block_anims = {}     # {(r, c): t0}

        # 各按钮（固定位置）
        self.start_btn = pygame.Rect(0, 0, 200, 60)
        self.start_btn.center = (C.WINDOW_WIDTH // 2, 360)
        self.restart_btn = pygame.Rect(C.WINDOW_WIDTH - 150, 20, 130, 42)
        self.again_btn = pygame.Rect(0, 0, 200, 56)
        self.again_btn.center = (C.WINDOW_WIDTH // 2, 380)
        self.menu_btn = pygame.Rect(0, 0, 200, 56)
        self.menu_btn.center = (C.WINDOW_WIDTH // 2, 460)

    # ---------- 坐标换算 ----------
    @property
    def board_x(self):
        return (C.WINDOW_WIDTH - self.game.cols * C.GRID_SIZE) // 2

    @property
    def board_y(self):
        return C.BOARD_TOP

    def cell_center(self, r, c):
        return (self.board_x + c * C.GRID_SIZE + C.GRID_SIZE // 2,
                self.board_y + r * C.GRID_SIZE + C.GRID_SIZE // 2)

    def cell_from_pos(self, pos):
        x, y = pos
        c = (x - self.board_x) // C.GRID_SIZE
        r = (y - self.board_y) // C.GRID_SIZE
        if 0 <= r < self.game.rows and 0 <= c < self.game.cols:
            return r, c
        return None

    # ---------- 主循环 ----------
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            self.update_anims()
            self.draw()
            pygame.display.flip()
            self.clock.tick(C.FPS)
        pygame.quit()

    # ---------- 点击分发 ----------
    def handle_click(self, pos):
        if self.scene == "start":
            if self.start_btn.collidepoint(pos):
                self.scene = "game"
                self.game = Game(LEVELS)
            return

        if self.scene == "result":
            if self.again_btn.collidepoint(pos):
                self.game = Game(LEVELS)
                self.scene = "game"
            elif self.menu_btn.collidepoint(pos):
                self.scene = "start"
            return

        if self.scene == "game":
            if self.restart_btn.collidepoint(pos):
                self.restart_level()
                return

            if self.game.status == "level_clear":
                self.game.next_level()
                return

            cell = self.cell_from_pos(pos)
            if cell is None:
                return
            r, c = cell
            result, arrow, blocker = self.game.click(r, c)

            if result == "fly":
                self.fly_anims.append({"r": r, "c": c, "d": arrow[2],
                                       "t0": pygame.time.get_ticks(), "x": 0, "y": 0})
            elif result == "blocked":
                self.block_anims[(r, c)] = pygame.time.get_ticks()

            if self.game.status == "win":
                self.scene = "result"
                self.result_kind = "win"
            elif self.game.status == "game_over":
                self.scene = "result"
                self.result_kind = "game_over"

    def restart_level(self):
        self.game.reset_level()
        self.fly_anims.clear()
        self.block_anims.clear()

    # ---------- 动画更新 ----------
    def update_anims(self):
        now = pygame.time.get_ticks()
        alive = []
        for a in self.fly_anims:
            dt = (now - a["t0"]) / 1000.0
            dist = dt * FLY_SPEED
            dr, dc = DIRS[a["d"]]
            cx, cy = self.cell_center(a["r"], a["c"])
            a["x"] = cx + dc * dist
            a["y"] = cy + dr * dist
            left = self.board_x - C.GRID_SIZE
            right = self.board_x + self.game.cols * C.GRID_SIZE + C.GRID_SIZE
            top = self.board_y - C.GRID_SIZE
            bottom = self.board_y + self.game.rows * C.GRID_SIZE + C.GRID_SIZE
            if not (left <= a["x"] <= right and top <= a["y"] <= bottom):
                continue
            alive.append(a)
        self.fly_anims = alive

        for key in list(self.block_anims.keys()):
            if (now - self.block_anims[key]) / 1000.0 >= BLOCK_TIME:
                del self.block_anims[key]

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.fill(C.BG_COLOR)
        if self.scene == "start":
            self.draw_start()
        elif self.scene == "game":
            self.draw_game()
        else:
            self.draw_result()

    def draw_text(self, text, size, color, center=None, topleft=None, bold=False):
        surf = get_font(size, bold).render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = center
        if topleft:
            rect.topleft = topleft
        self.screen.blit(surf, rect)
        return rect

    def draw_start(self):
        self.draw_text("一箭又一箭", 60, C.TITLE_COLOR, center=(C.WINDOW_WIDTH // 2, 150), bold=True)
        self.draw_text("点击箭头，让所有箭头飞出棋盘", 24, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 235))
        self.draw_text("前方有箭头阻挡时会消耗一次失误机会", 20, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 275))
        pygame.draw.rect(self.screen, C.ARROW_COLOR, self.start_btn, border_radius=10)
        self.draw_text("开始游戏", 28, (255, 255, 255), center=self.start_btn.center, bold=True)

    def draw_game(self):
        g = self.game
        # 顶部 HUD
        self.draw_text(g.levels[g.level_index]["name"], 28, C.TITLE_COLOR, topleft=(20, 20), bold=True)
        self.draw_text(f"剩余箭头：{g.remaining_arrows()}", 20, C.TEXT_COLOR, topleft=(20, 72))
        self.draw_text(f"剩余失误：{g.mistakes}", 20, C.MISTAKE_COLOR, topleft=(20, 102))
        pygame.draw.rect(self.screen, C.ARROW_COLOR, self.restart_btn, border_radius=8)
        self.draw_text("重新开始", 18, (255, 255, 255), center=self.restart_btn.center)

        # 棋盘背景 + 网格线
        bx, by = self.board_x, self.board_y
        for r in range(g.rows):
            for c in range(g.cols):
                rect = pygame.Rect(bx + c * C.GRID_SIZE, by + r * C.GRID_SIZE, C.GRID_SIZE, C.GRID_SIZE)
                pygame.draw.rect(self.screen, C.CELL_COLOR, rect)
                pygame.draw.rect(self.screen, C.GRID_LINE, rect, 1)

        # 棋盘上的箭头（碰撞时抖动并变红）
        now = pygame.time.get_ticks()
        for (r, c, d) in g.arrows:
            cx, cy = self.cell_center(r, c)
            color, offset = C.ARROW_COLOR, 0
            if (r, c) in self.block_anims:
                color = C.ARROW_BLOCKED
                elapsed = (now - self.block_anims[(r, c)]) / 1000.0
                offset = int(6 * math.sin(elapsed * 40))
            pygame.draw.polygon(self.screen, color, arrow_points(cx + offset, cy, d, C.GRID_SIZE * 0.34))

        # 飞出动画中的箭头
        for a in self.fly_anims:
            pygame.draw.polygon(self.screen, C.ARROW_COLOR, arrow_points(a["x"], a["y"], a["d"], C.GRID_SIZE * 0.34))

        # 过关遮罩
        if g.status == "level_clear":
            overlay = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            self.screen.blit(overlay, (0, 0))
            self.draw_text("过关！点击进入下一关", 40, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, C.WINDOW_HEIGHT // 2), bold=True)

    def draw_result(self):
        if self.result_kind == "win":
            self.draw_text("恭喜通关！", 56, (60, 170, 90), center=(C.WINDOW_WIDTH // 2, 200), bold=True)
            self.draw_text("你成功清除了所有关卡", 24, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 280))
        else:
            self.draw_text("游戏失败", 56, C.MISTAKE_COLOR, center=(C.WINDOW_WIDTH // 2, 200), bold=True)
            self.draw_text("失误次数耗尽，再来一次吧", 24, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 280))

        pygame.draw.rect(self.screen, C.ARROW_COLOR, self.again_btn, border_radius=10)
        self.draw_text("再玩一次", 26, (255, 255, 255), center=self.again_btn.center, bold=True)
        pygame.draw.rect(self.screen, (150, 155, 165), self.menu_btn, border_radius=10)
        self.draw_text("返回主菜单", 26, (255, 255, 255), center=self.menu_btn.center)


if __name__ == "__main__":
    App().run()
