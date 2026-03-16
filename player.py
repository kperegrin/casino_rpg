# ═══════════════════════════════════════════════════════════════════
#  PLAYER — moviment, animació i col·lisions
#  Soporta sprites reales de:
#   - assets/characters/2D Top Down Pixel Art Characters/XXX.png
#     (64x128, 2 cols x 4 rows, 32x32 por frame)
#     Row0=down, Row1=left, Row2=right, Row3=up  (2 frames cada dir)
#   - assets/characters/mana_seed/char_a_pONE3_0bas_humn_v03.png
#     (512x512, 8 cols x 8 rows de 64x64)
#     Row0=walk_down, Row1=walk_left, Row2=walk_right, Row3=walk_up
# ═══════════════════════════════════════════════════════════════════
import pygame
import math
import os
from settings import C, TILE, PLAYER_SPEED, PLAYER_W, PLAYER_H
from world import is_solid

START_X = 19 * TILE
START_Y = 18 * TILE

# ── Rutas de assets de personajes ───────────────────────────────────
_CHARS_DIR   = os.path.join("assets", "characters", "2D Top Down Pixel Art Characters")
_MANA_DIR    = os.path.join("assets", "characters", "mana_seed", "char_a_pONE3")
_CHAR_FILE   = "003.png"   # puedes cambiar a cualquier número del pack (001-039)
_MANA_FILE   = "char_a_pONE3_0bas_humn_v03.png"

# NPC sprites (otros personajes del casino)
NPC_FILES = ["005.png", "010.png", "015.png", "017.png", "021.png", "029.png"]

_sprite_cache = {}


# ════════════════════════════════════════════════════════════════════
#  Loaders de sprite sheets
# ════════════════════════════════════════════════════════════════════
def _load_topdown_pack(filename, target_w=32, target_h=32):
    """
    Carga un PNG del pack 'Top Down Pixel Art Characters'.
    Layout: 64x128 → 2 cols x 4 rows de 32x32
    Orden de filas: down(0), left(1), right(2), up(3)
    Cada fila tiene 2 frames de animación walk.
    Devuelve dict {dir: [frame0, frame1, ...]}
    """
    path = os.path.join(_CHARS_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        return None

    fw, fh = 32, 32  # tamaño de cada frame en el sheet
    dir_rows = {"down": 0, "left": 1, "right": 2, "up": 3}
    sprites = {}
    for direction, row in dir_rows.items():
        frames = []
        for col in range(2):
            region = pygame.Rect(col * fw, row * fh, fw, fh)
            frame  = sheet.subsurface(region).copy()
            if target_w != fw or target_h != fh:
                frame = pygame.transform.smoothscale(frame, (target_w, target_h))
            frames.append(frame)
        # Duplicar frames para tener 4 (0,1,0,1) como el fallback espera
        sprites[direction] = [frames[0], frames[1], frames[0], frames[1]]
    return sprites


def _load_mana_seed(filename, target_w=32, target_h=32):
    """
    Carga un PNG de Mana Seed.
    Layout: 512x512 → 8 cols x 8 rows de 64x64
    Filas walk: Row0=down, Row1=left, Row2=right, Row3=up
    Cada fila tiene hasta 8 frames; usamos los primeros 4.
    """
    path = os.path.join(_MANA_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        return None

    fw, fh = 64, 64
    dir_rows = {"down": 0, "left": 1, "right": 2, "up": 3}
    sprites = {}
    for direction, row in dir_rows.items():
        frames = []
        for col in range(4):  # 4 frames por dirección
            region = pygame.Rect(col * fw, row * fh, fw, fh)
            frame  = sheet.subsurface(region).copy()
            frame  = pygame.transform.smoothscale(frame, (target_w, target_h))
            frames.append(frame)
        sprites[direction] = frames
    return sprites


def _make_procedural_sprites():
    """Genera sprites por código (fallback sin assets)."""
    sprites = {"up": [], "down": [], "left": [], "right": []}
    for direction in sprites:
        for frame in range(4):
            s = _draw_character_proc(direction, frame)
            sprites[direction].append(s)
    return sprites


def load_player_sprites(target_w=PLAYER_W, target_h=PLAYER_H):
    """
    Intenta cargar sprites en este orden:
    1. Mana Seed (mayor calidad)
    2. Top Down Pack
    3. Procedural (fallback)
    """
    key = f"player_{target_w}_{target_h}"
    if key in _sprite_cache:
        return _sprite_cache[key]

    sprites = _load_mana_seed(_MANA_FILE, target_w, target_h)
    if sprites:
        print(f"[player] Sprites cargados: Mana Seed ({_MANA_FILE})")
        _sprite_cache[key] = sprites
        return sprites

    sprites = _load_topdown_pack(_CHAR_FILE, target_w, target_h)
    if sprites:
        print(f"[player] Sprites cargados: Top Down Pack ({_CHAR_FILE})")
        _sprite_cache[key] = sprites
        return sprites

    print("[player] Usando sprites procedurales (no se encontraron assets)")
    sprites = _make_procedural_sprites()
    _sprite_cache[key] = sprites
    return sprites


def load_npc_sprites(npc_index=0, target_w=PLAYER_W, target_h=PLAYER_H):
    """Carga sprites de NPC del pack top-down."""
    npc_file = NPC_FILES[npc_index % len(NPC_FILES)]
    key = f"npc_{npc_file}_{target_w}_{target_h}"
    if key in _sprite_cache:
        return _sprite_cache[key]
    sprites = _load_topdown_pack(npc_file, target_w, target_h)
    if not sprites:
        sprites = _make_procedural_sprites()
    _sprite_cache[key] = sprites
    return sprites


# ════════════════════════════════════════════════════════════════════
#  Sprite procedural (fallback)
# ════════════════════════════════════════════════════════════════════
def _draw_character_proc(direction, frame):
    w, h = PLAYER_W, PLAYER_H
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    leg_offset = [0, 3, 0, -3][frame]
    skin  = C["player_skin"]
    body  = C["player_body"]
    hair  = C["player_hair"]
    shoes = C["player_shoes"]
    dark  = (max(0,body[0]-30), max(0,body[1]-30), max(0,body[2]-30))
    cx = w // 2
    cy = 8
    pygame.draw.ellipse(s, skin, (cx-5, cy-5, 10, 11))
    if direction == "down":
        pygame.draw.arc(s, hair, (cx-5,cy-5,10,8), 0, math.pi, 3)
        pygame.draw.circle(s, (20,20,20), (cx-2,cy), 1)
        pygame.draw.circle(s, (20,20,20), (cx+2,cy), 1)
    elif direction == "up":
        pygame.draw.arc(s, hair, (cx-5,cy-5,10,10), 0, math.pi, 4)
    else:
        eye_x = cx + (3 if direction=="right" else -3)
        pygame.draw.circle(s, (20,20,20), (eye_x,cy), 1)
        pygame.draw.arc(s, hair, (cx-5,cy-5,10,9), 0, math.pi, 3)
    body_y = cy + 7
    pygame.draw.rect(s, body, (cx-5,body_y,10,11), border_radius=2)
    if direction in ("down","left","right"):
        pygame.draw.line(s, dark, (cx,body_y+1),(cx,body_y+8), 1)
    arm_swing = [2,4,2,0][frame]
    if direction in ("left","right"):
        arm_swing = 0
    pygame.draw.line(s, body, (cx-5,body_y+2),(cx-7,body_y+7+(arm_swing if direction=="down" else 0)), 3)
    pygame.draw.circle(s, skin, (cx-7,body_y+7+arm_swing), 2)
    pygame.draw.line(s, body, (cx+5,body_y+2),(cx+7,body_y+7-(arm_swing if direction=="down" else 0)), 3)
    pygame.draw.circle(s, skin, (cx+7,body_y+7-arm_swing), 2)
    leg_y = body_y + 11
    pygame.draw.line(s, dark, (cx-3,leg_y),(cx-3,leg_y+8+leg_offset), 4)
    pygame.draw.rect(s, shoes, (cx-6,leg_y+8+leg_offset,6,3), border_radius=1)
    pygame.draw.line(s, dark, (cx+3,leg_y),(cx+3,leg_y+8-leg_offset), 4)
    pygame.draw.rect(s, shoes, (cx+1,leg_y+8-leg_offset,6,3), border_radius=1)
    return s


# ════════════════════════════════════════════════════════════════════
#  Clase Player
# ════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self):
        self.x      = float(START_X)
        self.y      = float(START_Y)
        self.vx     = 0.0
        self.vy     = 0.0
        self.facing = "down"
        self.moving = False

        self._anim_timer = 0.0
        self._anim_frame = 0
        self._bob        = 0.0

        self._sprites = load_player_sprites(PLAYER_W, PLAYER_H)
        self._anim_speed = 7.0  # frames por segundo

    @property
    def rect(self):
        return pygame.Rect(
            int(self.x) - PLAYER_W // 2,
            int(self.y) - PLAYER_H // 2,
            PLAYER_W, PLAYER_H
        )

    @property
    def center(self):
        return (int(self.x), int(self.y))

    @property
    def tile_x(self):
        return int(self.x) // TILE

    @property
    def tile_y(self):
        return int(self.y) // TILE

    def update(self, dt, keys):
        dx, dy = 0.0, 0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= PLAYER_SPEED; self.facing = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += PLAYER_SPEED; self.facing = "right"
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= PLAYER_SPEED; self.facing = "up"
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += PLAYER_SPEED; self.facing = "down"

        if dx != 0 and dy != 0:
            dx *= 0.707; dy *= 0.707

        self.moving = (dx != 0 or dy != 0)

        new_x = self.x + dx
        if not self._collides(new_x, self.y):
            self.x = new_x
        new_y = self.y + dy
        if not self._collides(self.x, new_y):
            self.y = new_y

        if self.moving:
            self._anim_timer += dt * self._anim_speed
            self._anim_frame  = int(self._anim_timer) % 4
            self._bob = math.sin(self._anim_timer * math.pi) * 2
        else:
            self._anim_frame  = 0
            self._bob         = 0.0
            self._anim_timer  = 0.0

    def _collides(self, px, py):
        hw = PLAYER_W // 2 - 4
        hh = PLAYER_H // 2 - 8
        for cx, cy in [(px-hw,py+hh),(px+hw,py+hh),(px-hw,py-hh),(px+hw,py-hh)]:
            if is_solid(int(cx)//TILE, int(cy)//TILE):
                return True
        return False

    def draw(self, surf, cam_x, cam_y):
        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y + int(self._bob)

        frames = self._sprites.get(self.facing, self._sprites.get("down", []))
        if not frames:
            return
        frame_idx = min(self._anim_frame, len(frames)-1)
        sprite = frames[frame_idx]

        # Sombra
        shadow = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0,0,0,80), (0,0,28,10))
        surf.blit(shadow, (sx-14, sy+PLAYER_H//2-4))

        # Sprite
        surf.blit(sprite, (sx - PLAYER_W//2, sy - PLAYER_H//2))

        # Indicador de posición
        pygame.draw.circle(surf, C["neon_gold"],  (sx, sy-PLAYER_H//2-6), 3)
        pygame.draw.circle(surf, C["neon_white"], (sx, sy-PLAYER_H//2-6), 2)
