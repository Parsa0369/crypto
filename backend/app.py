from __future__ import annotations
import hashlib, hmac, json, os, secrets, logging
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from .analysis import analyze
from .backtesting import run_ema_backtest
from .market_data import MarketDataError, fetch_hourly_klines, get_runner_status, get_supported_symbols
from .deep_analysis import get_scan_state, start_scan

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))
PASSWORD_FILE = (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CryptoPulse" / "password.json"
                 if os.name == "nt" else Path.home() / ".local/share/cryptopulse/password.json")
ROUTES = {"index": "/", "login": "/login", "logout": "/logout", "backtesting_page": "/backtesting",
          "deep_analysis_page": "/deep-analysis", "behind_scenes_page": "/behind-scenes",
          "market_chart_page": "/market-chart", "static": "/static/{filename}"}

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "pbkdf2_sha256$" + salt.hex() + "$" + digest.hex()

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, expected = encoded.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000)
        return algorithm == "pbkdf2_sha256" and hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False

def saved_hash() -> str | None:
    try:
        value = json.loads(PASSWORD_FILE.read_text(encoding="utf-8"))
        return value.get("password_hash")
    except (OSError, ValueError, AttributeError):
        return None

def save_hash(encoded: str) -> None:
    PASSWORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSWORD_FILE.write_text(json.dumps({"password_hash": encoded}), encoding="utf-8")
    try: PASSWORD_FILE.chmod(0o600)
    except OSError: pass

def create_app(password: str | None = None) -> FastAPI:
    app = FastAPI(title="CryptoPulse", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=os.environ.get("CRYPTOPULSE_SECRET_KEY") or secrets.token_urlsafe(32),
                      same_site="strict", https_only=False, max_age=1800)
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
    TEMPLATES.env.globals["url_for"] = lambda name, **kw: (
        "/static/" + str(kw.get("filename", "")).lstrip("/") if name == "static" else ROUTES.get(name, "/"))
    configured_hash = hash_password(password.strip()) if password and password.strip() else None
    def current_hash(): return configured_hash or saved_hash()
    def authenticated(request: Request): return bool(request.session.get("authenticated"))
    def page(req: Request, name: str, **ctx: Any):
        ctx.setdefault("request", req)
        return TEMPLATES.TemplateResponse(request=req, name=name, context=ctx)
    def auth_error(): return JSONResponse({"error": "Authentication required."}, status_code=401)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update({"X-Content-Type-Options":"nosniff", "X-Frame-Options":"DENY",
                                 "Referrer-Policy":"no-referrer", "Cache-Control":"no-store"})
        return response

    @app.get("/")
    async def index(request: Request):
        return page(request, "dashboard.html") if authenticated(request) else RedirectResponse("/login", 303)

    @app.get("/backtesting")
    async def backtesting_page(request: Request):
        return page(request, "backtesting.html") if authenticated(request) else RedirectResponse("/login", 303)

    @app.get("/deep-analysis")
    async def deep_analysis_page(request: Request):
        return page(request, "deep_analysis.html") if authenticated(request) else RedirectResponse("/login", 303)

    @app.get("/behind-scenes")
    async def behind_scenes_page(request: Request):
        return page(request, "behind_scenes.html") if authenticated(request) else RedirectResponse("/login", 303)

    @app.get("/market-chart")
    async def market_chart_page(request: Request):
        return page(request, "market_chart.html") if authenticated(request) else RedirectResponse("/login", 303)

    @app.get("/login")
    async def login_page(request: Request):
        if authenticated(request): return RedirectResponse("/", 303)
        return page(request, "login.html", request=request, setup=current_hash() is None, transition=False, error=None)

    @app.post("/login")
    async def login(request: Request):
        form = await request.form()
        supplied = str(form.get("password", ""))
        encoded = current_hash()
        if encoded is None:
            confirm = str(form.get("confirm_password", ""))
            if len(supplied) < 10:
                return page(request, "login.html", request=request, setup=True, transition=False, error="رمز عبور باید حداقل ۱۰ نویسه داشته باشد.")
            if not hmac.compare_digest(supplied, confirm):
                return page(request, "login.html", request=request, setup=True, transition=False, error="تکرار رمز عبور مطابقت ندارد.")
            save_hash(hash_password(supplied))
        elif not verify_password(supplied, encoded):
            return page(request, "login.html", request=request, setup=False, transition=False, error="رمز عبور نادرست است.")
        request.session.clear()
        request.session["authenticated"] = True
        return page(request, "login.html", request=request, setup=False, transition=True, error=None)

    @app.post("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", 303)

    @app.get("/api/health")
    async def health(request: Request):
        return {"status":"ok","mode":"local-only"} if authenticated(request) else auth_error()

    @app.get("/api/runner-status")
    async def runner_status(request: Request):
        return get_runner_status() if authenticated(request) else auth_error()

    @app.get("/api/symbols")
    async def symbols(request: Request):
        return {"symbols":get_supported_symbols()} if authenticated(request) else auth_error()

    @app.post("/api/deep-analysis/start")
    async def deep_start(request: Request):
        if not authenticated(request): return auth_error()
        body = await request.json()
        try:
            target = float(body.get("target_pct", 5))
            if not 1 <= target <= 100: raise ValueError
        except (TypeError, ValueError, AttributeError):
            return JSONResponse({"error":"درصد هدف باید عددی بین ۱ تا ۱۰۰ باشد."}, 400)
        if not start_scan(target): return JSONResponse({"error":"یک اسکن دیگر در حال اجراست؛ صبر کن تا تمام شود."}, 409)
        return JSONResponse({"status":"running","message":"اسکن در پس‌زمینه شروع شد."}, 202)

    @app.get("/api/deep-analysis/status")
    async def deep_status(request: Request):
        return get_scan_state() if authenticated(request) else auth_error()

    @app.post("/api/analyze")
    async def analyze_api(request: Request):
        if not authenticated(request): return auth_error()
        body = await request.json()
        symbol = str(body.get("symbol", "BTCUSDT")).upper().strip()
        try:
            horizon, target = int(body.get("horizon_hours", 6)), float(body.get("target_pct", 5))
            if not 1 <= horizon <= 168: raise ValueError("افق زمانی باید بین ۱ تا ۱۶۸ ساعت باشد.")
            if not 0 <= target <= 100: raise ValueError("حداقل هدف باید بین صفر تا ۱۰۰ درصد باشد.")
            candles = fetch_hourly_klines(symbol)
            result = analyze(candles, horizon, target)
            last = candles[-1]
            result.update({"symbol":symbol,"source":last.get("source","Unknown"),"currency":last.get("currency","USDT"),
                           "last_candle_time_ms":last["open_time"],"snapshot_generated_at":last.get("snapshot_generated_at"),
                           "runner_shutdown_at":last.get("runner_shutdown_at")})
            return result
        except (ValueError, MarketDataError) as exc: return JSONResponse({"error":str(exc)}, 400)
        except Exception:
            return JSONResponse({"error":"Unexpected server error. Check local logs."}, 500)

    @app.post("/api/behind-scenes/analyze")
    async def behind_analyze(request: Request):
        if not authenticated(request): return auth_error()
        body = await request.json()
        symbol = str(body.get("symbol", "BTCUSDT")).upper().strip()
        try:
            target = float(body.get("target_pct", 5))
            if not 1 <= target <= 100: raise ValueError("درصد هدف باید بین ۱ تا ۱۰۰ باشد.")
            candles = fetch_hourly_klines(symbol)
            result = analyze(candles, 3, target)
            result.update({"symbol":symbol,"source":candles[-1].get("source","Unknown"),
                           "last_candle_time_ms":candles[-1].get("open_time"),
                           "chart_candles":[{"time":int(c.get("open_time",0)),"open":float(c["open"]),"high":float(c["high"]),
                                             "low":float(c["low"]),"close":float(c["close"])} for c in candles[-72:]],
                           "source_checks":["Binance","Bybit","Kraken","Yahoo Finance","GitHub Actions snapshot"]})
            return result
        except (ValueError, MarketDataError) as exc: return JSONResponse({"error":str(exc)}, 400)
        except Exception: return JSONResponse({"error":"خطای داخلی در پشت صحنه؛ گزارش محلی را بررسی کن."}, 500)

    @app.post("/api/backtest")
    async def backtest_api(request: Request):
        if not authenticated(request): return auth_error()
        body = await request.json()
        symbol = str(body.get("symbol","BTCUSDT")).upper().strip()
        if not symbol.endswith("USDT") or not symbol.isalnum() or not 5 <= len(symbol) <= 20:
            return JSONResponse({"error":"نماد معتبر USDT وارد کن؛ مثلاً BTCUSDT."}, 400)
        try:
            fee = float(body.get("fee_pct",0.1))
            if not 0 <= fee <= 2: raise ValueError("کارمزد باید بین صفر تا ۲ درصد برای هر سمت باشد.")
            candles = fetch_hourly_klines(symbol)
            result = run_ema_backtest(candles, fee)
            result.update({"symbol":symbol,"source":candles[-1].get("source","Unknown"),
                           "last_candle_time_ms":candles[-1].get("open_time")})
            return result
        except (ValueError, MarketDataError) as exc: return JSONResponse({"error":str(exc)}, 400)
        except Exception: return JSONResponse({"error":"خطای داخلی در بک‌تست؛ گزارش محلی را بررسی کن."}, 500)

    return app
