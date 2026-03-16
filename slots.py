import math
import random

import pygame

from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import Button, draw_hud, draw_panel, draw_rect_alpha, draw_result_screen, text

SYMBOLS = [
    {"name": "7", "color": (235, 60, 60), "weight": 1},
    {"name": "BAR", "color": (40, 40, 40), "weight": 2},
    {"name": "GEM", "color": (70, 180, 255), "weight": 3},
    {"name": "STAR", "color": (255, 210, 50), "weight": 4},
    {"name": "BELL", "color": (255, 180, 70), "weight": 5},
    {"name": "CHERRY", "color": (220, 60, 120), "weight": 6},
]


class SlotsGame:
    MIN_BET = 10

    def __init__(self, config=None):
        self.config = config or {"mode": "solo"}
        self.state = "betting"
        self.bet = 25
        self.result = [random.choice(SYMBOLS) for _ in range(3)]
        self.chips_delta = 0
        self.result_msg = ""
        self.spin_time = 0.0
        self.total_spin = 2.8
        self.reel_offsets = [0.0, 0.0, 0.0]
        self.reel_speeds = [0.0, 0.0, 0.0]
        self.reel_stop_at = [0.0, 0.0, 0.0]
        self.reel_locked = [False, False, False]
        self._glow_t = 0.0

        self._bet_btns = [
            Button(SCREEN_W // 2 - 220 + i * 110, SCREEN_H - 132, 92, 34,
                   f"+{value}", color=(45, 45, 95), font="small")
            for i, value in enumerate([10, 25, 50, 100])
        ]
        self._bet_values = [10, 25, 50, 100]
        self._spin_btn = Button(SCREEN_W // 2 - 80, SCREEN_H - 76, 160, 46,
                                "GIRAR", color=(120, 30, 30))
        self._max_btn = Button(SCREEN_W // 2 + 150, SCREEN_H - 132, 110, 34,
                               "MAX", color=(90, 70, 15), font="small")
        self._back_btn = Button(30, SCREEN_H - 70, 100, 40, "◀ SORTIR",
                                color=(60, 20, 20), font="small")

    def _pick_symbol(self):
        weights = [item["weight"] for item in SYMBOLS]
        return random.choices(SYMBOLS, weights=weights, k=1)[0]

    def _evaluate_result(self):
        names = [item["name"] for item in self.result]
        counts = {name: names.count(name) for name in set(names)}
        payout = 0
        message = "Sense premi"

        if len(set(names)) == 1:
            symbol = names[0]
            multipliers = {
                "7": 18,
                "BAR": 12,
                "GEM": 10,
                "STAR": 8,
                "BELL": 6,
                "CHERRY": 5,
            }
            payout = self.bet * multipliers.get(symbol, 4)
            message = f"JACKPOT {symbol}!"
        elif 2 in counts.values():
            repeated = next(name for name, count in counts.items() if count == 2)
            payout = self.bet * (3 if repeated in ("7", "BAR", "GEM") else 2)
            message = f"Parella de {repeated}"
        elif "CHERRY" in names:
            payout = self.bet
            message = "Cherry salva la tirada"

        STATE["chips"] += payout
        self.chips_delta = payout - self.bet
        self.result_msg = message
        if self.chips_delta > 0:
            STATE["wins"] += 1
        else:
            STATE["losses"] += 1
        self.state = "result"

    def _start_spin(self):
        if self.bet <= 0 or STATE["chips"] < self.bet:
            return
        STATE["chips"] -= self.bet
        self.state = "spinning"
        self.spin_time = self.total_spin
        self.reel_locked = [False, False, False]
        self.reel_speeds = [18.0, 23.0, 28.0]
        self.reel_stop_at = [1.8, 2.25, 2.7]
        self.result = [self._pick_symbol() for _ in range(3)]

    def handle_event(self, event):
        if self.state == "result":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "betting"
            if self._back_btn.clicked(event):
                return "exit"
            return None

        if self._back_btn.clicked(event):
            return "exit"

        if self.state == "betting":
            for button, value in zip(self._bet_btns, self._bet_values):
                if button.clicked(event):
                    self.bet = min(STATE["chips"], self.bet + value)
            if self._max_btn.clicked(event):
                self.bet = max(self.MIN_BET, min(STATE["chips"], max(self.bet, 250)))
            if self._spin_btn.clicked(event):
                self._start_spin()
        return None

    def update(self, dt):
        self._glow_t += dt
        if self.state == "spinning":
            self.spin_time = max(0.0, self.spin_time - dt)
            elapsed = self.total_spin - self.spin_time
            for index in range(3):
                if not self.reel_locked[index]:
                    self.reel_offsets[index] = (self.reel_offsets[index] + self.reel_speeds[index] * dt) % len(SYMBOLS)
                    self.reel_speeds[index] = max(4.5, self.reel_speeds[index] * (1 - dt * 0.55))
                    if elapsed >= self.reel_stop_at[index]:
                        target = SYMBOLS.index(self.result[index])
                        self.reel_offsets[index] = float(target)
                        self.reel_locked[index] = True
            if self.spin_time <= 0:
                self._evaluate_result()

        for button in self._bet_btns:
            button.update(dt)
        self._spin_btn.update(dt)
        self._max_btn.update(dt)
        self._back_btn.update(dt)

    def draw(self, surf):
        surf.fill((12, 10, 18))
        text(surf, "TRAGAPERRAS NEÓN", "big", C["neon_gold"],
             SCREEN_W // 2, 40, anchor="center")
        text(surf, "3 iguales = premio gordo · Cherry recupera apuesta",
             "small", C["ui_sub"], SCREEN_W // 2, 74, anchor="center")

        machine = pygame.Rect(SCREEN_W // 2 - 260, 120, 520, 360)
        draw_panel(surf, machine, alpha=235, radius=22)
        pygame.draw.rect(surf, (150, 25, 25), machine.inflate(-10, -10), border_radius=18)
        pygame.draw.rect(surf, C["neon_gold"], machine.inflate(-10, -10), 4, border_radius=18)

        glow = 120 + int(60 * math.sin(self._glow_t * 4.0))
        draw_rect_alpha(surf, C["neon_gold"],
                        (machine.x + 24, machine.y + 20, machine.w - 48, 54), glow, 18)
        text(surf, "ROYAL SLOTS", "big", C["black"],
             machine.centerx, machine.y + 46, anchor="center", shadow=False)

        window_y = machine.y + 108
        for index in range(3):
            reel_rect = pygame.Rect(machine.x + 42 + index * 150, window_y, 120, 180)
            pygame.draw.rect(surf, (245, 240, 225), reel_rect, border_radius=14)
            pygame.draw.rect(surf, C["ui_border"], reel_rect, 3, border_radius=14)
            self._draw_reel(surf, reel_rect, index)

        lever_x = machine.right + 28
        pygame.draw.line(surf, C["table_edge"], (lever_x, machine.y + 90), (lever_x, machine.y + 230), 12)
        lever_angle = 0.8 if self.state == "spinning" else 0.2
        knob_x = lever_x + int(math.sin(lever_angle) * 36)
        knob_y = machine.y + 230 + int(math.cos(lever_angle) * 12)
        pygame.draw.circle(surf, (210, 40, 40), (knob_x, knob_y), 18)
        pygame.draw.circle(surf, C["ui_border"], (knob_x, knob_y), 18, 3)

        panel = pygame.Rect(SCREEN_W // 2 - 200, 500, 400, 86)
        draw_panel(surf, panel, alpha=220, radius=12)
        text(surf, "APUESTA", "tiny", C["ui_sub"], panel.x + 18, panel.y + 16)
        text(surf, f"{self.bet} chips", "med", C["chips"], panel.x + 18, panel.y + 34)
        text(surf, "PAGOS", "tiny", C["ui_sub"], panel.x + 210, panel.y + 16)
        text(surf, "777 x18 · BAR x12 · GEM x10", "small", C["ui_text"], panel.x + 210, panel.y + 34)
        text(surf, "doble x2/x3", "small", C["ui_text"], panel.x + 210, panel.y + 56)

        for button in self._bet_btns:
            button.draw(surf)
        self._max_btn.draw(surf)
        if self.state == "betting":
            self._spin_btn.draw(surf)
        self._back_btn.draw(surf)

        draw_hud(surf)
        if self.state == "result":
            draw_result_screen(surf, self.result_msg, self.chips_delta)

    def _draw_reel(self, surf, reel_rect, index):
        center_slot = int(round(self.reel_offsets[index])) % len(SYMBOLS)
        visible = [
            SYMBOLS[(center_slot - 1) % len(SYMBOLS)],
            SYMBOLS[center_slot],
            SYMBOLS[(center_slot + 1) % len(SYMBOLS)],
        ]
        slot_h = reel_rect.h // 3
        for row, symbol in enumerate(visible):
            slot_rect = pygame.Rect(reel_rect.x + 8, reel_rect.y + row * slot_h + 6,
                                    reel_rect.w - 16, slot_h - 12)
            pygame.draw.rect(surf, (255, 252, 246), slot_rect, border_radius=10)
            pygame.draw.rect(surf, symbol["color"], slot_rect, 2, border_radius=10)
            color = symbol["color"] if row == 1 else tuple(max(40, c - 70) for c in symbol["color"])
            text(surf, symbol["name"], "med", color,
                 slot_rect.centerx, slot_rect.centery, anchor="center", shadow=False)

        marker = pygame.Rect(reel_rect.x - 6, reel_rect.y + reel_rect.h // 2 - 34,
                             reel_rect.w + 12, 68)
        pygame.draw.rect(surf, C["neon_gold"], marker, 3, border_radius=12)
