"""Production WSGI entry point for Render."""
import os

from backend.app import create_app

password = os.environ.get("CRYPTOPULSE_PASSWORD", "")
if len(password) < 10:
    raise RuntimeError(
        "Set CRYPTOPULSE_PASSWORD in the hosting environment to a strong password "
        "of at least 10 characters before starting CryptoPulse."
    )

app = create_app(password)
