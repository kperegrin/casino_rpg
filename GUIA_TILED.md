# Guia completa — Tiled + Grand Casino Royal

## Estructura de carpetes necessària

Posa tots els fitxers així **abans** d'obrir Tiled:

```
GrandCasinoRoyal/
├── main.py
├── world.py              ← substitueix pel nou world.py
├── network.py
├── ... (resta de .py)
└── assets/
    ├── casino.tmx            ← crearàs aquest amb Tiled
    ├── CasinoTileset.tsx     ← fitxer de tileset (adjunt)
    ├── 2D_TopDown_Tileset_Casino_1024x512.png
    └── Animated Sprite Sheets/
        ├── SlotMachinesAnimationSheet_0.png
        ├── SlotMachinesAnimationSheet_1.png
        ├── DoorAnimationSheet_0.png
        └── ... (resta d'animacions)
```

---

## Pas 1 — Configurar el nou projecte a Tiled

1. Obre **Tiled**
2. **File → New → New Map...**
3. Configuració:
   - Orientation: **Orthogonal**
   - Tile layer format: **CSV** (important!)
   - Tile render order: **Right Down**
   - Map size: **Fixed** → `100 x 80` tiles  *(o la mida que vulguis)*
   - Tile size: **16 x 16** px  ⚠️ *molt important — els assets són 16px*
4. Guarda com `assets/casino.tmx`

---

## Pas 2 — Importar el Tileset

1. Al panell **Tilesets** (baix a la dreta) → botó **+** (New Tileset)
2. Tria **Based on Tileset Image**
3. Selecciona `2D_TopDown_Tileset_Casino_1024x512.png`
4. Configuració:
   - Name: `CasinoTileset`
   - Tile width: **16** / Tile height: **16**
   - Spacing: **0** / Margin: **0**
5. Guarda com `assets/CasinoTileset.tsx`

---

## Pas 3 — Crear les capes (ORDRE IMPORTANT)

Crea exactament aquestes capes en aquest ordre (de baix a dalt al panell Layers):

| # | Nom capa  | Tipus              | Descripció                            |
|---|-----------|-------------------|---------------------------------------|
| 1 | `floor`   | Tile Layer         | Sòl base: moqueta roja/blava, parquet |
| 2 | `floor2`  | Tile Layer         | Segon sòl opcional (catifes, etc.)    |
| 3 | `objects`  | Tile Layer        | Mobles, taules de joc, màquines       |
| 4 | `walls`   | Tile Layer         | Parets, columnes, obstacles           |
| 5 | `zones`   | **Object Layer**   | Rectangles de les zones de joc        |
| 6 | `above`   | Tile Layer         | Elements per SOBRE del jugador        |

> ⚠️ Els noms han de ser **exactament** aquests (minúscules).

---

## Pas 4 — Marcar tiles sòlids (col·lisions)

Per a cada tile que bloquegi el pas (parets, mobles grans...):

1. Al panell **Tilesets**, fes doble clic sobre el tile
2. A la finestra que s'obre → **Add Property**:
   - Name: `collides`
   - Type: `bool`
   - Value: ✓ (true)
3. Repeteix per tots els tiles que bloquegin

> 💡 **Consell:** Selecciona múltiples tiles a la vegada i edita les propietats de tots alhora.

---

## Pas 5 — Crear les zones de joc

A la capa `zones` (Object Layer):

1. Selecciona l'eina **Rectangle** (R)
2. Dibuixa un rectangle sobre l'àrea del Poker
3. Al panell Properties → Name: `poker`
4. Repeteix per `blackjack` i `roulette`

```
Noms vàlids:   poker  |  blackjack  |  roulette
```

El jugador podrà prémer **E** quan entri dins d'aquestes zones.

---

## Pas 6 — Pintar el mapa

### Zones recomanades de tiles del tileset

El tileset `2D_TopDown_Tileset_Casino_1024x512.png` té **64 columnes × 32 files** de tiles 16×16:

```
Files 0-3   (y=0..3):    Moqueta roja amb patrons
Files 4-7   (y=4..7):    Moqueta blava amb patrons
Files 8-10  (y=8..10):   Parets i pilars
Files 11-13 (y=11..13):  Portes (estàtiques)
Files 14-16 (y=14..16):  Mobles de bany / barra
Files 17-20 (y=17..20):  Taules de poker/blackjack/ruleta
Files 21-24 (y=21..24):  Màquines escurabutxaques (estàtiques)
Files 25-28 (y=25..28):  Cadires, plantes, decoració
Files 29-31 (y=29..31):  Sòl de rajoles, parets externes
```

> Explora el tileset directament a Tiled — clica qualsevol tile per veure'l ampliat.

---

## Pas 7 — Afegir màquines animades (slot machines)

Les slot machines tenen animació. Per usar-les:

1. A la capa `objects`, pinta els tiles estàtics de les màquines
2. El codi detecta automàticament el sprite sheet `SlotMachinesAnimationSheet_0.png`
   i les anima (8 fps, 64 frames)

> Les animacions es carreguen automàticament si el fitxer existeix a
> `assets/Animated Sprite Sheets/`

---

## Pas 8 — Exportar i jugar

1. **File → Save** (`Ctrl+S`) → guarda `casino.tmx`
2. Executa el joc:
   ```bash
   pip install pytmx
   python main.py
   ```
3. El joc detectarà automàticament `assets/casino.tmx` i el carregarà.

Si hi ha errors, el joc farà servir el mapa generat per codi com a fallback.

---

## Resolució de problemes

| Problema | Solució |
|----------|---------|
| "pytmx no trobat" | `pip install pytmx` |
| Mapa no carrega | Comprova que `assets/casino.tmx` existeix |
| Tiles mal escalats | Verifica que el tile size és **16x16** al TMX |
| Jugador travessa parets | Afegeix `collides=true` als tiles de paret |
| Zones no funcionen | Comprova que la capa es diu exactament `zones` |
| Tileset no apareix | Verifica que el `.png` és a la mateixa carpeta que el `.tsx` |

---

## Crèdits del Tileset

Tileset creat per **Jephed / Game Between The Lines**
- Web: https://gamebetweenthelines.com/
- Itch.io: https://gamebetweenthelines.itch.io/
- Llicència: lliure per a ús comercial i no comercial
