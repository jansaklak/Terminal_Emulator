#!/usr/bin/env python3
import socket
import threading
import os
import pty
import select
import fcntl
import struct
import termios
import json
import logging
import datetime
import signal
import sys
from pathlib import Path

# Ścieżka do pliku konfiguracyjnego JSON
CONFIG_FILE = Path("config.json")
ONLINE_FILE = Path("online.json")

def get_live_config():
    """Wczytuje aktualną konfigurację z pliku JSON."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"BŁĄD krytyczny wczytywania config.json: {e}")
        return {"HOST": "0.0.0.0", "PORT": 5000, "USERS": {}, "CONFIGS": {}}

def update_online(username, config_name, action="add"):
    try:
        data = {}
        if ONLINE_FILE.exists():
            with open(ONLINE_FILE, 'r') as f:
                data = json.load(f)
        
        session_id = f"{username}@{config_name}"
        if action == "add":
            data[session_id] = {"user": username, "config": config_name, "since": datetime.datetime.now().isoformat()}
        else:
            data.pop(session_id, None)
            
        with open(ONLINE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        log.error(f"Błąd aktualizacji statusu online: {e}")

# Wstępne wczytanie parametrów startowych
initial_cfg = get_live_config()
HOST = initial_cfg.get("HOST", "0.0.0.0")
PORT = initial_cfg.get("PORT", 5000)
LOG_DIR = Path(initial_cfg.get("LOG_DIR", "/var/log/terminal-server"))

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "server.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("gateway")

class SessionLogger:
    def __init__(self, username: str, config: str):
        self.username = username
        self.config = config
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = LOG_DIR / f"{username}_{config}_{ts}.log"
        self.f = open(path, "a", encoding="utf-8", errors="replace")
        self.buf = ""
        self._write(f"=== Początek sesji: użytkownik={username} konfiguracja={config} ===\n")

    def feed(self, data: bytes):
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            return
        for ch in text:
            if ch in ('\r', '\n'):
                if self.buf.strip():
                    self._write(f"POLECENIE: {self.buf}\n")
                self.buf = ""
            elif ch == '\x7f':  # backspace
                self.buf = self.buf[:-1]
            elif ch.isprintable():
                self.buf += ch

    def _write(self, line: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.f.write(f"[{ts}] {line}")
        self.f.flush()

    def close(self):
        self._write("=== Koniec sesji ===\n")
        self.f.close()

def set_winsize(fd, rows: int, cols: int):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

def run_session(conn: socket.socket, addr, username: str, config_name: str, cmd_list: list):
    """Uruchamia kontener Dockera za pomocą PTY."""
    log.info("Uruchamianie sesji: użytkownik=%s konf=%s adres=%s polecenie=%s",
             username, config_name, addr, cmd_list)
    update_online(username, config_name, "add")

    session_log = SessionLogger(username, config_name)
    master_fd, slave_fd = pty.openpty()
    set_winsize(master_fd, 40, 120)

    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(master_fd)
        os.close(slave_fd)
        for fd in range(3, 256):
            try: os.close(fd)
            except OSError: pass
        os.execvp(cmd_list[0], cmd_list)
        os._exit(1)

    os.close(slave_fd)
    stop_event = threading.Event()

    def pty_to_tcp():
        while not stop_event.is_set():
            try:
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if r:
                    data = os.read(master_fd, 4096)
                    if not data: break
                    conn.sendall(data)
            except Exception: break
        stop_event.set()

    threading.Thread(target=pty_to_tcp, daemon=True).start()

    try:
        while not stop_event.is_set():
            try:
                conn.settimeout(1.0)
                data = conn.recv(1024)
                if not data: break
                session_log.feed(data)
                os.write(master_fd, data)
            except socket.timeout: continue
            except Exception: break
    finally:
        stop_event.set()
        session_log.close()
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: os.close(master_fd)
        except OSError: pass
        try: conn.close()
        except Exception: pass
        update_online(username, config_name, "remove")
        log.info("Koniec sesji: użytkownik=%s konf=%s", username, config_name)

def handle_client(conn: socket.socket, addr):
    """Realizuje dwuetapowy handshake: Autoryzacja -> Lista konfiguracji -> Wybór."""
    try:
        # Pobieramy świeże dane przy każdym nowym połączeniu
        cfg_data = get_live_config()
        users = cfg_data.get('USERS', {})
        configs = cfg_data.get('CONFIGS', {})

        # KROK 1: Autoryzacja użytkownika
        line = conn.recv(1024).decode().strip()
        if not line: return conn.close()
        
        auth_req = json.loads(line)
        username = auth_req.get("username")
        password = auth_req.get("password")

        user_info = users.get(username)
        if not user_info or user_info.get("password") != password:
            conn.sendall(json.dumps({"ok": False, "error": "Błędny login lub hasło"}).encode() + b"\n")
            log.warning("Nieudana próba logowania: %s z adresu %s", username, addr)
            return conn.close()

        # Wyślij listę dostępnych konfiguracji
        config_list = {k: v.get("description", k) for k, v in configs.items()}
        conn.sendall(json.dumps({
            "ok": True, 
            "display_name": user_info.get("display_name", username),
            "available_configs": config_list
        }).encode() + b"\n")

        # KROK 2: Oczekiwanie na wybór środowiska od klienta
        line = conn.recv(1024).decode().strip()
        if not line: return conn.close()
        
        choice_req = json.loads(line)
        selected_key = choice_req.get("config")

        if selected_key not in configs:
            log.error("Nieprawidłowy wybór konfiguracji: %s przez %s", selected_key, username)
            return conn.close()

        # Uruchomienie właściwej sesji
        raw_cmd = configs[selected_key]["cmd"]
        # Dynamiczne podstawianie nazwy użytkownika do komendy
        cmd = [part.replace("{user}", username) for part in raw_cmd]
        run_session(conn, addr, username, selected_key, cmd)

    except Exception as e:
        log.error("Błąd handshake z %s: %s", addr, e)
        try: conn.close()
        except: pass

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(50)
    log.info("Brama Terminalowa nasłuchuje na %s:%d", HOST, PORT)

    try:
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        log.info("Zamykanie serwera.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()