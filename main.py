# -*- coding: utf-8 -*-
"""
main.py —— “一箭又一箭” 主程序（pygame 界面与主循环）

运行：python main.py
包含：开始界面 / 选择关卡 / 设置界面 / 游戏界面 / 结果界面，以及飞出与碰撞动画。
"""

import os
import math
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "assets", "images")


def load_image(filename, size=None, alpha=True):
    """加载图片，可选缩放；alpha=True 保留透明通道"""
    path = os.path.join(IMG_DIR, filename)
    img = pygame.image.load(path)
    img = img.convert_alpha() if alpha else img.convert()
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img


from game import Game, UP, DOWN, LEFT, RIGHT, DIRS
from levels import LEVELS, generate_random_level
import constants as C

# 飞出速度系数（格/秒）
FLY_SPEED_FACTOR = 7
# 碰撞抖动时长（秒）
BLOCK_TIME = 0.6
# 碰撞弹回动画时长（秒）
BOUNCE_TIME = 0.45

# 悬停放大倍数
HOVER_SCALE = 1.08

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


def draw_heart(surface, cx, cy, size, color):
    """在 (cx, cy) 画一颗爱心，size 为整体宽度"""
    w = size
    r = max(2, w // 4)
    pygame.draw.circle(surface, color, (cx - r, cy - r), r)
    pygame.draw.circle(surface, color, (cx + r, cy - r), r)
    pygame.draw.polygon(surface, color, [
        (cx - w // 2, cy - r // 2),
        (cx + w // 2, cy - r // 2),
        (cx, cy + w // 2),
    ])


def draw_image_fit(surface, img, rect, hover=False):
    """
    把图片等比缩放到 rect 宽度以内，居中绘制到 rect。
    hover=True 时按 HOVER_SCALE 放大。
    """
    iw, ih = img.get_size()
    scale = rect.width / iw
    if hover:
        scale *= HOVER_SCALE
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    scaled = pygame.transform.smoothscale(img, (new_w, new_h))
    x = rect.centerx - new_w // 2
    y = rect.centery - new_h // 2
    surface.blit(scaled, (x, y))


class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        self.game = Game(LEVELS)

        # 加载背景图
        raw_bg = load_image("bg.png", alpha=False)
        w, h = raw_bg.get_size()
        scale = max(C.WINDOW_WIDTH / w, C.WINDOW_HEIGHT / h)
        new_w, new_h = int(w * scale), int(h * scale)
        raw_bg = pygame.transform.smoothscale(raw_bg, (new_w, new_h))
        crop_x = (new_w - C.WINDOW_WIDTH) // 2
        crop_y = (new_h - C.WINDOW_HEIGHT) // 2
        self.bg_img = raw_bg.subsurface((crop_x, crop_y, C.WINDOW_WIDTH, C.WINDOW_HEIGHT)).copy()

        # 标题和按钮图
        self.title_img = load_image("title.png")
        self.btn_start_img = load_image("btn_start.png")
        self.btn_select_img = load_image("btn_select.png")
        self.btn_settings_img = load_image("btn_settings.png")

        self.scene = "start"
        self.result_kind = None
        self.unlocked = 0

        # 音频
        self.volume = 0.5
        self.sound_on = True
        self.dragging_volume = False
        pygame.mixer.music.set_volume(self.volume)

        self.settings_back_scene = "start"

        # 点击音效
        self.click_sound = None
        sound_path = os.path.join("assets", "sounds", "click.wav")
        if os.path.exists(sound_path):
            try:
                self.click_sound = pygame.mixer.Sound(sound_path)
            except Exception:
                pass

        # 动画
        self.fly_anims = []
        self.block_anims = {}
        self.bounce_anims = {}

        # 新手引导
        self.show_tutorial = False
        self.help_btn_rect = pygame.Rect(C.WINDOW_WIDTH - 152, 20, 42, 42)
        self.tutorial_rect = pygame.Rect(0, 0, 560, 360)
        self.tutorial_rect.center = (C.WINDOW_WIDTH // 2, C.WINDOW_HEIGHT // 2)

        # 游戏内菜单
        self.game_menu_open = False
        self.menu_toggle_btn = pygame.Rect(C.WINDOW_WIDTH - 100, 20, 80, 42)
        self.menu_panel_rect = pygame.Rect(C.WINDOW_WIDTH - 180, 70, 160, 160)
        self.menu_restart_btn = pygame.Rect(C.WINDOW_WIDTH - 170, 80, 140, 40)
        self.menu_settings_btn = pygame.Rect(C.WINDOW_WIDTH - 170, 125, 140, 40)
        self.menu_home_btn = pygame.Rect(C.WINDOW_WIDTH - 170, 170, 140, 40)

        # 主菜单三个按钮
        self.start_btn = pygame.Rect(0, 0, 280, 80)
        self.start_btn.center = (C.WINDOW_WIDTH // 2, 340)
        self.select_btn = pygame.Rect(0, 0, 280, 80)
        self.select_btn.center = (C.WINDOW_WIDTH // 2, 440)
        self.settings_btn = pygame.Rect(0, 0, 280, 80)
        self.settings_btn.center = (C.WINDOW_WIDTH // 2, 540)

        self.back_btn = pygame.Rect(30, C.WINDOW_HEIGHT - 70, 120, 44)

        self.volume_slider_rect = pygame.Rect(200, 320, 320, 20)
        self.sound_toggle_rect = pygame.Rect(200, 400, 320, 60)

        self.again_btn = pygame.Rect(0, 0, 200, 56)
        self.again_btn.center = (C.WINDOW_WIDTH // 2, 360)
        self.result_select_btn = pygame.Rect(0, 0, 200, 56)
        self.result_select_btn.center = (C.WINDOW_WIDTH // 2, 436)
        self.menu_btn = pygame.Rect(0, 0, 200, 56)
        self.menu_btn.center = (C.WINDOW_WIDTH // 2, 512)

        # 关卡按钮
        self.level_btns = [pygame.Rect(0, 140 + i * 60, 280, 50) for i in range(len(LEVELS))]
        for b in self.level_btns:
            b.centerx = C.WINDOW_WIDTH // 2

        # 选择关卡页的“无尽模式”按钮（与关卡列表拉开间距）
        self.endless_select_btn = pygame.Rect(0, 0, 280, 60)
        self.endless_select_btn.center = (C.WINDOW_WIDTH // 2, 140 + len(LEVELS) * 60 + 70)

    # ---------- 坐标换算 ----------
    @property
    def cell(self):
        avail_w = C.WINDOW_WIDTH - 2 * C.BOARD_MARGIN
        avail_h = C.WINDOW_HEIGHT - C.BOARD_TOP - C.BOARD_MARGIN
        return min(C.MAX_CELL, avail_w // self.game.cols, avail_h // self.game.rows)

    @property
    def board_x(self):
        return (C.WINDOW_WIDTH - self.game.cols * self.cell) // 2

    @property
    def board_y(self):
        return C.BOARD_TOP

    def cell_center(self, r, c):
        return (self.board_x + c * self.cell + self.cell // 2,
                self.board_y + r * self.cell + self.cell // 2)

    def cell_from_pos(self, pos):
        x, y = pos
        c = (x - self.board_x) // self.cell
        r = (y - self.board_y) // self.cell
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
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_motion(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.handle_release()

            dt = self.clock.get_time()   # 上一帧耗时（毫秒）
            self.game.update(dt)         # 处理无尽模式延迟换关
            self.update_anims()
            self.draw()
            pygame.display.flip()
            self.clock.tick(C.FPS)
        pygame.quit()

    # ---------- 点击分发 ----------
    def handle_click(self, pos):
        if self.scene == "start":
            if self.start_btn.collidepoint(pos):
                self.start_level(0)
            elif self.select_btn.collidepoint(pos):
                self.scene = "select"
            elif self.settings_btn.collidepoint(pos):
                self.settings_back_scene = "start"
                self.scene = "settings"
            return

        if self.scene == "settings":
            if self.back_btn.collidepoint(pos):
                self.scene = self.settings_back_scene
                if self.scene == "game":
                    self.game_menu_open = False
                return
            if self.volume_slider_rect.collidepoint(pos):
                self.dragging_volume = True
                click_x = pos[0] - self.volume_slider_rect.x
                ratio = max(0.0, min(1.0, click_x / self.volume_slider_rect.width))
                self.volume = ratio
                pygame.mixer.music.set_volume(self.volume)
                return
            if self.sound_toggle_rect.collidepoint(pos):
                self.sound_on = not self.sound_on
                return
            return

        if self.scene == "select":
            if self.back_btn.collidepoint(pos):
                self.scene = "start"
                return
            if self.endless_select_btn.collidepoint(pos):
                self.start_endless()
                return
            for i, btn in enumerate(self.level_btns):
                if btn.collidepoint(pos) and i <= self.unlocked:
                    self.start_level(i)
                    return
            return

        if self.scene == "result":
            if self.again_btn.collidepoint(pos):
                self.start_level(0 if self.result_kind == "win" else self.game.level_index)
            elif self.result_select_btn.collidepoint(pos):
                self.scene = "select"
            elif self.menu_btn.collidepoint(pos):
                self.scene = "start"
            return

        if self.scene == "game":
            if self.show_tutorial:
                self.show_tutorial = False
                return

            if self.game_menu_open:
                if self.menu_restart_btn.collidepoint(pos):
                    self.game_menu_open = False
                    self.restart_level()
                    return
                elif self.menu_settings_btn.collidepoint(pos):
                    self.game_menu_open = False
                    self.settings_back_scene = "game"
                    self.scene = "settings"
                    return
                elif self.menu_home_btn.collidepoint(pos):
                    self.game_menu_open = False
                    self.scene = "start"
                    return
                else:
                    self.game_menu_open = False
                    return

            if self.menu_toggle_btn.collidepoint(pos):
                self.game_menu_open = True
                return

            if self.game.level_index == 0 and not self.game.endless and self.help_btn_rect.collidepoint(pos):
                self.show_tutorial = True
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
                self.play_sound()
                self.fly_anims.append({"r": r, "c": c, "d": arrow[2],
                                       "t0": pygame.time.get_ticks(), "x": 0, "y": 0})
            elif result == "blocked":
                self.play_sound()
                self.block_anims[(r, c)] = pygame.time.get_ticks()
                if arrow and blocker:
                    self.bounce_anims[(r, c)] = {
                        "t0": pygame.time.get_ticks(),
                        "d": arrow[2],
                        "blocker": blocker,
                    }

            if self.game.status == "level_clear":
                self.unlocked = max(self.unlocked, self.game.level_index + 1)
            elif self.game.status == "win":
                self.unlocked = len(LEVELS) - 1
                self.scene = "result"
                self.result_kind = "win"
            elif self.game.status == "game_over":
                self.scene = "result"
                self.result_kind = "game_over"

    def handle_motion(self, pos):
        if self.scene == "settings" and self.dragging_volume:
            click_x = pos[0] - self.volume_slider_rect.x
            ratio = max(0.0, min(1.0, click_x / self.volume_slider_rect.width))
            self.volume = ratio
            pygame.mixer.music.set_volume(self.volume)

    def handle_release(self):
        self.dragging_volume = False

    def play_sound(self):
        if self.sound_on and self.click_sound:
            self.click_sound.play()

    def start_level(self, i):
        """从第 i 关开始游戏"""
        self.game = Game(LEVELS)
        self.game.level_index = i
        self.game.reset_level()
        self.scene = "game"
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.game_menu_open = False
        self.show_tutorial = (i == 0)

    def start_endless(self):
        """启动无尽模式：随机生成 8×8 关卡，清空后自动生成下一关"""
        self.game = Game([generate_random_level(level_num=1)])
        self.game.level_index = 0
        self.game.endless_num = 1
        self.game.reset_level()
        self.scene = "game"
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.game_menu_open = False
        self.show_tutorial = False

    def restart_level(self):
        self.game.reset_level()
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.game_menu_open = False
        if self.game.level_index == 0 and not self.game.endless:
            self.show_tutorial = True

    # ---------- 动画更新 ----------
    def update_anims(self):
        now = pygame.time.get_ticks()
        alive = []
        for a in self.fly_anims:
            dt = (now - a["t0"]) / 1000.0
            dist = dt * self.cell * FLY_SPEED_FACTOR
            dr, dc = DIRS[a["d"]]
            cx, cy = self.cell_center(a["r"], a["c"])
            a["x"] = cx + dc * dist
            a["y"] = cy + dr * dist
            left = self.board_x - self.cell
            right = self.board_x + self.game.cols * self.cell + self.cell
            top = self.board_y - self.cell
            bottom = self.board_y + self.game.rows * self.cell + self.cell
            if not (left <= a["x"] <= right and top <= a["y"] <= bottom):
                continue
            alive.append(a)
        self.fly_anims = alive

        for key in list(self.block_anims.keys()):
            if (now - self.block_anims[key]) / 1000.0 >= BLOCK_TIME:
                del self.block_anims[key]

        for key in list(self.bounce_anims.keys()):
            info = self.bounce_anims[key]
            if (now - info["t0"]) / 1000.0 >= BOUNCE_TIME:
                del self.bounce_anims[key]

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.blit(self.bg_img, (0, 0))
        if self.scene == "start":
            self.draw_start()
        elif self.scene == "select":
            self.draw_select()
        elif self.scene == "settings":
            self.draw_settings()
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
        title_w = 560
        raw_w, raw_h = self.title_img.get_size()
        title_h = int(raw_h * title_w / raw_w)
        title_img = pygame.transform.smoothscale(self.title_img, (title_w, title_h))
        title_rect = title_img.get_rect(center=(C.WINDOW_WIDTH // 2, 150))
        self.screen.blit(title_img, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        for img, rect in [
            (self.btn_start_img, self.start_btn),
            (self.btn_select_img, self.select_btn),
            (self.btn_settings_img, self.settings_btn),
        ]:
            hover = rect.collidepoint(mouse_pos)
            draw_image_fit(self.screen, img, rect, hover=hover)

    def draw_select(self):
        self.draw_text("选择关卡", 44, C.TITLE_COLOR, center=(C.WINDOW_WIDTH // 2, 80), bold=True)
        for i, btn in enumerate(self.level_btns):
            locked = i > self.unlocked
            color = C.ARROW_COLOR if not locked else (200, 203, 210)
            pygame.draw.rect(self.screen, color, btn, border_radius=10)
            label = f"第 {i + 1} 关" + ("（未解锁）" if locked else "")
            self.draw_text(label, 24, (255, 255, 255), center=btn.center, bold=True)

        # 无尽模式按钮（橙色）
        pygame.draw.rect(self.screen, (235, 120, 60), self.endless_select_btn, border_radius=10)
        self.draw_text("无尽模式", 24, (255, 255, 255), center=self.endless_select_btn.center, bold=True)

        pygame.draw.rect(self.screen, (150, 155, 165), self.back_btn, border_radius=8)
        self.draw_text("返回", 22, (255, 255, 255), center=self.back_btn.center)

    def draw_settings(self):
        self.draw_text("设置", 50, C.TITLE_COLOR, center=(C.WINDOW_WIDTH // 2, 150), bold=True)

        self.draw_text("音量", 28, C.TEXT_COLOR, center=(140, 330))
        pygame.draw.rect(self.screen, (200, 200, 200), self.volume_slider_rect, border_radius=10)
        fill_width = int(self.volume_slider_rect.width * self.volume)
        fill_rect = pygame.Rect(self.volume_slider_rect.x, self.volume_slider_rect.y,
                                fill_width, self.volume_slider_rect.height)
        pygame.draw.rect(self.screen, C.ARROW_COLOR, fill_rect, border_radius=10)
        handle_x = self.volume_slider_rect.x + fill_width
        handle_y = self.volume_slider_rect.centery
        pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, handle_y), 14)
        pygame.draw.circle(self.screen, C.ARROW_COLOR, (handle_x, handle_y), 14, 3)
        self.draw_text(f"{int(self.volume * 100)}%", 20, C.TEXT_COLOR,
                       center=(self.volume_slider_rect.right + 60, 330))

        self.draw_text("音效", 28, C.TEXT_COLOR, center=(140, 430))
        toggle_color = (60, 170, 90) if self.sound_on else (150, 155, 165)
        pygame.draw.rect(self.screen, toggle_color, self.sound_toggle_rect, border_radius=10)
        toggle_text = "开启" if self.sound_on else "关闭"
        self.draw_text(toggle_text, 26, (255, 255, 255), center=self.sound_toggle_rect.center, bold=True)

        pygame.draw.rect(self.screen, (150, 155, 165), self.back_btn, border_radius=8)
        self.draw_text("返回", 22, (255, 255, 255), center=self.back_btn.center)

    def draw_game(self):
        g = self.game
        self.draw_text(g.levels[g.level_index]["name"], 28, C.TITLE_COLOR, topleft=(20, 20), bold=True)
        self.draw_text(f"剩余箭头：{g.remaining_arrows()}", 20, C.TEXT_COLOR, topleft=(20, 72))
        self.draw_text("生命：", 20, C.TEXT_COLOR, topleft=(20, 102))
        for i in range(g.max_hearts):
            color = C.HEART_COLOR if i < g.hearts else C.HEART_OFF
            draw_heart(self.screen, 75 + i * 34 + 13, 113, 26, color)

        bx, by = self.board_x, self.board_y
        board_overlay = pygame.Surface((g.cols * self.cell, g.rows * self.cell), pygame.SRCALPHA)
        board_overlay.fill((255, 255, 255, 180))
        self.screen.blit(board_overlay, (bx, by))

        for r in range(g.rows):
            for c in range(g.cols):
                rect = pygame.Rect(bx + c * self.cell, by + r * self.cell, self.cell, self.cell)
                pygame.draw.rect(self.screen, (200, 210, 225), rect, 1)

        now = pygame.time.get_ticks()
        for (r, c, d) in g.arrows:
            cx, cy = self.cell_center(r, c)
            color = C.ARROW_COLOR
            is_blocked = (r, c) in self.block_anims
            if is_blocked:
                color = C.ARROW_BLOCKED

            offset_x, offset_y = 0, 0
            if (r, c) in self.bounce_anims:
                info = self.bounce_anims[(r, c)]
                if "blocker" not in info:
                    del self.bounce_anims[(r, c)]
                else:
                    elapsed = (now - info["t0"]) / 1000.0
                    progress = min(1.0, elapsed / BOUNCE_TIME)
                    if progress < 0.3:
                        bounce = progress / 0.3
                    else:
                        bounce = 1 - (progress - 0.3) / 0.7
                    br, bc = info["blocker"]
                    steps = max(abs(br - r), abs(bc - c))
                    max_dist = self.cell * max(0.0, steps - 0.5)
                    dist = bounce * max_dist
                    dr, dc = DIRS[info["d"]]
                    offset_x = dc * dist
                    offset_y = dr * dist

            pts = arrow_points(cx + offset_x, cy + offset_y, d, self.cell * 0.34)

            if is_blocked:
                outline = arrow_points(cx + offset_x, cy + offset_y, d, self.cell * 0.46)
                pygame.draw.polygon(self.screen, (255, 255, 255), outline)

            pygame.draw.polygon(self.screen, color, pts)

        for a in self.fly_anims:
            pygame.draw.polygon(self.screen, C.ARROW_COLOR, arrow_points(a["x"], a["y"], a["d"], self.cell * 0.34))

        # 菜单
        pygame.draw.rect(self.screen, C.ARROW_COLOR, self.menu_toggle_btn, border_radius=8)
        self.draw_text("菜单", 18, (255, 255, 255), center=self.menu_toggle_btn.center, bold=True)

        if self.game_menu_open:
            shadow_rect = self.menu_panel_rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(self.screen, (180, 185, 195), shadow_rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 255, 255), self.menu_panel_rect, border_radius=10)
            pygame.draw.rect(self.screen, C.GRID_LINE, self.menu_panel_rect, 2, border_radius=10)

            for btn, label in [
                (self.menu_restart_btn, "重新开始"),
                (self.menu_settings_btn, "设置"),
                (self.menu_home_btn, "返回主菜单"),
            ]:
                pygame.draw.rect(self.screen, C.ARROW_COLOR, btn, border_radius=6)
                self.draw_text(label, 20, (255, 255, 255), center=btn.center)

        # 新手引导（仅普通模式第 1 关）
        if g.level_index == 0 and not g.endless:
            if not self.show_tutorial:
                pygame.draw.rect(self.screen, C.ARROW_COLOR, self.help_btn_rect, border_radius=8)
                self.draw_text("?", 24, (255, 255, 255), center=self.help_btn_rect.center, bold=True)
            else:
                overlay = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 170))
                self.screen.blit(overlay, (0, 0))

                pygame.draw.rect(self.screen, (255, 255, 255), self.tutorial_rect, border_radius=15)
                pygame.draw.rect(self.screen, C.ARROW_COLOR, self.tutorial_rect, 3, border_radius=15)

                self.draw_text("新手引导", 36, C.TITLE_COLOR,
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.y + 60), bold=True)
                self.draw_text("1. 点击箭头，箭头会沿其方向飞出棋盘。", 22, C.TEXT_COLOR,
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.y + 130))
                self.draw_text("2. 若前方有其它箭头阻挡，则无法飞出，", 22, C.TEXT_COLOR,
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.y + 180))
                self.draw_text("    并会消耗一颗爱心（生命）。", 22, C.TEXT_COLOR,
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.y + 210))
                self.draw_text("3. 清空所有箭头即可过关！", 22, C.TEXT_COLOR,
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.y + 260))

                self.draw_text("点击屏幕任意位置收起（变为问号）", 18, (150, 155, 165),
                               center=(self.tutorial_rect.centerx, self.tutorial_rect.bottom - 30))

        # 过关遮罩
        if g.status == "level_clear":
            overlay = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            self.screen.blit(overlay, (0, 0))
            self.draw_text("过关！点击进入下一关", 40, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, C.WINDOW_HEIGHT // 2), bold=True)

    def draw_result(self):
        if self.result_kind == "win":
            self.draw_text("恭喜通关！", 56, (60, 170, 90), center=(C.WINDOW_WIDTH // 2, 190), bold=True)
            self.draw_text("你成功清除了所有关卡", 24, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 270))
        else:
            self.draw_text("游戏失败", 56, C.ARROW_BLOCKED, center=(C.WINDOW_WIDTH // 2, 190), bold=True)
            self.draw_text("爱心耗尽，再来一次吧", 24, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 270))

        pygame.draw.rect(self.screen, C.ARROW_COLOR, self.again_btn, border_radius=10)
        self.draw_text("再玩一次", 26, (255, 255, 255), center=self.again_btn.center, bold=True)
        pygame.draw.rect(self.screen, (150, 155, 165), self.result_select_btn, border_radius=10)
        self.draw_text("选择关卡", 26, (255, 255, 255), center=self.result_select_btn.center)
        pygame.draw.rect(self.screen, (150, 155, 165), self.menu_btn, border_radius=10)
        self.draw_text("返回主菜单", 26, (255, 255, 255), center=self.menu_btn.center)


if __name__ == "__main__":
    App().run()