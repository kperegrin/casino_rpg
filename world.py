# ═══════════════════════════════════════════════════════════════════
#  WORLD — Llegeix el mapa de Tiled (.tmx) amb pytmx
#  pip install pytmx
#
#  ESTRUCTURA DE CAPES ESPERADA AL TILED:
#  ┌─────────────────────────────────────────────────────────────┐
#  │  Capa          Tipus       Descripció                       │
#  │  ──────────────────────────────────────────────────────────  │
#  │  floor         Tile        Sòl base (moqueta, parquet...)   │
#  │  floor2        Tile        Segon sòl opcional (sobre floor) │
#  │  objects       Tile        Mobles, taules, màquines...      │
#  │  walls         Tile        Parets i obstacles               │
#  │  zones         Object      Rectangles de zones de joc       │
#  │  above         Tile        Elements per sobre del jugador   │
#  └─────────────────────────────────────────────────────────────┘
#
#  PROPIETATS DE TILES (al Tiled, per tile al tileset):
#    collides = true    → bloqueja el pas del jugador
#
#  PROPIETATS D'OBJECTES DE ZONES (capa "zones"):
#    name = "poker" | "blackjack" | "roulette"
#
#  FITXERS NECESSARIS A LA CARPETA assets/:
#    casino.tmx
#    CasinoTileset.tsx  (o el nom que triïs)
#    2D_TopDown_Tileset_Casino_1024x512.png
#    (Animated Sprite Sheets/*.png  si vols animacions)
# ═══════════════════════════════════════════════════════════════════

import pygame
import math
import os

try:
    import pytmx
    PYTMX_OK = True
except ImportError:
    PYTMX_OK = False
    print("[world] pytmx no trobat — pip install pytmx")

from settings import C, TILE, MAP_W, MAP_H, SCREEN_W, SCREEN_H

# ── Fallback: mapa generat per codi (si no hi ha .tmx) ─────────────
EMPTY  = 0
FLOOR  = 1
WALL   = 2
CARPET = 3
TABLE  = 4
LAMP   = 6
BAR    = 7

ZONES = {}        # omplert en carregar el TMX (o valors per defecte)
ZONE_NAMES = {
    "poker":     "Poker",
    "blackjack": "Blackjack",
    "roulette":  "Ruleta",
    "slots":     "Tragaperras",
    "bowling":   "Bowling",
    "dice_duel": "Dados",
}
ZONE_INTERACT = {}

# Ruta per defecte del mapa
_MAP_PATH = os.path.join("assets", "casino.tmx")


# ════════════════════════════════════════════════════════════════════
#  CARREGADOR TMX
# ════════════════════════════════════════════════════════════════════
class TiledWorld:
    """Llegeix i renderitza un mapa de Tiled."""

    def __init__(self, tmx_path):
        self._tmx        = pytmx.load_pygame(tmx_path, pixelalpha=True)
        self._tw         = self._tmx.tilewidth    # mida tile del TMX (p.ex. 16)
        self._th         = self._tmx.tileheight
        self._map_w      = self._tmx.width        # tiles d'ample
        self._map_h      = self._tmx.height       # tiles d'alt
        self._scale      = TILE / self._tw        # escala a TILE (32px)
        self._solid      = set()                  # {(tx,ty)} tiles sòlids
        self._light_t    = 0.0

        # Cache de superfícies escalades
        self._surf_cache = {}

        # Carregar col·lisions i zones
        self._load_collisions()
        self._load_zones()

        # Sprites animats
        self._anim_sprites = {}   # {layer_name: [(surf, x, y)]}
        self._anim_t       = 0.0
        self._load_animations()

        print(f"[world] Mapa carregat: {self._map_w}x{self._map_h} tiles "
              f"({self._tw}px) → escala x{self._scale:.1f}")
        print(f"[world] Zones: {list(ZONES.keys())}")

    # ── Col·lisions ──────────────────────────────────────────────
    def _load_collisions(self):
        """Llegeix la propietat 'collides' dels tiles."""
        self._solid.clear()
        for layer in self._tmx.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, gid in layer:
                props = self._tmx.get_tile_properties_by_gid(gid) or {}
                if props.get("collides"):
                    tx = int(x * self._scale)
                    ty = int(y * self._scale)
                    # Cada tile TMX pot ocupar varios tiles interns si scale > 1
                    for dx in range(max(1, int(self._scale))):
                        for dy in range(max(1, int(self._scale))):
                            self._solid.add((tx + dx, ty + dy))

        # Capa "walls" sempre és sòlida
        walls_layer = self._tmx.get_layer_by_name("walls") if self._has_layer("walls") else None
        if walls_layer:
            for x, y, gid in walls_layer:
                if gid:
                    tx = int(x * self._scale)
                    ty = int(y * self._scale)
                    for dx in range(max(1, int(self._scale))):
                        for dy in range(max(1, int(self._scale))):
                            self._solid.add((tx + dx, ty + dy))

    def _load_zones(self):
        """Llegeix la capa d'objectes 'zones' per definir les àrees de joc."""
        global ZONES, ZONE_INTERACT
        ZONES.clear()
        ZONE_INTERACT.clear()

        if not self._has_layer("zones"):
            print("[world] Capa 'zones' no trobada — usant zones per defecte")
            self._default_zones()
            return

        obj_layer = self._tmx.get_layer_by_name("zones")
        for obj in obj_layer:
            name = obj.name.lower() if obj.name else ""
            if name in ("poker", "blackjack", "roulette"):
                # Escalar coordenades
                rx = int(obj.x * self._scale)
                ry = int(obj.y * self._scale)
                rw = int(obj.width  * self._scale)
                rh = int(obj.height * self._scale)
                ZONES[name] = pygame.Rect(rx, ry, rw, rh)
                # Punt d'interacció: centre de la zona
                ZONE_INTERACT[name] = pygame.Rect(
                    rx + rw // 2 - TILE, ry + rh // 2 - TILE,
                    TILE * 2, TILE * 2
                )

        if not ZONES:
            print("[world] Cap zona trobada a la capa 'zones' — usant zones per defecte")
            self._default_zones()

    def _default_zones(self):
        """Zones per defecte si no hi ha capa 'zones' al TMX."""
        global ZONES, ZONE_INTERACT
        ZONES = {
            "poker":     pygame.Rect(2*TILE,   2*TILE,  14*TILE, 12*TILE),
            "blackjack": pygame.Rect(20*TILE,  2*TILE,  16*TILE, 12*TILE),
            "roulette":  pygame.Rect(10*TILE, 16*TILE,  28*TILE, 14*TILE),
            "slots":     pygame.Rect(2*TILE,  16*TILE,   8*TILE, 12*TILE),
            "bowling":   pygame.Rect(38*TILE,  4*TILE,  10*TILE, 32*TILE),
            "dice_duel": pygame.Rect(10*TILE, 32*TILE,  28*TILE,  6*TILE),
        }
        ZONE_INTERACT = {
            k: pygame.Rect(v.centerx - TILE, v.centery - TILE, TILE * 2, TILE * 2)
            for k, v in ZONES.items()
        }

    def _load_animations(self):
        """Carrega els sprite sheets d'animació."""
        anim_dir = os.path.join("assets", "Animated Sprite Sheets")
        if not os.path.isdir(anim_dir):
            return

        # Slot machines
        for i in range(2):
            path = os.path.join(anim_dir, f"SlotMachinesAnimationSheet_{i}.png")
            if os.path.exists(path):
                sheet = pygame.image.load(path).convert_alpha()
                # 32x32 per frame, 8 frames per fila, 8 files = 64 frames
                self._anim_sprites[f"slot_{i}"] = {
                    "sheet":  sheet,
                    "fw": 32, "fh": 32,
                    "cols": sheet.get_width() // 32,
                    "total": (sheet.get_width() // 32) * (sheet.get_height() // 32),
                    "fps":   8,
                }

    def _has_layer(self, name):
        try:
            self._tmx.get_layer_by_name(name)
            return True
        except Exception:
            return False

    # ── Getters públics ──────────────────────────────────────────
    def is_solid(self, tx, ty):
        return (tx, ty) in self._solid

    def get_map_size_px(self):
        return (int(self._map_w * self._tw * self._scale),
                int(self._map_h * self._th * self._scale))

    # ── Escalar tile ──────────────────────────────────────────────
    def _get_scaled(self, surf):
        if self._scale == 1.0:
            return surf
        key = id(surf)
        if key not in self._surf_cache:
            nw = int(surf.get_width()  * self._scale)
            nh = int(surf.get_height() * self._scale)
            self._surf_cache[key] = pygame.transform.scale(surf, (nw, nh))
        return self._surf_cache[key]

    # ── Update ────────────────────────────────────────────────────
    def update(self, dt):
        self._light_t += dt
        self._anim_t  += dt

    # ── Draw ──────────────────────────────────────────────────────
    def draw(self, surf, cam_x, cam_y):
        sw, sh = surf.get_size()

        # Capes a dibuixar PER SOTA del jugador
        under_layers = ["floor", "floor2", "objects", "walls"]
        # Capes a dibuixar PER SOBRE del jugador
        above_layers = ["above"]

        self._draw_layers(surf, cam_x, cam_y, sw, sh, under_layers)
        self._draw_zone_glows(surf, cam_x, cam_y)

    def draw_above(self, surf, cam_x, cam_y):
        """Crides des de main.py DESPRÉS de dibuixar el jugador."""
        sw, sh = surf.get_size()
        self._draw_layers(surf, cam_x, cam_y, sw, sh, ["above"])

    def _draw_layers(self, surf, cam_x, cam_y, sw, sh, layer_names):
        ts = int(self._tw * self._scale)   # mida tile en pantalla

        for layer_name in layer_names:
            if not self._has_layer(layer_name):
                continue
            layer = self._tmx.get_layer_by_name(layer_name)
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue

            # Rang de tiles visible
            start_x = max(0, cam_x // ts)
            end_x   = min(self._map_w, start_x + sw // ts + 2)
            start_y = max(0, cam_y // ts)
            end_y   = min(self._map_h, start_y + sh // ts + 2)

            for ty in range(start_y, end_y):
                for tx in range(start_x, end_x):
                    tile_surf = self._tmx.get_tile_image(tx, ty, layer)
                    if tile_surf is None:
                        continue
                    scaled = self._get_scaled(tile_surf)
                    sx = tx * ts - cam_x
                    sy = ty * ts - cam_y
                    surf.blit(scaled, (sx, sy))

    def _draw_zone_glows(self, surf, cam_x, cam_y):
        """Aureola de llum sobre les zones de joc."""
        glow_colors = {
            "poker":     C["neon_red"],
            "blackjack": C["neon_cyan"],
            "roulette":  C["neon_gold"],
            "slots":     (200, 100, 255),
            "bowling":   (100, 200, 255),
            "dice_duel": (180, 255, 120),
        }
        a = int(20 + 15 * math.sin(self._light_t * 2.5))
        for zone_key, zone in ZONES.items():
            gc = glow_colors.get(zone_key, C["neon_gold"])
            gs = pygame.Surface((zone.width + 20, zone.height + 20), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*gc, a), (0, 0, zone.width + 20, zone.height + 20),
                             border_radius=12)
            surf.blit(gs, (zone.x - 10 - cam_x, zone.y - 10 - cam_y))

    def draw_zone_indicators(self, surf, cam_x, cam_y):
        """Fletxes que apunten a zones fora de pantalla."""
        sw, sh = surf.get_size()
        for k, z in ZONES.items():
            if not pygame.Rect(0, 0, sw, sh).colliderect(
                    pygame.Rect(z.x - cam_x, z.y - cam_y, z.width, z.height)):
                cx = max(20, min(sw - 20, z.centerx - cam_x))
                cy = max(20, min(sh - 20, z.centery - cam_y))
                names = {"poker": "Poker", "blackjack": "BJ", "roulette": "Rul."}
                try:
                    f = pygame.font.SysFont("Arial", 13, bold=True)
                    t = f.render(f"► {names.get(k, k)}", True, C["neon_gold"])
                    surf.blit(t, (cx, cy))
                except Exception:
                    pass

    def get_zone_at(self, px, py):
        for k, z in ZONE_INTERACT.items():
            if z.collidepoint(px, py):
                return k
        return None


# ════════════════════════════════════════════════════════════════════
#  FALLBACK: mapa generat per codi (igual que l'original)
# ════════════════════════════════════════════════════════════════════
def _build_fallback_map():
    m = [[FLOOR] * MAP_W for _ in range(MAP_H)]

    # Paredes exteriores
    for x in range(MAP_W):
        m[0][x] = WALL; m[MAP_H-1][x] = WALL
    for y in range(MAP_H):
        m[y][0] = WALL; m[y][MAP_W-1] = WALL

    # ── Sala Norte-Izquierda: POKER (tiles 2-13, 2-13) ──────────
    for y in range(2, 14):
        for x in range(2, 16):
            m[y][x] = CARPET

    # ── Sala Norte-Derecha: BLACKJACK (tiles 20-13, 2-13) ───────
    for y in range(2, 14):
        for x in range(20, 36):
            m[y][x] = CARPET

    # ── Pasillo central Norte ────────────────────────────────────
    for y in range(2, 14):
        for x in range(16, 20):
            m[y][x] = FLOOR

    # ── Sala Central: RULETA (tiles 10-36, 16-30) ───────────────
    for y in range(16, 30):
        for x in range(10, 38):
            m[y][x] = CARPET

    # ── Sala Oeste: TRAGAPERRAS (tiles 2-14, 16-28) ─────────────
    for y in range(16, 28):
        for x in range(2, 10):
            m[y][x] = CARPET

    # ── Sala Este: BOWLING (tiles 38-47, 4-35) ──────────────────
    for y in range(4, 36):
        for x in range(38, 48):
            m[y][x] = CARPET
    # Calle de bolos (madera)
    for y in range(8, 35):
        for x in range(39, 47):
            m[y][x] = FLOOR

    # ── Sala Sur: DADOS (tiles 10-36, 32-38) ────────────────────
    for y in range(32, 38):
        for x in range(10, 38):
            m[y][x] = CARPET

    # ── BAR central (separador norte-centro) ────────────────────
    for x in range(16, 22):
        for y in range(14, 16):
            m[y][x] = BAR

    # ── Lámparas decorativas ─────────────────────────────────────
    for pos in [
        (1,1),(1,MAP_W-2),(MAP_H-2,1),(MAP_H-2,MAP_W-2),
        (7,18),(7,19),(20,18),(20,19),
        (16,5),(16,25),(28,5),(28,25),
        (16,40),(28,40),(22,7),(22,32),
    ]:
        y_, x_ = pos
        if 0 < y_ < MAP_H-1 and 0 < x_ < MAP_W-1:
            m[y_][x_] = LAMP

    return m

_FALLBACK_MAP = _build_fallback_map()

_tile_cache = {}

def _ft(tx, ty):
    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
        return _FALLBACK_MAP[ty][tx]
    return WALL

def is_solid(tx, ty):
    """Funció global de col·lisió — compatible amb player.py."""
    t = _ft(tx, ty)
    return t in (WALL, TABLE, BAR)

def get_tile(tx, ty):
    return _ft(tx, ty)


def _make_floor_tile(v=0):
    k = f"f{v}"
    if k in _tile_cache: return _tile_cache[k]
    s = pygame.Surface((TILE, TILE))
    base = [C["floor1"], C["floor2"], C["floor3"]][v % 3]
    s.fill(base)
    if v % 2 == 0:
        pygame.draw.line(s, tuple(max(0,c-5) for c in base), (0,TILE//2),(TILE,TILE//2),1)
    else:
        pygame.draw.line(s, tuple(max(0,c-5) for c in base), (TILE//2,0),(TILE//2,TILE),1)
    _tile_cache[k] = s; return s

def _make_carpet_tile(x, y):
    k = f"c{(x+y)%2}"
    if k in _tile_cache: return _tile_cache[k]
    s = pygame.Surface((TILE, TILE))
    c = C["carpet1"] if (x+y)%2==0 else C["carpet2"]
    s.fill(c)
    pts = [(TILE//2,2),(TILE-2,TILE//2),(TILE//2,TILE-2),(2,TILE//2)]
    pygame.draw.polygon(s, C["carpet_pat"], pts, 1)
    _tile_cache[k] = s; return s

def _make_wall_tile(top=False):
    k = f"w{top}"
    if k in _tile_cache: return _tile_cache[k]
    s = pygame.Surface((TILE, TILE))
    c = C["wall_top"] if top else C["wall"]
    s.fill(c)
    for row in range(0, TILE, 8):
        off = 8 if (row//8)%2 else 0
        for col in range(-off, TILE+8, 16):
            pygame.draw.rect(s,(c[0]+8,c[1]+8,c[2]+8),(col+1,row+1,14,6))
    _tile_cache[k] = s; return s

def _make_bar_tile():
    if "bar" in _tile_cache: return _tile_cache["bar"]
    s = pygame.Surface((TILE, TILE)); s.fill((60,35,15))
    pygame.draw.rect(s,(80,50,20),(2,2,TILE-4,TILE-4))
    pygame.draw.rect(s,(100,65,25),(2,2,TILE-4,6))
    _tile_cache["bar"] = s; return s

def _make_lamp_tile():
    if "lamp" in _tile_cache: return _tile_cache["lamp"]
    s = pygame.Surface((TILE,TILE), pygame.SRCALPHA); s.fill((0,0,0,0))
    pygame.draw.circle(s,C["lamp_warm"],(TILE//2,TILE//2),TILE//3)
    pygame.draw.circle(s,C["neon_white"],(TILE//2,TILE//2),TILE//5)
    _tile_cache["lamp"] = s; return s


# ── Taules i decoració fallback ──────────────────────────────────────
def _draw_neon_sign(surf, x, y, txt, color):
    try:
        f = pygame.font.SysFont("Georgia", 22, bold=True)
        t2 = f.render(txt, True, (*color, 80))
        for dx,dy in [(-2,0),(2,0),(0,-2),(0,2)]:
            t2.set_alpha(60); surf.blit(t2, (x+dx, y+dy))
        surf.blit(f.render(txt, True, color), (x, y))
    except Exception: pass

def _draw_poker_table(surf, cx, cy, cam_x, cam_y):
    sx,sy = cx-cam_x, cy-cam_y
    tw,th = 160,90
    shadow = pygame.Surface((tw+10,th+10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow,(0,0,0,120),(0,0,tw+10,th+10))
    surf.blit(shadow,(sx-tw//2-5,sy-th//2+8))
    pygame.draw.ellipse(surf,C["table_edge"],(sx-tw//2-6,sy-th//2-6,tw+12,th+12))
    pygame.draw.ellipse(surf,C["felt_poker"],(sx-tw//2,sy-th//2,tw,th))
    try:
        f=pygame.font.SysFont("Georgia",11,bold=True)
        surf.blit(f.render("POKER",True,(0,0,0)),
                  f.render("POKER",True,(0,0,0)).get_rect(center=(sx,sy)))
    except: pass

def _draw_blackjack_table(surf, cx, cy, cam_x, cam_y):
    sx,sy = cx-cam_x, cy-cam_y
    tw,th = 160,90
    shadow = pygame.Surface((tw+10,th+10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow,(0,0,0,120),(0,0,tw+10,th+10))
    surf.blit(shadow,(sx-tw//2-5,sy-th//2+8))
    pygame.draw.ellipse(surf,C["table_edge"],(sx-tw//2-6,sy-th//2-6,tw+12,th+12))
    pygame.draw.ellipse(surf,C["felt_bj"],(sx-tw//2,sy-th//2,tw,th))

def _draw_roulette_table(surf, cx, cy, cam_x, cam_y):
    sx,sy = cx-cam_x, cy-cam_y
    pygame.draw.circle(surf,C["table_edge"],(sx,sy),58)
    pygame.draw.circle(surf,C["felt_rul"],(sx,sy),50)
    for i in range(37):
        angle = math.radians(i*(360/37)-90)
        rx,ry = sx+int(42*math.cos(angle)), sy+int(42*math.sin(angle))
        color = (180,20,20) if i%2==1 else (200,200,200)
        if i==0: color=(20,130,50)
        pygame.draw.circle(surf,color,(rx,ry),5)
    pygame.draw.circle(surf,C["table_edge"],(sx,sy),8)
    pygame.draw.circle(surf,C["neon_gold"],(sx,sy),5)


def _draw_slot_machine(surf, cx, cy, cam_x, cam_y):
    sx, sy = cx - cam_x, cy - cam_y
    # Cuerpo
    pygame.draw.rect(surf, (60, 20, 60), (sx-18, sy-28, 36, 52), border_radius=6)
    pygame.draw.rect(surf, (120, 40, 120), (sx-16, sy-26, 32, 48), border_radius=5)
    pygame.draw.rect(surf, C["neon_gold"], (sx-16, sy-26, 32, 48), 2, border_radius=5)
    # Pantalla con rodillos
    pygame.draw.rect(surf, (20, 10, 20), (sx-12, sy-20, 24, 22), border_radius=3)
    for i in range(3):
        rx = sx - 8 + i * 8
        pygame.draw.rect(surf, (40, 200, 40), (rx, sy-18, 6, 18), border_radius=2)
    # Botón
    pygame.draw.circle(surf, (200, 30, 30), (sx, sy+16), 6)
    pygame.draw.circle(surf, (255, 80, 80), (sx, sy+16), 4)
    # Palanca
    pygame.draw.line(surf, C["table_edge"], (sx+18, sy-10), (sx+24, sy+8), 3)
    pygame.draw.circle(surf, (220, 40, 40), (sx+24, sy+8), 5)


def _draw_bowling_lane(surf, cx, cy, cam_x, cam_y):
    sx, sy = cx - cam_x, cy - cam_y
    # Calle
    pygame.draw.rect(surf, (180, 140, 80), (sx-30, sy-80, 60, 160), border_radius=4)
    pygame.draw.rect(surf, (210, 170, 110), (sx-26, sy-76, 52, 152), border_radius=3)
    # Líneas de la calle
    for i in range(1, 5):
        y_line = sy - 76 + i * 30
        pygame.draw.line(surf, (230, 195, 140), (sx-26, y_line), (sx+26, y_line), 1)
    # Bolos (triángulo)
    pin_pos = [(0,-60),(-8,-72),(8,-72),(0,-84)]
    for px_, py_ in pin_pos:
        pygame.draw.ellipse(surf, (245,245,245), (sx+px_-5, sy+py_-8, 10, 16))
        pygame.draw.rect(surf, (200,30,30), (sx+px_-4, sy+py_-2, 8, 3))
    # Bola
    pygame.draw.circle(surf, (40, 40, 80), (sx, sy+50), 10)
    pygame.draw.circle(surf, (80, 80, 160), (sx-3, sy+46), 3)


def _draw_dice_table(surf, cx, cy, cam_x, cam_y):
    sx, sy = cx - cam_x, cy - cam_y
    tw, th = 140, 70
    # Mesa
    pygame.draw.rect(surf, C["table_edge"], (sx-tw//2-4, sy-th//2-4, tw+8, th+8), border_radius=10)
    pygame.draw.rect(surf, C["felt_poker"], (sx-tw//2, sy-th//2, tw, th), border_radius=8)
    # Dos dados
    for dx_ in [-22, 22]:
        dr = pygame.Rect(sx+dx_-12, sy-12, 24, 24)
        pygame.draw.rect(surf, (250, 248, 240), dr, border_radius=5)
        pygame.draw.rect(surf, C["ui_border"], dr, 2, border_radius=5)
        # Puntos de dado (valor 4)
        for dpx, dpy in [(-5,-5),(5,-5),(-5,5),(5,5)]:
            pygame.draw.circle(surf, (20,20,30), (sx+dx_+dpx, sy+dpy), 3)


# ════════════════════════════════════════════════════════════════════
#  CLASSE World  — interfície unificada (TMX o fallback)
# ════════════════════════════════════════════════════════════════════
class World:
    def __init__(self):
        self._light_timer = 0.0
        self._lamp_alpha  = 100
        self._tiled       = None

        # Intentar carregar el mapa de Tiled
        if PYTMX_OK and os.path.exists(_MAP_PATH):
            try:
                self._tiled = TiledWorld(_MAP_PATH)
                # Sobreescriure la funció global is_solid
                _patch_is_solid(self._tiled)
                print("[world] Mode Tiled actiu")
            except Exception as e:
                print(f"[world] Error carregant TMX: {e} — usant mapa fallback")
                self._tiled = None
        else:
            if not PYTMX_OK:
                print("[world] pytmx no disponible — usa: pip install pytmx")
            elif not os.path.exists(_MAP_PATH):
                print(f"[world] Mapa no trobat a '{_MAP_PATH}' — usant mapa fallback")

        # Zones per defecte si no hi ha Tiled
        if not self._tiled and not ZONES:
            _init_default_zones()

    def update(self, dt):
        self._light_timer += dt
        self._lamp_alpha = int(180 + 60 * math.sin(self._light_timer * 2.5))
        if self._tiled:
            self._tiled.update(dt)

    def draw(self, surf, cam_x, cam_y):
        if self._tiled:
            self._tiled.draw(surf, cam_x, cam_y)
        else:
            self._draw_fallback(surf, cam_x, cam_y)

    def draw_zone_indicators(self, surf, cam_x, cam_y):
        if self._tiled:
            self._tiled.draw_zone_indicators(surf, cam_x, cam_y)
        else:
            self._draw_fallback_indicators(surf, cam_x, cam_y)

    def get_zone_at(self, px, py):
        if self._tiled:
            return self._tiled.get_zone_at(px, py)
        for k, z in ZONE_INTERACT.items():
            if z.collidepoint(px, py):
                return k
        return None

    # ── Render fallback ──────────────────────────────────────────
    def _draw_fallback(self, surf, cam_x, cam_y):
        start_tx = max(0, cam_x // TILE)
        end_tx   = min(MAP_W, start_tx + SCREEN_W // TILE + 2)
        start_ty = max(0, cam_y // TILE)
        end_ty   = min(MAP_H, start_ty + SCREEN_H // TILE + 2)

        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                t  = _FALLBACK_MAP[ty][tx]
                sx = tx*TILE - cam_x
                sy = ty*TILE - cam_y
                if t == WALL:
                    is_top = (ty+1 < MAP_H and _FALLBACK_MAP[ty+1][tx] != WALL)
                    surf.blit(_make_wall_tile(is_top), (sx, sy))
                elif t == CARPET:
                    surf.blit(_make_carpet_tile(tx, ty), (sx, sy))
                elif t == BAR:
                    surf.blit(_make_bar_tile(), (sx, sy))
                elif t == LAMP:
                    surf.blit(_make_floor_tile((tx+ty)%3), (sx, sy))
                    surf.blit(_make_lamp_tile(), (sx, sy))
                else:
                    surf.blit(_make_floor_tile((tx+ty)%3), (sx, sy))

        # Taules
        pz = ZONES.get("poker")
        if pz:
            _draw_poker_table(surf, pz.centerx, pz.top+pz.height//3, cam_x, cam_y)
            _draw_poker_table(surf, pz.centerx, pz.top+2*pz.height//3, cam_x, cam_y)
        bz = ZONES.get("blackjack")
        if bz:
            _draw_blackjack_table(surf, bz.centerx, bz.top+bz.height//3, cam_x, cam_y)
            _draw_blackjack_table(surf, bz.centerx, bz.top+2*bz.height//3, cam_x, cam_y)
        rz = ZONES.get("roulette")
        if rz:
            _draw_roulette_table(surf, rz.centerx - 80, rz.centery, cam_x, cam_y)
            _draw_roulette_table(surf, rz.centerx + 80, rz.centery, cam_x, cam_y)
        sz = ZONES.get("slots")
        if sz:
            for i in range(3):
                _draw_slot_machine(surf, sz.centerx, sz.top + 40 + i*60, cam_x, cam_y)
        bwz = ZONES.get("bowling")
        if bwz:
            _draw_bowling_lane(surf, bwz.centerx - 60, bwz.centery, cam_x, cam_y)
            _draw_bowling_lane(surf, bwz.centerx + 60, bwz.centery, cam_x, cam_y)
        dz = ZONES.get("dice_duel")
        if dz:
            _draw_dice_table(surf, dz.centerx - 70, dz.centery, cam_x, cam_y)
            _draw_dice_table(surf, dz.centerx + 70, dz.centery, cam_x, cam_y)

        # Senyals neó
        if pz:  _draw_neon_sign(surf, pz.left-cam_x,  pz.top-28-cam_y,  "◆ POKER ◆",        C["neon_red"])
        if bz:  _draw_neon_sign(surf, bz.left-cam_x,  bz.top-28-cam_y,  "♠ BLACKJACK ♠",    C["neon_cyan"])
        if rz:  _draw_neon_sign(surf, rz.left-cam_x,  rz.top-28-cam_y,  "● RULETA ●",        C["neon_gold"])
        if sz:  _draw_neon_sign(surf, sz.left-cam_x,  sz.top-28-cam_y,  "🎰 TRAGAPERRAS",    C["neon_gold"])
        if bwz: _draw_neon_sign(surf, bwz.left-cam_x, bwz.top-28-cam_y, "🎳 BOWLING",        (100, 200, 255))
        if dz:  _draw_neon_sign(surf, dz.left-cam_x,  dz.top-28-cam_y,  "🎲 DADOS",          (200, 150, 255))
        _draw_neon_sign(surf, SCREEN_W//2-130, 18, "✦  GRAND CASINO ROYAL  ✦", C["neon_gold"])

        # Aureoles de zona
        glow_colors = {
            "poker":     C["neon_red"],
            "blackjack": C["neon_cyan"],
            "roulette":  C["neon_gold"],
            "slots":     (200, 100, 255),
            "bowling":   (100, 200, 255),
            "dice_duel": (180, 255, 120),
        }
        for zk, zone in ZONES.items():
            gc = glow_colors.get(zk, C["neon_gold"])
            a  = max(20, min(60, self._lamp_alpha//4))
            gs = pygame.Surface((zone.width+20, zone.height+20), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*gc, a), (0,0,zone.width+20,zone.height+20), border_radius=12)
            surf.blit(gs, (zone.x-10-cam_x, zone.y-10-cam_y))

    def _draw_fallback_indicators(self, surf, cam_x, cam_y):
        sw, sh = surf.get_size()
        for k, z in ZONES.items():
            if not pygame.Rect(0,0,sw,sh).colliderect(
                    pygame.Rect(z.x-cam_x,z.y-cam_y,z.width,z.height)):
                cx = max(20, min(sw-20, z.centerx-cam_x))
                cy = max(20, min(sh-20, z.centery-cam_y))
                names = {"poker":"Poker","blackjack":"BJ","roulette":"Rul."}
                try:
                    f=pygame.font.SysFont("Arial",13,bold=True)
                    t=f.render(f"► {names.get(k,k)}",True,C["neon_gold"])
                    surf.blit(t,(cx,cy))
                except: pass


# ── Helpers globals ──────────────────────────────────────────────────
def _patch_is_solid(tiled_world):
    """Sobreescriu la funció is_solid global per usar el TiledWorld."""
    import sys
    this_module = sys.modules[__name__]

    def _new_is_solid(tx, ty):
        return tiled_world.is_solid(tx, ty)

    this_module.is_solid = _new_is_solid


def _init_default_zones():
    global ZONES, ZONE_INTERACT
    ZONES = {
        "poker":     pygame.Rect(2*TILE,   2*TILE,  14*TILE, 12*TILE),
        "blackjack": pygame.Rect(20*TILE,  2*TILE,  16*TILE, 12*TILE),
        "roulette":  pygame.Rect(10*TILE, 16*TILE,  28*TILE, 14*TILE),
        "slots":     pygame.Rect(2*TILE,  16*TILE,   8*TILE, 12*TILE),
        "bowling":   pygame.Rect(38*TILE,  4*TILE,  10*TILE, 32*TILE),
        "dice_duel": pygame.Rect(10*TILE, 32*TILE,  28*TILE,  6*TILE),
    }
    ZONE_INTERACT = {
        k: pygame.Rect(v.centerx - TILE, v.centery - TILE, TILE*2, TILE*2)
        for k, v in ZONES.items()
    }

# Inicialitzar zones per defecte immediatament (per si world.py s'importa sense crear World)
_init_default_zones()
