#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path


def find_docker_cmd():
    if shutil.which('docker'):
        return ['docker', 'compose']
    if shutil.which('docker-compose'):
        return ['docker-compose']
    return None


def main():
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    os.environ['PROJECT_PATH'] = str(script_dir)

    docker_cmd = find_docker_cmd()
    if not docker_cmd:
        print('ERROR: Docker not found in PATH. Install Docker or add to PATH.')
        return 2

    print('[Server] Uruchamianie kontenerów...')
    try:
        subprocess.check_call(docker_cmd + ['up', '-d', '--build'])
    except subprocess.CalledProcessError as e:
        print(f'[Server] Błąd podczas uruchamiania kontenerów: {e}')
        return e.returncode

    addr = 'localhost:51234'
    cfg_file = script_dir / 'server_config.json'
    if cfg_file.exists():
        try:
            cfg = json.load(cfg_file.open('r', encoding='utf-8'))
            host = cfg.get('HOST', 'localhost')
            port = cfg.get('PORT', 51234)
            addr = f'{host}:{port}'
        except Exception:
            pass

    print('[Server] Usługi uruchomione:')
    print('  - Panel Admina: http://localhost:5001')
    print(f'  - Brama Terminalowa: {addr}')

    try:
        subprocess.check_call(docker_cmd + ['ps'])
    except subprocess.CalledProcessError:
        pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
