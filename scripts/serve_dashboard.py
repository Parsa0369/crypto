"""Run the CryptoPulse Flask dashboard on the local interface for a tunnel."""
import os
import sys
from pathlib import Path

# When launched as `python scripts/serve_dashboard.py`, Python may put only
# the scripts directory on sys.path. Add the repository root so `backend`
# can be imported reliably on GitHub Actions Windows runners.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app

password = os.environ.get("PASS", "").strip()
if len(password) < 10:
    raise SystemExit("PASS secret is missing or shorter than 10 characters. Configure repository secret PASS.")

port = int(os.environ.get("PORT", "8080"))
app = create_app(password)
print(f"CryptoPulse dashboard listening on 127.0.0.1:{port}", flush=True)
app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
