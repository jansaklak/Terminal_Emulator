#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
JVM_OPTS="--enable-native-access=ALL-UNNAMED"

if [ -f "$HERE/TerminalClient.jar" ]; then
  JAR="$HERE/TerminalClient.jar"
elif [ -f "$HERE/TerminalClient-mac.jar" ] && [[ "$OSTYPE" == "darwin"* ]]; then
  JAR="$HERE/TerminalClient-mac.jar"
elif [ -f "$HERE/TerminalClient-linux-arm64.jar" ] && [[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]]; then
  JAR="$HERE/TerminalClient-linux-arm64.jar"
elif [ -f "$HERE/TerminalClient-linux-x64.jar" ]; then
  JAR="$HERE/TerminalClient-linux-x64.jar"
else
  JAR="$(find "$HERE" -name "TerminalClient*.jar" | head -n1)"
fi

exec java $JVM_OPTS -jar "$JAR" "$@"
