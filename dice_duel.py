import random

import pygame

from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import Button, draw_hud, draw_panel, draw_result_screen, text


class DiceDuelGame:
    MIN_BET = 10

    def __init__(self, config=None):
        self.config = config or {"mode": "solo"}
        self.state = "betting"
        self.bet = 25
        self.player_dice = [1, 1]
        self.dealer_dice = [1, 1]
        self.anim_time = 0.0
        self.total_anim = 1.2
        self.chips_delta = 0
        self.result_msg = ""

        self._bet_btns = [
            Button(SCREEN_W // 2 - 180 + i * 90, SCREEN_H - 128, 74, 32,
                   f"+{v}", color=(40, 40, 90), font="small")
            for i, v in enumerate([10, 25, 50, 100])
        ]
        self._bet_values = [10, 25, 50, 100]
        self._roll_btn = Button(SCREEN_W // 2 - 80, SCREEN_H - 76, 160, 46,
                                "LANZAR DADOS", color=(30, 80, 30))
        self._back_btn = Button(30, SCREEN_H - 70, 100, 40, "◀ SORTIR",
                                color=(60, 20, 20), font="small")

    def _resolve_round(self):
        player_total = sum(self.player_dice)
        dealer_total = sum(self.dealer_dice)
        payout = 0
        message = "La banca gana"

        if self.player_dice == [6, 6]:
            payout = self.bet * 4
            message = "Doble seis! Jackpot"
        elif dealer_total > player_total:
            payout = 0
        elif dealer_total == player_total:
            payout = self.bet
            message = "Empate"
        else:
            payout = self.bet * 2
            if self.player_dice[0] == self.player_dice[1]:
                payout += self.bet
                message = "Pareja ganadora"
            else:
                message = "Ganaste la mano"

        STATE["chips"] += payout
        self.chips_delta = payout - self.bet
        self.result_msg = message
        if self.chips_delta > 0:
            STATE["wins"] += 1
        else:
            STATE["losses"] += 1
        self.state = "result"

    def _start_roll(self):
        if STATE["chips"] < self.bet:
            return
        STATE["chips"] -= self.bet
        self.state = "rolling"
        self.anim_time = self.total_anim

    def handle_event(self, event):
        if self._back_btn.clicked(event):
            return "exit"

        if self.state == "result":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "betting"
            return None

        if self.state == "betting":
            for button, value in zip(self._bet_btns, self._bet_values):
                if button.clicked(event):
                    self.bet = min(STATE["chips"], self.bet + value)
            if self._roll_btn.clicked(event):
                self._start_roll()
        return None

    def update(self, dt):
        if self.state == "rolling":
            self.anim_time = max(0.0, self.anim_time - dt)
            self.player_dice = [random.randint(1, 6), random.randint(1, 6)]
            self.dealer_dice = [random.randint(1, 6), random.randint(1, 6)]
            if self.anim_time <= 0:
                self._resolve_round()

        for button in self._bet_btns:
            button.update(dt)
        self._roll_btn.update(dt)
        self._back_btn.update(dt)

    def draw(self, surf):
        surf.fill((14, 18, 24))
        text(surf, "DUEL DE DADOS", "big", C["neon_gold"],
             SCREEN_W // 2, 40, anchor="center")
        text(surf, "Más total que la banca. Dobles pagan extra.",
             "small", C["ui_sub"], SCREEN_W // 2, 72, anchor="center")

        player_panel = pygame.Rect(SCREEN_W // 2 - 360, 150, 280, 260)
        dealer_panel = pygame.Rect(SCREEN_W // 2 + 80, 150, 280, 260)
        center_panel = pygame.Rect(SCREEN_W // 2 - 120, 190, 240, 180)
        draw_panel(surf, player_panel, alpha=220, radius=16)
        draw_panel(surf, dealer_panel, alpha=220, radius=16)
        draw_panel(surf, center_panel, alpha=205, radius=16)

        text(surf, "TÚ", "med", C["ui_text"], player_panel.centerx, player_panel.y + 20, anchor="center")
        text(surf, "BANCA", "med", C["ui_text"], dealer_panel.centerx, dealer_panel.y + 20, anchor="center")
        self._draw_dice_pair(surf, player_panel.centerx, player_panel.y + 120, self.player_dice)
        self._draw_dice_pair(surf, dealer_panel.centerx, dealer_panel.y + 120, self.dealer_dice)
        text(surf, f"{sum(self.player_dice)}", "big", C["chips"], player_panel.centerx, player_panel.bottom - 48, anchor="center")
        text(surf, f"{sum(self.dealer_dice)}", "big", C["chips"], dealer_panel.centerx, dealer_panel.bottom - 48, anchor="center")

        text(surf, "Apuesta", "tiny", C["ui_sub"], center_panel.centerx, center_panel.y + 22, anchor="center")
        text(surf, f"{self.bet} chips", "med", C["chips"], center_panel.centerx, center_panel.y + 48, anchor="center")
        text(surf, "12-12 = x4", "small", C["ui_text"], center_panel.centerx, center_panel.y + 92, anchor="center")
        text(surf, "dobles = x3", "small", C["ui_text"], center_panel.centerx, center_panel.y + 118, anchor="center")

        for button in self._bet_btns:
            button.draw(surf)
        if self.state == "betting":
            self._roll_btn.draw(surf)
        self._back_btn.draw(surf)
        draw_hud(surf)

        if self.state == "result":
            draw_result_screen(surf, self.result_msg, self.chips_delta)

    def _draw_dice_pair(self, surf, cx, cy, values):
        self._draw_die(surf, cx - 48, cy, values[0])
        self._draw_die(surf, cx + 48, cy, values[1])

    def _draw_die(self, surf, cx, cy, value):
        rect = pygame.Rect(cx - 36, cy - 36, 72, 72)
        pygame.draw.rect(surf, (252, 250, 244), rect, border_radius=12)
        pygame.draw.rect(surf, C["ui_border"], rect, 3, border_radius=12)
        positions = {
            1: [(0, 0)],
            2: [(-18, -18), (18, 18)],
            3: [(-18, -18), (0, 0), (18, 18)],
            4: [(-18, -18), (18, -18), (-18, 18), (18, 18)],
            5: [(-18, -18), (18, -18), (0, 0), (-18, 18), (18, 18)],
            6: [(-18, -18), (18, -18), (-18, 0), (18, 0), (-18, 18), (18, 18)],
        }
        for ox, oy in positions[value]:
            pygame.draw.circle(surf, (24, 24, 30), (cx + ox, cy + oy), 6)
