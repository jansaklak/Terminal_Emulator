#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# Sanitize JAVA_HOME if set incorrectly (e.g. pointing to bin/java instead of JDK root)
if [ -n "${JAVA_HOME:-}" ]; then
  JAVA_HOME="${JAVA_HOME%/bin/java}"
  JAVA_HOME="${JAVA_HOME%/bin}"
  export JAVA_HOME
fi

echo "=========================================================="
echo "  Budowanie Terminal Gateway Client (Wieloplatformowy)   "
echo "=========================================================="

echo "[1/5] Kompilacja i pakowanie Maven..."
./mvnw -DskipTests package

if [ ! -f "target/TerminalClient.jar" ]; then
  echo "BŁĄD: Nie znaleziono pliku target/TerminalClient.jar — sprawdź błędy Maven."
  exit 1
fi

JFX_VER=$(grep -oE "<javafx.version>[^<]+" pom.xml | head -n1 | sed 's/<javafx.version>//' || echo "20.0.2")

echo "[2/5] Przygotowywanie bibliotek natywnych dla macOS (Universal Binary: x86_64 + arm64)..."
MAC_X86_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-mac.jar" 2>/dev/null | head -n1 || true)
MAC_ARM_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-mac-aarch64.jar" 2>/dev/null | head -n1 || true)
WIN_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-win.jar" 2>/dev/null | head -n1 || true)
LINUX_X86_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-linux.jar" 2>/dev/null | head -n1 || true)
LINUX_ARM_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-linux-aarch64.jar" 2>/dev/null | head -n1 || true)

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/mac_x86" "$TMP_DIR/mac_arm" "$TMP_DIR/mac_universal" "$TMP_DIR/linux_x86" "$TMP_DIR/linux_arm" "$TMP_DIR/win"

# 1. macOS Universal dylibs
if [ -n "$MAC_X86_JAR" ] && [ -n "$MAC_ARM_JAR" ]; then
  unzip -q "$MAC_X86_JAR" "*.dylib" -d "$TMP_DIR/mac_x86" 2>/dev/null || true
  unzip -q "$MAC_ARM_JAR" "*.dylib" -d "$TMP_DIR/mac_arm" 2>/dev/null || true

  if command -v lipo >/dev/null 2>&1; then
    for f in "$TMP_DIR/mac_x86"/*.dylib; do
      [ -f "$f" ] || continue
      b=$(basename "$f")
      if [ -f "$TMP_DIR/mac_arm/$b" ]; then
        lipo -create "$TMP_DIR/mac_x86/$b" "$TMP_DIR/mac_arm/$b" -output "$TMP_DIR/mac_universal/$b"
      else
        cp "$f" "$TMP_DIR/mac_universal/$b"
      fi
    done
  else
    echo "Uwaga: Narzędzie 'lipo' nie jest dostępne (system non-macOS). Używam bibliotek z bieżącego środowiska."
    cp "$TMP_DIR/mac_arm"/*.dylib "$TMP_DIR/mac_universal/" 2>/dev/null || cp "$TMP_DIR/mac_x86"/*.dylib "$TMP_DIR/mac_universal/" 2>/dev/null || true
  fi
fi

# 2. Linux x86 & ARM .so
if [ -n "$LINUX_X86_JAR" ]; then
  unzip -q "$LINUX_X86_JAR" "*.so" -d "$TMP_DIR/linux_x86" 2>/dev/null || true
fi
if [ -n "$LINUX_ARM_JAR" ]; then
  unzip -q "$LINUX_ARM_JAR" "*.so" -d "$TMP_DIR/linux_arm" 2>/dev/null || true
fi

echo "[3/5] Generowanie paczek JAR w katalogu dist/..."
mkdir -p dist

# A) Główny uniwersalny JAR (TerminalClient.jar)
cp target/TerminalClient.jar dist/TerminalClient.jar
if ls "$TMP_DIR/mac_universal"/*.dylib >/dev/null 2>&1; then
  (cd "$TMP_DIR/mac_universal" && jar uf "$HERE/dist/TerminalClient.jar" *.dylib)
fi
if ls "$TMP_DIR/linux_x86"/*.so >/dev/null 2>&1; then
  (cd "$TMP_DIR/linux_x86" && jar uf "$HERE/dist/TerminalClient.jar" *.so)
fi
mkdir -p "$TMP_DIR/aarch64"
if ls "$TMP_DIR/linux_arm"/*.so >/dev/null 2>&1; then
  cp "$TMP_DIR/linux_arm"/*.so "$TMP_DIR/aarch64/"
  (cd "$TMP_DIR" && jar uf "$HERE/dist/TerminalClient.jar" aarch64/*.so)
fi

# B) Dedykowany JAR dla Windows (TerminalClient-windows.jar)
cp target/TerminalClient.jar dist/TerminalClient-windows.jar

# C) Dedykowany JAR dla macOS Universal (TerminalClient-mac.jar)
cp target/TerminalClient.jar dist/TerminalClient-mac.jar
if ls "$TMP_DIR/mac_universal"/*.dylib >/dev/null 2>&1; then
  (cd "$TMP_DIR/mac_universal" && jar uf "$HERE/dist/TerminalClient-mac.jar" *.dylib)
fi

# D) Dedykowany JAR dla Linux x86_64 (TerminalClient-linux-x64.jar)
cp target/TerminalClient.jar dist/TerminalClient-linux-x64.jar
if ls "$TMP_DIR/linux_x86"/*.so >/dev/null 2>&1; then
  (cd "$TMP_DIR/linux_x86" && jar uf "$HERE/dist/TerminalClient-linux-x64.jar" *.so)
fi

# E) Dedykowany JAR dla Linux ARM64 / Raspberry Pi (TerminalClient-linux-arm64.jar)
cp target/TerminalClient.jar dist/TerminalClient-linux-arm64.jar
if ls "$TMP_DIR/linux_arm"/*.so >/dev/null 2>&1; then
  (cd "$TMP_DIR/linux_arm" && jar uf "$HERE/dist/TerminalClient-linux-arm64.jar" *.so)
fi

echo "[4/5] Generowanie skryptów uruchomieniowych w dist/..."

# Skrypt uniwersalny / terminalowy: run.sh
cat > dist/run.sh <<'EOF'
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
EOF
chmod +x dist/run.sh || true

# Skrypt macOS (dwuklik w Finderze): run-mac.command
cat > dist/run-mac.command <<'EOF'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

JAR="$HERE/TerminalClient.jar"
if [ ! -f "$JAR" ]; then
  JAR="$HERE/TerminalClient-mac.jar"
fi

echo "Uruchamianie Terminal Gateway Client..."
java --enable-native-access=ALL-UNNAMED -jar "$JAR"
EOF
chmod +x dist/run-mac.command || true

# Skrypt Linux: run-linux.sh
cat > dist/run-linux.sh <<'EOF'
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
EOF
chmod +x dist/run-linux.sh || true

# Skrypt Windows konsola: run-windows.bat
cat > dist/run-windows.bat <<'EOF'
@echo off
setlocal
cd /d "%~dp0"
set "JAR=TerminalClient.jar"
if not exist "%JAR%" set "JAR=TerminalClient-windows.jar"

echo Uruchamianie Terminal Gateway Client...
java --enable-native-access=ALL-UNNAMED -jar "%JAR%" %*
EOF

# Skrypt Windows GUI w tle (bez czarnego okna cmd): run-windows-gui.bat
cat > dist/run-windows-gui.bat <<'EOF'
@echo off
setlocal
cd /d "%~dp0"
set "JAR=TerminalClient.jar"
if not exist "%JAR%" set "JAR=TerminalClient-windows.jar"

start "" javaw --enable-native-access=ALL-UNNAMED -jar "%JAR%" %*
EOF

# Skrót na pulpit Linux: TerminalClient.desktop
cat > dist/TerminalClient.desktop <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Terminal Gateway Client
Comment=Desktopowy klient emulatora terminala z obsługą sesji i kontenerów
Exec=bash -c "cd $(dirname %k) && ./run-linux.sh"
Terminal=false
Categories=Utility;Development;
EOF
chmod +x dist/TerminalClient.desktop || true

echo "[5/5] Gotowe! Wygenerowane pliki w katalogu dist/:"
ls -lh dist/

echo "=========================================================="
echo "Instrukcja szybkiego uruchomienia:"
echo "  • macOS:   Podwójne kliknięcie na dist/run-mac.command lub 'java -jar dist/TerminalClient.jar'"
echo "  • Windows: Podwójne kliknięcie na dist/run-windows-gui.bat lub 'java -jar dist\\TerminalClient.jar'"
echo "  • Linux:   Uruchomienie ./dist/run-linux.sh lub 'java -jar dist/TerminalClient.jar'"
echo "  • RPi/ARM: Uruchomienie 'java -jar dist/TerminalClient-linux-arm64.jar'"
echo "=========================================================="