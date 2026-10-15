from __future__ import annotations
import os
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .analysis import analyze
from .backtesting import run_ema_backtest
from .market_data import MarketDataError, fetch_hourly_klines, get_runner_status, get_supported_symbols
from .deep_analysis import get_scan_state, start_scan


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

    @app.get("/backtesting")
    @login_required
    def backtesting_page():
        return render_template("backtesting.html")

    @app.get("/deep-analysis")
    @login_required
    def deep_analysis_page():
        return render_template("deep_analysis.html")


    @app.get("/market-chart")
    @login_required
    def market_chart_page():
        return render_template("market_chart.html")

    @app.get("/api/chart-data")
    @login_required
    def chart_data():
        symbol = str(request.args.get("symbol", "BTCUSDT")).upper().strip()
        interval = str(request.args.get("interval", "1h"))
        if interval not in {"1h", "4h", "1d"}:
            return jsonify({"error": "بازهٔ زمانی معتبر نیست."}), 400
        try:
            candles = fetch_hourly_klines(symbol, limit=1000)
            step_ms = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}[interval]
            grouped = {}
            for candle in candles:
                bucket = (int(candle["open_time"]) // step_ms) * step_ms
                if bucket not in grouped:
                    grouped[bucket] = {"time": bucket // 1000, "open": candle["open"], "high": candle["high"],
                                       "low": candle["low"], "close": candle["close"], "volume": candle.get("volume", 0)}
                else:
                    item = grouped[bucket]
                    item["high"] = max(item["high"], candle["high"])
                    item["low"] = min(item["low"], candle["low"])
                    item["close"] = candle["close"]
                    item["volume"] += candle.get("volume", 0)
            rows = sorted(grouped.values(), key=lambda item: item["time"])
            if len(rows) < 2:
                raise MarketDataError("برای رسم نمودار دادهٔ کافی موجود نیست.")
            return jsonify({"symbol": symbol, "interval": interval, "source": candles[-1].get("source", "Unknown"),
                            "currency": candles[-1].get("currency", "USDT"), "candles": rows,
                            "last_updated_ms": candles[-1].get("open_time")})
        except (ValueError, MarketDataError) as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Unexpected chart data failure")
            return jsonify({"error": "دریافت دادهٔ نمودار ناموفق بود؛ گزارش محلی را بررسی کن."}), 500

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

    @app.get("/api/runner-status")
    @login_required
    def runner_status():
        return jsonify(get_runner_status())

    @app.get("/api/symbols")
    @login_required
    def supported_symbols():
        return jsonify({"symbols": get_supported_symbols()})

    @app.post("/api/deep-analysis/start")
    @login_required
    def start_deep_analysis():
        body = request.get_json(silent=True) or {}
        try:
            target = float(body.get("target_pct", 5))
            if not 1 <= target <= 100:
                raise ValueError("حداقل هدف باید بین ۱ تا ۱۰۰ درصد باشد.")
        except (TypeError, ValueError):
            return jsonify({"error": "درصد هدف باید عددی بین ۱ تا ۱۰۰ باشد."}), 400
        if not start_scan(target):
            return jsonify({"error": "یک اسکن دیگر در حال اجراست؛ صبر کن تا تمام شود."}), 409
        return jsonify({"status": "running", "message": "اسکن در پس‌زمینه شروع شد."}), 202

    @app.get("/api/deep-analysis/status")
    @login_required
    def deep_analysis_status():
        return jsonify(get_scan_state())

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


    @app.post("/api/backtest")
    @login_required
    def backtest_market():
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol", "BTCUSDT")).upper().strip()
        if not symbol.endswith("USDT") or not symbol.isalnum() or not 5 <= len(symbol) <= 20:
            return jsonify({"error": "نماد معتبر USDT وارد کن؛ مثلاً BTCUSDT."}), 400
        try:
            fee_pct = float(body.get("fee_pct", 0.1))
            if not 0 <= fee_pct <= 2:
                raise ValueError("کارمزد باید بین صفر تا ۲ درصد برای هر سمت باشد.")
            candles = fetch_hourly_klines(symbol)
            result = run_ema_backtest(candles, fee_pct)
            result["symbol"] = symbol
            result["source"] = candles[-1].get("source", "Unknown")
            result["last_candle_time_ms"] = candles[-1].get("open_time")
            return jsonify(result)
        except (ValueError, MarketDataError) as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Unexpected backtest failure")
            return jsonify({"error": "خطای داخلی در بک‌تست؛ گزارش محلی را بررسی کن."}), 500

    return app
