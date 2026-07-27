# Terminal Gateway Client

Klient emulatora terminala oparty na technologii JavaFX oraz bibliotece JediTerm. Aplikacja służy jako interfejs graficzny do łączenia się z bramą terminalową (Gateway) przez protokół TCP.

## Funkcje
- **Wybór konfiguracji:** Możliwość wyboru predefiniowanych sesji (np. Bazy danych, Terminal Linux).
- **Zintegrowany Terminal:** W pełni funkcjonalny emulator terminala dzięki integracji JediTerm ze SwingNode.
- **Bezpieczeństwo:** Autoryzacja za pomocą handshake'u JSON przed otwarciem sesji TTY.
- **Obsługa sesji:** Możliwość restartowania sesji bez konieczności ponownego uruchamiania aplikacji.

## Użyte technologie
- **Java 17+** (17 lub nowsza)
- **JavaFX 20.0.2:** Interfejs użytkownika.
- **JediTerm (3.61):** Rdzeń emulatora terminala (JetBrains).
- **Maven:** Zarządzanie projektem i zależnościami.
- **JSON (org.json):** Protokół komunikacyjny z serwerem.
- **Docker:** Strona serwera z zainstalowanym MySQL.

### Wymagania
- JRE / JDK 17+ na komputerze uruchamiającym klienta.
- Docker (do uruchomienia środowiska serwerowego).

---

## Uruchamianie serwera i klienta

### 1. Uruchomienie serwera (Docker)

Przejdź do katalogu `Server` i uruchom kontenery:

```bash
cd Server
docker compose up --build -d
```

---

## Budowanie i uruchamianie klienta (Plik JAR)

Wygenerowany plik JAR zawiera wszystkie zależności oraz biblioteki natywne JavaFX dla systemów:
- **Windows** (x86_64)
- **Linux** (x86_64 oraz **ARM64 / Raspberry Pi**)
- **macOS** (x86_64 oraz Apple Silicon arm64)

Plik JAR jest w pełni samowystarczalny i można go uruchomić na dowolnym komputerze / Raspberry Pi z zainstalowanym **Java 17+** (nie wymaga Mavena ani zewnętrznych instalacji JavaFX).

### 1. Budowanie pliku JAR

W katalogu `Client/` uruchom skrypt budujący:

- **Linux / macOS:**
  ```bash
  cd Client
  ./build_jar.sh
  ```
- **Windows:**
  ```cmd
  cd Client
  build_jar.bat
  ```
- **Alternatywnie (Maven Wrapper):**
  ```bash
  cd Client
  ./mvnw clean package
  ```

Gotowa paczka JAR zostanie zapisana w katalogu `Client/dist/TerminalClient.jar` (oraz w `Client/target/TerminalClient.jar`).

### 2. Uruchamianie pliku JAR

Plik `TerminalClient.jar` można przenieść na dowolny komputer z zainstalowaną Javą 17+ i uruchomić w konsoli:

```bash
java -jar TerminalClient.jar
```

Lub z poziomu katalogu `Client/`:

```bash
java -jar dist/TerminalClient.jar
```

Na systemach Linux / macOS w katalogu `dist/` znajduje się również skrypt pomocniczy:

```bash
./dist/run.sh
```
