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

echo "Buduję projekt Maven (pomiń testy)..."
./mvnw -DskipTests package

if [ ! -f "target/TerminalClient.jar" ]; then
  echo "Nie znaleziono pliku target/TerminalClient.jar — sprawdź wynik mvn package"
  exit 1
fi

JFX_VER=$(grep -oE "<javafx.version>[^<]+" pom.xml | sed 's/<javafx.version>//' || echo "20.0.2")

# Tworzenie Universal Binaries (fat dylib: x86_64 + arm64) dla macOS, jeśli lipo jest dostępne
if command -v lipo >/dev/null 2>&1; then
  echo "Łączenie bibliotek macOS (.dylib) w architekturę uniwersalną (x86_64 + arm64)..."
  MAC_X86_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-mac.jar" 2>/dev/null | head -n1 || true)
  MAC_ARM_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-mac-aarch64.jar" 2>/dev/null | head -n1 || true)

  if [ -n "$MAC_X86_JAR" ] && [ -n "$MAC_ARM_JAR" ]; then
    TMP_DIR=$(mktemp -d)
    mkdir -p "$TMP_DIR/x86" "$TMP_DIR/arm" "$TMP_DIR/universal"
    unzip -q "$MAC_X86_JAR" "*.dylib" -d "$TMP_DIR/x86" 2>/dev/null || true
    unzip -q "$MAC_ARM_JAR" "*.dylib" -d "$TMP_DIR/arm" 2>/dev/null || true

    for f in "$TMP_DIR/x86"/*.dylib; do
      [ -f "$f" ] || continue
      b=$(basename "$f")
      if [ -f "$TMP_DIR/arm/$b" ]; then
        lipo -create "$TMP_DIR/x86/$b" "$TMP_DIR/arm/$b" -output "$TMP_DIR/universal/$b"
      fi
    done

    if ls "$TMP_DIR/universal"/*.dylib >/dev/null 2>&1; then
      (cd "$TMP_DIR/universal" && jar uf "$HERE/target/TerminalClient.jar" *.dylib)
    fi
    rm -rf "$TMP_DIR"
  fi
fi

# Pakowanie bibliotek Linux ARM64 (aarch64) do katalogu aarch64/ wewnątrz JAR
LINUX_ARM_JAR=$(find .m2/repository -name "javafx-graphics-${JFX_VER}-linux-aarch64.jar" 2>/dev/null | head -n1 || true)
if [ -n "$LINUX_ARM_JAR" ]; then
  echo "Pakowanie bibliotek Linux ARM64 (aarch64) do katalogu aarch64/ w JAR..."
  TMP_DIR=$(mktemp -d)
  mkdir -p "$TMP_DIR/aarch64"
  unzip -q "$LINUX_ARM_JAR" "*.so" -d "$TMP_DIR/aarch64" 2>/dev/null || true
  if ls "$TMP_DIR/aarch64"/*.so >/dev/null 2>&1; then
    (cd "$TMP_DIR" && jar uf "$HERE/target/TerminalClient.jar" aarch64/*.so)
  fi
  rm -rf "$TMP_DIR"
fi

mkdir -p dist
cp target/TerminalClient.jar dist/TerminalClient.jar
echo "Zbudowano i skopiowano: dist/TerminalClient.jar"

cat > dist/run.sh <<'EOF'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
java -jar "$HERE/TerminalClient.jar" "$@"
EOF
chmod +x dist/run.sh || true

echo "Gotowe. Uruchomienie:"
echo "  java -jar dist/TerminalClient.jar"
echo "  lub: ./dist/run.sh"