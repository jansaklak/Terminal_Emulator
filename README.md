# Terminal Gateway Client

Klient emulatora terminala oparty na technologii JavaFX oraz bibliotece JediTerm. Aplikacja służy jako interfejs graficzny do łączenia się z bramą terminalową (Gateway) przez protokół TCP.

## Funkcje
- **Wybór konfiguracji:** Możliwość wyboru predefiniowanych sesji (np. Bazy danych, Terminal Linux).
- **Zintegrowany Terminal:** W pełni funkcjonalny emulator terminala dzięki integracji JediTerm ze SwingNode.
- **Bezpieczeństwo:** Autoryzacja za pomocą handshake'u JSON przed otwarciem sesji TTY.
- **Obsługa sesji:** Możliwość restartowania sesji bez konieczności ponownego uruchamiania aplikacji.

## Użyte technologie
- **Java 17+** (17 lub nowsza)
- **JavaFX 17.0.8:** Interfejs użytkownika.
- **JediTerm (2.65):** Rdzeń emulatora terminala (JetBrains).
- **Maven:** Zarządzanie projektem i zależnościami.
- **JSON (org.json):** Protokół komunikacyjny z serwerem.
- **Docker** Strona serwera z zainstalowanym MySQL

### Wymagania
- JDK 17+.
- Docker.
- `Client/run.py` do uruchamiania klienta.

### Kompilacja i start
Aby uruchomić projekt, najpierw startuj serwer, a potem klienta przez `run.py`:

```bash
cd ./Server
docker compose up --build -d
cd ../Client
python run.py
```

Aby otworzyć kilka okien klienta naraz:

```bash
python run.py --clients 10
```

