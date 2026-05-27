#!/usr/bin/env python3

import argparse
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from shutil import which
from typing import Optional


def parse_java_major(version_output: str) -> Optional[int]:
    match = re.search(r'version "([^"]+)"', version_output)
    if not match:
        return None

    version_text = match.group(1)
    parts = re.split(r"[._+-]", version_text)
    if not parts:
        return None

    try:
        if parts[0] == "1" and len(parts) > 1:
            return int(parts[1])
        return int(parts[0])
    except ValueError:
        return None


def java_executable_from_home(java_home: Path) -> Path:
    java_name = "java.exe" if platform.system() == "Windows" else "java"

    if java_home.is_file():
        return java_home

    return java_home / "bin" / java_name


def detect_java_home() -> Optional[Path]:
    candidates = []

    java_home_env = os.environ.get("JAVA_HOME")
    if java_home_env:
        candidates.append(Path(java_home_env))

    if platform.system() == "Darwin":
        java_home_tool = Path("/usr/libexec/java_home")
        if java_home_tool.exists():
            try:
                output = subprocess.check_output([str(java_home_tool)], text=True).strip()
                if output:
                    candidates.append(Path(output))
            except (subprocess.SubprocessError, OSError):
                pass

    java_path = which("java")
    if java_path:
        candidates.append(Path(java_path).resolve().parent.parent)

    for candidate in candidates:
        java_executable = java_executable_from_home(candidate)
        if not java_executable.exists():
            continue

        try:
            version_result = subprocess.run(
                [str(java_executable), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        except OSError:
            continue

        major_version = parse_java_major(version_result.stdout)
        if major_version is not None and major_version >= 17:
            return candidate if not candidate.is_file() else candidate.parent.parent

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the terminal client.")
    parser.add_argument(
        "--clients",
        type=int,
        default=1,
        help="Number of client windows to open.",
    )
    return parser.parse_args()


def build_maven_command(script_dir: Path) -> list[str]:
    if platform.system() == "Windows":
        return [
            "cmd",
            "/c",
            str(script_dir / "mvnw.cmd"),
            "-U",
            "-q",
            "-Dmaven.test.skip=true",
            "javafx:run",
        ]

    return [
        "bash",
        str(script_dir / "mvnw"),
        "-U",
        "-q",
        "-Dmaven.test.skip=true",
        "javafx:run",
    ]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    args = parse_args()

    if args.clients < 1:
        print("ERROR: --clients musi byc wieksze lub rowne 1.", file=sys.stderr)
        return 2

    java_home = detect_java_home()

    if java_home is None:
        print(
            "ERROR: Nie znaleziono JDK 17+. Zainstaluj JDK 17 lub nowsze albo ustaw JAVA_HOME.",
            file=sys.stderr,
        )
        return 1

    java_executable = java_executable_from_home(java_home)
    version_result = subprocess.run(
        [str(java_executable), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    java_version_line = version_result.stdout.splitlines()[0] if version_result.stdout else ""
    print(f"[run.py] Using JAVA_HOME={java_home} ({java_version_line})")

    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_home)

    command = build_maven_command(script_dir)

    if args.clients == 1:
        completed_process = subprocess.run(command, cwd=script_dir, env=env)
        return completed_process.returncode

    processes = []
    print(f"[run.py] Launching {args.clients} client instances...")
    for index in range(args.clients):
        process = subprocess.Popen(command, cwd=script_dir, env=env)
        processes.append(process)
        print(f"[run.py] Started client instance {index + 1}/{args.clients} (pid={process.pid})")
        time.sleep(0.5)

    exit_code = 0
    for process in processes:
        process_exit_code = process.wait()
        if process_exit_code != 0 and exit_code == 0:
            exit_code = process_exit_code

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())