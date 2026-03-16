import time

from network import GameServer


def main():
    server = GameServer(auto_relay=True)
    ip = server.start()
    print("=" * 62)
    print("Grand Casino Royal · Servidor dedicado (relay)")
    print(f"IP local detectada: {ip}")
    print("Puerto TCP: 55320")
    print("Modo relay: activo (player_pos/table_state/poker_action)")
    print("Ctrl+C para detener")
    print("=" * 62)

    try:
        while True:
            print(f"Jugadores conectados: {server.connected_count}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
    finally:
        server.stop()
        print("Servidor detenido")


if __name__ == "__main__":
    main()
