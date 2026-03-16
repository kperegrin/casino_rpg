# Grand Casino Royal 🎰
Joc de casino RPG en Python amb pygame — **v2.0 amb Multijugador LAN**

## Instal·lació ràpida
```bash
pip install pygame pillow
python main.py
```

## Novetats v2.0
- **Multijugador en xarxa local (LAN)** — fins a 4 jugadors
- **Llegibilitat millorada** — fonts més grans i millor contrast
- **Indicador de xarxa** al HUD (estat, jugadors connectats)
- **Avatars d'altres jugadors** visibles al casino
- **Nous minijocs**: Tragaperras, Bolos i Duel de Daus
- **Poker online per torns**: mode bots o grup online
- **Servidor dedicat relay**: `python dedicated_server.py`

## Com jugar en xarxa local

### El host (qui allotja la partida)
1. Executa `python main.py`
2. Escriu el teu nom
3. Fes clic a **"CREAR PARTIDA (host LAN)"**
4. Apareixerà la teva IP local (p.ex. `192.168.1.10`) — dona-la als altres
5. Entra al casino normalment

### Els clients (jugadors que s'uneixen)
1. Executa `python main.py`
2. Escriu el teu nom
3. Escriu la **IP del host** al camp "IP del host"
4. Fes clic a **"UNIR-SE A PARTIDA (LAN)"**

> **Important:** Tots a la mateixa xarxa Wi-Fi/cable. Port: **55320 TCP**

## Online 24/7 (gratis)
- Consulta la guia: [ONLINE_GRATIS.md](ONLINE_GRATIS.md)
- Opció recomanada: Oracle Cloud Always Free + `dedicated_server.py`

## Controls
| Tecla          | Acció                     |
|----------------|--------------------------|
| WASD / Fletxes | Moure el personatge      |
| E              | Entrar a la mesa propera |
| F11            | Pantalla completa        |
| ESPAI          | Continuar (resultats)    |

## Estructura de fitxers
```
casino_rpg/
├── main.py          ← punt d'entrada
├── network.py       ← NOU: servidor/client LAN
├── settings.py      ← constants i estat global
├── camera.py        ← càmera suau
├── world.py         ← mapa del casino
├── player.py        ← moviment i animació
├── ui.py            ← HUD i botons
├── card_renderer.py ← cartes i fitxes amb Pillow
├── blackjack.py     ← Blackjack
├── poker.py         ← Texas Hold'em
└── roulette.py      ← Ruleta europea
```

## Solució de problemes de xarxa
| Problema | Solució |
|----------|---------|
| "No s'ha pogut connectar" | El host ha de clicar "Crear Partida" PRIMER |
| Client no troba el host | Comproveu que esteu a la mateixa xarxa |
| Firewall bloqueja | Obre port 55320 TCP |
| Com saber la IP? | `ipconfig` (Windows) / `ifconfig` (Mac/Linux) |
