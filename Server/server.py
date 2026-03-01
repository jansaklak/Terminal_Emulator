#!/usr/bin/env python3
"""
Serwer Bramy Terminalowej (Terminal Gateway Server)
- Wielokliencki serwer TCP
- Autoryzacja poprzez kody użytkowników
- Uruchamianie programów Docker na podstawie konfiguracji (MySQL, bash, itp.)
- Logowanie aktywności sesji
- Mostek PTY między klientem TCP a kontenerem Dockera
"""

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

# Konfiguracja

HOST = '0.0.0.0'
PORT = 5000
LOG_DIR = Path("/var/log/terminal-server")

# Mapowanie: Kod użytkownika → nazwa użytkownika
USERS = {
    "1234": "student1",
    "5678": "student2",
    "9999": "admin",
    "0000": "demo",
}

# Nazwa konfiguracji → Polecenie Dockera do uruchomienia sesji
CONFIGS = {
    "Bazy1": {
        "cmd": [
            "docker", "run", "--rm", "-it",
            "--network", "lab-net",
            "--memory", "256m",
            "--cpus", "0.5",
            "mysql:8.0",
            "mysql",
            "-hmysql_lab",
            "-ulabuser",
            "-plabpass",
            "labdb"
        ],
        "description": "MySQL labdb (użytkownik labuser)"
    },
    "BazyRoot": {
        "cmd": [
            "docker", "run", "--rm", "-it",
            "--network", "lab-net",
            "--memory", "256m",
            "--cpus", "0.5",
            "mysql:8.0",
            "mysql",
            "-hmysql_lab",
            "-uroot",
            "-prootpass",
            "labdb"
        ],
        "description": "MySQL labdb (root)"
    },
    "ResetDatabase": {
        "cmd": [
            "docker", "exec", "-i", "mysql_lab",
            "sh", "-c", "mysql -uroot -prootpass labdb < /docker-entrypoint-initdb.d/init.sql && echo 'Baza danych została zresetowana.' "
        ],
        "description": "Przywraca bazę danych do stanu początkowego"
    },
    "LinuxTerminal": {
        "cmd": [
            "docker", "run", "--rm", "-it",
            "--memory", "256m",
            "--cpus", "0.5",
            "ubuntu:22.04",
            "/bin/bash"
        ],
        "description": "Powłoka bash (Ubuntu)"
    },
}

# Ustawienia logowania systemowego

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


# Logger sesji użytkownika

class SessionLogger:
    """Zapisuje polecenia sesji do dedykowanego pliku logu."""

    def __init__(self, username: str, config: str):
        self.username = username
        self.config = config
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = LOG_DIR / f"{username}_{config}_{ts}.log"
        self.f = open(path, "a", encoding="utf-8", errors="replace")
        self.buf = ""
        self._write(f"=== Początek sesji: użytkownik={username} konfiguracja={config} ===\n")

    def feed(self, data: bytes):
        """Przekazuje surowe bajty od klienta (klawisze) do loggera."""
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


# Mostek PTY / Docker

def set_winsize(fd, rows: int, cols: int):
    """Ustawia rozmiar okna terminala w PTY."""
    fcntl.ioctl(fd, termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0))


def run_session(conn: socket.socket, addr, username: str, config: str):
    """Uruchamia kontener Dockera za pomocą PTY i łączy go z połączeniem TCP."""
    cmd = CONFIGS[config]["cmd"]
    log.info("Uruchamianie sesji: użytkownik=%s konf=%s adres=%s polecenie=%s",
             username, config, addr, cmd)

    session_log = SessionLogger(username, config)
    master_fd, slave_fd = pty.openpty()
    set_winsize(master_fd, 40, 120)

    pid = os.fork()
    if pid == 0:
        # ── proces potomny: uruchomienie Dockera ────────────────────────────
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(master_fd)
        os.close(slave_fd)
        # Zamknięcie wszystkich pozostałych deskryptorów plików
        for fd in range(3, 256):
            try:
                os.close(fd)
            except OSError:
                pass
        os.execvp(cmd[0], cmd)
        os._exit(1)

    # proces nadrzędny: mostkowanie PTY ↔ TCP
    os.close(slave_fd)

    stop_event = threading.Event()

    def pty_to_tcp():
        """Wątek przesyłający dane z terminala (PTY) do klienta (TCP)."""
        while not stop_event.is_set():  # Pętla działa dopóki nie ustawiono sygnału zatrzymania
            try:
                # Sprawdzenie, czy są dostępne dane do odczytu z terminala PTY
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if r:
                    # Odczyt danych z PTY (np. dane wyjściowe procesu)
                    data = os.read(master_fd, 4096)
                    if not data:
                        break  # Jeśli brak danych, kończymy wątek
                    # Wysłanie odczytanych danych do klienta przez TCP
                    conn.sendall(data)
            except OSError:
                break  # Jeśli wystąpi błąd systemowy, wychodzimy z wątku
            except Exception as e:
                log.debug("Błąd pty_to_tcp: %s", e)  # Logowanie innych wyjątków
                break
        stop_event.set()  # Ustawienie flagi zatrzymania, jeśli wątek kończy działanie

    # Uruchomienie wątku odpowiedzialnego za przesyłanie danych z PTY do TCP
    reader_thread = threading.Thread(target=pty_to_tcp, daemon=True)
    reader_thread.start()

    try:
        while not stop_event.is_set():  # Główna pętla odbierająca dane od klienta
            try:
                conn.settimeout(1.0)  # Ustawienie timeoutu na odbiór danych
                data = conn.recv(1024)  # Odbiór danych od klienta (np. wpisy użytkownika)
                if not data:
                    break  # Jeśli brak danych, kończymy sesję
                session_log.feed(data)  # Zapis danych do logu sesji
                os.write(master_fd, data)  # Wysłanie danych do PTY (np. do powłoki)
            except socket.timeout:
                continue  # Timeout jest normalny, kontynuujemy pętlę
            except Exception:
                break  # Inne błędy powodują zakończenie pętli
    finally:
        stop_event.set()  # Ustawienie flagi zatrzymania dla wszystkich wątków
        session_log.close()  # Zamknięcie logu sesji
        try:
            os.kill(pid, signal.SIGTERM)  # Zakończenie procesu powłoki
        except ProcessLookupError:
            pass  # Jeśli proces już nie istnieje, ignorujemy
        try:
            os.close(master_fd)  # Zamknięcie deskryptora PTY
        except OSError:
            pass
        try:
            conn.close()  # Zamknięcie połączenia TCP
        except Exception:
            pass
        log.info("Koniec sesji: użytkownik=%s konf=%s", username, config)  # Logowanie zakończenia sesji


# ── Protokół Handshake ────────────────────────────────────────────────────────
#
# Klient wysyła linię JSON:     {"code": "1234", "config": "Bazy1"}
# Serwer odpowiada:             {"ok": true,  "username": "student1"}
#              lub:             {"ok": false, "error": "Błąd..."}

def handle_client(conn: socket.socket, addr):
    """Obsługuje proces logowania i uruchamia sesję."""
    log.info("Połączenie z adresu %s", addr)
    try:
        # Odczyt handshake (do 1 KB, zakończony znakiem nowej linii)
        raw = b""
        while b"\n" not in raw and len(raw) < 1024:
            chunk = conn.recv(256)
            if not chunk:
                return
            raw += chunk

        line = raw.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
        msg = json.loads(line)
        code = str(msg.get("code", "")).strip()
        config = str(msg.get("config", "")).strip()

        username = USERS.get(code)
        if username is None:
            conn.sendall(json.dumps({"ok": False, "error": "Nieprawidłowy kod"}).encode() + b"\n")
            conn.close()
            log.warning("Autoryzacja nieudana: kod=%s adres=%s", code, addr)
            return

        if config not in CONFIGS:
            conn.sendall(json.dumps({"ok": False, "error": f"Nieznana konfiguracja: {config}"}).encode() + b"\n")
            conn.close()
            return

        conn.sendall(json.dumps({"ok": True, "username": username}).encode() + b"\n")
        log.info("Autoryzacja OK: użytkownik=%s konf=%s adres=%s", username, config, addr)

        run_session(conn, addr, username, config)

    except json.JSONDecodeError:
        log.warning("Błędny handshake z adresu %s", addr)
        conn.close()
    except Exception as e:
        log.error("Błąd handle_client: %s", e, exc_info=True)
        conn.close()


# Main

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(50)
    log.info("Brama Terminalowa nasłuchuje na %s:%d", HOST, PORT)
    log.info("Dostępne konfiguracje: %s", list(CONFIGS.keys()))
    log.info("Użytkownicy: %d zarejestrowanych", len(USERS))

    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log.info("Zamykanie serwera.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    main()
