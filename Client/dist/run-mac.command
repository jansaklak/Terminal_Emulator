#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

JAR="$HERE/TerminalClient.jar"
if [ ! -f "$JAR" ]; then
  JAR="$HERE/TerminalClient-mac.jar"
fi

echo "Uruchamianie Terminal Gateway Client..."
java --enable-native-access=ALL-UNNAMED -jar "$JAR"
