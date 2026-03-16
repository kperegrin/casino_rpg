# ═══════════════════════════════════════════════════════════════════
#  ROULETTE — Ruleta europea amb animació de bola
# ═══════════════════════════════════════════════════════════════════
import pygame
import random
import math
from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import (Button, draw_panel, draw_hud, draw_result_screen,
                text, draw_rect_alpha, F, FloatMessage)
from card_renderer import make_chip, make_ball

# Ordre oficial dels números a la ruleta europea
WHEEL_ORDER = [
    0,32,15,19,4,21,2,25,17,34,6,27,13,36,
    11,30,8,23,10,5,24,16,33,1,20,14,31,9,
    22,18,29,7,28,12,35,3,26
]
RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


def _color_num(n):
    if n == 0:
        return C["ui_green"]
    return C["neon_red"] if n in RED_NUMS else (30,30,30)

def _is_red(n):   return n in RED_NUMS
def _is_black(n): return n not in RED_NUMS and n != 0
def _is_even(n):  return n != 0 and n % 2 == 0
def _is_odd(n):   return n != 0 and n % 2 == 1


def _angle_delta(target, current):
    return (target - current + math.pi) % (math.pi * 2) - math.pi


# ── Tipus d'aposta ────────────────────────────────────────────────
BETS = {
    "red":      {"label":"Roig",   "pays":1,  "check": lambda n: _is_red(n)},
    "black":    {"label":"Negre",  "pays":1,  "check": lambda n: _is_black(n)},
    "even":     {"label":"Parell", "pays":1,  "check": lambda n: _is_even(n)},
    "odd":      {"label":"Senar",  "pays":1,  "check": lambda n: _is_odd(n)},
    "1_18":     {"label":"1-18",   "pays":1,  "check": lambda n: 1<=n<=18},
    "19_36":    {"label":"19-36",  "pays":1,  "check": lambda n: 19<=n<=36},
    "d1":       {"label":"1a12",   "pays":2,  "check": lambda n: 1<=n<=12},
    "d2":       {"label":"13-24",  "pays":2,  "check": lambda n: 13<=n<=24},
    "d3":       {"label":"25-36",  "pays":2,  "check": lambda n: 25<=n<=36},
}


# ═══════════════════════════════════════════════════════════════════
class RouletteGame:

    WHEEL_R  = 160    # radi exterior
    INNER_R  = 120    # radi interior (pista de la bola)
    BALL_R   = INNER_R - 10

    def __init__(self, config=None):
        self.config      = config or {"mode": "solo", "room": "Royal"}
        self.state       = "betting"   # betting|spinning|result
        self.placed_bets = {}          # {bet_key: amount}
        self.result_num  = None
        self.result_msg  = ""
        self.chips_delta = 0
        self._float_msgs = []

        # Roda
        self._wheel_angle = 0.0
        self._wheel_speed = 0.0

        # Bola
        self._ball_angle  = 0.0
        self._ball_speed  = 0.0
        self._ball_r      = self.BALL_R
        self._spinning    = False
        self._spin_timer  = 0.0
        self._spin_total  = 4.0   # s de gir
        self._target_index = 0
        self._target_ball_angle = 0.0

        # Número directe (clic)
        self._selected_num   = None
        self._direct_amount  = 25

        # Centre de la roda
        self._cx = 260
        self._cy = SCREEN_H // 2

        # Botons
        self._spin_btn = Button(
            self._cx - 60, self._cy + self.WHEEL_R + 20,
            120, 44, "GIRAR", color=(120,20,20))
        self._clear_btn = Button(
            self._cx - 60, self._cy + self.WHEEL_R + 72,
            120, 36, "Netejar", color=(60,20,20), font="small")
        self._back_btn = Button(
            30, SCREEN_H-70, 100, 40, "◀ SORTIR",
            color=(60,20,20), font="small")

        self._chip_btns = [
            Button(SCREEN_W - 220, 80 + i*48, 90, 38,
                   f"{v}✦", color=(40,30,80))
            for i,v in enumerate([10,25,50,100,250])
        ]
        self._chip_values = [10,25,50,100,250]
        self._active_chip = 25

        # Botons de les apostes fixes
        self._bet_btns = []
        self._build_bet_buttons()

    # ── Botons d'aposta ──────────────────────────────────────────
    def _build_bet_buttons(self):
        bw, bh = 68, 34
        bx_start = 540
        by_start = SCREEN_H//2 - 60

        keys = list(BETS.keys())
        # Primera fila: roig,negre,parell,senar,1-18,19-36
        row1 = ["red","black","even","odd","1_18","19_36"]
        # Segona fila: dotzenes
        row2 = ["d1","d2","d3"]

        for i,k in enumerate(row1):
            x = bx_start + i*(bw+6)
            y = by_start + 160
            b = Button(x, y, bw, bh, BETS[k]["label"],
                       color=((120,20,20) if k in ("red","1_18","d1")
                              else (20,20,80) if k=="black"
                              else (20,80,20)),
                       font="small")
            b._bet_key = k
            self._bet_btns.append(b)

        for i,k in enumerate(row2):
            x = bx_start + i*(bw*2+10)
            y = by_start + 202
            b = Button(x, y, bw*2, bh, BETS[k]["label"],
                       color=(30,60,20), font="small")
            b._bet_key = k
            self._bet_btns.append(b)

    # ── Lògica ───────────────────────────────────────────────────
    def _place_bet(self, bet_key, amount):
        total = sum(self.placed_bets.values()) + amount
        if total > STATE["chips"]:
            return
        self.placed_bets[bet_key] = self.placed_bets.get(bet_key,0) + amount

    def _place_direct(self, num):
        key = f"num_{num}"
        total = sum(self.placed_bets.values()) + self._active_chip
        if total > STATE["chips"]:
            return
        self.placed_bets[key] = self.placed_bets.get(key,0) + self._active_chip

    def _start_spin(self):
        if not self.placed_bets:
            return
        total_bet = sum(self.placed_bets.values())
        if total_bet > STATE["chips"]:
            return
        STATE["chips"] -= total_bet

        self._wheel_speed = random.uniform(3.6, 5.4)
        self._ball_speed  = random.uniform(-11.5, -9.0)
        self._ball_r      = self.BALL_R
        self._spinning    = True
        self._spin_timer  = self._spin_total
        self.state        = "spinning"
        self.result_num   = None
        self._target_index = random.randrange(len(WHEEL_ORDER))
        self._target_ball_angle = self._wheel_angle + (self._target_index + 0.5) * (2 * math.pi / len(WHEEL_ORDER))
        self._ball_angle = random.uniform(0, math.pi * 2)

    def _resolve(self):
        self.result_num = WHEEL_ORDER[self._target_index % len(WHEEL_ORDER)]

        total_won = 0
        details   = []
        for key, amount in self.placed_bets.items():
            if key.startswith("num_"):
                n = int(key[4:])
                if n == self.result_num:
                    won = amount * 36
                    total_won += won
                    details.append(f"Número {n}: +{won}")
            elif key in BETS:
                if BETS[key]["check"](self.result_num):
                    pays = BETS[key]["pays"]
                    won  = amount * (pays + 1)
                    total_won += won
                    details.append(f"{BETS[key]['label']}: +{won-amount}")

        STATE["chips"] += total_won
        self.chips_delta = total_won - sum(self.placed_bets.values())

        if self.chips_delta > 0:
            self.result_msg = f"GUANYES!  Número {self.result_num}"
            STATE["wins"] += 1
        else:
            self.result_msg = f"PERDS  Número {self.result_num}"
            STATE["losses"] += 1

        self.placed_bets = {}
        self.state       = "result"

    # ── Events ───────────────────────────────────────────────────
    def handle_event(self, event):
        if self.state == "result":
            if (event.type==pygame.KEYDOWN
                    and event.key==pygame.K_SPACE):
                self.state = "betting"
            return None

        if self.state == "spinning":
            return None

        if self._back_btn.clicked(event):
            return "exit"

        if self._spin_btn.clicked(event):
            self._start_spin()

        if self._clear_btn.clicked(event):
            self.placed_bets = {}

        for i,b in enumerate(self._chip_btns):
            if b.clicked(event):
                self._active_chip = self._chip_values[i]

        for b in self._bet_btns:
            if b.clicked(event):
                self._place_bet(b._bet_key, self._active_chip)

        # Clic sobre un número de la roda
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Comprovar la graella de números (540..950, SCREEN_H//2-60..+140)
            gx0 = 540
            gy0 = SCREEN_H//2 - 60
            cw  = 34
            ch  = 34
            for n in range(37):
                if n == 0:
                    rx, ry = gx0, gy0 + 2
                    rw, rh = cw, ch*3
                else:
                    col = (n-1) % 3
                    row = (n-1) // 3
                    rx = gx0 + cw + row*cw
                    ry = gy0 + (2-col)*ch
                    rw, rh = cw, ch
                if rx <= mx <= rx+rw and ry <= my <= ry+rh:
                    self._place_direct(n)
                    break

        return None

    def update(self, dt):
        if self._spinning:
            self._spin_timer -= dt
            progress = 1 - max(0, self._spin_timer) / self._spin_total

            self._wheel_angle += self._wheel_speed * dt
            self._wheel_speed  = max(0.22, self._wheel_speed * (1 - dt*0.34))

            if progress < 0.76:
                self._ball_speed *= (1 - dt * 0.16)
                self._ball_angle += self._ball_speed * dt
                self._ball_r = self.BALL_R - progress * 24
            else:
                sector_angle = 2 * math.pi / len(WHEEL_ORDER)
                target_angle = self._wheel_angle + (self._target_index + 0.5) * sector_angle
                self._ball_angle += _angle_delta(target_angle, self._ball_angle) * min(1.0, dt * 7.5)
                settle = min(1.0, (progress - 0.76) / 0.24)
                self._ball_r = (self.BALL_R - 24) - settle * 16
                self._target_ball_angle = target_angle

            if self._spin_timer <= 0:
                self._spinning = False
                self._ball_angle = self._target_ball_angle
                self._resolve()

        for m in self._float_msgs:
            m.update(dt)
        self._float_msgs = [m for m in self._float_msgs if not m.done]

        dt_ = dt
        self._spin_btn.update(dt_)
        self._clear_btn.update(dt_)
        self._back_btn.update(dt_)
        for b in self._chip_btns:
            b.update(dt_)
        for b in self._bet_btns:
            b.update(dt_)

    # ── Renderitzat ───────────────────────────────────────────────
    def draw(self, surf):
        surf.fill(C["bg"])

        cx, cy = self._cx, self._cy

        # Títol
        text(surf, "RULETA EUROPEA", "big", C["neon_gold"],
             cx, cy - self.WHEEL_R - 30, anchor="center")

        # ── Roda ──────────────────────────────────────────────────
        self._draw_wheel(surf, cx, cy)

        # ── Bola ──────────────────────────────────────────────────
        if self._spinning or self.state == "result":
            bx = cx + int(self._ball_r * math.cos(self._ball_angle))
            by = cy + int(self._ball_r * math.sin(self._ball_angle))
            ball = make_ball(14)
            surf.blit(ball, (bx-7, by-7))

        # Número resultat
        if self.state == "result" and self.result_num is not None:
            color = _color_num(self.result_num)
            pygame.draw.circle(surf, color, (cx, cy), 28)
            pygame.draw.circle(surf, C["neon_gold"], (cx, cy), 28, 3)
            text(surf, str(self.result_num), "big", C["white"],
                 cx, cy, anchor="center")

        # ── Graella de números ────────────────────────────────────
        self._draw_grid(surf)

        # ── Apostes col·locades ───────────────────────────────────
        self._draw_placed_bets(surf)

        # ── Panel d'apostes totals ────────────────────────────────
        total = sum(self.placed_bets.values())
        panel_x = SCREEN_W - 230
        draw_panel(surf, (panel_x, 10, 220, 60), alpha=200, radius=8)
        text(surf, "APOSTA TOTAL", "tiny", C["ui_sub"], panel_x+10, 16)
        text(surf, f"{total} chips", "med", C["chips"], panel_x+10, 30)

        # ── Fitxa activa ──────────────────────────────────────────
        text(surf, "Fitxa activa:", "tiny", C["ui_sub"],
             SCREEN_W-225, 78)
        chip = make_chip(min(self._active_chip,1000), 32)
        surf.blit(chip, (SCREEN_W-185, 92))
        text(surf, f"{self._active_chip}", "small", C["chips"],
             SCREEN_W-145, 102)

        # Botons fitxes
        for i,b in enumerate(self._chip_btns):
            if self._chip_values[i] == self._active_chip:
                pygame.draw.rect(surf, C["neon_gold"],
                                 b.rect.inflate(4,4), 2, border_radius=10)
            b.draw(surf)

        # Botons d'aposta
        for b in self._bet_btns:
            b.draw(surf)

        # Botons principals
        if self.state == "betting":
            self._spin_btn.draw(surf)
            self._clear_btn.draw(surf)

        self._back_btn.draw(surf)
        draw_hud(surf)

        if self.state == "result":
            draw_result_screen(surf, self.result_msg, self.chips_delta)

        for m in self._float_msgs:
            m.draw(surf)

    def _draw_wheel(self, surf, cx, cy):
        # Ombra
        shadow = pygame.Surface((self.WHEEL_R*2+20, self.WHEEL_R*2+20),
                                  pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0,0,0,100),
                           (self.WHEEL_R+10, self.WHEEL_R+10),
                           self.WHEEL_R+10)
        surf.blit(shadow, (cx-self.WHEEL_R-10, cy-self.WHEEL_R+8))

        # Anell exterior (fusta)
        pygame.draw.circle(surf, C["table_edge"], (cx,cy), self.WHEEL_R)
        pygame.draw.circle(surf, (60, 30, 12), (cx, cy), self.WHEEL_R - 14)

        # Sectors de colors
        n_nums = len(WHEEL_ORDER)
        sector_angle = 2*math.pi / n_nums
        for i, num in enumerate(WHEEL_ORDER):
            angle = self._wheel_angle + i * sector_angle
            color = _color_num(num)
            start = angle
            end = angle + sector_angle
            points = []
            steps  = 5
            outer_r = self.WHEEL_R - 20
            inner_r = self.INNER_R - 10
            for step in range(steps + 1):
                a = start + step * sector_angle / steps
                points.append((cx + outer_r * math.cos(a), cy + outer_r * math.sin(a)))
            for step in range(steps, -1, -1):
                a = start + step * sector_angle / steps
                points.append((cx + inner_r * math.cos(a), cy + inner_r * math.sin(a)))
            pygame.draw.polygon(surf, color, points)

            # Divisor
            pygame.draw.line(surf,
                             (220, 200, 140),
                             (cx + inner_r*math.cos(angle), cy + inner_r*math.sin(angle)),
                             (cx + outer_r*math.cos(angle), cy + outer_r*math.sin(angle)),
                             1)

            label_angle = angle + sector_angle * 0.5
            lx = cx + int((inner_r + 22) * math.cos(label_angle))
            ly = cy + int((inner_r + 22) * math.sin(label_angle))
            text(surf, str(num), "tiny", C["white"], lx, ly,
                 anchor="center", shadow=False)

        pygame.draw.circle(surf, C["ui_border"], (cx, cy), self.WHEEL_R - 18, 3)
        pygame.draw.circle(surf, C["ui_border"], (cx, cy), self.INNER_R - 10, 2)

        # Cercle interior (centre de la roda)
        pygame.draw.circle(surf, (90, 55, 22), (cx,cy), self.INNER_R - 34)
        pygame.draw.circle(surf, C["table_edge"], (cx,cy), 32)
        pygame.draw.circle(surf, C["neon_gold"],  (cx,cy), 20)
        pygame.draw.circle(surf, C["table_edge"], (cx,cy), 8)

    def _draw_grid(self, surf):
        """Graella 12×3 de números (+ 0 a l'esquerra)."""
        gx0 = 540
        gy0 = SCREEN_H//2 - 60
        cw  = 34
        ch  = 34

        for n in range(37):
            if n == 0:
                rx, ry = gx0, gy0 + 2
                rw, rh = cw, ch*3
            else:
                col = (n-1) % 3
                row = (n-1) // 3
                rx  = gx0 + cw + row*cw
                ry  = gy0 + (2-col)*ch
                rw  = cw
                rh  = ch

            color = _color_num(n)
            pygame.draw.rect(surf, color, (rx+1, ry+1, rw-2, rh-2))
            pygame.draw.rect(surf, C["ui_border"], (rx, ry, rw, rh), 1)

            # Destacar si hi ha aposta
            key = f"num_{n}"
            if key in self.placed_bets:
                pygame.draw.rect(surf, C["neon_gold"], (rx, ry, rw, rh), 2)

            try:
                f = pygame.font.SysFont("Georgia", 10, bold=True)
                t = f.render(str(n), True, C["white"])
                surf.blit(t, t.get_rect(
                    center=(rx+rw//2, ry+rh//2)))
            except:
                pass

    def _draw_placed_bets(self, surf):
        """Mostra fitxes sobre les apostes col·locades."""
        y_base = SCREEN_H//2 + 110
        x = 540
        for key, amount in self.placed_bets.items():
            chip_v = min(amount, 1000)
            chip   = make_chip(chip_v, 20)
            surf.blit(chip, (x, y_base))
            text(surf, f"{key[:6]}:{amount}", "tiny", C["ui_sub"],
                 x, y_base+22)
            x += 50
            if x > SCREEN_W - 60:
                x = 540
                y_base += 44
