""""Local-only CryptoPulse launcher."""
import socket
import webbrowser
from threading import Timer
import os
import requests

from backend.app import create_app


def find_port(host: str = "127.0.0.1") -> int:
    # Let the OS select an unused ephemeral port; scanning all ports is unnecessary.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def start_github_runner_if_configured() -> None:
    """Trigger the hosted data-refresh workflow when an optional token is configured."""
    token = os.environ.get("CRYPTOPULSE_GITHUB_TOKEN", "").strip()
    if not token:
        print("GitHub runner auto-start: skipped (CRYPTOPULSE_GITHUB_TOKEN is not configured).")
        print("Set a GitHub token with Actions: write and Contents: read to enable auto-start.")
        return

    api = "https://api.github.com/repos/Parsa0369/crypto/actions/workflows/market-data-runner.yml"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        response = requests.get(f"{api}/runs", headers=headers,
                                params={"branch": "main", "per_page": 5}, timeout=10)
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
        if any(item.get("status") in ("queued", "in_progress") for item in runs):
            print("GitHub data runner is already queued or running; not starting a duplicate.")
            return
        response = requests.post(f"{api}/dispatches", headers=headers,
                                 json={"ref": "main"}, timeout=10)
        if response.status_code == 204:
            print("GitHub Windows data runner was triggered.")
        else:
            print(f"Could not start GitHub runner (HTTP {response.status_code}). Check token permissions.")
    except requests.RequestException as exc:
        print(f"Could not trigger GitHub runner: {type(exc).__name__}. Dashboard will still start.")


def main() -> None:
    print("\\nCryptoPulse | Local market research dashboard")
    # The password is configured as PASS; the user enters it on the website login page.
    password = os.environ.get("PASS", "").strip()
    if len(password) < 10:
        raise SystemExit("PASS is not configured (or is shorter than 10 characters). Set it in the hosting environment; no terminal prompt is used.")

    start_github_runner_if_configured()

    port = find_port()
    app = create_app(password)
    url = f"http://127.0.0.1:{port}"
    print(f"\\nDashboard: {url}")
    print("Local-only server. Press Ctrl+C to stop.\\n")
    Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
"