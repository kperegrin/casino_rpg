# ═══════════════════════════════════════════════════════════════════
#  CARD RENDERER — usa PNGs reales si están en assets/cards/
#  Fallback automático a generación con Pillow si no hay assets
# ═══════════════════════════════════════════════════════════════════
import pygame
import os
import io

_cache = {}

# ── Rutas de assets ──────────────────────────────────────────────────
_CARDS_DIR      = os.path.join("assets", "cards", "card_pngs", "card_faces")
_BACKS_DIR      = os.path.join("assets", "cards", "card_pngs", "card_backs")
_CARD_BACK_FILE = os.path.join(_BACKS_DIR, "card_back_1.png")

SUITS = {"♠": "spades", "♣": "clubs", "♥": "hearts", "♦": "diamonds"}
RANKS = {
    "A": "ace", "2": "2", "3": "3", "4": "4", "5": "5",
    "6": "6", "7": "7", "8": "8", "9": "9", "10": "10",
    "J": "jack", "Q": "queen", "K": "king",
}

def _card_filename(rank, suit):
    suit_name = SUITS.get(suit, "spades")
    rank_name = RANKS.get(rank, rank.lower())
    return f"{rank_name}_of_{suit_name}.png"

def _assets_available():
    return os.path.isdir(_CARDS_DIR)

def _load_card_png(rank, suit, w, h):
    fname = _card_filename(rank, suit)
    path  = os.path.join(_CARDS_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(surf, (w, h))
    except Exception:
        return None

def _load_back_png(w, h):
    if not os.path.exists(_CARD_BACK_FILE):
        return None
    try:
        surf = pygame.image.load(_CARD_BACK_FILE).convert_alpha()
        return pygame.transform.smoothscale(surf, (w, h))
    except Exception:
        return None

# ── Fallback Pillow ───────────────────────────────────────────────────
_font_cache = {}

def _load_pil_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    try:
        from PIL import ImageFont
        names = ["DejaVuSans-Bold.ttf","DejaVuSans.ttf","arialbd.ttf","arial.ttf"]
        for name in names:
            try:
                f = ImageFont.truetype(name, size)
                _font_cache[key] = f
                return f
            except Exception:
                continue
        f = ImageFont.load_default()
        _font_cache[key] = f
        return f
    except Exception:
        return None

def _make_card_pillow(rank, suit, w, h, face_up):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _make_card_minimal(rank, suit, w, h, face_up)

    _suit_colors = {"♠": "black", "♣": "black", "♥": "red", "♦": "red"}
    img  = Image.new("RGBA", (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    if not face_up:
        for y in range(h):
            t = y/h
            draw.line([(3,y),(w-4,y)], fill=(int(15+10*t), int(30+20*t), int(100+40*t), 255))
        mask = Image.new("L",(w,h),0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1], radius=6, fill=255)
        img.putalpha(mask)
        draw2 = ImageDraw.Draw(img)
        draw2.rounded_rectangle([1,1,w-2,h-2], radius=6, outline=(80,100,200,200), width=2)
        for i in range(-h,w+h,10):
            draw2.line([(i,0),(i+h,h)], fill=(255,255,255,20), width=1)
    else:
        for y in range(h):
            base = int(255-(y/max(1,h-1))*12)
            draw.line([(0,y),(w,y)], fill=(base,base-3,base-10,255))
        mask = Image.new("L",(w,h),0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1], radius=6, fill=255)
        img.putalpha(mask)
        draw2 = ImageDraw.Draw(img)
        draw2.rounded_rectangle([1,1,w-2,h-2], radius=5, outline=(190,170,110,255), width=2)
        color = (190,20,20,255) if _suit_colors.get(suit,"black")=="red" else (15,15,25,255)
        font_big = _load_pil_font(max(11,w//4), bold=True)
        if font_big:
            draw2.text((5,4),  rank, font=font_big, fill=color)
            draw2.text((5,18), suit, font=font_big, fill=color)
            bb = draw2.textbbox((0,0), rank, font=font_big)
            tw,th = bb[2]-bb[0], bb[3]-bb[1]
            draw2.text(((w-tw)//2, (h-th)//2-4), rank, font=font_big, fill=color)
            draw2.text(((w-tw)//2+2, (h-th)//2+th), suit, font=font_big, fill=color)

    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    surf = pygame.image.load(buf)
    return pygame.transform.smoothscale(surf, (w, h))

def _make_card_minimal(rank, suit, w, h, face_up):
    surf = pygame.Surface((w,h), pygame.SRCALPHA)
    if not face_up:
        surf.fill((20,40,120))
        pygame.draw.rect(surf,(80,100,200),(0,0,w,h),2,border_radius=4)
    else:
        surf.fill((250,248,238))
        pygame.draw.rect(surf,(180,150,80),(0,0,w,h),2,border_radius=4)
        try:
            f = pygame.font.SysFont("Arial",max(10,w//4),bold=True)
            col = (180,20,20) if suit in ("♥","♦") else (15,15,25)
            surf.blit(f.render(rank+suit,True,col),(3,3))
        except Exception:
            pass
    return surf

# ── API pública ───────────────────────────────────────────────────────
def make_card(rank, suit, w=60, h=84, face_up=True):
    key = f"card_{rank}{suit}_{w}_{h}_{face_up}"
    if key in _cache:
        return _cache[key]
    surf = None
    if face_up and _assets_available():
        surf = _load_card_png(rank, suit, w, h)
    elif not face_up:
        surf = _load_back_png(w, h)
    if surf is None:
        surf = _make_card_pillow(rank, suit, w, h, face_up)
    _cache[key] = surf
    return surf

# ── Fichas ────────────────────────────────────────────────────────────
CHIP_COLORS = {
    1:    ((220,220,220),(180,180,180)),
    5:    ((200,30, 30), (150,20, 20)),
    25:   ((30, 120,30), (20, 90, 20)),
    100:  ((30, 30, 180),(20, 20, 140)),
    500:  ((150,30, 150),(110,20, 110)),
    1000: ((180,140,20), (140,110,15)),
}

def make_chip(value, size=36):
    key = f"chip_{value}_{size}"
    if key in _cache: return _cache[key]
    try:
        from PIL import Image, ImageDraw
        import math
        w=h=size
        img=Image.new("RGBA",(w,h),(0,0,0,0))
        draw=ImageDraw.Draw(img)
        mc,dc=CHIP_COLORS.get(value,((100,100,100),(70,70,70)))
        draw.ellipse([3,4,w-1,h],fill=(0,0,0,100))
        draw.ellipse([1,1,w-2,h-2],fill=mc)
        draw.ellipse([1,1,w-2,h-2],outline=dc,width=3)
        cx=cy=w//2; r=w//2-5
        for a in range(0,360,45):
            rad=math.radians(a)
            draw.line([(cx+int((r-4)*math.cos(rad)),cy+int((r-4)*math.sin(rad))),
                       (cx+int(r*math.cos(rad)),cy+int(r*math.sin(rad)))],
                      fill=(255,255,255,100),width=2)
        ir=w//4
        draw.ellipse([cx-ir,cy-ir,cx+ir,cy+ir],fill=dc,outline=(255,255,255,60),width=1)
        draw.ellipse([cx-r+2,cy-r+2,cx-r//2,cy-r//2+4],fill=(255,255,255,80))
        buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
        surf=pygame.image.load(buf)
    except Exception:
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        mc=CHIP_COLORS.get(value,((100,100,100),(70,70,70)))[0]
        pygame.draw.circle(surf,mc,(size//2,size//2),size//2-2)
        pygame.draw.circle(surf,(255,210,50),(size//2,size//2),size//2-2,2)
    _cache[key]=surf
    return surf

def make_ball(size=14):
    key=f"ball_{size}"
    if key in _cache: return _cache[key]
    try:
        from PIL import Image, ImageDraw
        img=Image.new("RGBA",(size,size),(0,0,0,0))
        draw=ImageDraw.Draw(img)
        draw.ellipse([1,2,size-2,size-1],fill=(20,20,20,180))
        draw.ellipse([0,0,size-2,size-2],fill=(235,235,235))
        draw.ellipse([0,0,size-2,size-2],outline=(180,180,180),width=1)
        draw.ellipse([2,2,size//2,size//2],fill=(255,255,255,180))
        buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
        surf=pygame.image.load(buf)
    except Exception:
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        pygame.draw.circle(surf,(235,235,235),(size//2,size//2),size//2-1)
    _cache[key]=surf
    return surf

def make_button(text_label, w, h, bg=(30,80,30), hover=False):
    key=f"btn_{text_label}_{w}_{h}_{bg}_{hover}"
    if key in _cache: return _cache[key]
    surf=pygame.Surface((w,h),pygame.SRCALPHA)
    r,g,b=bg
    if hover: r=min(255,r+30); g=min(255,g+30); b=min(255,b+30)
    pygame.draw.rect(surf,(r,g,b),(0,0,w,h),border_radius=6)
    pygame.draw.rect(surf,(200,170,60),(0,0,w,h),2,border_radius=6)
    _cache[key]=surf
    return surf
