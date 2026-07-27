#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_docker_compose_cmd():
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def run_cmd(command: list[str]) -> bool:
    try:
        subprocess.check_call(command)
        return True
    except subprocess.CalledProcessError:
        return False


def cleanup_lab_network() -> None:
    network_name = "lab-net"
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"network={network_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    if container_ids:
        print(f"[Server] Zatrzymywanie kontenerów w {network_name}: {' '.join(container_ids)}")
        run_cmd(["docker", "rm", "-f", *container_ids])

    print(f"[Server] Usuwanie sieci {network_name}...")
    subprocess.run(["docker", "network", "rm", network_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


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

    cleanup_lab_network()

    print("[Server] Gotowe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())