#!/usr/bin/env bash
set -euo pipefail
# Watcher buduje JAR przy zmianach w src/ lub pom.xml.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

if command -v fswatch >/dev/null 2>&1; then
  echo "Używam fswatch do monitorowania zmian..."
  fswatch -o src pom.xml | while read -r _; do
    echo "Zmieniono pliki — buduję..."
    ./build_jar.sh
  done
else
  echo "fswatch nieznalezione — używam prostego loopa z poll (co 2s)."
  last=$(find src pom.xml -type f -print0 | xargs -0 stat -f "%m %N" | sort -n | tail -n1 | cut -d' ' -f1)
  while true; do
    sleep 2
    cur=$(find src pom.xml -type f -print0 | xargs -0 stat -f "%m %N" | sort -n | tail -n1 | cut -d' ' -f1)
    if [ "$cur" != "$last" ]; then
      echo "Zmiana wykryta — buduję..."
      ./build_jar.sh
      last=$cur
    fi
  done
fi