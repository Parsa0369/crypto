"""Run the CryptoPulse Flask dashboard on the local interface for a tunnel."""
import os
from backend.app import create_app

password = os.environ.get("PASS", "").strip()
if len(password) < 10:
    raise SystemExit("PASS secret is missing or shorter than 10 characters. Configure repository secret PASS.")

port = int(os.environ.get("PORT", "8080"))
app = create_app(password)
print(f"CryptoPulse dashboard listening on 127.0.0.1:{port}", flush=True)
app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
