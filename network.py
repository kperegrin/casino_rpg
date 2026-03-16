# ═══════════════════════════════════════════════════════════════════
#  NETWORK — Multijugador en xarxa local (LAN)
#  HOST: corre el servidor i el joc
#  CLIENT: es connecta a la IP del host
# ═══════════════════════════════════════════════════════════════════
import socket
import threading
import json
import time
import queue

PORT = 55320
BUFFER = 4096

# ── Missatge helper ──────────────────────────────────────────────────
def _send(sock, data: dict):
    try:
        raw = (json.dumps(data) + "\n").encode("utf-8")
        sock.sendall(raw)
        return True
    except Exception:
        return False

def _recv_lines(sock, partial_buf):
    """Llegeix totes les línies disponibles sense bloquejar."""
    messages = []
    try:
        sock.setblocking(False)
        chunk = sock.recv(BUFFER).decode("utf-8", errors="ignore")
        sock.setblocking(True)
        partial_buf += chunk
    except BlockingIOError:
        pass
    except Exception:
        return messages, partial_buf, True  # error/disconnect

    while "\n" in partial_buf:
        line, partial_buf = partial_buf.split("\n", 1)
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return messages, partial_buf, False


# ═══════════════════════════════════════════════════════════════════
#  SERVIDOR (host)
# ═══════════════════════════════════════════════════════════════════
class GameServer:
    """Servidor senzill per a 2–4 jugadors en LAN."""

    MAX_PLAYERS = 4

    def __init__(self, auto_relay=False):
        self.running       = False
        self._sock         = None
        self._clients      = {}   # id -> {sock, addr, name, partial}
        self._next_id      = 1
        self._lock         = threading.Lock()
        self.inbox         = queue.Queue()   # missatges rebuts (per al joc)
        self._game_state   = {}              # estat compartit
        self._local_id     = 0              # l'amfitrió sempre és 0
        self.auto_relay    = auto_relay

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("", PORT))
        self._sock.listen(self.MAX_PLAYERS)
        self._sock.settimeout(1.0)
        self.running = True
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        return self.get_local_ip()

    def stop(self):
        self.running = False
        with self._lock:
            for cid, c in list(self._clients.items()):
                try:
                    c["sock"].close()
                except Exception:
                    pass
            self._clients.clear()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self._sock.accept()
                cid = self._next_id
                self._next_id += 1
                with self._lock:
                    self._clients[cid] = {
                        "sock": conn, "addr": addr,
                        "name": f"Jugador{cid}", "partial": ""
                    }
                # Enviar ID al client
                _send(conn, {"type": "welcome", "your_id": cid,
                             "host_id": self._local_id})
                # Notificar a tothom que s'ha unit (amb nom provisional)
                self.broadcast({"type": "player_joined", "id": cid,
                                 "name": f"Jugador{cid}"})
                # Enviar estat actual al client nou
                if self._game_state:
                    _send(conn, {"type": "state_update",
                                 "state": self._game_state})
                # Enviar posicions de tots els jugadors ja connectats al client nou
                # (perquè el nou client vegi els que ja estaven)
                for existing_id, existing_data in list(self._clients.items()):
                    if existing_id != cid:
                        pass  # les posicions arribaran pel broadcast normal
                # Thread per llegir
                t = threading.Thread(
                    target=self._client_loop, args=(cid,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _client_loop(self, cid):
        while self.running:
            with self._lock:
                if cid not in self._clients:
                    break
                c = self._clients[cid]
            msgs, partial, err = _recv_lines(c["sock"], c["partial"])
            with self._lock:
                if cid in self._clients:
                    self._clients[cid]["partial"] = partial
            for m in msgs:
                m["_from"] = cid
                self.inbox.put(m)
                if self.auto_relay and m.get("type") in (
                        "player_pos", "table_state", "poker_action",
                        "blackjack_action", "room_event"):
                    self.broadcast(m, exclude=cid)
            if err:
                with self._lock:
                    self._clients.pop(cid, None)
                self.broadcast({"type": "player_left", "id": cid})
                break
            time.sleep(0.016)

    def broadcast(self, data: dict, exclude=None):
        with self._lock:
            dead = []
            for cid, c in self._clients.items():
                if cid == exclude:
                    continue
                if not _send(c["sock"], data):
                    dead.append(cid)
            for cid in dead:
                self._clients.pop(cid, None)

    def send_to(self, cid, data: dict):
        with self._lock:
            c = self._clients.get(cid)
        if c:
            _send(c["sock"], data)

    def push_state(self, state: dict):
        """Actualitza i difon l'estat del joc a tots els clients."""
        self._game_state = state
        self.broadcast({"type": "state_update", "state": state})

    @property
    def connected_count(self):
        with self._lock:
            return len(self._clients)

    @property
    def player_ids(self):
        with self._lock:
            return [self._local_id] + list(self._clients.keys())


# ═══════════════════════════════════════════════════════════════════
#  CLIENT
# ═══════════════════════════════════════════════════════════════════
class GameClient:
    def __init__(self):
        self.running    = False
        self._sock      = None
        self._partial   = ""
        self._lock      = threading.Lock()
        self.inbox      = queue.Queue()
        self.my_id      = None
        self.host_id    = None
        self.connected  = False
        self.last_state = {}

    def connect(self, host_ip: str, timeout=5.0) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(timeout)
            self._sock.connect((host_ip, PORT))
            self._sock.settimeout(None)
            self.running   = True
            self.connected = True
            t = threading.Thread(target=self._recv_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            return False

    def disconnect(self):
        self.running    = False
        self.connected  = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def send(self, data: dict):
        if self._sock and self.connected:
            _send(self._sock, data)

    def _recv_loop(self):
        while self.running:
            msgs, partial, err = _recv_lines(self._sock, self._partial)
            with self._lock:
                self._partial = partial
            for m in msgs:
                if m.get("type") == "welcome":
                    self.my_id   = m["your_id"]
                    self.host_id = m["host_id"]
                elif m.get("type") == "state_update":
                    self.last_state = m.get("state", {})
                self.inbox.put(m)
            if err:
                self.connected = False
                self.inbox.put({"type": "disconnected"})
                break
            time.sleep(0.016)

    def poll(self):
        """Retorna tots els missatges pendents."""
        msgs = []
        while not self.inbox.empty():
            try:
                msgs.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return msgs
