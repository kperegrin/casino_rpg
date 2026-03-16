# Online 24/7 gratis con Fly.io

Fly.io ofrece **3 VMs compartidas gratuitas** (256 MB RAM, shared CPU) que corren sin dormir mientras tengan tráfico. Es la forma más rápida de desplegar el servidor relay sin tarjeta de crédito obligatoria (solo para evitar el límite de 3 apps).

> **Puerto TCP `55320`** — Fly.io lo expone directamente al exterior. Los jugadores solo necesitan la URL pública `nombre-de-tu-app.fly.dev` o la IP que muestra `fly status`.

---

## 0) Requisitos previos

- Tener instalado [flyctl](https://fly.io/docs/hands-on/install-flyctl/) en tu máquina Windows:
  ```powershell
  iwr https://fly.io/install.ps1 -useb | iex
  ```
- Crear cuenta gratuita y hacer login:
  ```powershell
  fly auth signup   # o fly auth login si ya tienes cuenta
  ```

---

## 1) Crear los ficheros de despliegue

En la carpeta del juego crea estos dos ficheros nuevos:

### `Dockerfile` (solo para el relay, sin pygame)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY network.py dedicated_server.py ./
CMD ["python", "dedicated_server.py"]
```

> El relay solo usa stdlib + `network.py`; no necesita pygame ni pillow.

### `fly.toml`
```toml
app = "grand-casino-relay"   # cámbialo a un nombre único tuyo
primary_region = "mad"       # Madrid; usa "cdg" para París, "lhr" para Londres

[build]

[[services]]
  internal_port = 55320
  protocol      = "tcp"

  [[services.ports]]
    port = 55320
```

---

## 2) Desplegar

```powershell
cd C:\Users\kperegrina\Desktop\WPy64-31180\notebooks\casino_rpg
fly launch --no-deploy   # detecta el Dockerfile y crea la app en Fly.io
fly deploy               # construye la imagen y la arranca
```

Si `fly launch` pide crear un `fly.toml` nuevo di **No** (ya lo tienes).

Comprueba que está corriendo:
```powershell
fly status
fly logs        # muestra la consola de dedicated_server.py en tiempo real
```

---

## 3) Obtener la IP pública

```powershell
fly ips list
```

Apunta la IPv4 (o IPv6) que aparece — esa es la dirección que darás a los jugadores.

---

## 4) Conectar desde el juego

1. Abre **Grand Casino Royal** en tu PC.
2. En el menú principal → **UNIR-SE A PARTIDA (LAN)** → escribe la IPv4 de Fly.io.
3. Dentro del casino pulsa `G` → elige **Poker** o **Blackjack** → selecciona:
   - **CREAR GRUPO** para ser host de mesa.
   - **UNIRME** para ser invitado.

---

## 5) Mantenerlo siempre activo (anti-sleep)

Fly.io no duerme apps con tráfico activo. Si la app lleva un rato sin conexiones y quieres asegurarte de que no pare, activa el `min_machines_running`:

En `fly.toml` añade:
```toml
[machines]
  min_machines_running = 1
```

Luego `fly deploy` de nuevo.

---

## 6) Actualizar el servidor

Cada vez que cambies `network.py` o `dedicated_server.py`:
```powershell
fly deploy
```
El despliegue tarda ~30 segundos y no borra las conexiones activas (rolling restart).

---

## Solución de problemas

| Síntoma | Solución |
|---|---|
| `fly deploy` falla con "app name taken" | Cambia `app` en `fly.toml` a otro nombre |
| No conecta desde el juego | `fly logs` y comprueba que el relay imprime `Servidor relay activo` |
| Quieres ver los jugadores conectados | `fly logs` muestra cada 10s el conteo |
| Agotas el free tier (>3 apps) | Borra apps viejas con `fly apps destroy nombre` |

---

## Alternativas si Fly.io no funciona

- **Render Free** — También gratuito pero la VM duerme tras 15 min sin peticiones HTTP (no ideal para TCP puro).
- **Oracle Always Free** — VM Ubuntu sin límite de tiempo, 24/7 garantizado, requiere más configuración manual (ver versión anterior de esta guía).
