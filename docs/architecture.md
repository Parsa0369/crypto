# Architecture

- run.py prompts for a local dashboard password and binds Flask only to 127.0.0.1.
- backend/market_data.py downloads public hourly candles; no API key or trading permission is required.
- backend/analysis.py calculates historical frequencies and RSI.
- templates/ and static/ implement the Persian RTL dashboard.
- native/ contains an optional C++17 RSI implementation. It is not yet wired into the Python process.
- tests/ covers core calculation boundaries.

## Network and port behavior
The launcher asks the operating system to assign an available local port. It does not scan every port or claim that a port improves internet speed. Market-data requests go to the configured provider; local web traffic stays bound to loopback.

## Security
The password is prompted without terminal echo and only its password hash is held by the Flask app. The session secret is generated at startup unless CRYPTOPULSE_SECRET_KEY is set. Keep the dashboard local and never expose the Flask development server to the public internet.
