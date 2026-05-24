# Terminal Gateway Client

Klient emulatora terminala oparty na technologii JavaFX oraz bibliotece JediTerm. Aplikacja służy jako interfejs graficzny do łączenia się z bramą terminalową (Gateway) przez protokół TCP.

## Funkcje
- **Wybór konfiguracji:** Możliwość wyboru predefiniowanych sesji (np. Bazy danych, Terminal Linux).
- **Zintegrowany Terminal:** W pełni funkcjonalny emulator terminala dzięki integracji JediTerm ze SwingNode.
- **Bezpieczeństwo:** Autoryzacja za pomocą handshake'u JSON przed otwarciem sesji TTY.
- **Obsługa sesji:** Możliwość restartowania sesji bez konieczności ponownego uruchamiania aplikacji.

## Użyte technologie
- **Java 17+**
- **JavaFX 17.0.8:** Interfejs użytkownika.
- **JediTerm (2.65):** Rdzeń emulatora terminala (JetBrains).
- **Maven:** Zarządzanie projektem i zależnościami.
- **JSON (org.json):** Protokół komunikacyjny z serwerem.
- **Docker** Strona serwera z zainstalowanym MySQL

## Struktura Projektu
```text
Client/src/main/java/com/example/terminalapp/
├── Launcher.java             # Klasa startowa (obejście problemów z modułami JavaFX)
├── TerminalApp.java          # Główna klasa aplikacji JavaFX, zarządza oknami
├── LoginScreen.java          # Logika ekranu logowania i handshake'u
└── SocketTtyConnector.java   # Implementacja TtyConnector dla strumieni sieciowych
```

## Uruchomienie

### Wymagania
- JDK 17+.
- Docker.
- `run.sh` do uruchamiania klienta.

### Kompilacja i start
Aby uruchomić projekt, najpierw startuj serwer, a potem klienta przez `run.sh`:

```bash
cd ./Server
docker compose up --build -d
cd ../Client
./run.sh
```

Nie uruchamiaj klienta bezpośrednio przez `./mvnw` — używaj `./run.sh`, bo automatycznie dobiera odpowiednie `JAVA_HOME` i wersję Javy.
