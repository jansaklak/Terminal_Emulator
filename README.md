# Aplikacja Rozproszona do Prowadzenia Grupowych Zajęć z Baz Danych

Rozproszony system dydaktyczny umożliwiający prowadzenie zajęć laboratoryjnych z baz danych w architekturze klient-serwer. System zapewnia każdemu studentowi w pełni wyizolowane środowisko bazodanowe w kontenerze Docker z dostępem przez dedykowany emulator terminala, a prowadzącemu udostępnia webowy panel administracyjny do zarządzania użytkownikami i audytu sesji.

## Architektura projektu

Projekt składa się z dwóch głównych modułów:

- `Server/` – Serwer bramy terminalowej TCP (Python / Docker) oraz webowy panel administracyjny Flask.
- `Client/` – Wieloplatformowa aplikacja kliencka (Java 17 / JavaFX / JediTerm).
