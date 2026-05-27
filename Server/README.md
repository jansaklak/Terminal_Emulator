## Pliki

- `server.py` - główny proces serwera, który obsługuje logowanie i uruchamianie sesji kontenerów.
- `admin_panel.py` - panel administracyjny uruchamiany jako osobny kontener.
- `server_config.json` - konfiguracja dostępnych środowisk i poleceń `docker run`.
- `users.json` - baza użytkowników, haseł i grup dostępu.
- `online.json` - aktualny stan aktywnych sesji.
- `docker-compose.yml` - definicja usług uruchamianych lokalnie przez Dockera.
- `Dockerfile` - obraz dla komponentów Pythona w katalogu `Server`.
- `run.py` - skrypt startowy uruchamiający serwer.
- `stop.py` - skrypt zatrzymujący uruchomione procesy lub kontenery.

## Katalogi

- `Shared/` - pliki współdzielone dla środowisk
- `input/` - pliki wejściowe CSV z listami dla poszczególnych grup.
- `logs/` - logi działania serwera oraz logi sesji użytkowników.

