"""Start the FastAPI CryptoPulse dashboard on this computer only."""
import os
import socket
import webbrowser
from threading import Timer
import uvicorn
from backend.app import create_app
from port_speed import find_available_port

def main():
    host = "127.0.0.1"
    configured_port = os.environ.get("PORT", "").strip()
    if configured_port:
        port = int(configured_port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try: sock.bind((host, port))
            except OSError as exc: raise SystemExit(f"Port {port} is already in use. Close the other local server and retry.") from exc
    else:
        port = find_available_port(1000, 9999, 8080)
    password = os.environ.get("PASS", "").strip() or None
    app = create_app(password)
    url = f"http://{host}:{port}"
    print("\nCryptoPulse | FastAPI local dashboard")
    print(f"Dashboard: {url}")
    print("No Cloudflare, tunnel, public server, or terminal password prompt.")
    if password is None: print("First launch: create your dashboard password on the website.")
    print("Press Ctrl+C to stop.\n")
    Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")

if __name__ == "__main__": main()
