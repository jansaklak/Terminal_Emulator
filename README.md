# Aplikacja Rozproszona do Prowadzenia Grupowych Zajęć z Baz Danych

Rozproszony system dydaktyczny umożliwiający prowadzenie zajęć laboratoryjnych z baz danych w architekturze klient-serwer. System zapewnia każdemu studentowi w pełni wyizolowane środowisko bazodanowe w kontenerze Docker z dostępem przez dedykowany emulator terminala, a prowadzącemu udostępnia webowy panel administracyjny do zarządzania użytkownikami i audytu sesji.

## Architektura projektu

Projekt składa się z dwóch głównych modułów:

- `Server/` – Serwer bramy terminalowej TCP (Python / Docker) oraz webowy panel administracyjny Flask.
- `Client/` – Wieloplatformowa aplikacja kliencka (Java 17 / JavaFX / JediTerm).

## Szybki start

### 1. Uruchomienie serwera

Wymagania: Docker oraz Docker Compose.

```bash
cd Server
docker compose up -d --build
```

- Brama terminalowa TCP nasłuchuje na porcie `51234`.
- Panel administracyjny jest dostępny pod adresem: `http://localhost:5001`.

### 2. Uruchomienie klienta

Wymagania: Java 17+ (JRE lub JDK).

```bash
cd Client
java -jar dist/TerminalClient.jar
```

W oknie logowania należy podać adres serwera (`localhost` lub IP w sieci lokalnej), port `51234` oraz poświadczenia użytkownika.

### 3. Zatrzymanie systemu

```bash
cd Server
docker compose down
```

## Szczegółowa dokumentacja modułów

Szczegółowe instrukcje konfiguracji i budowania znajdują się w dedykowanych plikach:
- `Server/README.md` – konfiguracja środowisk bazodanowych, import użytkowników i REST API.
- `Client/README.md` – kompilacja ze źródeł Maven i tworzenie paczek dystrybucyjnych Universal JAR.
