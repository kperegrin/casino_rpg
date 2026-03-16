# ═══════════════════════════════════════════════════════════════════
#  CARD RENDERER — genera cartes i fitxes amb Pillow
# ═══════════════════════════════════════════════════════════════════
import pygame
from PIL import Image, ImageDraw, ImageFont
import io

_cache = {}
_font_cache = {}

SUITS = {"♠": "black", "♣": "black", "♥": "red", "♦": "red"}

def _pil_to_surface(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return pygame.image.load(buf)

def _hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


def _load_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    names = ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"]
    for name in names:
        try:
            font = ImageFont.truetype(name, size)
            _font_cache[key] = font
            return font
        except Exception:
            continue
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _draw_centered_text(draw, box, txt, font, fill):
    bbox = draw.textbbox((0, 0), txt, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - tw) / 2
    y = box[1] + (box[3] - box[1] - th) / 2 - 1
    draw.text((x, y), txt, font=font, fill=fill)


def _draw_suit(draw, suit, box, color):
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    if suit == "♥":
        r = min(w, h) * 0.22
        draw.ellipse([cx - 2 * r, y1 + h * 0.12, cx, y1 + h * 0.12 + 2 * r], fill=color)
        draw.ellipse([cx, y1 + h * 0.12, cx + 2 * r, y1 + h * 0.12 + 2 * r], fill=color)
        draw.polygon([(x1 + w * 0.16, y1 + h * 0.35), (x2 - w * 0.16, y1 + h * 0.35), (cx, y2 - h * 0.08)], fill=color)
    elif suit == "♦":
        draw.polygon([(cx, y1 + h * 0.06), (x2 - w * 0.12, cy),
                      (cx, y2 - h * 0.06), (x1 + w * 0.12, cy)], fill=color)
    elif suit == "♣":
        r = min(w, h) * 0.18
        draw.ellipse([cx - 2 * r, cy - r, cx, cy + r], fill=color)
        draw.ellipse([cx, cy - r, cx + 2 * r, cy + r], fill=color)
        draw.ellipse([cx - r, y1 + h * 0.1, cx + r, y1 + h * 0.1 + 2 * r], fill=color)
        draw.polygon([(cx - r * 0.6, cy + r * 0.7), (cx + r * 0.6, cy + r * 0.7),
                      (cx + r * 1.05, y2 - h * 0.1), (cx - r * 1.05, y2 - h * 0.1)], fill=color)
    else:  # ♠
        draw.polygon([(cx, y1 + h * 0.06), (x2 - w * 0.14, cy),
                      (cx, y2 - h * 0.22), (x1 + w * 0.14, cy)], fill=color)
        r = min(w, h) * 0.16
        draw.ellipse([cx - 2 * r, cy - r, cx, cy + r], fill=color)
        draw.ellipse([cx, cy - r, cx + 2 * r, cy + r], fill=color)
        draw.polygon([(cx - r * 0.55, cy + r * 0.9), (cx + r * 0.55, cy + r * 0.9),
                      (cx + r, y2 - h * 0.08), (cx - r, y2 - h * 0.08)], fill=color)


def _pip_positions(rank):
    return {
        "A": [(0.5, 0.5, 0.34)],
        "2": [(0.5, 0.28, 0.20), (0.5, 0.72, 0.20)],
        "3": [(0.5, 0.22, 0.18), (0.5, 0.5, 0.18), (0.5, 0.78, 0.18)],
        "4": [(0.32, 0.28, 0.18), (0.68, 0.28, 0.18), (0.32, 0.72, 0.18), (0.68, 0.72, 0.18)],
        "5": [(0.32, 0.28, 0.17), (0.68, 0.28, 0.17), (0.5, 0.5, 0.17), (0.32, 0.72, 0.17), (0.68, 0.72, 0.17)],
        "6": [(0.32, 0.22, 0.16), (0.68, 0.22, 0.16), (0.32, 0.5, 0.16), (0.68, 0.5, 0.16), (0.32, 0.78, 0.16), (0.68, 0.78, 0.16)],
        "7": [(0.32, 0.2, 0.15), (0.68, 0.2, 0.15), (0.5, 0.36, 0.15), (0.32, 0.5, 0.15), (0.68, 0.5, 0.15), (0.32, 0.78, 0.15), (0.68, 0.78, 0.15)],
        "8": [(0.32, 0.2, 0.15), (0.68, 0.2, 0.15), (0.32, 0.38, 0.15), (0.68, 0.38, 0.15), (0.32, 0.62, 0.15), (0.68, 0.62, 0.15), (0.32, 0.8, 0.15), (0.68, 0.8, 0.15)],
        "9": [(0.32, 0.18, 0.14), (0.68, 0.18, 0.14), (0.32, 0.34, 0.14), (0.68, 0.34, 0.14), (0.5, 0.5, 0.14), (0.32, 0.66, 0.14), (0.68, 0.66, 0.14), (0.32, 0.82, 0.14), (0.68, 0.82, 0.14)],
        "10": [(0.32, 0.18, 0.14), (0.68, 0.18, 0.14), (0.32, 0.34, 0.14), (0.68, 0.34, 0.14), (0.32, 0.5, 0.14), (0.68, 0.5, 0.14), (0.32, 0.66, 0.14), (0.68, 0.66, 0.14), (0.32, 0.82, 0.14), (0.68, 0.82, 0.14)],
    }.get(rank, [])


# ── Cara de carta ───────────────────────────────────────────────────
def make_card(rank, suit, w=60, h=84, face_up=True):
    key = f"card_{rank}{suit}_{w}_{h}_{face_up}"
    if key in _cache:
        return _cache[key]

    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not face_up:
        # Dors — degradat blau marí
        for y in range(h):
            t = y / h
            r_ = int(15 + 10 * t)
            g_ = int(30 + 20 * t)
            b_ = int(100 + 40 * t)
            draw.line([(3, y), (w-4, y)], fill=(r_, g_, b_, 255))

        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1], radius=6, fill=255)
        img.putalpha(mask)
        draw2 = ImageDraw.Draw(img)
        draw2.rounded_rectangle([1,1,w-2,h-2], radius=6,
                                 outline=(80,100,200,200), width=2)
        # Patró de rombos
        for i in range(-h, w+h, 10):
            draw2.line([(i,0),(i+h,h)], fill=(255,255,255,20), width=1)
            draw2.line([(i,h),(i+h,0)], fill=(255,255,255,14), width=1)
        # Logo
        cx, cy = w//2, h//2
        draw2.ellipse([cx-12, cy-8, cx+12, cy+8],
                      fill=(160,0,0,220), outline=(255,200,0,200), width=2)
    else:
        # Cara
        for y in range(h):
            blend = y / max(1, h - 1)
            base = int(255 - blend * 12)
            draw.line([(0, y), (w, y)], fill=(base, base - 3, base - 10, 255))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1], radius=6, fill=255)
        img.putalpha(mask)
        draw2 = ImageDraw.Draw(img)

        # Vora i ombra
        draw2.rounded_rectangle([1,1,w-2,h-2], radius=5,
                                 outline=(190, 170, 110, 255), width=2)
        draw2.rounded_rectangle([2,2,w-3,h-3], radius=4,
                                 outline=(220, 200, 140, 180), width=1)
        draw2.rounded_rectangle([6,6,w-7,h-7], radius=5,
                                 outline=(230, 225, 210, 90), width=1)

        color = (190, 20, 20, 255) if SUITS.get(suit, "black") == "red" else (15, 15, 25, 255)
        rank_font = _load_font(max(11, w // 4), bold=True)
        pip_font = _load_font(max(10, w // 5), bold=True)

        # Rang (cantonada superior-esquerra)
        draw2.text((6, 4), rank, font=rank_font, fill=color)
        _draw_suit(draw2, suit, (6, 22, 22, 38), color)

        # Rang (cantonada inferior-dreta, girat)
        rb = Image.new("RGBA", (24, 34), (0, 0, 0, 0))
        rdraw = ImageDraw.Draw(rb)
        rdraw.text((4, 0), rank, font=pip_font, fill=color)
        _draw_suit(rdraw, suit, (4, 16, 20, 30), color)
        rb = rb.rotate(180, expand=False)
        img.alpha_composite(rb, (w - 26, h - 36))

        pip_positions = _pip_positions(rank)
        if pip_positions:
            for nx, ny, scale in pip_positions:
                pw = w * scale
                ph = h * scale * 1.18
                box = (w * nx - pw / 2, h * ny - ph / 2, w * nx + pw / 2, h * ny + ph / 2)
                _draw_suit(draw2, suit, box, color)
        else:
            badge = (w * 0.2, h * 0.2, w * 0.8, h * 0.8)
            draw2.rounded_rectangle(badge, radius=8, fill=(248, 243, 230, 160), outline=(200, 185, 150, 200), width=2)
            _draw_centered_text(draw2, (w * 0.24, h * 0.22, w * 0.76, h * 0.48), rank, _load_font(max(16, w // 2), bold=True), color)
            _draw_suit(draw2, suit, (w * 0.28, h * 0.46, w * 0.72, h * 0.78), color)

    surf = _pil_to_surface(img)
    surf = pygame.transform.smoothscale(surf, (w, h))
    _cache[key] = surf
    return surf


# ── Fitxa de casino ─────────────────────────────────────────────────
CHIP_COLORS = {
    1:    ((220, 220, 220), (180, 180, 180)),   # blanc
    5:    ((200, 30,  30),  (150, 20,  20)),    # roig
    25:   ((30,  120, 30),  (20,  90,  20)),    # verd
    100:  ((30,  30,  180), (20,  20,  140)),   # blau
    500:  ((150, 30,  150), (110, 20,  110)),   # morat
    1000: ((180, 140, 20),  (140, 110, 15)),    # or
}

def make_chip(value, size=36):
    key = f"chip_{value}_{size}"
    if key in _cache:
        return _cache[key]

    w = h = size
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    main_c, dark_c = CHIP_COLORS.get(value, ((100,100,100),(70,70,70)))

    # Ombra
    draw.ellipse([3, 4, w-1, h], fill=(0,0,0,100))
    # Cos
    draw.ellipse([1, 1, w-2, h-2], fill=main_c)
    # Vora
    draw.ellipse([1, 1, w-2, h-2], outline=dark_c, width=3)
    # Ratlles de fitxa (segments)
    import math
    cx, cy, r = w//2, h//2, w//2 - 5
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int((r-4) * math.cos(rad))
        y1 = cy + int((r-4) * math.sin(rad))
        x2 = cx + int(r * math.cos(rad))
        y2 = cy + int(r * math.sin(rad))
        draw.line([(x1,y1),(x2,y2)], fill=(255,255,255,100), width=2)
    # Cercle interior
    ir = w//4
    draw.ellipse([cx-ir, cy-ir, cx+ir, cy+ir],
                 fill=dark_c, outline=(255,255,255,60), width=1)
    # Brillantor
    draw.ellipse([cx-r+2, cy-r+2, cx-r//2, cy-r//2+4],
                 fill=(255,255,255,80))

    surf = _pil_to_surface(img)
    _cache[key] = surf
    return surf


# ── Bola de ruleta ──────────────────────────────────────────────────
def make_ball(size=14):
    key = f"ball_{size}"
    if key in _cache:
        return _cache[key]
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([1,2,size-2,size-1], fill=(20,20,20,180))
    draw.ellipse([0,0,size-2,size-2], fill=(235,235,235))
    draw.ellipse([0,0,size-2,size-2], outline=(180,180,180), width=1)
    draw.ellipse([2,2,size//2, size//2], fill=(255,255,255,180))
    surf = _pil_to_surface(img)
    _cache[key] = surf
    return surf


# ── Botó UI ─────────────────────────────────────────────────────────
def make_button(text, w, h, bg=(30,80,30), hover=False):
    key = f"btn_{text}_{w}_{h}_{bg}_{hover}"
    if key in _cache:
        return _cache[key]
    img  = Image.new("RGBA", (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    r,g,b = bg
    if hover:
        r = min(255, r+30)
        g = min(255, g+30)
        b = min(255, b+30)
    # Degradat vertical
    for y in range(h):
        t = y / h
        rr = int(r * (1.2 - t*0.4))
        gg = int(g * (1.2 - t*0.4))
        bb = int(b * (1.2 - t*0.4))
        draw.line([(3,y),(w-4,y)],
                  fill=(min(255,rr), min(255,gg), min(255,bb), 255))
    mask = Image.new("L",(w,h),0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1], radius=6, fill=255)
    img.putalpha(mask)
    draw2 = ImageDraw.Draw(img)
    draw2.rounded_rectangle([1,1,w-2,h-2], radius=5,
                             outline=(200,170,60,220), width=2)
    surf = _pil_to_surface(img)
    _cache[key] = surf
    return surf
