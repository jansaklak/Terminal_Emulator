#!/usr/bin/env python3
"""
Serwer Terminali - brama uruchamiająca i podłączająca sesje Dockerowe.
Plik zawiera funkcje do wczytywania konfiguracji, zarządzania sesjami
i komunikacji z klientem przez gniazdo TCP. Komentarze są w języku polskim.
"""
import socket
import threading
import os
import subprocess
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
import re
import ntpath
import posixpath
from pathlib import Path
import time
import shutil
import base64

# Ścieżki do plików konfiguracyjnych JSON
CONFIG_FILE = Path("server_config.json")
IMAGES_DIR = Path("images")
USERS_FILE = Path("users.json")
ONLINE_FILE = Path("online.json")
COMMANDS_DIR = Path("commands")


def reset_online():
    """Czyści plik `online.json` — wywoływane przy starcie serwera.

    Funkcja nadpisuje plik pustym słownikiem, zapewniając, że po restarcie
    nie ma pozostałych wpisów o zalogowanych sesjach.
    """
    try:
        with open(ONLINE_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        try:
            log.info("Zresetowano plik %s", ONLINE_FILE)
        except NameError:
            print(f"Zresetowano plik {ONLINE_FILE}")
    except Exception as e:
        try:
            log.warning("Nie udało się zresetować %s: %s", ONLINE_FILE, e)
        except NameError:
            print(f"Nie udało się zresetować {ONLINE_FILE}: {e}")

def get_live_config():
    """Wczytuje aktualną konfigurację serwera oraz konfiguracje obrazów.

    Przeszukuje katalog `images/` i ładuje pliki `config.json` dla każdego obrazu.
    Dodaje do konfiguracji pole `_img_path` wskazujące ścieżkę do folderu obrazu.
    Zwraca słownik z kluczami: HOST, PORT, CONFIGS.
    """
    try:
        base_cfg = {"HOST": "0.0.0.0", "PORT": 51234, "CONFIGS": {}}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                base_cfg.update(json.load(f))

        # Skanowanie folderu images w poszukiwaniu konfiguracji
        if IMAGES_DIR.exists():
            for img_folder in IMAGES_DIR.iterdir():
                if img_folder.is_dir():
                    img_cfg_path = img_folder / "config.json"
                    if img_cfg_path.exists():
                        with open(img_cfg_path, 'r', encoding='utf-8') as f:
                            img_cfg = json.load(f)
                            # Zapisujemy ścieżkę do folderu obrazu, aby móc rozwiązywać ścieżki zasobów
                            img_cfg["_img_path"] = str(img_folder)
                            key = img_folder.name
                            base_cfg["CONFIGS"][key] = img_cfg

        return base_cfg
    except Exception as e:
        msg = f"BŁĄD wczytywania konfiguracji: {e}"
        if 'log' in globals(): log.error(msg)
        else: print(msg)
        return {"HOST": "0.0.0.0", "PORT": 51234, "CONFIGS": {}}

def get_users():
    """Wczytuje listę użytkowników z pliku `users.json`.

    Zwraca pusty słownik gdy plik nie istnieje lub wystąpi błąd.
    """
    try:
        if not USERS_FILE.exists():
            return {}
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"BŁĄD wczytywania {USERS_FILE}: {e}")
        return {}

def update_online(username, config_name, action="add"):
    # Aktualizuje plik `online.json`, rejestrując aktywne sesje użytkowników.
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
PORT = initial_cfg.get("PORT", 51234)
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
    def __init__(self, username: str, config: str, allow_commands: bool = False, image_name: str = ""):
        self.username = username
        self.config = config
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_img = re.sub(r'[^a-zA-Z0-9_.-]', '_', image_name).strip('_') if image_name else ""
        if clean_img and clean_img.lower() != config.lower():
            filename_part = f"{username}_{config}_{clean_img}_{ts}"
        else:
            filename_part = f"{username}_{config}_{ts}"

        path = LOG_DIR / f"{filename_part}.log"
        self.f = open(path, "a", encoding="utf-8", errors="replace")
        self.buf = ""
        self._write(f"=== Początek sesji: użytkownik={username} konfiguracja={config} obraz={image_name or 'domyślny'} ===\n")
        
        self.allow_commands = allow_commands
        if allow_commands:
            try:
                COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
                (COMMANDS_DIR / str(self.config)).mkdir(parents=True, exist_ok=True)
                self.commands_path = COMMANDS_DIR / str(self.config) / f"{filename_part}.cmds"
            except Exception:
                self.commands_path = None
        else:
            self.commands_path = None

    def feed(self, data: bytes):
        # 1. Zapis surowych danych do pliku .cmds (dla wiernego odtworzenia sesji)
        if self.allow_commands and self.commands_path:
            try:
                with open(self.commands_path, "ab") as cf:
                    cf.write(data)
            except Exception:
                pass

        # 2. Zapis czytelnych komend do pliku .log (czytelne dla człowieka w panelu admina)
        try:
            i = 0
            n = len(data)
            while i < n:
                b = data[i]

                # Obsługa sekwencji ANSI Escape (np. strzałki, kody sterujące CSI)
                if b == 0x1b: # ESC
                    if i + 1 < n and data[i+1:i+2] == b'[':
                        j = i + 2
                        while j < n and not (0x40 <= data[j] <= 0x7e):
                            j += 1
                        i = j + 1 if j < n else n
                        continue
                    else:
                        i += 1
                        continue

                # Enter (\r lub \n) -> Zapisz wyczyszczoną linię komendy
                if b in (0x0d, 0x0a):
                    clean_cmd = self.buf.strip()
                    if clean_cmd:
                        self._write(f"POLECENIE: {clean_cmd}\n")
                    self.buf = ""
                    i += 1
                    continue

                # Backspace (\x7f lub \x08) -> Usuń ostatni znak z bufora
                if b in (0x7f, 0x08):
                    if self.buf:
                        self.buf = self.buf[:-1]
                    i += 1
                    continue

                # Ctrl+U (\x15) lub Ctrl+C (\x03) -> Wyczyszczenie bufora linii
                if b in (0x15, 0x03):
                    self.buf = ""
                    i += 1
                    continue

                # Tab (\t) -> Spacja
                if b == 0x09:
                    self.buf += " "
                    i += 1
                    continue

                # Zwykłe drukowalne znaki (ASCII i UTF-8)
                if b >= 32:
                    char_len = 1
                    if b >= 0xf0: char_len = 4
                    elif b >= 0xe0: char_len = 3
                    elif b >= 0xc0: char_len = 2

                    chunk = data[i:i+char_len]
                    try:
                        ch = chunk.decode("utf-8")
                        if ch.isprintable():
                            self.buf += ch
                    except Exception:
                        pass
                    i += char_len
                else:
                    i += 1

        except Exception:
            pass

    def _write(self, line: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.f.write(f"[{ts}] {line}")
        self.f.flush()

    def close(self):
        self._write("=== Koniec sesji ===\n")
        self.f.close()

def set_winsize(fd, rows: int, cols: int):
    """Ustawia rozmiar terminala (TTY) dla deskryptora `fd`.

    Przydatne do przekazania informacji o rozmiarze okna od klienta do PTY.
    """
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def resolve_host_path(base_path: str, relative_path: str) -> str:
    """Rozwiązuje ścieżkę relatywną w kontekście platformy hosta.

    Dla ścieżek zawierających dwukropek lub backslash używa `ntpath` (Windows),
    w przeciwnym razie `posixpath` (Linux/macOS).
    """
    if ":" in base_path or "\\" in base_path:
        return ntpath.normpath(ntpath.join(base_path, relative_path))
    return posixpath.normpath(posixpath.join(base_path, relative_path))


def sanitize_docker_name(value: str) -> str:
    """Zamienia nazwę użytkownika na bezpieczną nazwę kontenera Docker.

    Pozwala tylko na małe litery, cyfry oraz znaki `_.-`, pozostałe zamieniane są na `-`.
    """
    sanitized = re.sub(r"[^a-z0-9_.-]+", "-", value.lower()).strip("-._")
    return sanitized or "user"


def run_docker_command(args: list[str]) -> subprocess.CompletedProcess:
    """Uruchamia polecenie Docker i zwraca obiekt CompletedProcess.

    Domyślnie przechwytuje stdout/stderr jako tekst.
    """
    return subprocess.run(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def get_session_definition(config: dict) -> dict:
    # Zwraca część `session` z konfiguracji obrazu, jeżeli istnieje.
    return config.get("session", config)


class SafeTemplateDict(dict):
    def __missing__(self, key):
        # Jeśli brak wartości podczas formatowania, pozostaw placeholder niezmieniony.
        return "{" + key + "}"


def render_template(value, context: dict):
    """Rekurencyjnie renderuje szablony zawarte w wartościach konfiguracji.

    Wspiera stringi, listy, tuple i dicty — zastępuje {placeholder} z kontekstu.
    """
    if isinstance(value, str):
        return value.format_map(SafeTemplateDict(context))
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if isinstance(value, tuple):
        return [render_template(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render_template(item, context) for key, item in value.items()}
    return value


def build_session_context(username: str, container_name: str, host_project_path: str, config: dict) -> dict:
    # Buduje kontekst sesji używany do podstawiania wartości w szablonach `run_command`.
    session = get_session_definition(config)
    img_base = config.get("_img_path", "")
    network_name = session.get("network", "lab-net")
    image = session.get("image", "ubuntu:22.04")
    data_volume = f"{container_name}_data"
    hostname_template = session.get("hostname_template", "{user}-lab")

    context = dict(session)
    context.update({
        "username": username,
        "sanitized_user": sanitize_docker_name(username),
        "container_name": container_name,
        "network": network_name,
        "image": image,
        "host_project_path": host_project_path,
        "data_volume": data_volume,
        "hostname": hostname_template.replace("{user}", sanitize_docker_name(username)),
    })

    raw_sql_path = session.get("seed_sql")
    if raw_sql_path:
        img_sql_path = resolve_host_path(img_base, raw_sql_path)
        context["seed_sql_host_path"] = resolve_host_path(host_project_path, img_sql_path)

    return context


def build_attach_context(username: str, container_name: str, config: dict) -> dict:
    # Buduje mniejszy kontekst dla polecenia `attach` (wejście do działającego kontenera).
    session = get_session_definition(config)
    context = dict(session)
    context.update({
        "username": username,
        "sanitized_user": sanitize_docker_name(username),
        "container_name": container_name,
        "image": session.get("image", "ubuntu:22.04"),
        "data_volume": f"{container_name}_data",
    })
    return context


def remove_docker_container(container_name: str) -> None:
    # Usuwa kontener Docker, jeśli istnieje (używane podczas recreate/cleanup).
    inspect_result = run_docker_command(["inspect", container_name])
    if inspect_result.returncode != 0:
        return

    remove_result = run_docker_command(["rm", "-f", container_name])
    if remove_result.returncode != 0:
        raise RuntimeError(remove_result.stderr.strip() or f"Nie udało się usunąć kontenera {container_name}")


def remove_docker_volume(volume_name: str) -> None:
    # Usuwa wolumen Dockerowy, jeśli istnieje.
    inspect_result = run_docker_command(["volume", "inspect", volume_name])
    if inspect_result.returncode != 0:
        return

    remove_result = run_docker_command(["volume", "rm", volume_name])
    if remove_result.returncode != 0:
        raise RuntimeError(remove_result.stderr.strip() or f"Nie udało się usunąć wolumenu {volume_name}")


def ensure_session_container(username: str, host_project_path: str, config: dict) -> str:
    # Tworzy (lub uruchamia istniejący) kontener sesji dla użytkownika zgodnie z konfiguracją obrazu.
    session = get_session_definition(config)
    base_container_name = session.get("base_name", "session")
    container_name = f"{base_container_name}_{sanitize_docker_name(username)}"
    context = build_session_context(username, container_name, host_project_path, config)

    # Upewnienie się, że sieć istnieje
    network_name = context["network"]
    run_docker_command(["network", "create", network_name]) # Ignorujemy błąd jeśli już istnieje

    existing = run_docker_command(["inspect", "-f", "{{.State.Running}}", container_name])
    if existing.returncode == 0:
        if existing.stdout.strip() != "true":
            start_result = run_docker_command(["start", container_name])
            if start_result.returncode != 0:
                raise RuntimeError(start_result.stderr.strip() or f"Nie udało się uruchomić kontenera {container_name}")
        return container_name

    run_command = session.get("run_command")
    if not run_command:
        raise RuntimeError(f"Konfiguracja {base_container_name} nie definiuje run_command")

    run_args = render_template(run_command, context)
    create_result = run_docker_command(run_args)
    if create_result.returncode != 0:
        raise RuntimeError(create_result.stderr.strip() or f"Nie udało się utworzyć kontenera {container_name}")

    return container_name


def recreate_session_state(username: str, host_project_path: str, config: dict) -> None:
    # Usuwa istniejący kontener i wolumen danych, a następnie tworzy nowy kontener.
    session = get_session_definition(config)
    base_container_name = session.get("base_name", "session")
    container_name = f"{base_container_name}_{sanitize_docker_name(username)}"
    data_volume = f"{container_name}_data"
    
    # Obsługa pliku komend - oznaczamy jako archiwalny (_old)
    try:
        config_name = None
        # Próbujemy znaleźć nazwę konfiguracji (klucz w CONFIGS)
        live_cfg = get_live_config()
        for k, v in live_cfg.get('CONFIGS', {}).items():
            if v.get('session', {}).get('base_name') == base_container_name:
                config_name = k
                break
        
        if config_name:
            config_dir = COMMANDS_DIR / str(config_name)
            if config_dir.exists():
                for cmd_path in config_dir.glob(f"{username}*.cmds"):
                    if "_old" not in cmd_path.name:
                        old_path = config_dir / f"{cmd_path.stem}_old.cmds"
                        try:
                            cmd_path.rename(old_path)
                            log.info("Zarchiwizowano plik komend: %s -> %s", cmd_path.name, old_path.name)
                        except Exception: pass
    except Exception as e:
        try:
            log.warning("Błąd podczas archiwizacji pliku komend: %s", e)
        except NameError: pass

    remove_docker_container(container_name)
    remove_docker_volume(data_volume)
    ensure_session_container(username, host_project_path, config)


def is_reset_control_message(data: bytes) -> bool:
    # Sprawdza, czy otrzymane dane to komunikat kontrolny resetu sesji.
    try:
        payload = json.loads(data.decode("utf-8", errors="strict").strip())
    except Exception:
        return False

    return payload.get("__control__") == "reset_session"


def handle_control_message(data: bytes, master_fd: int, reset_handler=None, conn: socket.socket = None) -> bool:
    # Obsługuje komunikaty kontrolne wysyłane przez klienta (reset, clear screen itp.).
    try:
        payload = json.loads(data.decode("utf-8", errors="strict").strip())
    except Exception:
        return False

    ctrl = payload.get("__control__")
    if ctrl == "reset_session":
        if reset_handler is not None:
            reset_handler()
        return True

    if ctrl == "clear_screen":
        try:
            # write to PTY master (if available)
            os.write(master_fd, b"\x1b[H\x1b[2J")
            # send an Enter so shell prints prompt immediately
            try:
                os.write(master_fd, b"\n")
            except Exception:
                pass
        except Exception:
            pass
        try:
            # also send directly to client socket so UI clears even if PTY is misbehaving
            if conn is not None:
                conn.sendall(b"\x1b[H\x1b[2J")
                try:
                    conn.sendall(b"\n")
                except Exception:
                    pass
        except Exception:
            pass
        # Do not signal session shutdown; return False so run_session continues
        # Komunikat czyszczenia ekranu nie powoduje zakończenia sesji.
        return False

    return False


def build_attach_command(username: str, container_name: str, config: dict) -> list[str]:
    # Tworzy rzeczywiste polecenie `docker exec ...` do dołączenia do kontenera.
    session = get_session_definition(config)
    context = build_attach_context(username, container_name, config)
    attach_template = session.get("attach_command", [])
    if not attach_template:
        raise RuntimeError(f"Konfiguracja {session.get('base_name', 'session')} nie definiuje attach_command")

    command = render_template(attach_template, context)
    return ["docker", "exec", "-it", container_name, *command]


def shutdown_session(pid: int, master_fd: int, conn: socket.socket, stop_event: threading.Event, session_log: SessionLogger, username: str, config_name: str) -> None:
    # Zatrzymuje sesję: kończy proces, zamyka deskryptory i usuwa wpis online.
    stop_event.set()
    session_log.close()
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        os.close(master_fd)
    except OSError:
        pass
    try:
        conn.close()
    except Exception:
        pass
    update_online(username, config_name, "remove")

def run_session(conn: socket.socket, addr, username: str, config_name: str, cmd_list: list, reset_handler=None):
    """Uruchamia PTY i przekierowuje wejście/wyjście między klientem TCP a procesem.

    Funkcja tworzy PTY, forkuje proces, uruchamia polecenie (kontener/attach) i
    tworzy wątek przesyłający dane z PTY do gniazda TCP. Odbiera dane od klienta
    i zapisuje je do PTY. Obsługuje komunikaty kontrolne (resize/reset/clear).
    """
    log.info("Uruchamianie sesji: użytkownik=%s konf=%s adres=%s polecenie=%s",
             username, config_name, addr, cmd_list)
    update_online(username, config_name, "add")

    # Dowiadujemy się, czy ten obraz zezwala na zapisywanie/odtwarzanie komend
    try:
        cfg = get_live_config()
        session_cfg = cfg.get('CONFIGS', {}).get(config_name, {})
        session_def = get_session_definition(session_cfg)
        image_name = session_def.get("image", "")
    except Exception:
        session_cfg = {}
        image_name = ""

    # `forbid_*` wyłącza funkcję, a brak flagi oznacza domyślnie: dozwolone.
    forbid_cmd = bool(session_cfg.get('forbid_command_recording', False))
    allow_cmds = not forbid_cmd

    forbid_auto = bool(session_cfg.get('forbid_auto_execute', False))
    auto_exec = not forbid_auto

    session_permissions = {
        "can_record_commands": allow_cmds,
        "can_auto_execute": auto_exec,
    }

    session_log = SessionLogger(username, config_name, allow_commands=allow_cmds, image_name=image_name)
    master_fd, slave_fd = pty.openpty()
    # Domyślny rozmiar na start (zostanie nadpisany przez klienta)
    set_winsize(master_fd, 24, 80)

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

    # Blokada do bezpiecznego wysyłania danych przez socket z wielu wątków
    socket_lock = threading.Lock()
    def safe_send(data: bytes):
        try:
            with socket_lock:
                conn.sendall(data)
        except Exception:
            pass

    # Clear client screen on session start to avoid mid-screen leftover
    safe_send(b"\x1b[H\x1b[2J")

    def pty_to_tcp():
        while not stop_event.is_set():
            try:
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if r:
                    data = os.read(master_fd, 4096)
                    if not data: break
                    safe_send(data)
            except Exception: break
        stop_event.set()

    # Wątek czytający z PTY i wysyłający do klienta
    threading.Thread(target=pty_to_tcp, daemon=True).start()

    try:
        while not stop_event.is_set():
            try:
                conn.settimeout(1.0)
                data = conn.recv(1024)
                if not data: break
                # Obsługa komunikatów kontrolnych (resize/reset oraz save/load komend)
                if b"__control__" in data:
                    try:
                        payload = json.loads(data.decode("utf-8", errors="strict").strip())
                    except Exception:
                        payload = None

                    if isinstance(payload, dict):
                        ctrl = payload.get("__control__")
                        # Pobierz listę komend z serwera
                        if ctrl == "get_commands":
                            if not allow_cmds or not session_log.commands_path:
                                safe_send(json.dumps({"__control__": "commands_data", "data": ""}).encode('utf-8') + b"\n")
                            else:
                                try:
                                    if session_log.commands_path.exists():
                                        # Odczytujemy jako surowe bajty i kodujemy w base64, aby uniknąć błędów JSON
                                        with open(session_log.commands_path, 'rb') as cf:
                                            cmds_bytes = cf.read()
                                        print(f"DEBUG: get_commands reading {len(cmds_bytes)} bytes from {session_log.commands_path}")
                                        cmds_b64 = base64.b64encode(cmds_bytes).decode('utf-8')
                                        safe_send(json.dumps({"__control__": "commands_data", "data": cmds_b64, "b64": True}).encode('utf-8') + b"\n")
                                    else:
                                        print(f"DEBUG: get_commands path does not exist: {session_log.commands_path}")
                                        safe_send(json.dumps({"__control__": "commands_data", "data": ""}).encode('utf-8') + b"\n")
                                except Exception as e:
                                    print(f"DEBUG: get_commands error: {e}")
                                    safe_send(json.dumps({"__control__": "commands_data", "data": ""}).encode('utf-8') + b"\n")
                            continue

                        # Zapisz snapshot pliku komend
                        if ctrl == "save_commands":
                            if not allow_cmds or not session_log.commands_path:
                                continue
                            else:
                                name = payload.get('name') or datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                                snap = COMMANDS_DIR / str(config_name) / f"{username}_{name}.cmds"
                                try:
                                    shutil.copyfile(session_log.commands_path, snap)
                                    try:
                                        safe_send(f"[SERVER] Zapisano komendy: {snap}\n".encode('utf-8'))
                                    except Exception:
                                        pass
                                except Exception:
                                    try:
                                        safe_send("[SERVER] Błąd zapisu komend\n".encode('utf-8'))
                                    except Exception:
                                        pass
                            continue

                        # Wczytaj plik komend przesłany z klienta i (opcjonalnie) wykonaj
                        if ctrl == "load_commands":
                            if not allow_cmds or not session_log.commands_path:
                                continue
                            # odczyt zawartości (może być base64 lub tekst)
                            data_field = payload.get('data')
                            if data_field is None:
                                print("DEBUG: load_commands data_field is None")
                                continue
                            try:
                                print(f"DEBUG: load_commands received data of length {len(data_field)}")
                                if payload.get('b64'):
                                    raw = base64.b64decode(data_field.encode('utf-8'))
                                else:
                                    # Próbujemy odczytać jako utf-8, fallback na latin-1 dla surowych bajtów
                                    try:
                                        raw = data_field.encode('utf-8')
                                    except UnicodeEncodeError:
                                        raw = data_field.encode('latin-1', errors='replace')
                                
                                print(f"DEBUG: load_commands writing {len(raw)} bytes to {session_log.commands_path}")
                                # zapisz do pliku (nadpisanie)
                                session_log.commands_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(session_log.commands_path, 'wb') as cf:
                                    cf.write(raw)
                                
                                # opcjonalne natychmiastowe wykonanie
                                if payload.get('execute', True):
                                    # Wierne odtworzenie: jeśli są znaki sterujące (np. \r), wysyłamy bajt po bajcie
                                    # W przeciwnym razie wysyłamy linia po linii.
                                    if b'\r' in raw or b'\x1b' in raw or b'\t' in raw:
                                        print("DEBUG: load_commands executing byte by byte")
                                        for i in range(len(raw)):
                                            os.write(master_fd, raw[i:i+1])
                                            # Mały delay dla stabilności (szczególnie przy Tab/Arrows)
                                            time.sleep(0.01)
                                    else:
                                        print("DEBUG: load_commands executing line by line")
                                        text = raw.decode('utf-8', errors='replace')
                                        for line in text.splitlines():
                                            if not line.strip(): continue
                                            try:
                                                os.write(master_fd, (line.rstrip('\r\n') + "\n").encode('utf-8'))
                                                time.sleep(0.15)
                                            except Exception:
                                                pass
                            except Exception as e:
                                print(f"DEBUG: load_commands error: {e}")
                                continue

                        # Dopisz pojedynczą komendę do pliku .cmds (pozostawione dla kompatybilności)
                        if ctrl == "append_command":
                            if not allow_cmds or not session_log.commands_path:
                                continue
                            cmd_text = payload.get('command')
                            if cmd_text:
                                try:
                                    session_log.commands_path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(session_log.commands_path, 'a', encoding='utf-8', errors='replace') as cf:
                                        cf.write(cmd_text.strip() + "\n")
                                except Exception:
                                    pass
                            continue

                    # Fallback: obsługa reset/clear i innych
                    if handle_control_message(data, master_fd, reset_handler, conn):
                        shutdown_session(pid, master_fd, conn, stop_event, session_log, username, config_name)
                        break
                    continue

                session_log.feed(data)
                os.write(master_fd, data)
            except socket.timeout: continue
            except Exception: break
    finally:
        if not stop_event.is_set():
            shutdown_session(pid, master_fd, conn, stop_event, session_log, username, config_name)
        log.info("Koniec sesji: użytkownik=%s konf=%s", username, config_name)

def handle_client(conn: socket.socket, addr):
    """Obsługuje jednego klienta: autoryzacja, wybór konfiguracji i uruchomienie sesji.

    Przebieg:
      1. Odczyt poświadczeń i weryfikacja użytkownika.
      2. Wysłanie listy dostępnych konfiguracji.
      3. Odbiór wyboru i uruchomienie/załączenie do kontenera.
    """
    try:
        # Pobieramy świeże dane przy każdym nowym połączeniu
        cfg_data = get_live_config()
        users = get_users()
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
        should_reset = bool(choice_req.get("reset", False))

        if selected_key not in configs:
            log.error("Nieprawidłowy wybór konfiguracji: %s przez %s", selected_key, username)
            return conn.close()

        host_project_path = os.environ.get("PROJECT_PATH") or os.path.abspath(os.path.dirname(__file__))

        if should_reset:
            try:
                log.info("Resetowanie kontenera na żądanie klienta dla użytkownika=%s, konf=%s", username, selected_key)
                recreate_session_state(username, host_project_path, configs[selected_key])
            except Exception as e:
                log.error("Błąd podczas resetowania kontenera w handshake: %s", e)

        # Uruchomienie właściwej sesji
        session_config = get_session_definition(configs[selected_key])
        session_permissions = {
            "can_record_commands": not bool(session_config.get("forbid_command_recording", False)),
            "can_auto_execute": not bool(session_config.get("forbid_auto_execute", False)),
        }

        conn.sendall(json.dumps({
            "ok": True,
            "selected_config": selected_key,
            "permissions": session_permissions,
        }).encode() + b"\n")

        session_container_name = ensure_session_container(username, host_project_path, configs[selected_key])
        cmd = build_attach_command(username, session_container_name, configs[selected_key])

        run_session(
            conn,
            addr,
            username,
            selected_key,
            cmd,
            reset_handler=lambda: recreate_session_state(username, host_project_path, configs[selected_key]),
        )

    except Exception as e:
        log.error("Błąd handshake z %s: %s", addr, e)
        try: conn.close()
        except: pass

def main():
    # Punkt wejścia serwera: nasłuchuje na porcie i akceptuje połączenia TCP.
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Resetujemy listę zalogowanych użytkowników przy starcie serwera
    reset_online()
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