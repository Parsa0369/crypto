"""Local-only CryptoPulse launcher."""
from getpass import getpass
import secrets
import socket
import webbrowser
from threading import Timer

from backend.app import create_app


def find_port(host: str = "127.0.0.1") -> int:
    # Let the OS select an unused ephemeral port; scanning all ports is unnecessary.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def main() -> None:
    print("\nCryptoPulse | Local market research dashboard")
    password = getpass("Create dashboard password (hidden): ")
    if len(password) < 10:
        raise SystemExit("Use a password with at least 10 characters.")
    confirm = getpass("Confirm password: ")
    if not secrets.compare_digest(password, confirm):
        raise SystemExit("Passwords do not match.")

    port = find_port()
    app = create_app(password)
    url = f"http://127.0.0.1:{port}"
    print(f"\nDashboard: {url}")
    print("Local-only server. Press Ctrl+C to stop.\n")
    Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
