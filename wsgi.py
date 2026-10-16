"""Production WSGI entry point for Render."""
import os

from backend.app import create_app

password = os.environ.get("PASS", "").strip()
if len(password) < 10:
    raise RuntimeError(
        "Set PASS in the hosting environment to a strong password "
        "of at least 10 characters. Users enter it on the website login page."
    )

app = create_app(password)
