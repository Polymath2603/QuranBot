#!/usr/bin/env python3
"""Start QuranBot and ShellBot as parallel subprocesses.
Ctrl-C or SIGTERM stops both cleanly."""

import os, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent

PROCS = [
    ("QuranBot", [sys.executable, str(HERE / "bot.py")]),
    ("ShellBot",  [sys.executable, str(HERE / "shell.py")]),
]


def main():
    running = []
    for name, cmd in PROCS:
        p = subprocess.Popen(cmd, cwd=HERE)
        running.append((name, p))
        print(f"[start] {name} — pid {p.pid}")

    def _shutdown(sig, frame):
        print("\n[start] shutting down …")
        for name, p in running:
            p.terminate()
        for name, p in running:
            try:   p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill()
            print(f"[start] {name} stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        for name, p in running:
            if p.poll() is not None:
                print(f"[start] {name} exited (code {p.returncode}) — stopping all")
                _shutdown(None, None)
        time.sleep(1)


if __name__ == "__main__":
    main()
