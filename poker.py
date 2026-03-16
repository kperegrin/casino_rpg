# ═══════════════════════════════════════════════════════════════════
#  POKER — Texas Hold'em (jugador vs 2 bots)
# ═══════════════════════════════════════════════════════════════════
import pygame
import random
import math
from settings import C, STATE, SCREEN_W, SCREEN_H
from ui import (Button, draw_panel, draw_hud, draw_result_screen,
                text, draw_rect_alpha, F, FloatMessage)
from card_renderer import make_card, make_chip

RANKS   = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
SUITS_L = ["♠","♥","♦","♣"]
RANK_V  = {r:i for i,r in enumerate(RANKS)}
CW, CH  = 60, 84

# ── Baralla ──────────────────────────────────────────────────────────
def _new_deck():
    d = [(r,s) for r in RANKS for s in SUITS_L]
    random.shuffle(d)
    return d

# ── Avaluació de mans (complet) ────────────────────────────────────
def _best5(cards):
    """Retorna la millor mà de 5 entre totes les combinacions de 7."""
    from itertools import combinations
    best = None
    for combo in combinations(cards, 5):
        score = _score5(list(combo))
        if best is None or score > best:
            best = score
    return best

def _score5(hand):
    """Retorna una tupla comparable per determinar el guanyador."""
    ranks = sorted([RANK_V[r] for r,_ in hand], reverse=True)
    suits = [s for _,s in hand]
    flush  = len(set(suits)) == 1
    straight = (ranks == list(range(ranks[0], ranks[0]-5, -1))
                or ranks == [12,3,2,1,0])  # A-2-3-4-5

    counts = {}
    for r in ranks:
        counts[r] = counts.get(r,0)+1
    freq = sorted(counts.values(), reverse=True)
    groups = sorted(counts.keys(),
                    key=lambda r: (counts[r], r), reverse=True)

    if straight and flush:
        return (8, ranks[0])
    if freq[0] == 4:
        return (7, groups[0], groups[1])
    if freq[:2] == [3,2]:
        return (6, groups[0], groups[1])
    if flush:
        return (5,) + tuple(ranks)
    if straight:
        return (4, ranks[0])
    if freq[0] == 3:
        return (3, groups[0]) + tuple(groups[1:3])
    if freq[:2] == [2,2]:
        return (2, max(groups[:2]), min(groups[:2]), groups[2])
    if freq[0] == 2:
        return (1, groups[0]) + tuple(groups[1:4])
    return (0,) + tuple(ranks)

HAND_NAMES = {
    8:"Escala de Color",7:"Poker",6:"Full",5:"Color",
    4:"Escala",3:"Trio",2:"Doble Parella",1:"Parella",0:"Carta Alta"
}

def _hand_name(score):
    return HAND_NAMES.get(score[0],"?")

# ── IA bàsica ─────────────────────────────────────────────────────
def _bot_action(hand, community, pot, call_amount, chips, stage):
    """Decisió simple basada en la força de la mà."""
    all_cards = hand + community
    if len(all_cards) >= 5:
        score = _best5(all_cards)[0]
    elif len(all_cards) >= 2:
        # Pre-flop: parella, carta alta
        v1, v2 = RANK_V[hand[0][0]], RANK_V[hand[1][0]]
        score = 1 if v1==v2 else (0 if max(v1,v2) < 8 else 0)
    else:
        score = 0

    # Decisió
    if score >= 5 or (score >= 2 and random.random() < 0.7):
        return "raise", min(call_amount*2+random.randint(10,50), chips)
    if score >= 1 or call_amount == 0:
        return "call", call_amount
    if random.random() < 0.3:
        return "call", call_amount
    return "fold", 0


# ═══════════════════════════════════════════════════════════════════
class PokerGame:

    BIG_BLIND  = 20
    SMALL_BLIND= 10

    def __init__(self, config=None):
        self.config = config or {"mode": "bots", "room": "Royal"}
        self.mode   = self.config.get("mode", "bots")
        if self.mode == "solo":
            self.mode = "bots"
        self.room   = self.config.get("room", "Royal")
        self._remote_ok = self.mode != "lan_client"
        self.deck   = _new_deck()
        self.state  = "bet_setup"   # bet_setup|preflop|flop|turn|river|showdown|result
        self.bet    = 50
        self.chips  = [STATE["chips"], 800, 800]
        self.hands  = [[], [], []]
        self.folded = [True, True, True]
        self.active = 0
        self.community = []
        self.pot    = 0
        self.current_bets = [0,0,0]
        self.call_amount  = 0
        self.result       = ""
        self.chips_delta  = 0
        self._bot_timer   = 0.0
        self._bot_delay   = 1.2
        self._show_bots   = False
        self._float_msgs  = []
        self._stage_label = ""

        bw, bh = 110, 44
        yr = SCREEN_H - 72
        self._btns = {
            "call":  Button(SCREEN_W//2-170, yr, bw, bh, "CALL",  color=(20,80,20)),
            "raise": Button(SCREEN_W//2-50,  yr, bw, bh, "RAISE", color=(60,60,10)),
            "fold":  Button(SCREEN_W//2+70,  yr, bw, bh, "FOLD",  color=(80,20,20)),
            "deal":  Button(SCREEN_W//2-55,  SCREEN_H-72, 110, bh, "DEAL", color=(20,80,20)),
            "back":  Button(30, SCREEN_H-70, 100, 40, "◀ SORTIR",
                            color=(60,20,20), font="small"),
        }
        self._raise_btns = [
            Button(SCREEN_W//2-200+i*90, SCREEN_H-120, 80, 32,
                   f"+{v}", color=(40,40,80))
            for i,v in enumerate([20,50,100,200])
        ]
        self._raise_amount = self.BIG_BLIND * 2
        self.local_player_id = STATE.get("net_my_id", 0)
        self.local_seat = 0
        self.seat_ids = [0, -1, -2]
        self.seat_names = ["Tu", "Bot1", "Bot2"]
        self._build_seats()

    def _build_seats(self):
        if self.mode == "bots":
            self.local_player_id = 0
            self.local_seat = 0
            self.seat_ids = [0, -1, -2]
            self.seat_names = [STATE.get("player_name", "Tu"), "Bot1", "Bot2"]
            self.folded = [False, False, False]
            self.chips = [STATE["chips"], 800, 800]
            return

        self.local_player_id = STATE.get("net_my_id", 0)
        if self.mode == "lan_client":
            self.seat_ids = [0, None, None]
            self.seat_names = ["Host", "Jugador2", "Jugador3"]
            self.local_seat = 0
            self.folded = [False, True, True]
            return

        ids = []
        if STATE.get("net_mode") == "host":
            server = STATE.get("net_server")
            if server:
                ids = list(server.player_ids)
        elif STATE.get("net_mode") == "client":
            ids = [self.local_player_id] + [int(pid) for pid in STATE.get("net_players", {}).keys()]

        unique_ids = []
        for pid in ids:
            if pid not in unique_ids:
                unique_ids.append(pid)
        unique_ids = unique_ids[:3]
        while len(unique_ids) < 3:
            unique_ids.append(None)

        self.seat_ids = unique_ids
        self.seat_names = []
        net_players = STATE.get("net_players", {})
        for pid in self.seat_ids:
            if pid is None:
                self.seat_names.append("Libre")
            elif int(pid) == int(self.local_player_id):
                self.seat_names.append(STATE.get("player_name", "Tu"))
            elif pid == 0 and STATE.get("net_mode") == "client":
                self.seat_names.append("Host")
            else:
                pdata = net_players.get(pid) or net_players.get(str(pid), {})
                self.seat_names.append(pdata.get("name", f"J{pid}"))

        self.local_seat = self._seat_from_player(self.local_player_id)
        if self.local_seat < 0:
            self.local_seat = 0
        for i in range(3):
            if self.seat_ids[i] is None:
                self.folded[i] = True

    def _seat_from_player(self, player_id):
        for i, pid in enumerate(self.seat_ids):
            if pid is None:
                continue
            try:
                if int(pid) == int(player_id):
                    return i
            except Exception:
                pass
        return -1

    def _active_seats(self):
        return [i for i in range(3) if self.seat_ids[i] is not None and not self.folded[i]]

    def _next_active_from(self, current):
        idx = current
        for _ in range(3):
            idx = (idx + 1) % 3
            if self.seat_ids[idx] is not None and not self.folded[idx]:
                return idx
        return current

    def _is_bot_seat(self, seat_idx):
        pid = self.seat_ids[seat_idx]
        return pid is not None and pid < 0

    def _update_local_chips(self):
        seat = self._seat_from_player(self.local_player_id)
        if 0 <= seat < 3:
            STATE["chips"] = int(self.chips[seat])

    def _serialize_state(self):
        return {
            "state": self.state,
            "bet": self.bet,
            "chips": self.chips,
            "hands": self.hands,
            "folded": self.folded,
            "active": self.active,
            "community": self.community,
            "pot": self.pot,
            "current_bets": self.current_bets,
            "call_amount": self.call_amount,
            "result": self.result,
            "chips_delta": self.chips_delta,
            "show_bots": self._show_bots,
            "stage_label": self._stage_label,
            "raise_amount": self._raise_amount,
            "seat_ids": self.seat_ids,
            "seat_names": self.seat_names,
            "room": self.room,
        }

    def _apply_remote_state(self, data):
        self.state = data.get("state", self.state)
        self.bet = data.get("bet", self.bet)
        self.chips = data.get("chips", self.chips)
        self.hands = data.get("hands", self.hands)
        self.folded = data.get("folded", self.folded)
        self.active = data.get("active", self.active)
        self.community = data.get("community", self.community)
        self.pot = data.get("pot", self.pot)
        self.current_bets = data.get("current_bets", self.current_bets)
        self.call_amount = data.get("call_amount", self.call_amount)
        self.result = data.get("result", self.result)
        self.chips_delta = data.get("chips_delta", self.chips_delta)
        self._show_bots = data.get("show_bots", self._show_bots)
        self._stage_label = data.get("stage_label", self._stage_label)
        self._raise_amount = data.get("raise_amount", self._raise_amount)
        self.seat_ids = data.get("seat_ids", self.seat_ids)
        self.seat_names = data.get("seat_names", self.seat_names)
        self.room = data.get("room", self.room)
        self.local_seat = self._seat_from_player(self.local_player_id)
        self._update_local_chips()
        self._remote_ok = True

    def _broadcast_state(self):
        payload = {
            "type": "table_state",
            "game": "poker",
            "room": self.room,
            "state": self._serialize_state(),
        }
        server = STATE.get("net_server")
        if self.mode == "lan_host" and server:
            server.broadcast(payload)
            return
        client = STATE.get("net_client")
        if self.mode == "lan_host" and client and client.connected:
            client.send(payload)

    def _send_action(self, action, amount=0):
        client = STATE.get("net_client")
        if client and client.connected:
            client.send({
                "type": "poker_action",
                "room": self.room,
                "actor_id": self.local_player_id,
                "action": action,
                "amount": amount,
            })

    def _poll_network(self):
        if self.mode == "lan_host":
            server = STATE.get("net_server")
            if server:
                while not server.inbox.empty():
                    try:
                        msg = server.inbox.get_nowait()
                    except Exception:
                        break
                    if msg.get("type") != "poker_action":
                        continue
                    actor_id = msg.get("actor_id", msg.get("_from"))
                    seat = self._seat_from_player(actor_id)
                    if seat >= 0 and seat == self.active and self.state not in ("bet_setup", "result"):
                        self._apply_action(seat, msg.get("action", "call"), msg.get("amount", 0))
            client = STATE.get("net_client")
            if client and client.connected:
                for msg in client.poll():
                    if msg.get("type") == "poker_action":
                        seat = self._seat_from_player(msg.get("actor_id"))
                        if seat >= 0 and seat == self.active and self.state not in ("bet_setup", "result"):
                            self._apply_action(seat, msg.get("action", "call"), msg.get("amount", 0))
            return

        if self.mode == "lan_client":
            client = STATE.get("net_client")
            if client and client.connected:
                for msg in client.poll():
                    if msg.get("type") == "table_state" and msg.get("game") == "poker":
                        self._apply_remote_state(msg.get("state", {}))

    # ── Lògica ───────────────────────────────────────────────────
    def _deal_round(self):
        self._build_seats()
        participants = [i for i, pid in enumerate(self.seat_ids) if pid is not None]
        if len(participants) < 2:
            self._float_msgs.append(FloatMessage(
                "Necesitas al menos 2 jugadores conectados para Poker online",
                SCREEN_W//2, SCREEN_H//2, C["ui_red"], 3.0))
            return

        self.deck = _new_deck()
        self.hands = [[], [], []]
        self.folded = [True, True, True]
        self.community = []
        self.pot = 0
        self.current_bets = [0,0,0]
        self._show_bots = False
        self.result = ""

        for _ in range(2):
            for i in participants:
                self.hands[i].append(self.deck.pop())
                self.folded[i] = False

        sb, bb = self.SMALL_BLIND, self.BIG_BLIND
        sb_idx = participants[0]
        bb_idx = participants[1]
        self.chips[sb_idx] = max(0, self.chips[sb_idx] - sb)
        self.chips[bb_idx] = max(0, self.chips[bb_idx] - bb)
        self.current_bets[sb_idx] = sb
        self.current_bets[bb_idx] = bb
        self.pot         = sb + bb
        self.call_amount = bb
        self.active      = self._next_active_from(bb_idx)
        self.state       = "preflop"
        self._stage_label= "PRE-FLOP"
        self._update_local_chips()

    def _next_stage(self):
        self.current_bets = [0,0,0]
        self.call_amount  = 0
        active = self._active_seats()
        if not active:
            self.state = "result"
            return
        self.active = active[0]
        if self.state == "preflop":
            self.community += [self.deck.pop() for _ in range(3)]
            self.state = "flop"
            self._stage_label = "FLOP"
        elif self.state == "flop":
            self.community.append(self.deck.pop())
            self.state = "turn"
            self._stage_label = "TURN"
        elif self.state == "turn":
            self.community.append(self.deck.pop())
            self.state = "river"
            self._stage_label = "RIVER"
        elif self.state == "river":
            self._showdown()

    def _apply_action(self, seat_idx, action, amount=0):
        if self.folded[seat_idx]:
            return
        if action == "fold":
            self.folded[seat_idx] = True
        elif action == "call":
            to_call = max(0, self.call_amount - self.current_bets[seat_idx])
            amt = min(to_call, self.chips[seat_idx])
            self.chips[seat_idx] -= amt
            self.pot      += amt
            self.current_bets[seat_idx] += amt
        elif action == "raise":
            target = max(self.call_amount + self.BIG_BLIND, int(amount))
            target = min(target, self.current_bets[seat_idx] + self.chips[seat_idx])
            paid = max(0, target - self.current_bets[seat_idx])
            self.chips[seat_idx] -= paid
            self.pot             += paid
            self.current_bets[seat_idx] = target
            self.call_amount            = target

        active_players = self._active_seats()
        if len(active_players) == 1:
            self._award(active_players[0])
            return

        self.active = self._next_active_from(seat_idx)
        self._check_stage_complete()
        self._update_local_chips()

    def _bot_turn(self, bot_idx):
        action, amount = _bot_action(
            self.hands[bot_idx], self.community,
            self.pot, self.call_amount,
            self.chips[bot_idx], self.state
        )
        self._apply_action(bot_idx, action, amount)
        self._float_msgs.append(FloatMessage(
            f"{self.seat_names[bot_idx]} {action.upper()}",
            SCREEN_W//2, SCREEN_H//2 - 60 + bot_idx*30,
            C["ui_sub"]
        ))

    def _check_stage_complete(self):
        active = self._active_seats()
        if not active:
            return
        bets = [self.current_bets[i] for i in active]
        if len(set(bets)) <= 1 and all(self.current_bets[i] >= self.call_amount for i in active):
            self._next_stage()

    def _showdown(self):
        self._show_bots = True
        active = self._active_seats()
        if len(active) == 1:
            self._award(active[0])
            return

        scores = {
            i: _best5(self.hands[i] + self.community)
            for i in active
        }
        winner = max(scores, key=lambda i: scores[i])
        self._award(winner, show=True, scores=scores)

    def _award(self, winner, show=False, scores=None):
        self.chips[winner] += self.pot
        before = STATE["chips"]
        self._update_local_chips()
        delta = STATE["chips"] - before

        if winner == self.local_seat:
            self.result = "GUANYES EL POT!"
            STATE["wins"] += 1
        else:
            self.result = f"Guanya {self.seat_names[winner]}"
            STATE["losses"] += 1

        if show and scores:
            self.result += f"\n{_hand_name(scores[winner])}"

        self.chips_delta = delta
        self.state = "result"

    # ── Events ───────────────────────────────────────────────────
    def handle_event(self, event):
        if self._btns["back"].clicked(event):
            return "exit"

        if self.state == "result":
            if (event.type==pygame.KEYDOWN
                    and event.key==pygame.K_SPACE
                    and self.mode != "lan_client"):
                self.state = "bet_setup"
            return None

        if self.state == "bet_setup":
            if self.mode == "lan_client":
                return None
            if self._btns["deal"].clicked(event):
                self._deal_round()
            return None

        is_local_turn = (self.active == self.local_seat)
        if not is_local_turn:
            return None

        if self._btns["fold"].clicked(event):
            if self.mode == "lan_client":
                self._send_action("fold")
            else:
                self._apply_action(self.local_seat, "fold")
        elif self._btns["call"].clicked(event):
            if self.mode == "lan_client":
                self._send_action("call")
            else:
                self._apply_action(self.local_seat, "call")
        elif self._btns["raise"].clicked(event):
            if self.mode == "lan_client":
                self._send_action("raise", self._raise_amount)
            else:
                self._apply_action(self.local_seat, "raise", self._raise_amount)

        for b in self._raise_btns:
            if b.clicked(event):
                v = int(b.label[1:])
                self._raise_amount = min(
                    self._raise_amount + v, self.chips[self.local_seat])

        return None

    def update(self, dt):
        self._poll_network()

        if (self.mode != "lan_client"
                and self._is_bot_seat(self.active)
                and self.state not in ("result","bet_setup")):
            self._bot_timer -= dt
            if self._bot_timer <= 0:
                self._bot_turn(self.active)
                self._bot_timer = self._bot_delay

        for m in self._float_msgs:
            m.update(dt)
        self._float_msgs = [m for m in self._float_msgs if not m.done]

        for btn in self._btns.values():
            btn.update(dt)
        for b in self._raise_btns:
            b.update(dt)

        if self.mode == "lan_host":
            self._broadcast_state()

    # ── Renderitzat ───────────────────────────────────────────────
    def draw(self, surf):
        surf.fill(C["bg"])
        _draw_mode_banner(surf, self.mode, self.room)

        # Taula oval
        tw, th = 800, 420
        tx, ty = (SCREEN_W-tw)//2, (SCREEN_H-th)//2 - 10
        shadow = pygame.Surface((tw+16,th+16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0,0,0,120), (0,0,tw+16,th+16))
        surf.blit(shadow, (tx-8, ty+6))
        pygame.draw.ellipse(surf, C["table_edge"], (tx-8, ty-8, tw+16, th+16))
        pygame.draw.ellipse(surf, C["felt_poker"], (tx, ty, tw, th))

        # Títol
        text(surf, "TEXAS HOLD'EM POKER", "big", C["neon_gold"],
             SCREEN_W//2, ty+14, anchor="center")

        # Etapa
        if self._stage_label:
            text(surf, self._stage_label, "med", C["ui_sub"],
                 SCREEN_W//2, ty+44, anchor="center")

        # Pot
        text(surf, f"POT: {self.pot}", "med", C["chips"],
             SCREEN_W//2, ty+64, anchor="center")

        # Community cards
        if self.community:
            _draw_cards_row(surf, self.community,
                             SCREEN_W//2, SCREEN_H//2 - 20)

        # Mans laterals
        side_order = [i for i in range(3) if i != self.local_seat]
        side_positions = [1, -1]
        for side_idx, i in enumerate(side_order):
            if side_idx >= 2:
                continue
            bx = SCREEN_W//2 + (1 if i==1 else -1) * 300
            if side_idx < len(side_positions):
                bx = SCREEN_W//2 + side_positions[side_idx] * 300
            by = SCREEN_H//2 - 120
            if self.seat_ids[i] is None:
                text(surf, "Seient lliure", "small", C["ui_sub"], bx, by, anchor="center")
                continue
            if self.folded[i]:
                text(surf, f"{self.seat_names[i]} FOLD", "small", C["ui_red"], bx, by, anchor="center")
            else:
                face_up = (i == self.local_seat) or self._show_bots or self.state in ("showdown","result")
                _draw_cards_row(surf, self.hands[i], bx, by, face_up=face_up)
                text(surf, f"{self.seat_names[i]}  {self.chips[i]}✦",
                     "small", C["ui_text"], bx, by-22, anchor="center")
                if self.active == i:
                    text(surf, "...", "med", C["neon_gold"], bx, by+CH+6, anchor="center")

        # Mà local
        ph_y = SCREEN_H - 200
        _draw_cards_row(surf, self.hands[self.local_seat], SCREEN_W//2, ph_y)
        text(surf, f"{self.seat_names[self.local_seat]}  {self.chips[self.local_seat]}✦  |  Aposta: {self._raise_amount}",
             "small", C["ui_text"], SCREEN_W//2, ph_y-22, anchor="center")

        # Botons
        if self.mode != "lan_client" and self.state == "bet_setup":
            self._btns["deal"].draw(surf)
        elif (self.mode != "lan_client"
                and self.state not in ("result",)
                and self.active == self.local_seat):
            call_lbl = f"CALL {self.call_amount}" if self.call_amount else "CHECK"
            self._btns["call"].label = call_lbl
            self._btns["call"].draw(surf)
            self._btns["raise"].draw(surf)
            self._btns["fold"].draw(surf)
            for b in self._raise_btns:
                b.draw(surf)
        elif (self.mode == "lan_client"
                and self.state not in ("result", "bet_setup")
                and self.active == self.local_seat):
            call_lbl = f"CALL {self.call_amount}" if self.call_amount else "CHECK"
            self._btns["call"].label = call_lbl
            self._btns["call"].draw(surf)
            self._btns["raise"].draw(surf)
            self._btns["fold"].draw(surf)
            for b in self._raise_btns:
                b.draw(surf)

        if self.state == "result":
            draw_result_screen(surf, self.result, self.chips_delta)

        self._btns["back"].draw(surf)
        draw_hud(surf)

        if self.mode == "lan_client" and not self._remote_ok:
            draw_panel(surf, (SCREEN_W//2-220, 92, 440, 90), alpha=225, radius=12)
            text(surf, "Esperando la mesa LAN del host...", "med", C["ui_text"],
                 SCREEN_W//2, 126, anchor="center")
            text(surf, "Aquí verás la partida compartida cuando empiece.",
                 "small", C["ui_sub"], SCREEN_W//2, 156, anchor="center")

        for m in self._float_msgs:
            m.draw(surf)


def _draw_cards_row(surf, cards, cx, cy, face_up=True):
    n = len(cards)
    if n == 0:
        return
    gap = min(CW+6, 600//max(n,1))
    total_w = (n-1)*gap + CW
    sx = cx - total_w//2
    for i,(r,s) in enumerate(cards):
        x = sx + i*gap
        card_surf = make_card(r, s, CW, CH, face_up=face_up)
        shadow = pygame.Surface((CW+4,CH+4), pygame.SRCALPHA)
        pygame.draw.rect(shadow,(0,0,0,80),(3,3,CW,CH),border_radius=6)
        surf.blit(shadow,(x-1,cy-1))
        surf.blit(card_surf,(x,cy))


def _draw_mode_banner(surf, mode, room):
    labels = {
        "bots": "Bots locales",
        "lan_host": f"Grupo LAN · Host · {room}",
        "lan_client": f"Grupo LAN · Invitado · {room}",
    }
    draw_panel(surf, (18, 18, 250, 50), alpha=210, radius=10)
    text(surf, labels.get(mode, mode), "small", C["ui_text"], 30, 32)
    text(surf, "Modo LAN comparte la mesa con tu grupo.", "tiny", C["ui_sub"],
         30, 54)
