# ═══════════════════════════════════════════════════════════════════
#  UI — HUD, botons, missatges flotants, transicions
#  Usa assets reales del UI Pack (Crusenho) e Icons Pack si están en:
#    assets/ui/Complete_UI_Essential_Pack_Free/01_Flat_Theme/Sprites/
#    assets/icons/Icons_Essential/v1.2/Icons/
# ═══════════════════════════════════════════════════════════════════
import pygame
import math
import os
from settings import C, STATE, SCREEN_W, SCREEN_H
from card_renderer import make_chip

pygame.font.init()

# ── Rutas de assets ──────────────────────────────────────────────────
_UI_DIR    = os.path.join("assets", "ui",
             "Complete_UI_Essential_Pack_Free", "01_Flat_Theme", "Sprites")
_ICONS_DIR = os.path.join("assets", "icons", "Icons_Essential", "v1.2", "Icons")

_ui_cache    = {}
_icon_cache  = {}

def _ui_available():
    return os.path.isdir(_UI_DIR)

def _icons_available():
    return os.path.isdir(_ICONS_DIR)

def _load_ui(name, scale=1.0):
    """Carga un sprite del UI pack escalado."""
    key = f"{name}_{scale}"
    if key in _ui_cache:
        return _ui_cache[key]
    path = os.path.join(_UI_DIR, name)
    if not os.path.exists(path):
        _ui_cache[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        if scale != 1.0:
            w = max(1, int(surf.get_width()  * scale))
            h = max(1, int(surf.get_height() * scale))
            surf = pygame.transform.scale(surf, (w, h))
        _ui_cache[key] = surf
        return surf
    except Exception:
        _ui_cache[key] = None
        return None

def _load_ui_scaled(name, target_w, target_h):
    """Carga y escala a tamaño exacto."""
    key = f"{name}_{target_w}x{target_h}"
    if key in _ui_cache:
        return _ui_cache[key]
    path = os.path.join(_UI_DIR, name)
    if not os.path.exists(path):
        _ui_cache[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.scale(surf, (target_w, target_h))
        _ui_cache[key] = surf
        return surf
    except Exception:
        _ui_cache[key] = None
        return None

def load_icon(name, size=16):
    """Carga un icono del Icons pack."""
    key = f"{name}_{size}"
    if key in _icon_cache:
        return _icon_cache[key]
    path = os.path.join(_ICONS_DIR, name)
    if not os.path.exists(path):
        _icon_cache[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        if size != 16:
            surf = pygame.transform.scale(surf, (size, size))
        _icon_cache[key] = surf
        return surf
    except Exception:
        _icon_cache[key] = None
        return None


# ── Fonts ─────────────────────────────────────────────────────────────
def _font(size, bold=False):
    for name in ("Segoe UI", "Arial", "Helvetica", "Georgia", ""):
        try:
            f = pygame.font.SysFont(name, size, bold=bold) if name else pygame.font.Font(None, size)
            return f
        except Exception:
            continue
    return pygame.font.Font(None, size)

def _font_mono(size):
    for name in ("Consolas", "Courier New", "Lucida Console", ""):
        try:
            f = pygame.font.SysFont(name, size, bold=True) if name else pygame.font.Font(None, size)
            return f
        except Exception:
            continue
    return pygame.font.Font(None, size)

F = {
    "title": _font(48, bold=True),
    "big":   _font(32, bold=True),
    "med":   _font(23, bold=True),
    "small": _font(18),
    "tiny":  _font(14),
    "mono":  _font_mono(18),
    "hud":   _font(20, bold=True),
    "chips": _font(26, bold=True),
}


# ── Helpers de dibujo ──────────────────────────────────────────────────
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
    """Panel con fondo oscuro y borde dorado. Usa frame del UI pack si está disponible."""
    r = rect if isinstance(rect, pygame.Rect) else pygame.Rect(*rect)

    if _ui_available():
        # Fondo propio + frame escalado del UI pack encima
        draw_rect_alpha(surf, C["ui_bg"], r, alpha, radius)
        frame = _load_ui_scaled("UI_Flat_Frame01a.png", r.width, r.height)
        if frame:
            surf.blit(frame, r.topleft)
            return

    # Fallback procedural
    draw_rect_alpha(surf, C["ui_bg"], r, alpha, radius)
    pygame.draw.rect(surf, C["ui_border"], r, 2, border_radius=radius)

def gold_line(surf, x1, y1, x2, y2, width=1):
    pygame.draw.line(surf, C["ui_border"], (x1,y1), (x2,y2), width)


# ── Botón con sprite real ─────────────────────────────────────────────
class Button:
    # Estados: _1=normal, _2=hover, _3=pressed, _4=disabled
    _BTN_NORMAL  = "UI_Flat_Button01a_1.png"
    _BTN_HOVER   = "UI_Flat_Button01a_2.png"
    _BTN_PRESS   = "UI_Flat_Button01a_3.png"

    def __init__(self, x, y, w, h, label,
                 color=(30,80,30), text_color=None, font="med"):
        self.rect  = pygame.Rect(x, y, w, h)
        self.label = label
        self.color = color
        self.tc    = text_color or C["ui_text"]
        self.font  = font
        self._hov  = False
        self._anim = 0.0
        self._pressed = False

    def update(self, dt):
        mx, my = pygame.mouse.get_pos()
        self._hov = self.rect.collidepoint(mx, my)
        target = 1.0 if self._hov else 0.0
        self._anim += (target - self._anim) * min(1, dt * 10)

    def draw(self, surf):
        a = self._anim

        if _ui_available():
            # Elegir estado del botón
            if self._pressed:
                sprite_name = self._BTN_PRESS
            elif self._hov:
                sprite_name = self._BTN_HOVER
            else:
                sprite_name = self._BTN_NORMAL

            btn_surf = _load_ui_scaled(sprite_name, self.rect.w, self.rect.h)
            if btn_surf:
                # Teñir con el color del botón sutilmente
                tinted = btn_surf.copy()
                r, g, b = self.color
                tint = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
                tint.fill((r, g, b, 60))
                tinted.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                surf.blit(tinted, self.rect.topleft)
                # Borde dorado en hover
                if self._hov:
                    pygame.draw.rect(surf, C["neon_gold"], self.rect, 2, border_radius=6)
                text(surf, self.label, self.font, self.tc,
                     self.rect.centerx, self.rect.centery, anchor="center")
                return

        # Fallback procedural
        r, g, b = self.color
        cr = int(r + (min(255,r+40)-r) * a)
        cg = int(g + (min(255,g+40)-g) * a)
        cb = int(b + (min(255,b+40)-b) * a)
        rect = self.rect.inflate(int(a*4), int(a*2))
        sr = rect.move(3,3)
        draw_rect_alpha(surf, (0,0,0), sr, 120, 8)
        pygame.draw.rect(surf, (cr,cg,cb), rect, border_radius=8)
        hl = pygame.Surface((rect.w, rect.h//2), pygame.SRCALPHA)
        hl.fill((255,255,255, int(30*(1+a))))
        surf.blit(hl, rect.topleft)
        border_c = (220,185,70) if a > 0.3 else C["ui_border"]
        pygame.draw.rect(surf, border_c, rect, 2, border_radius=8)
        text(surf, self.label, self.font, self.tc,
             rect.centerx, rect.centery, anchor="center")

    def clicked(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos)):
            self._pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self._pressed = False
        return False


# ── HUD ────────────────────────────────────────────────────────────────
def draw_hud(surf):
    panel = pygame.Rect(SCREEN_W - 240, 8, 232, 52)
    draw_panel(surf, panel, alpha=220, radius=8)

    # Icono de moneda del pack de iconos (si disponible)
    coin_icon = load_icon("Coin.png", size=28)
    if coin_icon:
        surf.blit(coin_icon, (panel.x + 8, panel.y + 12))
        icon_offset = 44
    else:
        chip = make_chip(100, 32)
        surf.blit(chip, (panel.x + 8, panel.y + 10))
        icon_offset = 48

    text(surf, "CHIPS", "tiny", C["ui_sub"],  panel.x + icon_offset, panel.y + 7)
    text(surf, f"{STATE['chips']:,}", "chips", C["chips"], panel.x + icon_offset, panel.y + 22)

    # Trophy icon para wins
    trophy = load_icon("Trophy.png", size=14)
    wl_x = panel.x + 175
    if trophy:
        surf.blit(trophy, (wl_x - 14, panel.y + 10))
    text(surf, f"✓{STATE['wins']}  ✗{STATE['losses']}", "small",
         C["ui_sub"], wl_x + 4, panel.y + 18, anchor="center")

    # Indicador de red
    net_mode = STATE.get("net_mode")
    if net_mode == "host":
        server = STATE.get("net_server")
        count  = (server.connected_count if server else 0) + 1
        draw_rect_alpha(surf, (0,80,0), (panel.x, panel.y+panel.h+4, panel.w, 22), 200, 4)
        text(surf, f"🌐 HOST  {count} jugadors", "tiny", (100,255,100),
             panel.x+panel.w//2, panel.y+panel.h+14, anchor="center")
    elif net_mode == "client":
        draw_rect_alpha(surf, (0,40,80), (panel.x, panel.y+panel.h+4, panel.w, 22), 200, 4)
        client = STATE.get("net_client")
        status = "connectat" if (client and client.connected) else "desconnectat"
        text(surf, f"🌐 CLIENT  {status}", "tiny", (100,200,255),
             panel.x+panel.w//2, panel.y+panel.h+14, anchor="center")


# ── Mensaje flotante ──────────────────────────────────────────────────
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


# ── Transición fade ───────────────────────────────────────────────────
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
        alpha = int(255 * ratio) if self.fade_in else int(255 * (1-ratio))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.fill((0,0,0))
        overlay.set_alpha(alpha)
        surf.blit(overlay, (0,0))


# ── Hint de interacción ───────────────────────────────────────────────
def draw_interact_hint(surf, x, y, game_name):
    panel_w, panel_h = 220, 44
    px = x - panel_w // 2
    py = y - 60

    if _ui_available():
        frame = _load_ui_scaled("UI_Flat_FrameMarker01a.png", panel_w, panel_h)
        if frame:
            surf.blit(frame, (px, py))
            # Icono [E]
            key_icon = load_icon("Key.png", 20)
            if key_icon:
                surf.blit(key_icon, (px+8, py+12))
                text(surf, f" {game_name}", "small", C["ui_text"], px+34, py+13)
            else:
                text(surf, f"[E] {game_name}", "small", C["ui_text"], px+10, py+13)
            # Parpadeo
            t = pygame.time.get_ticks() / 1000
            alpha = int(180 + 75 * math.sin(t * 3))
            glow = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C["neon_gold"], alpha//4), (0,0,panel_w,panel_h), border_radius=6)
            surf.blit(glow, (px, py))
            return

    # Fallback
    draw_panel(surf, (px, py, panel_w, panel_h), alpha=200, radius=8)
    eq = pygame.Rect(px+10, py+10, 24, 24)
    pygame.draw.rect(surf, C["ui_border"], eq, border_radius=4)
    pygame.draw.rect(surf, C["ui_text"],   eq, 2, border_radius=4)
    text(surf, "E", "small", C["ui_text"], eq.centerx, eq.centery, anchor="center", shadow=False)
    text(surf, f" {game_name}", "small", C["ui_text"], px+40, py+13)
    t = pygame.time.get_ticks() / 1000
    alpha = int(180 + 75 * math.sin(t * 3))
    pygame.draw.rect(surf, (*C["neon_gold"], alpha), eq, 2, border_radius=4)


# ── Pantalla de resultado ─────────────────────────────────────────────
def draw_result_screen(surf, message, chips_delta, font="big"):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0,0,0,160))
    surf.blit(overlay, (0,0))

    pw, ph = 420, 180
    px = (SCREEN_W - pw) // 2
    py = (SCREEN_H - ph) // 2
    draw_panel(surf, (px, py, pw, ph), alpha=230, radius=12)

    color = C["ui_green"] if chips_delta >= 0 else C["ui_red"]

    # Icono de trofeo si ganó
    if chips_delta > 0:
        trophy = load_icon("Trophy.png", 32)
        if trophy:
            surf.blit(trophy, (px + 16, py + 16))

    text(surf, message, font, color, SCREEN_W//2, py+40, anchor="center")
    delta_txt = f"+{chips_delta}" if chips_delta >= 0 else str(chips_delta)
    delta_color = C["chips"] if chips_delta >= 0 else C["ui_red"]

    # Icono moneda junto al delta
    coin = load_icon("Coin.png", 20)
    if coin:
        coin_x = SCREEN_W//2 - 60
        surf.blit(coin, (coin_x, py+82))
        text(surf, f"{delta_txt} chips", "med", delta_color, coin_x+26, py+90, anchor="topleft")
    else:
        text(surf, f"{delta_txt} chips", "med", delta_color, SCREEN_W//2, py+90, anchor="center")

    text(surf, "Prem ESPAI per continuar", "small", C["ui_sub"],
         SCREEN_W//2, py+140, anchor="center")


# ── Input field con sprite real ───────────────────────────────────────
def draw_input_field(surf, rect, value, editing=False, placeholder=""):
    r = rect if isinstance(rect, pygame.Rect) else pygame.Rect(*rect)

    if _ui_available():
        field = _load_ui_scaled("UI_Flat_InputField01a.png", r.w, r.h)
        if field:
            surf.blit(field, r.topleft)
            if editing:
                pygame.draw.rect(surf, C["neon_gold"], r, 2, border_radius=6)
            display = value if value else placeholder
            col = C["ui_text"] if value else C["ui_sub"]
            text(surf, display, "small", col, r.centerx, r.centery, anchor="center")
            return

    # Fallback
    draw_panel(surf, r, alpha=220, radius=6)
    bc = C["neon_gold"] if editing else C["ui_border"]
    pygame.draw.rect(surf, bc, r, 2, border_radius=6)
    display = value if value else placeholder
    col = C["ui_text"] if value else C["ui_sub"]
    text(surf, display, "small", col, r.centerx, r.centery, anchor="center")


# ── Mini etiqueta de sala ──────────────────────────────────────────────
def draw_room_label(surf, room_name):
    text(surf, room_name, "tiny", C["ui_sub"], 10, SCREEN_H-20)
