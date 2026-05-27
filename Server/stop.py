#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_docker_compose_cmd():
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutilr:
        return ["docker-compose"]
    return None


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)

    docker_cmd = find_docker_compose_cmd()
    if not docker_cmd:
        print("ERROR: Docker not found in PATH. Install Docker or add to PATH.")
        return 2

    print("[Server] Zatrzymywanie kontenerów...")
    try:
        subprocess.check_call(docker_cmd + ["down"])
    except subprocess.CalledProcessError as exc:
        print(f"[Server] Błąd podczas zatrzymywania kontenerów: {exc}")
        return exc.returncode

    print("[Server] Gotowe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())