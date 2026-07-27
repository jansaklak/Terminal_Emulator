# Terminal Gateway – Serwer (Server)

Serwer bramy terminalowej (Terminal Gateway Server) to komponent po stronie backendu, który odpowiada za autoryzację użytkowników, zarządzanie izolowanymi kontenerami Docker oraz udostępnia zaawansowany **Panel Administracyjny Web**.

---

## Główne Funkcjonalności

### 1. Brama Terminalowa TCP (`server.py`)
- **Izolowane sesje kontenerowe**: Dla każdego użytkownika tworzony jest dedykowany kontener Docker na żądanie.
- **Komunikacja TTY**: Przekierowywanie strumienia TTY w czasie rzeczywistym przez gniazdo TCP (port `51234`).
- **Nagrywanie i odtwarzanie komend (`.cmds`)**: Surowe logowanie wejścia/wyjścia umożliwiające idealne odtworzenie przebiegu sesji.
- **Obsługa komunikatów kontrolnych**: Dynamiczny reset środowiska (`reset_session`), czyszczenie ekranu (`clear_screen`), zapis i wczytywanie komend (`load_commands`).

### 2. Panel Administracyjny Web (`admin_panel.py` & `admin_panel.html`)
Dostępny pod adresem: **`http://localhost:5001`**
- **Zarządzanie Użytkownikami**: Dodawanie kont, edycja danych, zmiana grup, usuwanie oraz resetowanie haseł z wygenerowaniem nowego klucza.
- **Grupowy Import CSV**: Masowe tworzenie użytkowników z pliku CSV w formacie `Nazwisko;Imię`.
- **Zbiorcze Operacje (Bulk Actions)**: Zaznaczanie użytkowników po przefiltrowaniu (grupa, status online/offline, wyszukiwarka) z opcją:
  - **Zbiorczego usuwania** zaznaczonych kont.
  - **Zbiorczego dodawania** zaznaczonych użytkowników do grupy.
- **Zarządzanie Logami**:
  - Podgląd na żywo plików logów serwera.
  - **Filtrowanie logów po użytkowniku**.
  - Przycisk **`Logi`** na liście użytkowników – natychmiastowe przejście do odfiltrowanych logów wybranego konta i otwarcie najnowszego wpisu.
  - Przycisk **`Pobierz plik cmds`** – możliwość pobrania surowego pliku komend `.cmds` skojarzonego z danym plikiem logu.
- **Motyw (Dark/Light Mode)**: Przełącznik motywu w nagłówku z automatycznym zapamiętywaniem preferencji w `localStorage`.

---

## 📁 Struktura Plików i Katalogów

| Plik / Katalog | Opis |
| :--- | :--- |
| `server.py` | Główny proces serwera TCP (brama terminalowa). |
| `admin_panel.py` | Backend panelu administracyjnego w technologii Flask. |
| `templates/admin_panel.html` | Szablon HTML/CSS/JS panelu administracyjnego z Ciemnym Motywem. |
| `server_config.json` | Konfiguracja dostępnych środowisk (obrazów Docker, uprawnień i komend). |
| `users.json` | Baza użytkowników, haseł, nazw wyświetlanych i grup. |
| `online.json` | Lista i stan obecnie aktywnych połączeń. |
| `docker-compose.yml` | Konteneryzacja serwera i panelu administracyjnego. |
| `Dockerfile` | Definicja obrazu dla serwera i panelu administracyjnego. |
| `run.py` / `stop.py` | Skrypty do uruchamiania i zatrzymywania procesów serwera lokalnie. |
| `commands/` | Przechowuje zapisane pliki komend sesji (`.cmds`) pogrupowane wg środowisk. |
| `logs/` | Logi działania serwera oraz podgląd logów użytkowników. |
| `images/` | Pliki pomocnicze i konfiguracje obrazów Docker. |
| `Shared/` | Pliki i skrypty montowane we wspólnych wolumenach kontenerów. |

---

## REST API Panelu Administracyjnego

| Metoda | Endpoint | Opis |
| :--- | :--- | :--- |
| `GET` | `/api/users` | Pobiera listę wszystkich użytkowników. |
| `POST` | `/api/users` | Dodaje nowego użytkownika. |
| `PUT` | `/api/users/<username>` | Aktualizuje dane użytkownika. |
| `DELETE` | `/api/users/<username>` | Usuwa podanego użytkownika. |
| `POST` | `/api/users/<username>/reset-password` | Resetuje hasło użytkownika. |
| `POST` | `/api/users/bulk-delete` | Masowe usuwanie listy użytkowników. |
| `POST` | `/api/users/bulk-add-group` | Masowe dodawanie listy użytkowników do grupy. |
| `POST` | `/api/import` | Grupowy import użytkowników z pliku CSV (`Nazwisko;Imię`). |
| `GET` | `/api/logs` | Zwraca listę dostępnych plików logów. |
| `GET` | `/api/logs/<filename>` | Zwraca zawartość wskazanego pliku logu. |
| `GET` | `/api/logs/<filename>/download-cmds` | Pobiera odpowiedni plik komend `.cmds` dla wskazanego logu. |
| `GET` | `/api/online` | Pobiera listę obecnie połączonych użytkowników. |

---

## Uruchamianie Serwera

### Uruchomienie przez Docker Compose (zalecane)

W katalogu `Server/`:

```bash
docker compose up --build -d
```

Po uruchomieniu:
- **Brama TCP**: Nasłuchuje na porcie `51234`.
- **Panel Administracyjny**: Dostępny pod adresem `http://localhost:5001`.

### Uruchomienie lokalne (Python 3.10+)

1. Zainstaluj zależności:
   ```bash
   pip install flask
   ```
2. Uruchom serwer i panel:
   ```bash
   python3 run.py
   ```
3. Aby zatrzymać:
   ```bash
   python3 stop.py
   ```
