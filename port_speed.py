"""Find an available localhost port in the requested range.

This measures availability, not Internet speed: port numbers do not make a
localhost web server faster. The default port (8080) is preferred when free.
"""
from __future__ import annotations
import socket
import time
from typing import Iterable

HOST = "127.0.0.1"
PORT_START = 1000
PORT_END = 9999
PREFERRED_PORT = 8080

def _can_bind(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            sock.bind((HOST, port))
        return True
    except OSError:
        return False

def _candidate_order(start: int, end: int, preferred: int) -> Iterable[int]:
    if start <= preferred <= end:
        yield preferred
    yield from (p for p in range(start, end + 1) if p != preferred)

def find_available_port(start: int = PORT_START, end: int = PORT_END,
                        preferred: int = PREFERRED_PORT) -> int:
    """Return a bindable localhost port, preferring 8080 when available."""
    if not (1 <= start <= end <= 65535):
        raise ValueError("Port range must satisfy 1 <= start <= end <= 65535.")
    started = time.perf_counter()
    for port in _candidate_order(start, end, preferred):
        if _can_bind(port):
            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"Selected available localhost port: {port} (checked in {elapsed_ms:.1f} ms)")
            print("Note: this checks port availability, not Internet speed.")
            return port
    raise RuntimeError(f"No available localhost port found in range {start}-{end}.")

if __name__ == "__main__":
    print(find_available_port())
