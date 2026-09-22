# -*- coding: utf-8 -*-
"""
game.py —— “一箭又一箭” 核心游戏逻辑

本文件不依赖 pygame，只负责游戏规则与状态，便于单独测试。
核心概念：
  - 箭头：用三元组 (row, col, direction) 表示，direction 为 up/down/left/right
  - 关卡：由字符网格定义，例如 ["→·↑", "·↓·"]，'↑↓←→' 表示箭头，'·' 表示空格
  - 路径检测：从箭头沿其方向一格一格走到棋盘边界，途中遇到其它箭头即被阻挡
"""

UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"

# 四个方向对应的 (行增量, 列增量)
DIRS = {
    UP:    (-1, 0),
    DOWN:  (1, 0),
    LEFT:  (0, -1),
    RIGHT: (0, 1),
}

# 字符 -> 方向 的映射
CHAR_TO_DIR = {"↑": UP, "↓": DOWN, "←": LEFT, "→": RIGHT}


class Game:
    def __init__(self, levels):
        self.levels = levels
        self.level_index = 0
        self.endless_num = 1
        self.reset_level()

    # ---------- 关卡初始化 ----------
    def reset_level(self):
        level = self.levels[self.level_index]
        self.grid = level["grid"]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0
        self.arrows = self._parse_grid(self.grid)
        self.max_hearts = level.get("hearts", 3)
        self.hearts = self.max_hearts
        self.endless = level.get("name", "").startswith("无尽模式")
        self.status = "playing"   # playing / level_clear / endless_clear / win / game_over
        self.endless_pending = False
        self.endless_timer = 0

        # ---- 统计信息 ----
        self.clicks = 0
        self.mistakes = 0
        self.best_clicks = len(self.arrows)
        self.elapsed = 0

    @staticmethod
    def _parse_grid(grid):
        arrows = []
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch in CHAR_TO_DIR:
                    arrows.append((r, c, CHAR_TO_DIR[ch]))
        return arrows

    # ---------- 路径检测 ----------
    def find_blocker(self, arrow):
        return self._find_blocker_in(arrow, self.arrows)

    def _find_blocker_in(self, arrow, arrows):
        r, c, d = arrow
        dr, dc = DIRS[d]
        occupied = {(a[0], a[1]) for a in arrows if (a[0], a[1]) != (r, c)}
        rr, cc = r + dr, c + dc
        while 0 <= rr < self.rows and 0 <= cc < self.cols:
            if (rr, cc) in occupied:
                return (rr, cc)
            rr += dr
            cc += dc
        return None

    # ---------- 点击处理 ----------
    def click(self, r, c):
        for arrow in self.arrows:
            if arrow[0] == r and arrow[1] == c:
                self.clicks += 1
                blocker = self.find_blocker(arrow)
                if blocker is None:
                    self.arrows.remove(arrow)
                    if not self.arrows:
                        if self.endless:
                            # 无尽模式：先显示结算，玩家点击（或 2 秒后）再换关
                            self.status = "endless_clear"
                        elif self.level_index == len(self.levels) - 1:
                            self.status = "win"
                        else:
                            self.status = "level_clear"
                    return "fly", arrow, None
                else:
                    self.hearts -= 1
                    self.mistakes += 1
                    if self.hearts <= 0:
                        self.hearts = 0
                        self.status = "game_over"
                    return "blocked", arrow, blocker
        return "invalid", None, None

    # ---------- 帧更新 ----------
    def update(self, dt):
        if self.endless_pending:
            self.endless_timer -= dt
            if self.endless_timer <= 0:
                self.endless_pending = False
                from levels import generate_random_level
                self.endless_num += 1
                self.levels[self.level_index] = generate_random_level(level_num=self.endless_num)
                self.reset_level()

    def tick(self, dt):
        if self.status == "playing" and not self.endless_pending:
            self.elapsed += dt

    # ---------- 关卡切换 ----------
    def next_level(self):
        self.level_index += 1
        self.reset_level()

    # ---------- 工具 ----------
    def remaining_arrows(self):
        return len(self.arrows)

    def is_solvable(self):
        remaining = list(self.arrows)
        changed = True
        while remaining and changed:
            changed = False
            for arrow in list(remaining):
                if self._find_blocker_in(arrow, remaining) is None:
                    remaining.remove(arrow)
                    changed = True
        return not remaining
    def find_hint(self):
        """
        返回一个当前可以飞出的箭头 (r, c, d)，没有则返回 None。
        即：该箭头前进方向上没有其它箭头。
        """
        for arrow in self.arrows:
            if self.find_blocker(arrow) is None:
                return arrow
        return None