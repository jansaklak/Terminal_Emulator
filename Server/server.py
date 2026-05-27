#!/usr/bin/env python3
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

# Ścieżki do plików konfiguracyjnych JSON
CONFIG_FILE = Path("server_config.json")
IMAGES_DIR = Path("images")
USERS_FILE = Path("users.json")
ONLINE_FILE = Path("online.json")

def get_live_config():
    """Wczytuje aktualną konfigurację serwera i wszystkich obrazów z folderu images/."""
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
    """Wczytuje listę użytkowników."""
    try:
        if not USERS_FILE.exists():
            return {}
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"BŁĄD wczytywania {USERS_FILE}: {e}")
        return {}

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


def resolve_host_path(base_path: str, relative_path: str) -> str:
    if ":" in base_path or "\\" in base_path:
        return ntpath.normpath(ntpath.join(base_path, relative_path))
    return posixpath.normpath(posixpath.join(base_path, relative_path))


def sanitize_docker_name(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9_.-]+", "-", value.lower()).strip("-._")
    return sanitized or "user"


def run_docker_command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def get_session_definition(config: dict) -> dict:
    return config.get("session", config)


def seed_directory_into_volume(volume_name: str, seed_source: str, image: str) -> None:
    seed_result = run_docker_command([
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/target",
        "-v",
        f"{seed_source}:/seed:ro",
        image,
        "bash",
        "-lc",
        "mkdir -p /target && cp -a /seed/. /target/",
    ])
    if seed_result.returncode != 0:
        raise RuntimeError(seed_result.stderr.strip() or f"Nie udało się zainicjalizować wolumenu {volume_name}")


def remove_docker_container(container_name: str) -> None:
    inspect_result = run_docker_command(["inspect", container_name])
    if inspect_result.returncode != 0:
        return

    remove_result = run_docker_command(["rm", "-f", container_name])
    if remove_result.returncode != 0:
        raise RuntimeError(remove_result.stderr.strip() or f"Nie udało się usunąć kontenera {container_name}")


def remove_docker_volume(volume_name: str) -> None:
    inspect_result = run_docker_command(["volume", "inspect", volume_name])
    if inspect_result.returncode != 0:
        return

    remove_result = run_docker_command(["volume", "rm", volume_name])
    if remove_result.returncode != 0:
        raise RuntimeError(remove_result.stderr.strip() or f"Nie udało się usunąć wolumenu {volume_name}")


def ensure_session_container(username: str, host_project_path: str, config: dict, cpu_limit: str, mem_limit: str) -> str:
    session = get_session_definition(config)
    mode = session.get("mode", "container")
    base_container_name = session.get("base_name", "session")
    container_name = f"{base_container_name}_{sanitize_docker_name(username)}"
    img_base = config.get("_img_path", "")

    # Upewnienie się, że sieć istnieje
    network_name = session.get("network", "lab-net")
    run_docker_command(["network", "create", network_name]) # Ignorujemy błąd jeśli już istnieje

    existing = run_docker_command(["inspect", "-f", "{{.State.Running}}", container_name])
    if existing.returncode == 0:
        if existing.stdout.strip() != "true":
            start_result = run_docker_command(["start", container_name])
            if start_result.returncode != 0:
                raise RuntimeError(start_result.stderr.strip() or f"Nie udało się uruchomić kontenera {container_name}")
        return container_name

    if mode == "mysql":
        image = session.get("image", "mysql:8.0")
        network_name = session.get("network", "lab-net")
        root_password = session.get("root_password", "rootpass")
        database_name = session.get("database", "labdb")
        database_user = session.get("user", "labuser")
        database_password = session.get("password", "labpass")
        
        # Rozwiązywanie ścieżki SQL względem folderu obrazu
        raw_sql_path = session.get("seed_sql", "resources/init.sql")
        img_sql_path = resolve_host_path(img_base, raw_sql_path)
        init_sql = resolve_host_path(host_project_path, img_sql_path)
        
        data_volume = f"{container_name}_data"

        run_args = [
            "run",
            "-d",
            "--name",
            container_name,
            "--network",
            network_name,
            "-e",
            f"MYSQL_ROOT_PASSWORD={root_password}",
            "-e",
            f"MYSQL_DATABASE={database_name}",
            "-e",
            f"MYSQL_USER={database_user}",
            "-e",
            f"MYSQL_PASSWORD={database_password}",
            "-v",
            f"{data_volume}:/var/lib/mysql",
            "-v",
            f"{init_sql}:{session.get('seed_target', '/docker-entrypoint-initdb.d/init.sql')}:ro",
            image,
        ]

        service_command = session.get("service_command")
        if service_command:
            run_args.extend(service_command)

        create_result = run_docker_command(run_args)
        if create_result.returncode != 0:
            raise RuntimeError(create_result.stderr.strip() or f"Nie udało się utworzyć kontenera {container_name}")

        return container_name

    image = session.get("image", "ubuntu:22.04")
    
    # Rozwiązywanie ścieżki seed względem folderu obrazu
    raw_seed_path = session.get("seed_dir", "shared")
    img_seed_path = resolve_host_path(img_base, raw_seed_path)
    seed_dir = resolve_host_path(host_project_path, img_seed_path)
    
    mount_path = session.get("mount_path", "/shared_data")
    data_volume = f"{container_name}_data"
    hostname_template = session.get("hostname_template", "{user}-lab")
    hostname = hostname_template.replace("{user}", sanitize_docker_name(username))

    seed_directory_into_volume(data_volume, seed_dir, image)

    create_result = run_docker_command([
        "run",
        "-d",
        "--name",
        container_name,
        "--hostname",
        hostname,
        "--cpus",
        cpu_limit,
        "--memory",
        mem_limit,
        "-v",
        f"{data_volume}:{mount_path}",
        image,
        *session.get("service_command", ["sleep", "infinity"]),
    ])
    if create_result.returncode != 0:
        raise RuntimeError(create_result.stderr.strip() or f"Nie udało się utworzyć kontenera {container_name}")

    return container_name


def recreate_session_state(username: str, host_project_path: str, config: dict, cpu_limit: str, mem_limit: str) -> None:
    session = get_session_definition(config)
    base_container_name = session.get("base_name", "session")
    container_name = f"{base_container_name}_{sanitize_docker_name(username)}"
    data_volume = f"{container_name}_data"
    remove_docker_container(container_name)
    remove_docker_volume(data_volume)
    ensure_session_container(username, host_project_path, config, cpu_limit, mem_limit)


def is_reset_control_message(data: bytes) -> bool:
    try:
        payload = json.loads(data.decode("utf-8", errors="strict").strip())
    except Exception:
        return False

    return payload.get("__control__") == "reset_session"


def build_attach_command(username: str, container_name: str, config: dict) -> list[str]:
    session = get_session_definition(config)
    attach_template = session.get("attach_command", [])
    command = [
        part.replace("{user}", username).replace("{service_container}", container_name)
        for part in attach_template
    ]

    if session.get("mode", "container") == "mysql":
        return ["docker", "exec", "-it", container_name, *command]

    return [
        "docker",
        "exec",
        "-it",
        "-w",
        session.get("workdir", "/shared_data"),
        container_name,
        *command,
    ]


def shutdown_session(pid: int, master_fd: int, conn: socket.socket, stop_event: threading.Event, session_log: SessionLogger, username: str, config_name: str) -> None:
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
    """Uruchamia kontener Dockera za pomocą PTY."""
    log.info("Uruchamianie sesji: użytkownik=%s konf=%s adres=%s polecenie=%s",
             username, config_name, addr, cmd_list)
    update_online(username, config_name, "add")

    session_log = SessionLogger(username, config_name)
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
                
                # Obsługa komunikatów kontrolnych (resize/reset)
                if b"__control__" in data:
                    if handle_control_message(data, master_fd, reset_handler):
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
    """Realizuje dwuetapowy handshake: Autoryzacja -> Lista konfiguracji -> Wybór."""
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

        if selected_key not in configs:
            log.error("Nieprawidłowy wybór konfiguracji: %s przez %s", selected_key, username)
            return conn.close()

        # Uruchomienie właściwej sesji
        session_config = get_session_definition(configs[selected_key])
        cpu_limit = configs[selected_key].get("cpu_limit", "0.5")
        mem_limit = configs[selected_key].get("mem_limit", "256m")

        # Dynamiczne podstawianie nazwy użytkownika i rozwiązywanie ścieżek relatywnych
        host_project_path = os.environ.get("PROJECT_PATH") or os.path.abspath(os.path.dirname(__file__))
        session_container_name = ensure_session_container(username, host_project_path, configs[selected_key], cpu_limit, mem_limit)
        cmd = build_attach_command(username, session_container_name, configs[selected_key])

        run_session(
            conn,
            addr,
            username,
            selected_key,
            cmd,
            reset_handler=lambda: recreate_session_state(username, host_project_path, configs[selected_key], cpu_limit, mem_limit),
        )

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
    main().info("Brama Terminalowa nasłuchuje na %s:%d", HOST, PORT)

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