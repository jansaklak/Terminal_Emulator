# Terminal Gateway Client

Klient emulatora terminala oparty na technologii JavaFX oraz bibliotece JediTerm. Aplikacja służy jako interfejs graficzny do łączenia się z bramą terminalową (Gateway) przez protokół TCP.

## Funkcje
- **Wybór konfiguracji:** Możliwość wyboru predefiniowanych sesji (np. Bazy danych, Terminal Linux).
- **Zintegrowany Terminal:** W pełni funkcjonalny emulator terminala dzięki integracji JediTerm ze SwingNode.
- **Bezpieczeństwo:** Autoryzacja za pomocą handshake'u JSON przed otwarciem sesji TTY.
- **Obsługa sesji:** Możliwość restartowania sesji bez konieczności ponownego uruchamiania aplikacji.

## Użyte technologie
- **Java 18+**
- **JavaFX 18:** Interfejs użytkownika.
- **JediTerm (2.65):** Rdzeń emulatora terminala (JetBrains).
- **Maven:** Zarządzanie projektem i zależnościami.
- **JSON (org.json):** Protokół komunikacyjny z serwerem.

## Struktura Projektu
```text
src/main/java/com/example/terminalapp/
├── Launcher.java             # Klasa startowa (obejście problemów z modułami JavaFX)
├── TerminalApp.java          # Główna klasa aplikacji JavaFX, zarządza oknami
├── LoginScreen.java          # Logika ekranu logowania i handshake'u
└── SocketTtyConnector.java   # Implementacja TtyConnector dla strumieni sieciowych
```

## Uruchomienie

### Wymagania
- JDK 18 lub nowsze.
- Maven (dołączony wrapper `mvnw` w projekcie).

### Kompilacja i start
Aby skompilować projekt i uruchomić aplikację, wykonaj poniższe polecenia w terminalu:

```powershell
# Pobranie zależności i kompilacja
./mvnw clean compile

# Uruchomienie serwera Docker

cd ./Server
docker compose up --build -d

# Uruchomienie aplikacji
cd ..
./mvnw javafx:run
```

