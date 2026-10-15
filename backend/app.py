from __future__ import annotations
import os
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .analysis import analyze
from .market_data import MarketDataError, fetch_hourly_klines


def create_app(password: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(
        SECRET_KEY=os.environ.get("CRYPTOPULSE_SECRET_KEY") or os.urandom(32),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=False, PERMANENT_SESSION_LIFETIME=1800,
        DASHBOARD_PASSWORD_HASH=generate_password_hash(password or "disabled"),
        MAX_CONTENT_LENGTH=16 * 1024,
    )

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("authenticated"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return render_template("dashboard.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            supplied = request.form.get("password", "")
            if check_password_hash(app.config["DASHBOARD_PASSWORD_HASH"], supplied):
                session.clear()
                session["authenticated"] = True
                session.permanent = True
                return redirect(url_for("index"))
            error = "رمز عبور نادرست است."
        return render_template("login.html", error=error)

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/api/health")
    @login_required
    def health():
        return jsonify({"status": "ok", "mode": "local-only"})

    @app.post("/api/analyze")
    @login_required
    def analyze_market():
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol", "BTCUSDT")).upper().strip()
        try:
            horizon = int(body.get("horizon_hours", 6))
            target = float(body.get("target_pct", 5))
            if not 1 <= horizon <= 168:
                raise ValueError("افق زمانی باید بین ۱ تا ۱۶۸ ساعت باشد.")
            if not 0 <= target <= 100:
                raise ValueError("حداقل هدف باید بین صفر تا ۱۰۰ درصد باشد.")
            candles = fetch_hourly_klines(symbol)
            result = analyze(candles, horizon, target)
            latest = candles[-1]
            result["symbol"] = symbol
            result["source"] = latest.get("source", "Unknown")
            result["currency"] = latest.get("currency", "USDT")
            result["last_candle_time_ms"] = latest["open_time"]
            result["snapshot_generated_at"] = latest.get("snapshot_generated_at")
            result["runner_shutdown_at"] = latest.get("runner_shutdown_at")
            return jsonify(result)
        except (ValueError, MarketDataError) as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Unexpected analysis failure")
            return jsonify({"error": "Unexpected server error. Check local logs."}), 500

    return app
