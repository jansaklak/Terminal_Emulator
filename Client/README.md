# Terminal Gateway – Klient (Client)

Klient bramy terminalowej (Terminal Gateway Client) to aplikacja desktopowa napisana w języku Java (JavaFX + JediTerm), służąca jako emulator terminala i interfejs połączeniowy z serwerem Terminal Gateway przez protokół TCP.

---

## Główne Funkcjonalności

### 1. Ekran Logowania i Konfiguracji Połączenia (`LoginScreen.java`)
- **Autoryzacja**: Podawanie adresu serwera, portu, loginu oraz hasła z weryfikacją handshake JSON.
- **Wybór Motywu**: Wybór motywu aplikacji (Ciemny / Jasny).
- **Ekran Wyboru Środowiska**:
  - Przeglądanie i uruchamianie powierzonych środowisk kontenerowych (np. Bazy Pociągi MySQL, Bazy Pociągi SQLite).
  - **Przycisk `Wczytaj plik .cmds`**:
    - Umożliwia wybór pliku z nagraną sesją poleceń (`.cmds`).
    - **Automatyczne rozpoznawanie obrazu**: System analizuje nazwę pliku `.cmds` oraz jego zawartość, dopasowując automatycznie właściwe środowisko.
    - **Reset kontenera**: Przed odtworzeniem poleceń wysyłana jest flaga resetu kontenera (`reset: true`), co gwarantuje uruchomienie komend na czystym kontenerze.

### 2. Emulator Terminala (`TerminalApp.java`)
- **Integracja z JediTerm**: Wydajny i zaawansowany emulator TTY zintegrowany ze SwingNode w JavaFX.
- **Pasek Narzędzi Terminala**:
  - `Clear` – czyszczenie zawartości ekranu terminala.
  - `⟳ Reset` – zresetowanie stanu sesji i kontenera.
  - `-` / `+` – płynna zmiana rozmiaru czcionki.
  - `Save cmds` – zapis bieżącej sesji poleceń do pliku `.cmds`.

### 3. Łącznik TTY TCP (`SocketTtyConnector.java`)
- Asynchroniczne przekazywanie danych wejścia/wyjścia pomiędzy biblioteką JediTerm a gniazdem TCP serwera.
- Filtrowanie i obsługa ramek kontrolnych w formacie JSON (reset, clear, nagrywanie i wczytywanie komend).

---

## Wymagania i Użyte Technologie

- **Java 17+** (JDK/JRE 17 lub nowsza)
- **JavaFX 20.0.2** (UI)
- **JediTerm 3.61** (JetBrains Terminal Emulator)
- **org.json** (Protokół komunikacji JSON)
- **Maven** (Zarządzanie zależnościami)

---

## Budowanie Pliku JAR (Fat JAR / Universal Binary)

Wygenerowana paczka `TerminalClient.jar` jest samowystarczalna i zawiera zintegrowane biblioteki natywne JavaFX dla systemów:
- **macOS** (Universal Binary: x86_64 + Apple Silicon arm64)
- **Linux** (x86_64 oraz ARM64 / Raspberry Pi)
- **Windows** (x86_64)

### 1. Budowanie Skryptem

W katalogu `Client/`:

- **macOS / Linux**:
  ```bash
  ./build_jar.sh
  ```
- **Windows**:
  ```cmd
  build_jar.bat
  ```

### 2. Budowanie przez Maven

```bash
./mvnw clean package
```

Gotowa paczka zapisuje się w:
- `Client/dist/TerminalClient.jar`
- `Client/target/TerminalClient.jar`

---

## Uruchamianie Klienta

Plik `TerminalClient.jar` można przenieść i uruchomić na dowolnym komputerze z zainstalowaną Javą 17+:

```bash
java -jar dist/TerminalClient.jar
```

Na systemach macOS / Linux można również użyć skryptu pomocniczego:

```bash
./dist/run.sh
```

---

## Struktura Kodu Źródłowego (`src/main/java/com/example/terminalapp/`)

| Plik | Opis |
| :--- | :--- |
| `Launcher.java` | Główny punkt wejścia Java (ustawia cachowanie JavaFX i uruchamia TerminalApp). |
| `TerminalApp.java` | Klasa aplikacji JavaFX, buduje okno terminala JediTerm i pasek narzędzi. |
| `LoginScreen.java` | Ekran logowania, wyboru środowiska oraz automatycznego wczytywania `.cmds`. |
| `SocketTtyConnector.java` | Łącznik TTY komunikujący się z serwerem przez TCP socket i JSON control frames. |
