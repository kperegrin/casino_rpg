# ═══════════════════════════════════════════════════════════════════
#  SETTINGS — Casino RPG
# ═══════════════════════════════════════════════════════════════════

# Pantalla
SCREEN_W     = 1280
SCREEN_H     = 720
FPS          = 60
TITLE        = "Grand Casino Royal"

# Tile
TILE         = 32          # píxels per tile
MAP_W        = 50          # tiles d'ample
MAP_H        = 40          # tiles d'alt

# Jugador
PLAYER_SPEED = 3
PLAYER_W     = 24
PLAYER_H     = 32
START_CHIPS  = 2000        # fitxes inicials

# Zona d'interacció (px de radi)
INTERACT_DIST = 48

# ── Millores de llegibilitat ────────────────────────────────────────
# Mida de font base (augmentar per millorar llegibilitat)
FONT_SCALE   = 1.15        # multiplicador global de fonts

# Paleta de colors
C = {
    # Fons casino
    "bg":           (8,   18,  10),
    "floor1":       (20,  60,  30),
    "floor2":       (18,  52,  26),
    "floor3":       (14,  44,  22),
    "wall":         (12,  28,  16),
    "wall_top":     (10,  22,  13),

    # Moqueta
    "carpet1":      (80,  15,  15),
    "carpet2":      (70,  12,  12),
    "carpet_pat":   (90,  20,  20),

    # Taules
    "felt_poker":   (18,  90,  40),
    "felt_bj":      (15,  75,  35),
    "felt_rul":     (20,  100, 45),
    "table_edge":   (80,  55,  20),
    "table_leg":    (60,  40,  15),

    # Llums / neó
    "neon_gold":    (255, 210, 50),
    "neon_red":     (220, 30,  30),
    "neon_cyan":    (0,   210, 210),
    "neon_white":   (240, 240, 255),
    "lamp_warm":    (255, 200, 100),
    "accent":       (180, 120, 20),

    # UI
    "ui_bg":        (10,  10,  20),
    "ui_border":    (180, 150, 50),
    "ui_text":      (240, 220, 160),
    "ui_sub":       (140, 120, 80),
    "ui_green":     (50,  200, 80),
    "ui_red":       (200, 50,  50),
    "ui_blue":      (60,  120, 220),
    "chips":        (255, 210, 50),

    # Cartes
    "card_white":   (252, 248, 238),
    "card_red":     (190, 20,  20),
    "card_black":   (15,  15,  25),
    "card_back":    (20,  40,  120),
    "card_border":  (200, 180, 120),

    # Personatge
    "player_body":  (60,  130, 220),
    "player_skin":  (210, 170, 130),
    "player_hair":  (40,  25,  15),
    "player_shoes": (30,  20,  10),

    # NPCs
    "npc1":         (180, 60,  60),
    "npc2":         (60,  60,  180),
    "npc3":         (60,  160, 60),

    # Efectes
    "shadow":       (0,   0,   0),
    "white":        (255, 255, 255),
    "black":        (0,   0,   0),
    "gold":         (255, 210, 50),
    "highlight":    (255, 255, 200),
}

# Estat global del jugador (compartit entre mòduls)
STATE = {
    "chips":        START_CHIPS,
    "player_name":  "Jugador",
    "wins":         0,
    "losses":       0,
    "scene":        "world",   # "world" | "poker" | "blackjack" | "roulette"

    # ── Xarxa ──────────────────────────────────────────────────────
    "net_mode":     None,       # None | "host" | "client"
    "net_server":   None,       # instància GameServer (host)
    "net_client":   None,       # instància GameClient (client)
    "net_players":  {},         # {id: {name, x, y, chips}}
    "net_my_id":    0,          # ID local
    "net_host_ip":  "",         # IP del host (client)
}
