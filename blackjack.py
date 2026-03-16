# ═══════════════════════════════════════════════════════════════════
#  BLACKJACK — lògica i renderitzat complets
# ═══════════════════════════════════════════════════════════════════
import pygame
import random
import math
from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import (Button, draw_panel, draw_hud, draw_result_screen,
                text, draw_rect_alpha, F, FloatMessage)
from card_renderer import make_card, make_chip

# ── Baralla ──────────────────────────────────────────────────────────
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
SUITS_LIST = ["♠","♥","♦","♣"]

def _new_deck(n=6):
    deck = [(r, s) for r in RANKS for s in SUITS_LIST] * n
    random.shuffle(deck)
    return deck

def _card_value(rank):
    if rank in ("J","Q","K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)

def _hand_value(hand):
    total = sum(_card_value(r) for r, _ in hand)
    aces  = sum(1 for r, _ in hand if r == "A")
    while total > 21 and aces:
        total -= 10
        aces  -= 1
    return total

def _is_blackjack(hand):
    return len(hand) == 2 and _hand_value(hand) == 21

def _is_bust(hand):
    return _hand_value(hand) > 21

# Mides de carta
CW, CH = 68, 96


# ═══════════════════════════════════════════════════════════════════
class BlackjackGame:

    MIN_BET = 10
    MAX_BET = STATE["chips"]

    # estats: "bet" | "player" | "dealer" | "result"
    def __init__(self, config=None):
        self.config      = config or {"mode": "solo", "room": "Royal"}
        self.mode        = self.config.get("mode", "solo")
        self.room        = self.config.get("room", "Royal")
        self._remote_ok  = self.mode != "lan_client"
        self.deck       = _new_deck()
        self.state      = "bet"
        self.bet        = 50
        self.player_hand= []
        self.dealer_hand= []
        self.split_hand = []
        self.active_hand= 0    # 0=principal, 1=split
        self.doubled    = False
        self.result     = ""
        self.chips_delta= 0
        self._dealer_timer = 0.0
        self._dealer_delay = 0.8
        self._float_msgs   = []
        self._card_anim    = []  # [{surf,x,y,tx,ty,t}]
        self._result_timer = 0.0

        # Botons
        bw, bh = 110, 44
        y_row = SCREEN_H - 70
        self._btns = {
            "hit":    Button(SCREEN_W//2-170, y_row, bw, bh, "HIT",
                             color=(20,80,20)),
            "stand":  Button(SCREEN_W//2-50,  y_row, bw, bh, "STAND",
                             color=(80,20,20)),
            "double": Button(SCREEN_W//2+70,  y_row, bw, bh, "DOUBLE",
                             color=(60,60,10)),
            "split":  Button(SCREEN_W//2+190, y_row, bw, bh, "SPLIT",
                             color=(20,40,80)),
            "deal":   Button(SCREEN_W//2-55,  y_row, 110, bh, "DEAL",
                             color=(20,80,20)),
            "back":   Button(30, SCREEN_H-70, 100, 40, "◀ SORTIR",
                             color=(60,20,20), font="small"),
        }
        self._bet_buttons = [
            Button(SCREEN_W//2 - 230 + i*90, SCREEN_H//2+60, 80, 36,
                   f"+{v}", color=(40,40,80))
            for i, v in enumerate([10,25,50,100,250])
        ]
        self._clear_btn = Button(SCREEN_W//2+240, SCREEN_H//2+60, 80, 36,
                                  "Clear", color=(80,20,20))

    def _serialize_state(self):
        return {
            "state": self.state,
            "bet": self.bet,
            "player_hand": self.player_hand,
            "dealer_hand": self.dealer_hand,
            "split_hand": self.split_hand,
            "active_hand": self.active_hand,
            "doubled": self.doubled,
            "result": self.result,
            "chips_delta": self.chips_delta,
        }

    def _apply_remote_state(self, data):
        self.state = data.get("state", self.state)
        self.bet = data.get("bet", self.bet)
        self.player_hand = data.get("player_hand", [])
        self.dealer_hand = data.get("dealer_hand", [])
        self.split_hand = data.get("split_hand", [])
        self.active_hand = data.get("active_hand", 0)
        self.doubled = data.get("doubled", False)
        self.result = data.get("result", "")
        self.chips_delta = data.get("chips_delta", 0)
        self._remote_ok = True

    def _sync_online_table(self):
        if self.mode == "lan_host":
            server = STATE.get("net_server")
            if server:
                server.broadcast({
                    "type": "table_state",
                    "game": "blackjack",
                    "room": self.room,
                    "state": self._serialize_state(),
                })
            client = STATE.get("net_client")
            if client and client.connected:
                client.send({
                    "type": "table_state",
                    "game": "blackjack",
                    "room": self.room,
                    "state": self._serialize_state(),
                })
        elif self.mode == "lan_client":
            client = STATE.get("net_client")
            if client and client.connected:
                for msg in client.poll():
                    if (msg.get("type") == "table_state"
                            and msg.get("game") == "blackjack"):
                        self._apply_remote_state(msg.get("state", {}))

    # ── Lògica ───────────────────────────────────────────────────
    def _deal_card(self, hand):
        if not self.deck:
            self.deck = _new_deck()
        card = self.deck.pop()
        hand.append(card)
        return card

    def _start_round(self):
        if STATE["chips"] < self.bet:
            self.bet = max(self.MIN_BET, STATE["chips"])
        self.player_hand = []
        self.dealer_hand = []
        self.split_hand  = []
        self.active_hand = 0
        self.doubled     = False
        STATE["chips"]  -= self.bet

        for _ in range(2):
            self._deal_card(self.player_hand)
            self._deal_card(self.dealer_hand)

        if _is_blackjack(self.player_hand):
            self.state = "dealer"
        else:
            self.state = "player"

    def _hit(self):
        hand = self.player_hand if self.active_hand == 0 else self.split_hand
        self._deal_card(hand)
        if _is_bust(hand):
            if self.active_hand == 0 and self.split_hand:
                self.active_hand = 1
            else:
                self.state = "dealer"

    def _stand(self):
        if self.active_hand == 0 and self.split_hand:
            self.active_hand = 1
        else:
            self.state = "dealer"
            self._dealer_timer = self._dealer_delay

    def _double(self):
        if STATE["chips"] >= self.bet and len(self.player_hand) == 2:
            STATE["chips"] -= self.bet
            self.bet       *= 2
            self.doubled    = True
            self._deal_card(self.player_hand)
            self._stand()

    def _split(self):
        hand = self.player_hand
        if (len(hand) == 2
                and _card_value(hand[0][0]) == _card_value(hand[1][0])
                and STATE["chips"] >= self.bet):
            STATE["chips"] -= self.bet
            self.split_hand = [hand.pop()]
            self._deal_card(self.player_hand)
            self._deal_card(self.split_hand)

    def _dealer_play(self):
        """Jugada automàtica del crupier (plantada al 17)."""
        while _hand_value(self.dealer_hand) < 17:
            self._deal_card(self.dealer_hand)
        self._resolve()

    def _resolve(self):
        dv = _hand_value(self.dealer_hand)
        hands = [self.player_hand]
        if self.split_hand:
            hands.append(self.split_hand)

        total_delta = 0
        messages    = []

        for hand in hands:
            pv = _hand_value(hand)
            bust_d  = _is_bust(self.dealer_hand)
            bust_p  = _is_bust(hand)
            bj_p    = _is_blackjack(hand)

            if bust_p:
                msg = "BUST!"
                delta = 0
            elif bj_p and not _is_blackjack(self.dealer_hand):
                msg   = "BLACKJACK! 3:2"
                delta = int(self.bet * 2.5)
            elif bust_d or pv > dv:
                msg   = "GUANYES!"
                delta = self.bet * 2
            elif pv == dv:
                msg   = "EMPAT"
                delta = self.bet
            else:
                msg   = "PERDS"
                delta = 0

            STATE["chips"] += delta
            total_delta    += delta - self.bet
            messages.append(msg)

        self.result     = " / ".join(set(messages))
        self.chips_delta = total_delta

        if total_delta > 0:
            STATE["wins"] += 1
        else:
            STATE["losses"] += 1

        self.state = "result"

    # ── Events ───────────────────────────────────────────────────
    def handle_event(self, event):
        btns = self._btns

        if self.mode == "lan_client":
            if btns["back"].clicked(event):
                return "exit"
            return None

        if self.state == "result":
            if (event.type == pygame.KEYDOWN
                    and event.key == pygame.K_SPACE):
                self.state = "bet"
            return None

        if self.state == "bet":
            for b in self._bet_buttons:
                if b.clicked(event):
                    val = int(b.label[1:])
                    self.bet = min(self.bet + val, STATE["chips"])
            if self._clear_btn.clicked(event):
                self.bet = self.MIN_BET
            if btns["deal"].clicked(event) and self.bet > 0:
                self._start_round()
            if btns["back"].clicked(event):
                return "exit"

        elif self.state == "player":
            hand = (self.player_hand if self.active_hand == 0
                    else self.split_hand)
            if btns["hit"].clicked(event):
                self._hit()
            if btns["stand"].clicked(event):
                self._stand()
            if btns["double"].clicked(event):
                self._double()
            if (btns["split"].clicked(event)
                    and len(self.player_hand) == 2
                    and not self.split_hand):
                self._split()
            if btns["back"].clicked(event):
                return "exit"

        return None

    def update(self, dt):
        self._sync_online_table()

        # Dealer play (amb retard per animació)
        if self.mode != "lan_client" and self.state == "dealer":
            self._dealer_timer -= dt
            if self._dealer_timer <= 0:
                self._dealer_play()

        for m in self._float_msgs:
            m.update(dt)
        self._float_msgs = [m for m in self._float_msgs if not m.done]

        dt_val = dt
        for btn in self._btns.values():
            btn.update(dt_val)
        for b in self._bet_buttons:
            b.update(dt_val)
        self._clear_btn.update(dt_val)

        if self.mode == "lan_host":
            self._sync_online_table()

    # ── Renderitzat ───────────────────────────────────────────────
    def draw(self, surf):
        # Fons
        surf.fill(C["bg"])

        # Feltre de taula
        tw, th = 900, 480
        tx = (SCREEN_W - tw) // 2
        ty = (SCREEN_H - th) // 2 - 20
        draw_rect_alpha(surf, C["felt_bj"], (tx, ty, tw, th), 220, 16)
        pygame.draw.rect(surf, C["table_edge"], (tx, ty, tw, th), 4, border_radius=16)

        # Línia semicircular del crupier
        pygame.draw.arc(surf, C["table_edge"],
                        (tx+60, ty+10, tw-120, th//2),
                        math.pi, math.pi*2, 3)

        # Títol
        text(surf, "BLACKJACK", "big", C["neon_gold"],
             SCREEN_W//2, ty+14, anchor="center")
        _draw_mode_banner(surf, self.mode, self.room)

        gold_line = lambda x1,y1,x2,y2: pygame.draw.line(
            surf, C["ui_border"], (x1,y1),(x2,y2), 1)

        # ── Mà del crupier ────────────────────────────────────────
        dealer_y = ty + 60
        _draw_hand_centered(
            surf,
            self.dealer_hand,
            SCREEN_W // 2,
            dealer_y,
            hide_second=(self.state == "player"),
        )
        dv_show = _hand_value([self.dealer_hand[0]]) if self.state == "player" else _hand_value(self.dealer_hand)
        text(surf, f"Crupier: {dv_show}", "med", C["ui_text"],
             SCREEN_W//2, dealer_y - 24, anchor="center")

        # ── Mà del jugador ────────────────────────────────────────
        player_y = ty + th - 130
        _draw_hand_centered(surf, self.player_hand, SCREEN_W//2, player_y)

        pv = _hand_value(self.player_hand)
        pv_color = (C["ui_red"] if _is_bust(self.player_hand)
                    else C["ui_green"] if pv == 21
                    else C["ui_text"])
        text(surf, f"Tu: {pv}", "med", pv_color,
             SCREEN_W//2, player_y + CH + 8, anchor="center")

        # Split
        if self.split_hand:
            split_x = SCREEN_W//2 + 220
            _draw_hand_centered(surf, self.split_hand, split_x, player_y)
            sv = _hand_value(self.split_hand)
            text(surf, f"Split: {sv}", "small", C["ui_text"],
                 split_x, player_y + CH + 8, anchor="center")
            if self.active_hand == 1:
                pygame.draw.rect(surf, C["neon_gold"],
                                 (split_x-50, player_y-4, 100, CH+8), 2, border_radius=4)

        # ── BET screen ────────────────────────────────────────────
        if self.mode != "lan_client" and self.state == "bet":
            _draw_bet_panel(surf, self.bet)
            for b in self._bet_buttons:
                b.draw(surf)
            self._clear_btn.draw(surf)
            self._btns["deal"].draw(surf)

        # ── PLAYER screen ─────────────────────────────────────────
        elif self.mode != "lan_client" and self.state == "player":
            self._btns["hit"].draw(surf)
            self._btns["stand"].draw(surf)
            if STATE["chips"] >= self.bet and len(self.player_hand) == 2:
                self._btns["double"].draw(surf)
            hand = self.player_hand
            if (len(hand)==2
                    and _card_value(hand[0][0])==_card_value(hand[1][0])
                    and not self.split_hand
                    and STATE["chips"] >= self.bet):
                self._btns["split"].draw(surf)

        # ── RESULT ────────────────────────────────────────────────
        elif self.state == "result":
            draw_result_screen(surf, self.result, self.chips_delta)

        # Botó sortir
        self._btns["back"].draw(surf)

        # HUD
        draw_hud(surf)

        if self.mode == "lan_client" and not self._remote_ok:
            draw_panel(surf, (SCREEN_W//2-210, 110, 420, 90), alpha=225, radius=12)
            text(surf, "Esperando la mesa del host...", "med", C["ui_text"],
                 SCREEN_W//2, 144, anchor="center")
            text(surf, "Cuando el host abra Blackjack verás la partida aquí.",
                 "small", C["ui_sub"], SCREEN_W//2, 174, anchor="center")

        # Missatges flotants
        for m in self._float_msgs:
            m.draw(surf)


def _draw_hand_centered(surf, hand, cx, cy, hide_second=False):
    n   = len(hand)
    if n == 0:
        return
    gap = min(CW + 8, (700 // max(n,1)))
    total_w = (n-1)*gap + CW
    start_x = cx - total_w//2

    for i, (rank, suit) in enumerate(hand):
        x = start_x + i * gap
        face_up = not (i == 1 and hide_second)
        card_surf = make_card(rank, suit, CW, CH, face_up=face_up)
        # Ombra
        shadow = pygame.Surface((CW+4, CH+4), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0,0,0,80), (3,3,CW,CH), border_radius=6)
        surf.blit(shadow, (x-1, cy-1))
        surf.blit(card_surf, (x, cy))


def _draw_bet_panel(surf, bet):
    pw, ph = 340, 90
    px = (SCREEN_W - pw)//2
    py = SCREEN_H//2 - 10
    draw_panel(surf, (px, py, pw, ph), alpha=220, radius=10)
    text(surf, "APOSTA ACTUAL", "small", C["ui_sub"],
         SCREEN_W//2, py+12, anchor="center")
    text(surf, f"{bet} chips", "big", C["chips"],
         SCREEN_W//2, py+38, anchor="center")

    # Fitxes
    chip_vals = [10, 25, 50, 100, 250]
    for i, v in enumerate(chip_vals):
        chip = make_chip(min(v, 100), 28)
        cx = px - 160 + i*90 + 40
        surf.blit(chip, (cx, py + ph + 40))


def _draw_mode_banner(surf, mode, room):
    labels = {
        "solo": "Mesa local",
        "bots": "Bots locales",
        "lan_host": f"Grupo LAN · Host · {room}",
        "lan_client": f"Grupo LAN · Invitado · {room}",
    }
    draw_panel(surf, (18, 18, 250, 50), alpha=210, radius=10)
    text(surf, labels.get(mode, mode), "small", C["ui_text"], 30, 32)
    text(surf, "En LAN se comparte la mesa en tiempo real.", "tiny", C["ui_sub"],
         30, 54)
