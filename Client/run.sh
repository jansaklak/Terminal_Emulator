#!/usr/bin/env bash
set -euo pipefail

detect_jdk_home() {
  local os_name="$1"
  local jdk_home=""

  if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]]; then
    jdk_home="$JAVA_HOME"
  elif [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME" ]]; then
    jdk_home="$(cd "$(dirname "$JAVA_HOME")/.." && pwd)"
  elif [[ "$os_name" == "Darwin" ]]; then
    local brew_jdk="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    if [[ -d "$brew_jdk" ]]; then
      jdk_home="$brew_jdk"
    elif command -v /usr/libexec/java_home >/dev/null 2>&1; then
      jdk_home="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
    fi
  else
    local java_bin=""
    if command -v java >/dev/null 2>&1; then
      java_bin="$(command -v java)"
      java_bin="$(readlink -f "$java_bin" 2>/dev/null || true)"
      if [[ -n "$java_bin" ]]; then
        jdk_home="$(cd "$(dirname "$java_bin")/.." && pwd)"
      fi
    fi
  fi

  if [[ -n "$jdk_home" ]]; then
    local actual_ver
    actual_ver="$($jdk_home/bin/java -version 2>&1 | head -n 1 || true)"
    if [[ "$actual_ver" =~ "version \"17" ]]; then
      printf '%s\n' "$jdk_home"
      return 0
    fi
  fi

  return 1
}

OS_NAME="$(uname -s)"
JDK_HOME="$(detect_jdk_home "$OS_NAME" || true)"

if [[ "$JDK_HOME" == "" ]]; then
  echo "ERROR: Nie znaleziono JDK 17. Zainstaluj JDK 17 albo ustaw JAVA_HOME na JDK 17." >&2
    exit 1
fi

export JAVA_HOME="$JDK_HOME"

JAVA_VERSION="$("$JAVA_HOME/bin/java" -version 2>&1 | head -n 1 || true)"
echo "[run.sh] Using JAVA_HOME=$JAVA_HOME ($JAVA_VERSION)"

./mvnw -U -q -Dmaven.test.skip=true javafx:run
