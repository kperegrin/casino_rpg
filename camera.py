# ═══════════════════════════════════════════════════════════════════
#  CAMERA — seguiment suau del jugador
# ═══════════════════════════════════════════════════════════════════
from settings import TILE, MAP_W, MAP_H, SCREEN_W, SCREEN_H

MAP_PX_W = MAP_W * TILE
MAP_PX_H = MAP_H * TILE


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0

    def follow(self, target_x, target_y, dt, smooth=8.0):
        """Seguiment suau (lerp)."""
        # Centrar la càmera sobre el jugador
        self._target_x = target_x - SCREEN_W // 2
        self._target_y = target_y - SCREEN_H // 2

        # Lerp
        factor = min(1.0, dt * smooth)
        self.x += (self._target_x - self.x) * factor
        self.y += (self._target_y - self.y) * factor

        # Límits del mapa
        self.x = max(0, min(self.x, MAP_PX_W - SCREEN_W))
        self.y = max(0, min(self.y, MAP_PX_H - SCREEN_H))

    def snap(self, target_x, target_y):
        """Posicionament immediat (sense interpolació)."""
        self.x = target_x - SCREEN_W // 2
        self.y = target_y - SCREEN_H // 2
        self.x = max(0, min(self.x, MAP_PX_W - SCREEN_W))
        self.y = max(0, min(self.y, MAP_PX_H - SCREEN_H))

    @property
    def ix(self):
        return int(self.x)

    @property
    def iy(self):
        return int(self.y)
