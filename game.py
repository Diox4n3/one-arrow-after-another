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

# 字符 -> 方向 的映射，用于解析关卡字符串
CHAR_TO_DIR = {"↑": UP, "↓": DOWN, "←": LEFT, "→": RIGHT}


class Game:
    def __init__(self, levels):
        """
        levels: 关卡列表，每一项形如 {"grid": ["→·↑", "·↓·"], "mistakes": 3}
        """
        self.levels = levels
        self.level_index = 0
        self.reset_level()

    # ---------- 关卡初始化 ----------
    def reset_level(self):
        level = self.levels[self.level_index]
        self.grid = level["grid"]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0
        self.arrows = self._parse_grid(self.grid)
        self.max_mistakes = level.get("mistakes", 3)
        self.mistakes = self.max_mistakes
        self.status = "playing"   # playing / level_clear / win / game_over

    @staticmethod
    def _parse_grid(grid):
        """把字符网格解析成箭头列表 [(row, col, dir), ...]"""
        arrows = []
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch in CHAR_TO_DIR:
                    arrows.append((r, c, CHAR_TO_DIR[ch]))
        return arrows

    # ---------- 核心：路径检测 ----------
    def find_blocker(self, arrow):
        """返回 arrow 前进方向上最近的阻挡箭头位置 (r, c)；无阻挡返回 None"""
        return self._find_blocker_in(arrow, self.arrows)

    def _find_blocker_in(self, arrow, arrows):
        """
        在给定箭头集合 arrows 里，找 arrow 的阻挡者。
        从 arrow 沿其方向一格一格走，直到走出棋盘边界；
        途中第一个被其它箭头占据的格子就是阻挡者。
        """
        r, c, d = arrow
        dr, dc = DIRS[d]
        # 其它所有箭头占据的格子集合
        occupied = {(a[0], a[1]) for a in arrows if (a[0], a[1]) != (r, c)}

        rr, cc = r + dr, c + dc
        while 0 <= rr < self.rows and 0 <= cc < self.cols:
            if (rr, cc) in occupied:
                return (rr, cc)     # 被这个箭头挡住
            rr += dr
            cc += dc
        return None                 # 一路走到边界，无阻挡

    # ---------- 点击处理 ----------
    def click(self, r, c):
        """
        玩家点击格子 (r, c)。
        返回 (result, arrow, blocker)：
          result == "fly"     -> 箭头飞出并被消除
          result == "blocked" -> 被阻挡，失误次数 -1
          result == "invalid" -> 该格没有箭头
        """
        for arrow in self.arrows:
            if arrow[0] == r and arrow[1] == c:
                blocker = self.find_blocker(arrow)
                if blocker is None:
                    self.arrows.remove(arrow)
                    if not self.arrows:
                        # 本关清空：是最后一关则通关，否则进入“过关”状态
                        if self.level_index == len(self.levels) - 1:
                            self.status = "win"
                        else:
                            self.status = "level_clear"
                    return "fly", arrow, None
                else:
                    self.mistakes -= 1
                    if self.mistakes <= 0:
                        self.mistakes = 0
                        self.status = "game_over"
                    return "blocked", arrow, blocker
        return "invalid", None, None

    # ---------- 关卡切换 ----------
    def next_level(self):
        self.level_index += 1
        self.reset_level()

    # ---------- 工具 ----------
    def remaining_arrows(self):
        return len(self.arrows)

    def is_solvable(self):
        """
        判断当前关卡是否存在合法消除顺序（贪心验证）：
        反复移除“当前无阻挡”的箭头，若最终能全部移除，则可通关。
        因为移除箭头只会清空路径、不会新增阻挡，贪心是正确且完备的。
        """
        remaining = list(self.arrows)
        changed = True
        while remaining and changed:
            changed = False
            for arrow in list(remaining):
                if self._find_blocker_in(arrow, remaining) is None:
                    remaining.remove(arrow)
                    changed = True
        return not remaining
