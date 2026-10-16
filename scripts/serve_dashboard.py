"""Optional local FastAPI entry point; no public tunnel is started."""
import os
import sys
from pathlib import Path
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import create_app

if __name__ == "__main__":
    password = os.environ.get("PASS", "").strip() or None
    uvicorn.run(create_app(password), host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), log_level="warning")
