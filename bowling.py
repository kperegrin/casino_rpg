import math

import pygame

from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import Button, draw_hud, draw_panel, draw_result_screen, text

PIN_LAYOUT = [
    (0, 0),
    (-18, -24), (18, -24),
    (-36, -48), (0, -48), (36, -48),
    (-54, -72), (-18, -72), (18, -72), (54, -72),
]


class BowlingGame:
    MIN_BET = 25
    FRAMES = 5

    def __init__(self, config=None):
        self.config = config or {"mode": "solo"}
        self.state = "aim"
        self.bet = 50
        self.frame_index = 1
        self.total_score = 0
        self.current_knock = 0
        self.chips_delta = 0
        self.result_msg = ""
        self.power_meter = 0.15
        self.aim_meter = 0.0
        self.power_dir = 1
        self.aim_dir = 1
        self.ball_progress = 0.0
        self.ball_x = 0.0
        self.ball_curve = 0.0
        self._lane = pygame.Rect(SCREEN_W // 2 - 130, 90, 260, 500)
        self._throw_btn = Button(SCREEN_W // 2 - 80, SCREEN_H - 76, 160, 46,
                                 "LANZAR", color=(30, 80, 30))
        self._back_btn = Button(30, SCREEN_H - 70, 100, 40, "◀ SORTIR",
                                color=(60, 20, 20), font="small")
        self._bet_btns = [
            Button(SCREEN_W // 2 - 175 + i * 90, SCREEN_H - 124, 72, 32,
                   f"+{v}", color=(40, 40, 90), font="small")
            for i, v in enumerate([25, 50, 100, 200])
        ]
        self._bet_values = [25, 50, 100, 200]

    def _reset_frame(self):
        self.state = "aim"
        self.current_knock = 0
        self.power_meter = 0.15
        self.aim_meter = 0.0
        self.power_dir = 1
        self.aim_dir = 1
        self.ball_progress = 0.0
        self.ball_x = 0.0
        self.ball_curve = 0.0

    def _start_series(self):
        if STATE["chips"] < self.bet:
            return
        STATE["chips"] -= self.bet
        self.total_score = 0
        self.frame_index = 1
        self.chips_delta = 0
        self._reset_frame()

    def _throw_ball(self):
        self.state = "rolling"
        self.ball_progress = 0.0
        self.ball_x = self.aim_meter * 84
        self.ball_curve = (0.5 - self.power_meter) * 0.45

    def _resolve_throw(self):
        accuracy = max(0.0, 1.0 - abs(self.aim_meter) * 1.25)
        power_score = 1.0 - abs(self.power_meter - 0.72) * 1.5
        curve_penalty = abs(self.ball_curve) * 0.4
        quality = max(0.0, accuracy * 0.65 + power_score * 0.45 - curve_penalty)
        knocked = max(0, min(10, int(round(quality * 10))))

        if quality > 0.93:
            knocked = 10
        elif quality > 0.82:
            knocked = max(knocked, 8)

        self.current_knock = knocked
        self.total_score += knocked

        if self.frame_index >= self.FRAMES:
            payout = self.bet + int(self.total_score * self.bet * 0.35)
            if self.total_score >= 45:
                payout += self.bet * 2
                self.result_msg = "Perfecte! Torneig dominat"
            elif self.total_score >= 36:
                payout += self.bet
                self.result_msg = "Gran sèrie!"
            elif self.total_score >= 25:
                self.result_msg = "Bona tanda"
            else:
                payout = int(self.bet * 0.5)
                self.result_msg = "La pista s'ha resistit"

            STATE["chips"] += payout
            self.chips_delta = payout - self.bet
            if self.chips_delta > 0:
                STATE["wins"] += 1
            else:
                STATE["losses"] += 1
            self.state = "result"
            return

        self.frame_index += 1
        self.state = "frame_result"

    def handle_event(self, event):
        if self._back_btn.clicked(event):
            return "exit"

        if self.state == "result":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "setup"
            return None

        if self.state == "setup":
            for button, value in zip(self._bet_btns, self._bet_values):
                if button.clicked(event):
                    self.bet = min(STATE["chips"], self.bet + value)
            if self._throw_btn.clicked(event):
                self._start_series()
            return None

        if self.state == "aim":
            if self._throw_btn.clicked(event) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                self._throw_ball()
        elif self.state == "frame_result":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self._reset_frame()
        return None

    def update(self, dt):
        if self.state == "setup":
            pass
        elif self.state == "aim":
            self.power_meter += dt * 0.95 * self.power_dir
            if self.power_meter >= 1.0:
                self.power_meter = 1.0
                self.power_dir = -1
            elif self.power_meter <= 0.0:
                self.power_meter = 0.0
                self.power_dir = 1

            self.aim_meter += dt * 1.35 * self.aim_dir
            if self.aim_meter >= 1.0:
                self.aim_meter = 1.0
                self.aim_dir = -1
            elif self.aim_meter <= -1.0:
                self.aim_meter = -1.0
                self.aim_dir = 1
        elif self.state == "rolling":
            self.ball_progress = min(1.0, self.ball_progress + dt * 0.85)
            lateral = math.sin(self.ball_progress * math.pi) * self.ball_curve * 80
            self.ball_x += lateral * dt
            if self.ball_progress >= 1.0:
                self._resolve_throw()

        self._throw_btn.update(dt)
        self._back_btn.update(dt)
        for button in self._bet_btns:
            button.update(dt)

    def draw(self, surf):
        surf.fill((16, 12, 8))
        text(surf, "BOWLING ROYALE", "big", C["neon_gold"],
             SCREEN_W // 2, 38, anchor="center")
        text(surf, "Clava potencia y centro para tirar todos los bolos",
             "small", C["ui_sub"], SCREEN_W // 2, 70, anchor="center")

        self._draw_lane(surf)
        self._draw_side_panel(surf)

        if self.state == "setup":
            panel = pygame.Rect(SCREEN_W // 2 - 220, SCREEN_H - 190, 440, 90)
            draw_panel(surf, panel, alpha=225, radius=12)
            text(surf, "APUESTA DEL TORNEO", "small", C["ui_sub"],
                 panel.centerx, panel.y + 16, anchor="center")
            text(surf, f"{self.bet} chips · 5 lanzamientos", "med", C["chips"],
                 panel.centerx, panel.y + 44, anchor="center")
            for button in self._bet_btns:
                button.draw(surf)
            self._throw_btn.label = "EMPEZAR"
            self._throw_btn.draw(surf)
        elif self.state == "aim":
            self._throw_btn.label = "LANZAR"
            self._throw_btn.draw(surf)
            text(surf, "ESPACIO para lanzar", "small", C["ui_text"],
                 SCREEN_W // 2, SCREEN_H - 108, anchor="center")
        elif self.state == "frame_result":
            panel = pygame.Rect(SCREEN_W // 2 - 180, SCREEN_H - 134, 360, 74)
            draw_panel(surf, panel, alpha=220, radius=12)
            text(surf, f"Tirada: {self.current_knock} bolos", "med", C["ui_green"],
                 panel.centerx, panel.y + 20, anchor="center")
            text(surf, "Pulsa ESPACIO para la siguiente", "small", C["ui_sub"],
                 panel.centerx, panel.y + 46, anchor="center")
        elif self.state == "result":
            draw_result_screen(surf, self.result_msg, self.chips_delta)

        self._back_btn.draw(surf)
        draw_hud(surf)

    def _draw_lane(self, surf):
        lane = self._lane
        pygame.draw.rect(surf, (126, 90, 54), lane, border_radius=12)
        pygame.draw.rect(surf, (196, 158, 110), lane.inflate(-24, -18), border_radius=10)
        pygame.draw.rect(surf, C["ui_border"], lane, 4, border_radius=12)

        for index in range(1, 8):
            y = lane.bottom - index * (lane.h // 8)
            pygame.draw.line(surf, (215, 195, 160), (lane.x + 22, y), (lane.right - 22, y), 1)

        pins_center = (lane.centerx, lane.y + 120)
        standing = 10 if self.state in ("setup", "aim", "rolling") else max(0, 10 - self.current_knock)
        for pin_index, (px, py) in enumerate(PIN_LAYOUT):
            color = (245, 245, 245) if pin_index < standing else (150, 90, 90)
            self._draw_pin(surf, pins_center[0] + px, pins_center[1] - py, color)

        if self.state in ("aim", "rolling", "frame_result"):
            bx = lane.centerx + int(self.ball_x)
            by = lane.bottom - 42 - int(self.ball_progress * 360)
            size = max(18, 28 - int(self.ball_progress * 8))
            pygame.draw.circle(surf, (40, 40, 70), (bx, by), size)
            pygame.draw.circle(surf, (100, 120, 210), (bx - 6, by - 6), max(3, size // 4))

        self._draw_meter(surf, lane.right + 32, lane.bottom - 220, "POTENCIA", self.power_meter, (255, 180, 70))
        self._draw_meter(surf, lane.x - 62, lane.bottom - 220, "PUNTERÍA", (self.aim_meter + 1) / 2, (90, 210, 255))

    def _draw_side_panel(self, surf):
        panel = pygame.Rect(SCREEN_W // 2 + 190, 120, 250, 170)
        draw_panel(surf, panel, alpha=220, radius=12)
        text(surf, f"FRAME {self.frame_index}/{self.FRAMES}", "med", C["ui_text"],
             panel.centerx, panel.y + 20, anchor="center")
        text(surf, f"Puntuación: {self.total_score}", "med", C["chips"],
             panel.centerx, panel.y + 60, anchor="center")
        text(surf, f"Última: {self.current_knock}", "small", C["ui_sub"],
             panel.centerx, panel.y + 94, anchor="center")
        text(surf, f"Apuesta: {self.bet}", "small", C["ui_sub"],
             panel.centerx, panel.y + 124, anchor="center")

    def _draw_meter(self, surf, x, y, label, value, color):
        rect = pygame.Rect(x, y, 28, 180)
        pygame.draw.rect(surf, (30, 24, 24), rect, border_radius=8)
        pygame.draw.rect(surf, C["ui_border"], rect, 2, border_radius=8)
        fill_h = int((rect.h - 8) * max(0.0, min(1.0, value)))
        pygame.draw.rect(surf, color,
                         (rect.x + 4, rect.bottom - 4 - fill_h, rect.w - 8, fill_h),
                         border_radius=6)
        text(surf, label, "tiny", C["ui_sub"], rect.centerx, rect.y - 18, anchor="center")

    def _draw_pin(self, surf, x, y, color):
        pygame.draw.ellipse(surf, color, (x - 8, y - 18, 16, 26))
        pygame.draw.rect(surf, (210, 40, 40), (x - 7, y - 8, 14, 4), border_radius=2)
        pygame.draw.circle(surf, (235, 235, 235), (x, y - 20), 6)
