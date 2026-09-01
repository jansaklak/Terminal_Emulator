# Serwer Bramy Terminalowej (Server)

Serwer pośredniczący odpowiedzialny za autoryzację studentów, zarządzanie pseudoterminalami POSIX PTY, orkiestrację wyizolowanych kontenerów Docker oraz webowy panel administracyjny.

## Wymagania

- System operacyjny Windows, Linux lub macOS z zainstalowanym środowiskiem Docker i Docker Compose.
- Python 3.10+ (w przypadku uruchamiania poza kontenerem).

## Uruchomienie

### 1. Uruchomienie za pomocą Docker Compose (zalecane)

W katalogu `Server/`:

```bash
docker compose up -d --build
```

lub przy użyciu skryptu pomocniczego:

```bash
python3 run.py
```

### 2. Dostępne usługi

Po uruchomieniu serwera dostępne są dwa punkty wejścia:

- **Brama terminalowa TCP:** port `51234` (dla aplikacji klienckich Java).
- **Webowy Panel Administracyjny:** `http://localhost:5001` (zarządzanie kontami, grupami, import CSV, podgląd logów i monitorowanie sesji).

### 3. Zatrzymanie serwera

Aby bezpiecznie zatrzymać wszystkie usługi i powiązane kontenery:

```bash
docker compose down
```

lub:

```bash
python3 stop.py
```

## Struktura katalogów

- `server.py` – proces główny bramy terminalowej TCP.
- `admin_panel.py` – backend panelu administracyjnego (Flask).
- `templates/` – szablony interfejsu panelu administracyjnego.
- `images/` – konfiguracje i skrypty inicjalizacyjne środowisk bazodanowych.
- `input/` – pliki CSV z listami studentów do automatycznego importu (`Nazwisko;Imie`).
- `users.json` – baza użytkowników, haseł i przypisanych grup.
- `server_config.json` – definicja dostępnych środowisk laboratoryjnych.
- `commands/` – rejestr historii komend sesji (`.cmds`).
- `logs/` – logi operacji serwera i sesji użytkowników.
