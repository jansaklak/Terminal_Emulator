# Serwer Bramy Terminalowej (Server)

Serwer pośredniczący odpowiedzialny za autoryzację studentów, zarządzanie pseudoterminalami POSIX PTY, orkiestrację wyizolowanych kontenerów Docker oraz webowy panel administracyjny.

## Wymagania

- System operacyjny Windows, Linux lub macOS z zainstalowanym środowiskiem Docker i Docker Compose.

## Uruchomienie

W katalogu `Server/`:

```bash
docker compose up -d --build
```

### Tryb czystego uruchomienia

```bash
docker compose build --no-cache && docker compose up -d --force-recreate
```

---

### Dostępne usługi

Po uruchomieniu serwera dostępne są dwa punkty wejścia:

- **Brama terminalowa TCP:** port `51234` (dla aplikacji klienckich Java).
- **Webowy Panel Administracyjny:** `http://localhost:5001` (zarządzanie kontami, grupami, import CSV, podgląd logów i monitorowanie sesji).

---

### Zatrzymanie serwera i czyszczenie

Aby zatrzymać serwer:

```bash
docker compose down
```

Podczas zatrzymywania serwer automatycznie usuwa wszystkie dynamicznie utworzone kontenery sesyjne studentów.

Aby dodatkowo usunąć wszystkie wolumeny danych:

```bash
docker compose down -v
```

## Struktura katalogów

- `server.py` – proces główny bramy terminalowej TCP.
- `web_panel/` – moduł webowego panelu administracyjnego:
  - `admin_panel.py` – backend panelu administracyjnego (Flask).
  - `admin_panel.html` – główny szablon panelu administracyjnego.
  - `login.html` – szablon strony logowania administratora.
- `images/` – konfiguracje i skrypty inicjalizacyjne środowisk bazodanowych.
- `input/` – pliki CSV z listami studentów do automatycznego importu (`Nazwisko;Imie`).
- `users.json` – baza użytkowników, haseł i przypisanych grup.
- `server_config.json` – definicja dostępnych środowisk laboratoryjnych.
- `commands/` – rejestr historii komend sesji (`.cmds`).
- `logs/` – logi operacji serwera i sesji użytkowników.
