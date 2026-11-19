"""Run the suite with external Python socket connections denied.

Local HTTP callback/server tests still work. This does not sandbox subprocesses;
tests must continue to replace external command and publishing adapters.
"""

from __future__ import annotations

import ipaddress
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
real_connect = socket.socket.connect
real_connect_ex = socket.socket.connect_ex
blocked: list[str] = []


def check(address):
    if not isinstance(address, tuple):
        return
    host = str(address[0])
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    if not local:
        blocked.append(host)
        raise OSError("External networking is disabled in the offline test runner")


def connect(sock, address):
    check(address)
    return real_connect(sock, address)


def connect_ex(sock, address):
    check(address)
    return real_connect_ex(sock, address)


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", connect), patch.object(socket.socket, "connect_ex", connect_ex):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    if blocked:
        print(f"ERROR: blocked {len(blocked)} unexpected external connection attempts.", file=sys.stderr)
    sys.exit(0 if result.wasSuccessful() and not blocked else 1)
