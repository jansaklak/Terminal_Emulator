#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

ARCH="$(uname -m)"
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]] && [ -f "$HERE/TerminalClient-linux-arm64.jar" ]; then
  JAR="$HERE/TerminalClient-linux-arm64.jar"
elif [ -f "$HERE/TerminalClient.jar" ]; then
  JAR="$HERE/TerminalClient.jar"
else
  JAR="$HERE/TerminalClient-linux-x64.jar"
fi

exec java --enable-native-access=ALL-UNNAMED -jar "$JAR" "$@"
