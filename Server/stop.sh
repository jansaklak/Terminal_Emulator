#!/usr/bin/env bash
set -e

# Przejdź do katalogu skryptu
cd "$(dirname "$0")"

echo "[Server] Zatrzymywanie kontenerów..."
docker compose down

echo "[Server] Gotowe."
