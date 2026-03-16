# ═══════════════════════════════════════════════════════════════════
#  PLAYER — moviment, animació i col·lisions
# ═══════════════════════════════════════════════════════════════════
import pygame
import math
from settings import C, TILE, PLAYER_SPEED, PLAYER_W, PLAYER_H
from world import is_solid

# Punts d'inici (centre del mapa, corredor central)
START_X = 19 * TILE
START_Y = 18 * TILE


class Player:
    def __init__(self):
        self.x      = float(START_X)
        self.y      = float(START_Y)
        self.vx     = 0.0
        self.vy     = 0.0
        self.facing = "down"   # up / down / left / right
        self.moving = False

        # Animació
        self._anim_timer = 0.0
        self._anim_frame = 0
        self._bob        = 0.0  # oscil·lació vertical

        # Sprites generats per codi
        self._sprites = _make_player_sprites()

    # ── Propietats ────────────────────────────────────────────────
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

    # ── Update ────────────────────────────────────────────────────
    def update(self, dt, keys):
        dx, dy = 0.0, 0.0

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            dx -= PLAYER_SPEED
            self.facing = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED
            self.facing = "right"
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            dy -= PLAYER_SPEED
            self.facing = "up"
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            dy += PLAYER_SPEED
            self.facing = "down"

        # Normalitzar diagonal
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        self.moving = (dx != 0 or dy != 0)

        # Col·lisió X
        new_x = self.x + dx
        if not self._collides(new_x, self.y):
            self.x = new_x

        # Col·lisió Y
        new_y = self.y + dy
        if not self._collides(self.x, new_y):
            self.y = new_y

        # Animació caminar
        if self.moving:
            self._anim_timer += dt * 8
            self._anim_frame  = int(self._anim_timer) % 4
            self._bob = math.sin(self._anim_timer * math.pi) * 2
        else:
            self._anim_frame  = 0
            self._bob         = 0.0
            self._anim_timer  = 0.0

    def _collides(self, px, py):
        hw = PLAYER_W // 2 - 4
        hh = PLAYER_H // 2 - 8
        corners = [
            (px - hw, py + hh),
            (px + hw, py + hh),
            (px - hw, py - hh),
            (px + hw, py - hh),
        ]
        for cx, cy in corners:
            tx = int(cx) // TILE
            ty = int(cy) // TILE
            if is_solid(tx, ty):
                return True
        return False

    # ── Draw ──────────────────────────────────────────────────────
    def draw(self, surf, cam_x, cam_y):
        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y + int(self._bob)

        sprite = self._sprites[self.facing][self._anim_frame]

        # Ombra al terra
        shadow = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0,0,0,80), (0,0,28,10))
        surf.blit(shadow, (sx - 14, sy + PLAYER_H//2 - 4))

        # Personatge
        surf.blit(sprite, (sx - PLAYER_W//2, sy - PLAYER_H//2))

        # Indicador de posició (punt de llum)
        pygame.draw.circle(surf, C["neon_gold"],
                           (sx, sy - PLAYER_H//2 - 6), 3)
        pygame.draw.circle(surf, C["neon_white"],
                           (sx, sy - PLAYER_H//2 - 6), 2)


# ── Generador de sprites ──────────────────────────────────────────────
def _make_player_sprites():
    """Genera 4 direccions × 4 frames de personatge pixel-art."""
    sprites = {"up": [], "down": [], "left": [], "right": []}

    for direction in sprites:
        for frame in range(4):
            s = _draw_character(direction, frame)
            sprites[direction].append(s)

    return sprites


def _draw_character(direction, frame):
    w, h = PLAYER_W, PLAYER_H
    s = pygame.Surface((w, h), pygame.SRCALPHA)

    # Animació de cames
    leg_offset = [0, 3, 0, -3][frame]

    skin   = C["player_skin"]
    body   = C["player_body"]
    hair   = C["player_hair"]
    shoes  = C["player_shoes"]
    dark   = (max(0,body[0]-30), max(0,body[1]-30), max(0,body[2]-30))

    # ── Cap ──────────────────────────────────────────────────────
    cx = w // 2
    cy = 8
    pygame.draw.ellipse(s, skin, (cx-5, cy-5, 10, 11))

    # Cabell
    if direction == "down":
        pygame.draw.arc(s, hair,
                        (cx-5, cy-5, 10, 8), 0, math.pi, 3)
        # Ulls
        pygame.draw.circle(s, (20,20,20), (cx-2, cy), 1)
        pygame.draw.circle(s, (20,20,20), (cx+2, cy), 1)
    elif direction == "up":
        pygame.draw.arc(s, hair,
                        (cx-5, cy-5, 10, 10), 0, math.pi, 4)
    else:
        # Lateral
        eye_x = cx + (3 if direction=="right" else -3)
        pygame.draw.circle(s, (20,20,20), (eye_x, cy), 1)
        pygame.draw.arc(s, hair,
                        (cx-5, cy-5, 10, 9), 0, math.pi, 3)

    # ── Cos ──────────────────────────────────────────────────────
    body_y = cy + 7
    pygame.draw.rect(s, body, (cx-5, body_y, 10, 11), border_radius=2)
    # Solapa
    if direction in ("down","left","right"):
        pygame.draw.line(s, dark, (cx, body_y+1), (cx, body_y+8), 1)

    # ── Braços ───────────────────────────────────────────────────
    arm_swing = [2, 4, 2, 0][frame]
    if direction in ("left","right"):
        arm_swing = 0

    # Braç esquerre
    pygame.draw.line(s, body,
                     (cx-5, body_y+2),
                     (cx-7, body_y+7 + (arm_swing if direction=="down" else 0)),
                     3)
    pygame.draw.circle(s, skin, (cx-7, body_y+7+arm_swing), 2)

    # Braç dret
    pygame.draw.line(s, body,
                     (cx+5, body_y+2),
                     (cx+7, body_y+7 - (arm_swing if direction=="down" else 0)),
                     3)
    pygame.draw.circle(s, skin, (cx+7, body_y+7-arm_swing), 2)

    # ── Cames ────────────────────────────────────────────────────
    leg_y = body_y + 11
    # Cama esquerra
    pygame.draw.line(s, dark,
                     (cx-3, leg_y),
                     (cx-3, leg_y+8 + leg_offset),
                     4)
    pygame.draw.rect(s, shoes, (cx-6, leg_y+8+leg_offset, 6, 3),
                     border_radius=1)

    # Cama dreta
    pygame.draw.line(s, dark,
                     (cx+3, leg_y),
                     (cx+3, leg_y+8 - leg_offset),
                     4)
    pygame.draw.rect(s, shoes, (cx+1, leg_y+8-leg_offset, 6, 3),
                     border_radius=1)

    return s
