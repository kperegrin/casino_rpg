# ═══════════════════════════════════════════════════════════════════
#  UI — HUD, botons, missatges flotants, transicions
# ═══════════════════════════════════════════════════════════════════
import pygame
import math
from settings import C, STATE, SCREEN_W, SCREEN_H
from card_renderer import make_chip

pygame.font.init()

# ── Fonts (mides augmentades per millor llegibilitat) ─────────────────
def _font(size, bold=False):
    # Intentar fonts llegibles en ordre de preferència
    for name in ("Segoe UI", "Arial", "Helvetica", "Georgia", ""):
        try:
            if name:
                f = pygame.font.SysFont(name, size, bold=bold)
            else:
                f = pygame.font.Font(None, size)
            return f
        except Exception:
            continue
    return pygame.font.Font(None, size)

def _font_mono(size):
    for name in ("Consolas", "Courier New", "Lucida Console", ""):
        try:
            if name:
                f = pygame.font.SysFont(name, size, bold=True)
            else:
                f = pygame.font.Font(None, size)
            return f
        except Exception:
            continue
    return pygame.font.Font(None, size)

# Mides augmentades respecte a l'original per millor llegibilitat
F = {
    "title":  _font(48, bold=True),   # era 42
    "big":    _font(32, bold=True),   # era 28
    "med":    _font(23, bold=True),   # era 20
    "small":  _font(18),              # era 15
    "tiny":   _font(14),              # era 12
    "mono":   _font_mono(18),         # era 16
    "hud":    _font(20, bold=True),   # era 18
    "chips":  _font(26, bold=True),   # era 22
}


# ── Helpers ──────────────────────────────────────────────────────────
def text(surf, txt, font_key, color, x, y, anchor="topleft", shadow=True):
    f = F[font_key]
    if shadow:
        s = f.render(str(txt), True, (0,0,0))
        r = s.get_rect(**{anchor: (x+1, y+1)})
        surf.blit(s, r)
    s = f.render(str(txt), True, color)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r

def draw_rect_alpha(surf, color, rect, alpha=180, radius=0):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    if radius > 0:
        pygame.draw.rect(s, (*color[:3], alpha), (0,0,rect[2],rect[3]), border_radius=radius)
    else:
        s.fill((*color[:3], alpha))
    surf.blit(s, (rect[0], rect[1]))

def draw_panel(surf, rect, alpha=210, radius=10):
    """Panel fosc amb vora daurada."""
    draw_rect_alpha(surf, C["ui_bg"], rect, alpha, radius)
    pygame.draw.rect(surf, C["ui_border"], rect, 2, border_radius=radius)

def gold_line(surf, x1, y1, x2, y2, width=1):
    pygame.draw.line(surf, C["ui_border"], (x1,y1), (x2,y2), width)


# ── Botó ─────────────────────────────────────────────────────────────
class Button:
    def __init__(self, x, y, w, h, label,
                 color=(30,80,30), text_color=None, font="med"):
        self.rect  = pygame.Rect(x, y, w, h)
        self.label = label
        self.color = color
        self.tc    = text_color or C["ui_text"]
        self.font  = font
        self._hov  = False
        self._anim = 0.0   # 0..1 hover anim

    def update(self, dt):
        mx, my = pygame.mouse.get_pos()
        self._hov = self.rect.collidepoint(mx, my)
        target = 1.0 if self._hov else 0.0
        self._anim += (target - self._anim) * min(1, dt * 10)

    def draw(self, surf):
        a = self._anim
        r, g, b = self.color
        cr = int(r + (min(255,r+40) - r) * a)
        cg = int(g + (min(255,g+40) - g) * a)
        cb = int(b + (min(255,b+40) - b) * a)

        rect = self.rect.inflate(int(a*4), int(a*2))

        # Ombra
        sr = rect.move(3, 3)
        draw_rect_alpha(surf, (0,0,0), sr, 120, 8)

        # Cos
        pygame.draw.rect(surf, (cr,cg,cb), rect, border_radius=8)

        # Degradat clar a dalt
        hl = pygame.Surface((rect.w, rect.h//2), pygame.SRCALPHA)
        hl.fill((255,255,255, int(30 * (1+a))))
        surf.blit(hl, rect.topleft)

        # Vora
        border_c = (220, 185, 70) if a > 0.3 else C["ui_border"]
        pygame.draw.rect(surf, border_c, rect, 2, border_radius=8)

        # Text
        text(surf, self.label, self.font, self.tc,
             rect.centerx, rect.centery, anchor="center")

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


# ── HUD ──────────────────────────────────────────────────────────────
def draw_hud(surf):
    """Barra de chips a dalt a la dreta, amb millor llegibilitat."""
    panel = pygame.Rect(SCREEN_W - 240, 8, 232, 52)
    draw_panel(surf, panel, alpha=220, radius=8)

    chip = make_chip(100, 32)
    surf.blit(chip, (panel.x + 8, panel.y + 10))

    text(surf, "CHIPS", "tiny", C["ui_sub"],
         panel.x + 48, panel.y + 7)
    text(surf, f"{STATE['chips']:,}", "chips", C["chips"],
         panel.x + 48, panel.y + 22)

    # Wins/losses amb icones
    wl_x = panel.x + 168
    text(surf, f"✓{STATE['wins']}  ✗{STATE['losses']}", "small",
         C["ui_sub"], wl_x, panel.y + 18, anchor="center")

    # Indicador de xarxa
    net_mode = STATE.get("net_mode")
    if net_mode == "host":
        server = STATE.get("net_server")
        count  = (server.connected_count if server else 0) + 1
        draw_rect_alpha(surf, (0, 80, 0), (panel.x, panel.y + panel.h + 4,
                                            panel.w, 22), 200, 4)
        text(surf, f"🌐 HOST  {count} jugadors", "tiny", (100, 255, 100),
             panel.x + panel.w // 2, panel.y + panel.h + 14, anchor="center")
    elif net_mode == "client":
        draw_rect_alpha(surf, (0, 40, 80), (panel.x, panel.y + panel.h + 4,
                                             panel.w, 22), 200, 4)
        client = STATE.get("net_client")
        status = "connectat" if (client and client.connected) else "desconnectat"
        text(surf, f"🌐 CLIENT  {status}", "tiny", (100, 200, 255),
             panel.x + panel.w // 2, panel.y + panel.h + 14, anchor="center")


# ── Missatge flotant ─────────────────────────────────────────────────
class FloatMessage:
    def __init__(self, txt, x, y, color=None, duration=2.0, font="med"):
        self.txt      = txt
        self.x        = x
        self.y        = y
        self.color    = color or C["ui_text"]
        self.timer    = duration
        self.duration = duration
        self.font     = font

    def update(self, dt):
        self.timer -= dt
        self.y     -= 30 * dt

    def draw(self, surf):
        alpha_ratio = max(0, self.timer / self.duration)
        a = int(255 * alpha_ratio)
        f = F[self.font]
        s = f.render(self.txt, True, (*self.color[:3],))
        s.set_alpha(a)
        r = s.get_rect(centerx=int(self.x), centery=int(self.y))
        surf.blit(s, r)

    @property
    def done(self):
        return self.timer <= 0


# ── Transició de pantalla (fade) ─────────────────────────────────────
class FadeTransition:
    def __init__(self, duration=0.4, fade_in=True):
        self.duration = duration
        self.timer    = duration
        self.fade_in  = fade_in
        self.done     = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.done = True

    def draw(self, surf):
        ratio = max(0, self.timer / self.duration)
        alpha = int(255 * ratio) if self.fade_in else int(255 * (1 - ratio))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.fill((0,0,0))
        overlay.set_alpha(alpha)
        surf.blit(overlay, (0,0))


# ── Indicador "Prem E per jugar" ─────────────────────────────────────
def draw_interact_hint(surf, x, y, game_name):
    panel_w, panel_h = 220, 44
    px = x - panel_w // 2
    py = y - 60
    draw_panel(surf, (px, py, panel_w, panel_h), alpha=200, radius=8)

    # Quadrat [E]
    eq = pygame.Rect(px + 10, py + 10, 24, 24)
    pygame.draw.rect(surf, C["ui_border"], eq, border_radius=4)
    pygame.draw.rect(surf, C["ui_text"],   eq, 2, border_radius=4)
    text(surf, "E", "small", C["ui_text"], eq.centerx, eq.centery,
         anchor="center", shadow=False)

    text(surf, f" Jugar al {game_name}", "small", C["ui_text"],
         px + 40, py + 13)

    # Parpadeig
    t = pygame.time.get_ticks() / 1000
    alpha = int(180 + 75 * math.sin(t * 3))
    pygame.draw.rect(surf, (*C["neon_gold"], alpha), eq, 2, border_radius=4)


# ── Pantalla de fi de ronda ───────────────────────────────────────────
def draw_result_screen(surf, message, chips_delta, font="big"):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0,0))

    pw, ph = 420, 180
    px = (SCREEN_W - pw) // 2
    py = (SCREEN_H - ph) // 2
    draw_panel(surf, (px, py, pw, ph), alpha=230, radius=12)

    color = C["ui_green"] if chips_delta >= 0 else C["ui_red"]
    text(surf, message, font, color, SCREEN_W//2, py+40, anchor="center")

    delta_txt = f"+{chips_delta}" if chips_delta >= 0 else str(chips_delta)
    delta_color = C["chips"] if chips_delta >= 0 else C["ui_red"]
    text(surf, f"{delta_txt} chips", "med", delta_color,
         SCREEN_W//2, py + 90, anchor="center")
    text(surf, "Prem ESPAI per continuar", "small", C["ui_sub"],
         SCREEN_W//2, py + 140, anchor="center")


# ── Mini-mapa de sala ─────────────────────────────────────────────────
def draw_room_label(surf, room_name):
    text(surf, room_name, "tiny", C["ui_sub"], 10, SCREEN_H - 20)
