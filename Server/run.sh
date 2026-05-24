#!/usr/bin/env bash
set -e

# Przejdź do katalogu skryptu
cd "$(dirname "$0")"

echo "[Server] Uruchamianie kontenerów..."
# PROJECT_PATH jest potrzebny dla poprawnego montowania wolumenów przez serwer TCP
export PROJECT_PATH=$(pwd)

docker compose up -d --build

echo "[Server] Usługi uruchomione:"
echo "  - Panel Admina: http://localhost:5001"
echo "  - Brama Terminalowa: localhost:51234"
docker compose ps
