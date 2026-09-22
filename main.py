# -*- coding: utf-8 -*-
"""
main.py —— “一箭又一箭” 主程序（pygame 界面与主循环）

运行：python main.py
包含：开始界面 / 选择关卡 / 设置界面 / 游戏界面 / 结果界面，以及飞出与碰撞动画。
所有按钮支持悬停放大。
"""

import os
import math
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "assets", "images")


def load_image(filename, size=None, alpha=True):
    path = os.path.join(IMG_DIR, filename)
    img = pygame.image.load(path)
    img = img.convert_alpha() if alpha else img.convert()
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img


from game import Game, UP, DOWN, LEFT, RIGHT, DIRS
from levels import LEVELS, generate_random_level
import constants as C

FLY_SPEED_FACTOR = 7
BLOCK_TIME = 0.6
BOUNCE_TIME = 0.45
HOVER_SCALE = 1.08
ENDLESS_CLEAR_DURATION = 2000

FRAME_OPENING = (179, 192, 896, 883)
FRAME_INSET = 12

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/Deng.ttf",
]


def get_font(size, bold=False):
    if bold:
        for path in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf"):
            if os.path.exists(path):
                return pygame.font.Font(path, size)
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def arrow_points(cx, cy, d, r):
    if d == RIGHT:
        return [(cx + r, cy), (cx - r * 0.6, cy - r * 0.8), (cx - r * 0.6, cy + r * 0.8)]
    if d == LEFT:
        return [(cx - r, cy), (cx + r * 0.6, cy - r * 0.8), (cx + r * 0.6, cy + r * 0.8)]
    if d == UP:
        return [(cx, cy - r), (cx - r * 0.8, cy + r * 0.6), (cx + r * 0.8, cy + r * 0.6)]
    return [(cx, cy + r), (cx - r * 0.8, cy - r * 0.6), (cx + r * 0.8, cy - r * 0.6)]


def draw_heart(surface, cx, cy, size, color):
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
    """等比缩放到 rect 宽度以内，居中绘制；hover=True 时按 HOVER_SCALE 放大"""
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

        raw_bg = load_image("bg.png", alpha=False)
        w, h = raw_bg.get_size()
        scale = max(C.WINDOW_WIDTH / w, C.WINDOW_HEIGHT / h)
        new_w, new_h = int(w * scale), int(h * scale)
        raw_bg = pygame.transform.smoothscale(raw_bg, (new_w, new_h))
        crop_x = (new_w - C.WINDOW_WIDTH) // 2
        crop_y = (new_h - C.WINDOW_HEIGHT) // 2
        self.bg_img = raw_bg.subsurface((crop_x, crop_y, C.WINDOW_WIDTH, C.WINDOW_HEIGHT)).copy()

        self.title_img = load_image("title.png")
        self.btn_start_img = load_image("btn_start.png")
        self.btn_select_img = load_image("btn_select.png")
        self.btn_settings_img = load_image("btn_settings.png")

        self.board_6_img = load_image("board_6.png")
        self.board_frame_img = load_image("board_frame.png")

        self.arrow_imgs = {
            UP:    load_image("arrow_up.png"),
            DOWN:  load_image("arrow_down.png"),
            LEFT:  load_image("arrow_left.png"),
            RIGHT: load_image("arrow_right.png"),
        }

        self.btn_menu_img = load_image("btn_menu.png")
        self.btn_help_img = load_image("btn_help.png")
        self.btn_hint_img = load_image("btn_hint.png")

        self.hud_panel_img = load_image("hud_panel.png")
        self.heart_img = load_image("heart.png")
        self.icon_heart_img = load_image("icon_heart.png")
        self.icon_arrow_img = load_image("icon_arrow.png")
        self.icon_clock_img = load_image("icon_clock.png")

        self.scene = "start"
        self.result_kind = None
        self.unlocked = 0

        self.volume = 0.5
        self.sound_on = True
        self.dragging_volume = False
        pygame.mixer.music.set_volume(self.volume)
        self.settings_back_scene = "start"

        self.click_sound = None
        sound_path = os.path.join("assets", "sounds", "click.wav")
        if os.path.exists(sound_path):
            try:
                self.click_sound = pygame.mixer.Sound(sound_path)
            except Exception:
                pass

        self.fly_anims = []
        self.block_anims = {}
        self.bounce_anims = {}

        self.show_tutorial = False
        self.help_btn_rect = pygame.Rect(C.WINDOW_WIDTH - 110, 20, 90, 90)
        self.hint_btn_rect = pygame.Rect(C.WINDOW_WIDTH - 190, 130, 170, 35)
        self.hint_target = None
        self.hint_t0 = 0
        self.tutorial_rect = pygame.Rect(0, 0, 560, 360)
        self.tutorial_rect.center = (C.WINDOW_WIDTH // 2, C.WINDOW_HEIGHT // 2)

        self.game_menu_open = False
        self.menu_toggle_btn = pygame.Rect(20, 20, 200, 100)
        self.menu_panel_rect = pygame.Rect(20, 140, 160, 160)
        self.menu_restart_btn = pygame.Rect(30, 150, 140, 40)
        self.menu_settings_btn = pygame.Rect(30, 195, 140, 40)
        self.menu_home_btn = pygame.Rect(30, 240, 140, 40)

        self.start_btn = pygame.Rect(0, 0, 280, 80)
        self.start_btn.center = (C.WINDOW_WIDTH // 2, 340)
        self.select_btn = pygame.Rect(0, 0, 280, 80)
        self.select_btn.center = (C.WINDOW_WIDTH // 2, 440)
        self.settings_btn = pygame.Rect(0, 0, 280, 80)
        self.settings_btn.center = (C.WINDOW_WIDTH // 2, 560)

        self.back_btn = pygame.Rect(30, C.WINDOW_HEIGHT - 70, 120, 44)
        _slider_w = 320
        _slider_x = (C.WINDOW_WIDTH - _slider_w) // 2
        self.volume_slider_rect = pygame.Rect(_slider_x, 320, _slider_w, 20)

        _toggle_w = 320
        _toggle_x = (C.WINDOW_WIDTH - _toggle_w) // 2
        self.sound_toggle_rect = pygame.Rect(_toggle_x, 440, _toggle_w, 60)

        self.again_btn = pygame.Rect(0, 0, 200, 56)
        self.again_btn.center = (C.WINDOW_WIDTH // 2, 360)
        self.result_select_btn = pygame.Rect(0, 0, 200, 56)
        self.result_select_btn.center = (C.WINDOW_WIDTH // 2, 436)
        self.menu_btn = pygame.Rect(0, 0, 200, 56)
        self.menu_btn.center = (C.WINDOW_WIDTH // 2, 512)

        self.level_btns = [pygame.Rect(0, 140 + i * 60, 280, 50) for i in range(len(LEVELS))]
        for b in self.level_btns:
            b.centerx = C.WINDOW_WIDTH // 2

        self.endless_select_btn = pygame.Rect(0, 0, 280, 60)
        self.endless_select_btn.center = (C.WINDOW_WIDTH // 2, 140 + len(LEVELS) * 60 + 70)

        self.endless_clear_t0 = 0

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

            dt = self.clock.get_time()
            self.game.update(dt)
            self.game.tick(dt)
            self.update_anims()

            if self.scene == "game" and self.game.status == "endless_clear":
                if self.endless_clear_t0 == 0:
                    self.endless_clear_t0 = pygame.time.get_ticks()
                elif pygame.time.get_ticks() - self.endless_clear_t0 > ENDLESS_CLEAR_DURATION:
                    self._next_endless_level()

            self.draw()
            pygame.display.flip()
            self.clock.tick(C.FPS)
        pygame.quit()

    def _next_endless_level(self):
        self.game.endless_num += 1
        self.game.levels[self.game.level_index] = generate_random_level(
            level_num=self.game.endless_num
        )
        self.game.reset_level()
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.endless_clear_t0 = 0
        self.hint_target = None

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
            # 滑块判定：上下各扩展 30 像素，更容易点中
            slider_hit = self.volume_slider_rect.inflate(0, 60)
            if slider_hit.collidepoint(pos):
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

            if self.help_btn_rect.collidepoint(pos):
                self.show_tutorial = True
                return

            if self.hint_btn_rect.collidepoint(pos):
                self.hint_target = self.game.find_hint()
                self.hint_t0 = pygame.time.get_ticks()
                return

            if self.game.status == "level_clear":
                self.game.next_level()
                return

            if self.game.status == "endless_clear":
                self._next_endless_level()
                return

            cell = self.cell_from_pos(pos)
            if cell is None:
                return
            r, c = cell
            self.hint_target = None
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
        self.game = Game(LEVELS)
        self.game.level_index = i
        self.game.reset_level()
        self.scene = "game"
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.game_menu_open = False
        self.show_tutorial = (i == 0)
        self.hint_target = None
        self.endless_clear_t0 = 0

    def start_endless(self):
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
        self.hint_target = None
        self.endless_clear_t0 = 0

    def restart_level(self):
        self.game.reset_level()
        self.fly_anims.clear()
        self.block_anims.clear()
        self.bounce_anims.clear()
        self.game_menu_open = False
        self.show_tutorial = (self.game.level_index == 0 and not self.game.endless)
        self.hint_target = None
        self.endless_clear_t0 = 0

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

    # ---------- 通用按钮绘制（带悬停放大）----------
    def draw_hover_rect_button(self, rect, base_color, label, mouse_pos,
                               text_color=(255, 255, 255), font_size=22):
        """文字按钮：悬停时稍微放大 + 颜色变亮"""
        hover = rect.collidepoint(mouse_pos)
        if hover:
            scaled = rect.inflate(10, 8)
        else:
            scaled = rect
        color = base_color
        if hover:
            color = tuple(min(255, c + 30) for c in base_color)
        pygame.draw.rect(self.screen, color, scaled, border_radius=10)
        self.draw_text(label, font_size, text_color, center=scaled.center, bold=True)
        return hover

    def draw_start(self):
        title_w = 560
        raw_w, raw_h = self.title_img.get_size()
        title_h = int(raw_h * title_w / raw_w)
        title_img = pygame.transform.smoothscale(self.title_img, (title_w, title_h))
        title_rect = title_img.get_rect(center=(C.WINDOW_WIDTH // 2, 170))
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
        mouse_pos = pygame.mouse.get_pos()
        self.draw_text("选择关卡", 44, C.TITLE_COLOR,
                       center=(C.WINDOW_WIDTH // 2, 80), bold=True)

        for i, btn in enumerate(self.level_btns):
            locked = i > self.unlocked
            base = C.ARROW_COLOR if not locked else (200, 203, 210)
            label = f"第 {i + 1} 关" + ("（未解锁）" if locked else "")
            self.draw_hover_rect_button(btn, base, label, mouse_pos, font_size=24)

        # 无尽模式按钮
        self.draw_hover_rect_button(self.endless_select_btn, (235, 120, 60),
                                    "无尽模式", mouse_pos, font_size=24)

        # 返回按钮
        self.draw_hover_rect_button(self.back_btn, (150, 155, 165), "返回",
                                    mouse_pos, font_size=22)

    def draw_settings(self):
        mouse_pos = pygame.mouse.get_pos()
        self.draw_text("设置", 50, C.TITLE_COLOR, center=(C.WINDOW_WIDTH // 2, 150), bold=True)

        # 音量滑块：水平居中
        slider_w = 320
        slider_x = (C.WINDOW_WIDTH - slider_w) // 2
        slider_y = 320
        slider_rect = pygame.Rect(slider_x, slider_y, slider_w, 20)

        self.draw_text("音量", 28, C.TEXT_COLOR,
                       center=(C.WINDOW_WIDTH // 2, slider_y - 50))

        pygame.draw.rect(self.screen, (200, 200, 200), slider_rect, border_radius=10)
        fill_width = int(slider_rect.width * self.volume)
        fill_rect = pygame.Rect(slider_rect.x, slider_rect.y,
                                fill_width, slider_rect.height)
        pygame.draw.rect(self.screen, C.ARROW_COLOR, fill_rect, border_radius=10)
        handle_x = slider_rect.x + fill_width
        handle_y = slider_rect.centery
        pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, handle_y), 14)
        pygame.draw.circle(self.screen, C.ARROW_COLOR, (handle_x, handle_y), 14, 3)
        self.draw_text(f"{int(self.volume * 100)}%", 20, C.TEXT_COLOR,
                       center=(slider_rect.right + 40, slider_rect.centery))

        # 音效开关：水平居中
        toggle_w = 320
        toggle_x = (C.WINDOW_WIDTH - toggle_w) // 2
        toggle_y = 440
        toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, 60)

        self.draw_text("音效", 28, C.TEXT_COLOR,
                       center=(C.WINDOW_WIDTH // 2, toggle_y - 50))

        toggle_base = (60, 170, 90) if self.sound_on else (150, 155, 165)
        toggle_text = "开启" if self.sound_on else "关闭"
        self.draw_hover_rect_button(toggle_rect, toggle_base,
                                    toggle_text, mouse_pos, font_size=26)

        # 返回按钮
        self.draw_hover_rect_button(self.back_btn, (150, 155, 165), "返回",
                                    mouse_pos, font_size=22)

    def draw_game(self):
        g = self.game
        mouse_pos = pygame.mouse.get_pos()

        # ---- 左上角：菜单按钮 ----
        if self.btn_menu_img:
            hover = self.menu_toggle_btn.collidepoint(mouse_pos)
            draw_image_fit(self.screen, self.btn_menu_img, self.menu_toggle_btn, hover=hover)
        else:
            self.draw_hover_rect_button(self.menu_toggle_btn, C.ARROW_COLOR,
                                        "菜单", mouse_pos, font_size=18)

        # ---- HUD 底板 ----
        panel_w = 300
        panel_h = 250
        panel_x = 20
        panel_y = 140

        if self.hud_panel_img:
            scaled_panel = pygame.transform.smoothscale(self.hud_panel_img, (panel_w, panel_h))
            self.screen.blit(scaled_panel, (panel_x, panel_y))
        else:
            pygame.draw.rect(self.screen, (255, 240, 210),
                             (panel_x, panel_y, panel_w, panel_h), border_radius=14)

        row1_y = panel_y + 65
        row2_y = panel_y + 125
        row3_y = panel_y + 185

        icon_size = 50
        text_x = panel_x + 100

        # 第一行：生命
        if self.icon_heart_img:
            icon = pygame.transform.smoothscale(self.icon_heart_img, (icon_size, icon_size))
            self.screen.blit(icon, (panel_x + 40, row1_y - icon_size // 2))
        self.draw_text("生命：", 22, (90, 60, 30), topleft=(text_x, row1_y - 14), bold=True)

        heart_size = 34
        heart_start_x = text_x + 60
        for i in range(g.max_hearts):
            hx = heart_start_x + i * (heart_size + 6)
            hy = row1_y - heart_size // 2
            if i < g.hearts:
                if self.heart_img:
                    h = pygame.transform.smoothscale(self.heart_img, (heart_size, heart_size))
                    self.screen.blit(h, (hx, hy))
                else:
                    draw_heart(self.screen, hx + heart_size // 2, hy + heart_size // 2,
                               heart_size, C.HEART_COLOR)
            else:
                draw_heart(self.screen, hx + heart_size // 2, hy + heart_size // 2,
                           heart_size, C.HEART_OFF)

        # 第二行：剩余箭头
        if self.icon_arrow_img:
            icon = pygame.transform.smoothscale(self.icon_arrow_img, (icon_size, icon_size))
            self.screen.blit(icon, (panel_x + 40, row2_y - icon_size // 2))
        self.draw_text(f"剩余箭头：{g.remaining_arrows()}", 22, (90, 60, 30),
                       topleft=(text_x, row2_y - 14), bold=True)

        # 第三行：用时
        if self.icon_clock_img:
            icon = pygame.transform.smoothscale(self.icon_clock_img, (icon_size, icon_size))
            self.screen.blit(icon, (panel_x + 40, row3_y - icon_size // 2))
        elapsed_sec = g.elapsed / 1000.0
        self.draw_text(f"用时：{elapsed_sec:.1f}s", 22, (90, 60, 30),
                       topleft=(text_x, row3_y - 14), bold=True)

        # ---- 右上角：问号 ----
        if self.btn_help_img:
            hover = self.help_btn_rect.collidepoint(mouse_pos)
            draw_image_fit(self.screen, self.btn_help_img, self.help_btn_rect, hover=hover)
        else:
            self.draw_hover_rect_button(self.help_btn_rect, C.ARROW_COLOR,
                                        "?", mouse_pos, font_size=24)

        # ---- 提示按钮 ----
        if self.btn_hint_img:
            hover = self.hint_btn_rect.collidepoint(mouse_pos)
            draw_image_fit(self.screen, self.btn_hint_img, self.hint_btn_rect, hover=hover)
        else:
            self.draw_hover_rect_button(self.hint_btn_rect, (60, 170, 90),
                                        "提示", mouse_pos, font_size=22)

        # ---- 顶部中间：关卡名称 ----
        level_name = g.levels[g.level_index]["name"]
        font = get_font(28, bold=True)
        text_surf = font.render(level_name, True, (90, 60, 30))
        text_rect = text_surf.get_rect(center=(C.WINDOW_WIDTH // 2, 65))

        bg_rect = text_rect.inflate(30, 14)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (255, 240, 210, 200),
                         bg_surf.get_rect(), border_radius=10)
        pygame.draw.rect(bg_surf, (140, 90, 40),
                         bg_surf.get_rect(), 2, border_radius=10)
        self.screen.blit(bg_surf, bg_rect.topleft)
        self.screen.blit(text_surf, text_rect)

        # ---- 棋盘图片 ----
        bx, by = self.board_x, self.board_y
        board_w = g.cols * self.cell
        board_h = g.rows * self.cell

        if self.board_6_img:
            scaled_board = pygame.transform.smoothscale(self.board_6_img, (board_w, board_h))
            self.screen.blit(scaled_board, (bx, by))
        else:
            fallback = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
            fallback.fill((255, 255, 255, 180))
            self.screen.blit(fallback, (bx, by))

        # ---- 棋盘装饰边框 ----
        if self.board_frame_img:
            ox, oy, ow, oh = FRAME_OPENING
            tw = board_w - 2 * FRAME_INSET
            th = board_h - 2 * FRAME_INSET
            sx = tw / ow
            sy = th / oh
            fw = int(self.board_frame_img.get_width() * sx)
            fh = int(self.board_frame_img.get_height() * sy)
            frame = pygame.transform.smoothscale(self.board_frame_img, (fw, fh))
            self.screen.blit(frame, (bx + FRAME_INSET - int(ox * sx), by + FRAME_INSET - int(oy * sy)))

        # ---- 箭头 ----
        now = pygame.time.get_ticks()
        arrow_size = int(self.cell * 0.85)
        for (r, c, d) in g.arrows:
            cx, cy = self.cell_center(r, c)
            if self.hint_target and (r, c) == self.hint_target[:2]:
                elapsed = (now - self.hint_t0) / 1000.0
                cy += int(4 * math.sin(elapsed * 8))
            is_blocked = (r, c) in self.block_anims

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

            # 提示高亮
            if self.hint_target and (r, c) == self.hint_target[:2]:
                elapsed = (now - self.hint_t0) / 1000.0
                pulse = abs(math.sin(elapsed * 5))
                glow_alpha = int(80 + 80 * pulse)
                glow_rect = pygame.Rect(0, 0, self.cell - 8, self.cell - 8)
                glow_rect.center = (cx, cy)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (255, 230, 60, glow_alpha),
                                 glow_surf.get_rect(), border_radius=10)
                self.screen.blit(glow_surf, glow_rect.topleft)
                border_w = 4 + int(3 * pulse)
                pygame.draw.rect(self.screen, (255, 200, 0),
                                 glow_rect, border_w, border_radius=10)

            img = self.arrow_imgs.get(d)
            if img:
                scaled = pygame.transform.smoothscale(img, (arrow_size, arrow_size))
                if is_blocked:
                    scaled = scaled.copy()
                    red_overlay = pygame.Surface((arrow_size, arrow_size), pygame.SRCALPHA)
                    red_overlay.fill((230, 60, 60, 130))
                    scaled.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                rect = scaled.get_rect(center=(cx + offset_x, cy + offset_y))
                self.screen.blit(scaled, rect)
            else:
                color = C.ARROW_BLOCKED if is_blocked else C.ARROW_COLOR
                pts = arrow_points(cx + offset_x, cy + offset_y, d, self.cell * 0.34)
                pygame.draw.polygon(self.screen, color, pts)

        # ---- 飞出动画 ----
        for a in self.fly_anims:
            img = self.arrow_imgs.get(a["d"])
            if img:
                scaled = pygame.transform.smoothscale(img, (arrow_size, arrow_size))
                rect = scaled.get_rect(center=(a["x"], a["y"]))
                self.screen.blit(scaled, rect)
            else:
                pygame.draw.polygon(self.screen, C.ARROW_COLOR,
                                    arrow_points(a["x"], a["y"], a["d"], self.cell * 0.34))

        # ---- 菜单面板 ----
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
                self.draw_hover_rect_button(btn, C.ARROW_COLOR, label,
                                            mouse_pos, font_size=20)

        # ---- 新手引导弹窗 ----
        if self.show_tutorial:
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

        # ---- 过关遮罩 ----
        if g.status == "level_clear":
            overlay = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            stars = 1
            if g.mistakes == 0:
                stars = 3 if g.clicks == g.best_clicks else 2

            star_str = "★" * stars + "☆" * (3 - stars)
            self.draw_text("过关！", 52, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 200), bold=True)
            self.draw_text(star_str, 56, (255, 215, 0),
                           center=(C.WINDOW_WIDTH // 2, 280), bold=True)

            elapsed_sec = g.elapsed / 1000.0
            self.draw_text(f"用时：{elapsed_sec:.1f}s", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 360))
            self.draw_text(f"点击：{g.clicks} / 最佳：{g.best_clicks}", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 400))
            self.draw_text(f"失误：{g.mistakes}", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 440))
            self.draw_text("点击进入下一关", 22, (200, 200, 200),
                           center=(C.WINDOW_WIDTH // 2, 510))

        # ---- 无尽模式结算 ----
        if g.status == "endless_clear":
            overlay = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            stars = 1
            if g.mistakes == 0:
                stars = 3 if g.clicks == g.best_clicks else 2

            star_str = "★" * stars + "☆" * (3 - stars)
            self.draw_text(f"第 {self.game.endless_num} 关通过！", 44, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 180), bold=True)
            self.draw_text(star_str, 56, (255, 215, 0),
                           center=(C.WINDOW_WIDTH // 2, 260), bold=True)

            elapsed_sec = g.elapsed / 1000.0
            self.draw_text(f"用时：{elapsed_sec:.1f}s", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 340))
            self.draw_text(f"点击：{g.clicks} / 最佳：{g.best_clicks}", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 380))
            self.draw_text(f"失误：{g.mistakes}", 24, (255, 255, 255),
                           center=(C.WINDOW_WIDTH // 2, 420))
            self.draw_text("点击进入下一关", 22, (200, 200, 200),
                           center=(C.WINDOW_WIDTH // 2, 490))

    def draw_result(self):
        mouse_pos = pygame.mouse.get_pos()

        if self.result_kind == "win":
            self.draw_text("恭喜通关！", 56, (60, 170, 90),
                           center=(C.WINDOW_WIDTH // 2, 190), bold=True)
            self.draw_text("你成功清除了所有关卡", 24, C.TEXT_COLOR,
                           center=(C.WINDOW_WIDTH // 2, 270))
        else:
            self.draw_text("游戏失败", 56, C.ARROW_BLOCKED,
                           center=(C.WINDOW_WIDTH // 2, 190), bold=True)
            self.draw_text("爱心耗尽，再来一次吧", 24, C.TEXT_COLOR,
                           center=(C.WINDOW_WIDTH // 2, 270))
            self.draw_text(f"用时：{self.game.elapsed/1000:.1f}s  失误：{self.game.mistakes}",
                           20, C.TEXT_COLOR, center=(C.WINDOW_WIDTH // 2, 310))

        self.draw_hover_rect_button(self.again_btn, C.ARROW_COLOR,
                                    "再玩一次", mouse_pos, font_size=26)
        self.draw_hover_rect_button(self.result_select_btn, (150, 155, 165),
                                    "选择关卡", mouse_pos, font_size=26)
        self.draw_hover_rect_button(self.menu_btn, (150, 155, 165),
                                    "返回主菜单", mouse_pos, font_size=26)


if __name__ == "__main__":
    App().run()