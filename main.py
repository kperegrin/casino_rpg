# ═══════════════════════════════════════════════════════════════════
#  MAIN — Grand Casino Royal  (v2.0 — Xarxa LAN + Llegibilitat)
# ═══════════════════════════════════════════════════════════════════
import pygame
import sys
import math
from settings import (SCREEN_W, SCREEN_H, FPS, TITLE, C, STATE, TILE)
from camera  import Camera
from world   import World, ZONES, ZONE_NAMES, ZONE_INTERACT
from player  import Player
from ui      import (draw_hud, draw_panel, draw_rect_alpha, text,
                     FadeTransition, FloatMessage, Button, F)
from blackjack import BlackjackGame
from poker     import PokerGame
from roulette  import RouletteGame
from slots     import SlotsGame
from bowling   import BowlingGame
from dice_duel import DiceDuelGame
from network   import GameServer, GameClient


def _draw_net_players(surf, cam_x, cam_y, my_id):
    """Dibuixa els avatars dels altres jugadors connectats."""
    net_players = STATE.get("net_players", {})
    for pid, pdata in net_players.items():
        # Comparació robusta — pid pot arribar com int o string des del JSON
        try:
            if int(pid) == int(my_id):
                continue
        except (ValueError, TypeError):
            pass

        px = int(pdata.get("x", 0)) - cam_x
        py = int(pdata.get("y", 0)) - cam_y

        # Culling — no dibuixar si fora de pantalla
        sw = surf.get_width()
        sh = surf.get_height()
        if not (-60 < px < sw + 60 and -60 < py < sh + 60):
            continue

        colors = [(220, 80, 80), (80, 80, 220), (80, 200, 80), (220, 200, 60)]
        try:
            col = colors[int(pid) % len(colors)]
        except Exception:
            col = colors[0]

        # Ombra al terra
        shadow = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, 28, 10))
        surf.blit(shadow, (px - 14, py + 12))

        # Cos del personatge
        pygame.draw.ellipse(surf, tuple(max(0, c - 40) for c in col),
                            (px - 8, py - 10, 16, 20))   # ombra cos
        pygame.draw.ellipse(surf, col, (px - 7, py - 12, 14, 18))

        # Cap
        pygame.draw.circle(surf, (210, 170, 130), (px, py - 18), 6)
        # Ulls
        pygame.draw.circle(surf, (30, 20, 10), (px - 2, py - 19), 1)
        pygame.draw.circle(surf, (30, 20, 10), (px + 2, py - 19), 1)

        # Nom i chips sobre el personatge
        name = pdata.get("name", f"P{pid}")
        chips = pdata.get("chips", 0)
        try:
            fn = pygame.font.SysFont("Arial", 13, bold=True)

            # Fons del nom per llegibilitat
            name_surf = fn.render(name, True, (255, 255, 200))
            chip_surf = fn.render(f"{chips:,} ✦", True, C["chips"])

            # Centrar sobre el jugador
            nx = px - name_surf.get_width() // 2
            ny = py - 38
            cx2 = px - chip_surf.get_width() // 2
            cy2 = py - 24

            # Fons semitransparent
            bg_w = max(name_surf.get_width(), chip_surf.get_width()) + 8
            bg = pygame.Surface((bg_w, 28), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            surf.blit(bg, (px - bg_w // 2, ny - 2))

            surf.blit(name_surf, (nx, ny))
            surf.blit(chip_surf, (cx2, cy2))
        except Exception:
            pass


class MenuScene:
    # Alçada total del contingut del panell (calculada dinàmicament)
    # Layout vertical fix: títol → subtítol → línia → [panell central] → version
    # El panell central conté: label+camp_nom, label+camp_ip, 4 botons, missatge estat
    # Tots els elements es calculen a _build_layout() en base a SW/SH reals.

    FIELD_H  = 38   # alçada dels camps de text
    BTN_H    = 48   # alçada dels botons principals
    BTN_H_SM = 40   # alçada botó "Sortir"
    GAP      = 10   # espai entre elements
    LABEL_H  = 16   # espai per a l'etiqueta sobre cada camp

    def __init__(self):
        self._time       = 0.0
        self._cursor_t   = 0.0
        self._name_var   = STATE["player_name"]
        self._ip_var     = STATE.get("net_host_ip", "")
        self._editing    = "name"
        self._status_msg = ""
        self._status_col = C["ui_sub"]

        SW, SH = pygame.display.get_surface().get_size()
        self._SW = SW
        self._SH = SH
        self._stars = [
            (pygame.Vector2(pygame.time.get_ticks() % SW, i * 37 % SH),
             (i % 3) * 0.4 + 0.2)
            for i in range(80)
        ]
        self._build_layout(SW, SH)

    def _build_layout(self, SW, SH):
        """Calcula tots els rects i botons en base a la mida real de la finestra."""
        # Ample del panell central (màx 340, mínim 260, adaptat a SW)
        pw = min(340, max(260, SW // 4))
        cx = SW // 2
        bw = pw  # botons igual d'amples que el panell

        # Reservem espai per: títol (part superior), versió (part inferior)
        # El panell central comença a ~45% de SH
        title_cy    = int(SH * 0.20)   # centre del títol
        subtitle_y  = int(SH * 0.32)
        divider_y   = int(SH * 0.37)

        # Primer element del panell: camp nom (amb etiqueta)
        y = divider_y + 18

        # Camp nom
        self._name_rect = pygame.Rect(cx - pw // 2, y + self.LABEL_H, pw, self.FIELD_H)
        y = self._name_rect.bottom + self.GAP

        # Camp IP
        self._ip_rect = pygame.Rect(cx - pw // 2, y + self.LABEL_H, pw, self.FIELD_H)
        y = self._ip_rect.bottom + self.GAP + 6

        # 4 botons verticals
        btn_colors = [
            (100, 70, 10),   # or — entrar sol
            (20, 80, 40),    # verd — host
            (20, 40, 90),    # blau — client
            (70, 20, 20),    # roig — sortir
        ]
        btn_labels = [
            "ENTRAR AL CASINO (sol)",
            "CREAR PARTIDA  (host LAN)",
            "UNIR-SE A PARTIDA  (LAN)",
            "SORTIR",
        ]
        btn_heights = [self.BTN_H, self.BTN_H, self.BTN_H, self.BTN_H_SM]

        self._btns = []
        self._btn_y_start = y
        for i in range(4):
            bh = btn_heights[i]
            btn = Button(cx - bw // 2, y, bw, bh, btn_labels[i],
                         color=btn_colors[i])
            self._btns.append(btn)
            y += bh + self.GAP

        # Zona del missatge d'estat (baix dels botons)
        self._status_y = y + 4

        # Guardem referències per al draw
        self._title_cy   = title_cy
        self._subtitle_y = subtitle_y
        self._divider_y  = divider_y
        self._cx         = cx
        self._pw         = pw

    def handle_event(self, event):
        # Redimensió dinàmica si la finestra canvia de mida
        if event.type == pygame.VIDEORESIZE:
            self._SW, self._SH = event.w, event.h
            self._build_layout(event.w, event.h)
            return None

        if event.type == pygame.KEYDOWN:
            if self._editing == "name":
                if event.key == pygame.K_RETURN:
                    self._editing = "none"
                    STATE["player_name"] = self._name_var or "Jugador"
                elif event.key == pygame.K_BACKSPACE:
                    self._name_var = self._name_var[:-1]
                elif event.unicode.isprintable() and len(self._name_var) < 16:
                    self._name_var += event.unicode
            elif self._editing == "ip":
                if event.key == pygame.K_RETURN:
                    self._editing = "none"
                elif event.key == pygame.K_BACKSPACE:
                    self._ip_var = self._ip_var[:-1]
                elif event.unicode.isprintable() and len(self._ip_var) < 20:
                    self._ip_var += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._name_rect.collidepoint(event.pos):
                self._editing = "name"; return None
            if self._ip_rect.collidepoint(event.pos):
                self._editing = "ip";   return None
            self._editing = "none"

        if self._btns[0].clicked(event):
            STATE["player_name"] = self._name_var or "Jugador"
            STATE["net_mode"] = None
            return "world"

        if self._btns[1].clicked(event):
            STATE["player_name"] = self._name_var or "Jugador"
            server = GameServer()
            ip = server.start()
            STATE["net_server"] = server
            STATE["net_mode"]   = "host"
            STATE["net_my_id"]  = 0
            self._status_msg = f"Servidor actiu!  IP per als altres: {ip}"
            self._status_col = C["ui_green"]
            return "world"

        if self._btns[2].clicked(event):
            ip = self._ip_var.strip()
            if not ip:
                self._status_msg = "Introdueix la IP del host al camp de dalt"
                self._status_col = C["ui_red"]
                return None
            STATE["player_name"] = self._name_var or "Jugador"
            client = GameClient()
            if client.connect(ip, timeout=4.0):
                STATE["net_client"]  = client
                STATE["net_mode"]    = "client"
                STATE["net_host_ip"] = ip
                self._status_msg = f"Connectat a {ip}!"
                self._status_col = C["ui_green"]
                return "world"
            else:
                self._status_msg = f"No s'ha pogut connectar a {ip}"
                self._status_col = C["ui_red"]
            return None

        if self._btns[3].clicked(event):
            return "quit"
        return None

    def update(self, dt):
        self._time     += dt
        self._cursor_t += dt
        for b in self._btns:
            b.update(dt)

    def draw(self, surf):
        SW, SH = surf.get_size()

        # Si la mida ha canviat, reconstruir el layout
        if SW != self._SW or SH != self._SH:
            self._SW, self._SH = SW, SH
            self._build_layout(SW, SH)

        surf.fill(C["bg"])

        # ── Estrelles de fons ────────────────────────────────────
        for pos, speed in self._stars:
            pos.x = (pos.x + speed * 0.3) % SW
            r = max(1, int(speed * 2.5))
            a = int(100 + 80 * math.sin(self._time * speed + pos.y))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 220, 100, a), (r, r), r)
            surf.blit(s, (int(pos.x), int(pos.y)))

        # ── Títol (mida adaptada a l'ample) ─────────────────────
        title_size = max(36, min(72, SW // 18))
        t_scale = 1.0 + 0.03 * math.sin(self._time * 1.5)
        try:
            fnt = pygame.font.SysFont("Georgia", int(title_size * t_scale), bold=True)
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                gs = fnt.render("GRAND CASINO ROYAL", True, (180, 120, 0))
                gs.set_alpha(55)
                surf.blit(gs, gs.get_rect(center=(SW // 2 + dx, self._title_cy + dy)))
            mt = fnt.render("GRAND CASINO ROYAL", True, C["neon_gold"])
            surf.blit(mt, mt.get_rect(center=(SW // 2, self._title_cy)))
        except Exception:
            text(surf, "GRAND CASINO ROYAL", "title", C["neon_gold"],
                 SW // 2, self._title_cy, anchor="center")

        # ── Subtítol ─────────────────────────────────────────────
        text(surf, "◆  Poker  ·  Blackjack  ·  Ruleta  ◆",
             "med", C["ui_sub"], SW // 2, self._subtitle_y, anchor="center")

        # ── Línia divisòria ──────────────────────────────────────
        lw = min(self._pw + 80, SW - 40)
        pygame.draw.line(surf, C["ui_border"],
                         (SW // 2 - lw // 2, self._divider_y),
                         (SW // 2 + lw // 2, self._divider_y), 1)

        cur = int(self._cursor_t * 2) % 2 == 0

        # ── Camp nom ─────────────────────────────────────────────
        nr = self._name_rect
        text(surf, "El teu nom", "tiny", C["ui_sub"], nr.left, nr.top - 15)
        draw_panel(surf, nr, alpha=220, radius=6)
        bc = C["neon_gold"] if self._editing == "name" else C["ui_border"]
        pygame.draw.rect(surf, bc, nr, 2, border_radius=6)
        dn = self._name_var + ("|" if self._editing == "name" and cur else "")
        text(surf, dn or "El teu nom...", "small",
             C["ui_text"] if self._name_var else C["ui_sub"],
             nr.centerx, nr.centery, anchor="center")

        # ── Camp IP ──────────────────────────────────────────────
        ir = self._ip_rect
        text(surf, "IP del host  (per unir-se a LAN)", "tiny", C["ui_sub"],
             ir.left, ir.top - 15)
        draw_panel(surf, ir, alpha=220, radius=6)
        bc = C["neon_gold"] if self._editing == "ip" else C["ui_border"]
        pygame.draw.rect(surf, bc, ir, 2, border_radius=6)
        di = self._ip_var + ("|" if self._editing == "ip" and cur else "")
        text(surf, di or "p.ex.  192.168.1.10", "small",
             C["ui_text"] if self._ip_var else C["ui_sub"],
             ir.centerx, ir.centery, anchor="center")

        # ── Botons ───────────────────────────────────────────────
        for b in self._btns:
            b.draw(surf)

        # ── Missatge d'estat ─────────────────────────────────────
        if self._status_msg:
            msg_w = min(F["small"].size(self._status_msg)[0] + 28, SW - 40)
            msg_x = SW // 2 - msg_w // 2
            draw_rect_alpha(surf, (0, 0, 0), (msg_x, self._status_y, msg_w, 28), 190, 6)
            text(surf, self._status_msg, "small", self._status_col,
                 SW // 2, self._status_y + 14, anchor="center", shadow=False)

        # ── Peu de pàgina ────────────────────────────────────────
        text(surf, "v2.0  ·  LAN Multiplayer  ·  ENTER per confirmar camps",
             "tiny", C["ui_sub"], SW // 2, SH - 18, anchor="center")


class WorldScene:
    SYNC_INTERVAL = 0.05

    def __init__(self):
        self.world       = World()
        self.player      = Player()
        self.camera      = Camera()
        self.camera.snap(self.player.x, self.player.y)
        self._near_zone  = None
        self._float_msgs = []
        self._fade       = FadeTransition(0.4, fade_in=True)
        self._sync_t     = 0.0
        self._catalog_open = False
        self._setup_target = None
        self._setup_mode   = "solo"
        self._setup_room   = "Royal"
        self._setup_edit   = False
        self._setup_status = ""
        self._build_overlay_ui()

    def _build_overlay_ui(self):
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        labels = [
            ("poker", "POKER"),
            ("blackjack", "BLACKJACK"),
            ("roulette", "RULETA"),
            ("slots", "TRAGAPERRAS"),
            ("bowling", "BOLOS"),
            ("dice_duel", "DADOS"),
        ]
        self._catalog_buttons = []
        self._catalog_button_keys = {}
        for index, (game_key, label) in enumerate(labels):
            col = index % 3
            row = index // 3
            btn = Button(cx - 260 + col * 180, cy - 80 + row * 90,
                         150, 54, label, color=(35, 70, 35))
            self._catalog_buttons.append(btn)
            self._catalog_button_keys[id(btn)] = game_key

        self._catalog_close_btn = Button(cx - 80, cy + 122, 160, 42,
                                         "CERRAR", color=(70, 20, 20),
                                         font="small")
        self._setup_mode_buttons = {
            "solo": Button(cx - 210, cy - 8, 140, 44, "SOLO/BOTS",
                           color=(35, 80, 35), font="small"),
            "lan_host": Button(cx - 50, cy - 8, 160, 44, "CREAR GRUPO",
                               color=(20, 70, 90), font="small"),
            "lan_client": Button(cx + 130, cy - 8, 160, 44, "UNIRME",
                                 color=(90, 60, 15), font="small"),
        }
        self._setup_launch_btn = Button(cx - 110, cy + 92, 220, 46,
                                        "ENTRAR EN LA MESA",
                                        color=(30, 80, 30))
        self._setup_cancel_btn = Button(cx - 110, cy + 146, 220, 40,
                                        "VOLVER", color=(70, 20, 20),
                                        font="small")
        self._setup_room_rect = pygame.Rect(cx - 180, cy - 82, 360, 38)

    def _open_setup(self, game_key):
        self._catalog_open = True
        self._setup_target = game_key
        self._setup_mode = "solo"
        self._setup_room = self._setup_room or "Royal"
        self._setup_edit = False
        self._setup_status = ""

    def _launch_game(self):
        room = self._setup_room.strip() or "Royal"
        mode = self._setup_mode
        net_mode = STATE.get("net_mode")
        if mode == "lan_host" and net_mode not in ("host", "client"):
            self._setup_status = "Para crear grupo, primero conéctate por LAN/IP (host o cliente)."
            return None
        if mode == "lan_client" and net_mode != "client":
            self._setup_status = "Para unirte a un grupo, entra como cliente LAN desde el menú."
            return None
        self._catalog_open = False
        target = self._setup_target
        self._setup_target = None
        if target == "poker" and mode == "solo":
            mode = "bots"
        return ("game", target, {"mode": mode, "room": room})

    def _handle_catalog_event(self, event):
        if self._setup_target:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._setup_target = None
                    self._setup_edit = False
                    return None
                if self._setup_edit:
                    if event.key == pygame.K_RETURN:
                        self._setup_edit = False
                    elif event.key == pygame.K_BACKSPACE:
                        self._setup_room = self._setup_room[:-1]
                    elif event.unicode.isprintable() and len(self._setup_room) < 18:
                        self._setup_room += event.unicode
                    return None

            if event.type == pygame.MOUSEBUTTONDOWN:
                self._setup_edit = self._setup_room_rect.collidepoint(event.pos)

            for mode_key, button in self._setup_mode_buttons.items():
                if button.clicked(event):
                    self._setup_mode = mode_key
                    self._setup_status = ""

            if self._setup_launch_btn.clicked(event):
                return self._launch_game()
            if self._setup_cancel_btn.clicked(event):
                self._setup_target = None
                self._setup_edit = False
            return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._catalog_open = False
            return None

        for button in self._catalog_buttons:
            if button.clicked(event):
                game_key = self._catalog_button_keys.get(id(button), "roulette")
                if game_key in ("poker", "blackjack"):
                    self._open_setup(game_key)
                    return None
                self._catalog_open = False
                return ("game", game_key, {"mode": "solo", "room": "Royal"})

        if self._catalog_close_btn.clicked(event):
            self._catalog_open = False
        return None

    def _net_sync(self, dt):
        self._sync_t += dt
        if self._sync_t < self.SYNC_INTERVAL:
            return
        self._sync_t = 0.0

        my_id   = STATE.get("net_my_id", 0)
        mode    = STATE.get("net_mode")
        payload = {
            "type":  "player_pos",
            "id":    my_id,
            "name":  STATE["player_name"],
            "x":     int(self.player.x),
            "y":     int(self.player.y),
            "chips": STATE["chips"],
        }

        if mode == "host":
            server = STATE.get("net_server")
            if server:
                # El host difon la seva posició a tots els clients
                server.broadcast(payload)
                # Llegir i processar missatges entrants dels clients
                while not server.inbox.empty():
                    try:
                        msg = server.inbox.get_nowait()
                        self._handle_net_msg(msg)
                        # Re-difondre posicions de clients a la resta
                        if msg.get("type") == "player_pos":
                            # Actualitzar nom real del client si és la primera vegada
                            cid  = msg.get("_from")
                            name = msg.get("name", "")
                            if cid and name:
                                # Notificar actualització de nom a tothom
                                server.broadcast({
                                    "type": "player_joined",
                                    "id":   msg["id"],
                                    "name": name,
                                }, exclude=cid)
                            server.broadcast(msg, exclude=cid)
                    except Exception:
                        pass

        elif mode == "client":
            client = STATE.get("net_client")
            if client and client.connected:
                client.send(payload)
                for msg in client.poll():
                    self._handle_net_msg(msg)

    def _handle_net_msg(self, msg):
        t = msg.get("type")
        if t == "welcome":
            # El client guarda el seu propi ID
            my_id = msg.get("your_id")
            if my_id is not None:
                STATE["net_my_id"] = my_id
        elif t == "player_pos":
            pid = msg["id"]
            # Ignorar la nostra pròpia posició reflectida
            try:
                if int(pid) == int(STATE.get("net_my_id", -999)):
                    return
            except (ValueError, TypeError):
                pass
            STATE["net_players"][pid] = {
                "name":  msg.get("name", f"J{pid}"),
                "x":     msg.get("x", 0),
                "y":     msg.get("y", 0),
                "chips": msg.get("chips", 0),
            }
        elif t == "player_joined":
            pid = msg["id"]
            name = msg.get("name", f"J{pid}")
            if pid not in STATE["net_players"]:
                STATE["net_players"][pid] = {"name": name, "x": 0, "y": 0, "chips": 0}
            self._float_msgs.append(
                FloatMessage(f"{name} s'ha connectat!", SCREEN_W // 2, 200, C["ui_green"], 3.0))
        elif t == "player_left":
            pid = msg["id"]
            name = STATE["net_players"].pop(pid, {}).get("name", f"J{pid}")
            self._float_msgs.append(
                FloatMessage(f"{name} s'ha desconnectat", SCREEN_W // 2, 200, C["ui_red"], 3.0))
        elif t == "disconnected":
            self._float_msgs.append(
                FloatMessage("Desconnectat del servidor", SCREEN_W // 2, 200, C["ui_red"], 4.0))
            STATE["net_mode"] = None

    def handle_event(self, event):
        if self._catalog_open:
            return self._handle_catalog_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g:
                self._catalog_open = not self._catalog_open
                self._setup_target = None
                self._setup_edit = False
                return None
            if event.key == pygame.K_e and self._near_zone:
                if self._near_zone in ("poker", "blackjack"):
                    self._open_setup(self._near_zone)
                    return None
                return ("game", self._near_zone, {"mode": "solo", "room": "Royal"})
        return None

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        self.camera.follow(self.player.x, self.player.y, dt)
        self.world.update(dt)

        px, py = self.player.x, self.player.y
        self._near_zone = None
        for k, z in ZONE_INTERACT.items():
            if z.collidepoint(px, py):
                self._near_zone = k
                break

        for m in self._float_msgs:
            m.update(dt)
        self._float_msgs = [m for m in self._float_msgs if not m.done]

        if self._fade:
            self._fade.update(dt)
            if self._fade.done:
                self._fade = None

        self._net_sync(dt)

    def draw(self, surf):
        cam_x = self.camera.ix
        cam_y = self.camera.iy

        self.world.draw(surf, cam_x, cam_y)
        my_id = STATE.get("net_my_id", 0)
        _draw_net_players(surf, cam_x, cam_y, my_id)
        self.player.draw(surf, cam_x, cam_y)
        self.world.draw_zone_indicators(surf, cam_x, cam_y)

        if self._near_zone:
            px_ = int(self.player.x) - cam_x
            py_ = int(self.player.y) - cam_y
            from ui import draw_interact_hint
            draw_interact_hint(surf, px_, py_, ZONE_NAMES[self._near_zone])

        draw_hud(surf)

        # Barra d'instruccions amb fons per llegibilitat
        bar_w = 640
        bar_s = pygame.Surface((bar_w, 26), pygame.SRCALPHA)
        bar_s.fill((0, 0, 0, 150))
        surf.blit(bar_s, (6, SCREEN_H - 32))
        text(surf, "WASD/Flechas mover · E mesa · G catálogo de juegos · F11 pantalla completa",
             "tiny", (220, 220, 200), 14, SCREEN_H - 22)

        for m in self._float_msgs:
            m.draw(surf)

        if self._catalog_open:
            self._draw_catalog_overlay(surf)

        if self._fade:
            self._fade.draw(surf)

    def _draw_catalog_overlay(self, surf):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_W // 2 - 320, SCREEN_H // 2 - 210, 640, 420)
        draw_panel(surf, panel, alpha=235, radius=18)

        if self._setup_target:
            game_title = {"poker": "POKER", "blackjack": "BLACKJACK"}.get(self._setup_target, self._setup_target.upper())
            text(surf, f"CONFIGURAR {game_title}", "big", C["neon_gold"],
                 panel.centerx, panel.y + 34, anchor="center")
            subtitle = ("Escoge si quieres jugar local o compartir mesa LAN."
                        if self._setup_target == "blackjack"
                        else "Bots locales o mesa LAN compartida para el grupo.")
            text(surf, subtitle, "small", C["ui_sub"],
                 panel.centerx, panel.y + 68, anchor="center")

            room_rect = self._setup_room_rect
            text(surf, "Nombre del grupo", "tiny", C["ui_sub"], room_rect.x, room_rect.y - 18)
            draw_panel(surf, room_rect, alpha=220, radius=8)
            border = C["neon_gold"] if self._setup_edit else C["ui_border"]
            pygame.draw.rect(surf, border, room_rect, 2, border_radius=8)
            room_txt = self._setup_room + ("|" if self._setup_edit and int(pygame.time.get_ticks() / 350) % 2 == 0 else "")
            text(surf, room_txt or "Royal", "small", C["ui_text"],
                 room_rect.centerx, room_rect.centery, anchor="center")

            for mode_key, button in self._setup_mode_buttons.items():
                if self._setup_target == "poker" and mode_key == "solo":
                    button.label = "BOTS"
                elif self._setup_target == "blackjack" and mode_key == "solo":
                    button.label = "SOLO"
                button.draw(surf)
                if self._setup_mode == mode_key:
                    pygame.draw.rect(surf, C["neon_gold"], button.rect.inflate(6, 6), 2, border_radius=12)

            hint = "Crear grupo = host LAN · Unirme = cliente LAN"
            text(surf, hint, "small", C["ui_text"], panel.centerx, panel.y + 246, anchor="center")
            if self._setup_status:
                text(surf, self._setup_status, "small", C["ui_red"],
                     panel.centerx, panel.y + 274, anchor="center")

            self._setup_launch_btn.draw(surf)
            self._setup_cancel_btn.draw(surf)
            return

        text(surf, "CATÁLOGO DEL CASINO", "big", C["neon_gold"],
             panel.centerx, panel.y + 34, anchor="center")
        text(surf, "Nuevos juegos incluidos: tragaperras, bolos y dados.",
             "small", C["ui_sub"], panel.centerx, panel.y + 68, anchor="center")
        for button in self._catalog_buttons:
            button.draw(surf)
        self._catalog_close_btn.draw(surf)


class GameScene:
    def __init__(self, game_type, config=None):
        self._type = game_type
        if game_type == "blackjack":
            self._game = BlackjackGame(config)
        elif game_type == "poker":
            self._game = PokerGame(config)
        elif game_type == "roulette":
            self._game = RouletteGame(config)
        elif game_type == "slots":
            self._game = SlotsGame(config)
        elif game_type == "bowling":
            self._game = BowlingGame(config)
        elif game_type == "dice_duel":
            self._game = DiceDuelGame(config)
        self._fade = FadeTransition(0.4, fade_in=True)

    def handle_event(self, event):
        result = self._game.handle_event(event)
        if result == "exit":
            return "world"
        return None

    def update(self, dt):
        self._game.update(dt)
        if self._fade:
            self._fade.update(dt)
            if self._fade.done:
                self._fade = None

    def draw(self, surf):
        self._game.draw(surf)
        if self._fade:
            self._fade.draw(surf)


class GameOverScene:
    def __init__(self):
        self._btn  = Button(SCREEN_W // 2 - 120, SCREEN_H // 2 + 60,
                            240, 54, "TORNAR A JUGAR", color=(80, 60, 10))
        self._quit = Button(SCREEN_W // 2 - 120, SCREEN_H // 2 + 128,
                            240, 46, "SORTIR",         color=(70, 20, 20))

    def handle_event(self, event):
        if self._btn.clicked(event):
            STATE["chips"]  = 2000
            STATE["wins"]   = 0
            STATE["losses"] = 0
            return "menu"
        if self._quit.clicked(event):
            return "quit"
        return None

    def update(self, dt):
        self._btn.update(dt)
        self._quit.update(dt)

    def draw(self, surf):
        surf.fill(C["bg"])
        text(surf, "SENSE FITXES", "title", C["ui_red"],
             SCREEN_W // 2, SCREEN_H // 2 - 100, anchor="center")
        text(surf, "Has perdut totes les fitxes. Torna-ho a intentar!",
             "med", C["ui_sub"], SCREEN_W // 2, SCREEN_H // 2 - 30, anchor="center")
        self._btn.draw(surf)
        self._quit.draw(surf)


class SceneManager:
    def __init__(self):
        self._scenes      = {}
        self._current_key = None
        self._current     = None

    def load(self, key, scene):
        self._scenes[key] = scene

    def switch(self, key, *args):
        if key == "world":
            self._scenes["world"] = WorldScene()
        elif key == "menu":
            self._scenes["menu"] = MenuScene()
        elif key == "gameover":
            self._scenes["gameover"] = GameOverScene()
        elif key == "game":
            game_type = args[0] if args else "blackjack"
            config = args[1] if len(args) > 1 else None
            self._scenes["game"] = GameScene(game_type, config)
        self._current_key = key
        self._current     = self._scenes.get(key)

    def handle_event(self, event):
        if not self._current:
            return
        result = self._current.handle_event(event)
        if result:
            self._handle_transition(result)

    def _handle_transition(self, result):
        if result == "quit":
            self._cleanup_network()
            pygame.quit()
            sys.exit()
        elif result == "world":
            self.switch("world")
        elif result == "menu":
            self._cleanup_network()
            self.switch("menu")
        elif result == "gameover":
            self.switch("gameover")
        elif isinstance(result, tuple) and result[0] == "game":
            game_key = result[1] if len(result) > 1 else "blackjack"
            config = result[2] if len(result) > 2 else None
            self.switch("game", game_key, config)

    def _cleanup_network(self):
        server = STATE.get("net_server")
        if server:
            server.stop()
            STATE["net_server"] = None
        client = STATE.get("net_client")
        if client:
            client.disconnect()
            STATE["net_client"] = None
        STATE["net_mode"]    = None
        STATE["net_players"] = {}

    def update(self, dt):
        if not self._current:
            return
        if self._current_key == "world" and STATE["chips"] <= 0:
            self.switch("gameover")
            return
        self._current.update(dt)

    def draw(self, surf):
        if self._current:
            self._current.draw(surf)


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(icon, C["neon_gold"], (16, 16), 14)
    pygame.draw.circle(icon, C["accent"],    (16, 16), 10)
    pygame.draw.circle(icon, C["neon_gold"], (16, 16), 6)
    pygame.display.set_icon(icon)

    sm = SceneManager()
    sm.load("menu",     MenuScene())
    sm.load("world",    WorldScene())
    sm.load("gameover", GameOverScene())
    sm.switch("menu")

    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sm._cleanup_network()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            sm.handle_event(event)

        sm.update(dt)
        sm.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
