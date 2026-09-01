# Klient Terminala (Client)

Aplikacja kliencka w języku Java (JavaFX / JediTerm) umożliwiająca studentom łączenie się z bramą terminalową i pracę w wyizolowanych środowiskach bazodanowych.

## Wymagania

- Java Runtime Environment (JRE) lub Java Development Kit (JDK) w wersji 17 lub nowszej.
- Narzędzie Maven (w przypadku samodzielnego budowania ze źródeł).

## Uruchomienie

### 1. Uruchomienie gotowego pliku JAR

W katalogu `Client/`:

```bash
java -jar dist/TerminalClient.jar
```

Aplikacja uruchamia się bez konieczności wcześniejszej instalacji i nie wymaga uprawnień administratora.

## Budowanie ze źródeł

Projekt korzysta z narzędzia Maven. Aby zbudować samowystarczalny plik Universal Fat JAR zawierający wszystkie biblioteki graficzne:

- **System Linux / macOS:**
  ```bash
  ./build_jar.sh
  ```
- **System Windows:**
  ```cmd
  build_jar.bat
  ```

Wynikowy plik `TerminalClient.jar` zostanie wygenerowany w katalogu `dist/`.

## Konfiguracja połączenia

Domyślnie klient łączy się z adresem `localhost:51234`. W przypadku pracy w pracowni komputerowej należy w oknie logowania podać adres IP maszyny serwerowej, port `51234` oraz poświadczenia użytkownika (login i hasło otrzymane od prowadzącego).
