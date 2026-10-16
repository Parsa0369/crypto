"""Local machine-learning ensemble for crypto direction research.

Models are trained on recent hourly candles each time the endpoint is called.
Validation is chronological and includes a horizon-sized purge gap to reduce
label leakage from overlapping future windows. Outputs are research estimates,
not financial advice or guaranteed probabilities.
"""
from __future__ import annotations
from typing import Any

FEATURE_NAMES = [
    "return_1h", "return_3h", "return_6h", "return_12h", "return_24h",
    "return_48h", "return_72h", "volatility_6h", "volatility_24h",
    "volatility_72h", "ema_gap_12h", "ema_gap_24h", "ema_gap_50h",
    "rsi_14", "rsi_7", "macd_proxy", "bollinger_position", "range_pct",
    "volume_change", "volume_vs_24h", "candle_body_pct", "upper_wick_pct",
    "lower_wick_pct", "trend_consistency_24h",
]

def _features(candles: list[dict[str, Any]], i: int) -> list[float]:
    history = candles[:i + 1]
    closes = [float(c["close"]) for c in history]
    highs = [float(c["high"]) for c in history]
    lows = [float(c["low"]) for c in history]
    volumes = [max(0.0, float(c.get("volume", 0) or 0)) for c in history]
    c = closes[-1]
    eps = 1e-12

    def ret(period: int) -> float:
        return c / closes[-period - 1] - 1.0 if len(closes) > period and closes[-period - 1] else 0.0

    def volatility(period: int) -> float:
        changes = [closes[j] / closes[j - 1] - 1 for j in range(max(1, len(closes) - period), len(closes))]
        if len(changes) < 2: return 0.0
        avg = sum(changes) / len(changes)
        return (sum((v - avg) ** 2 for v in changes) / len(changes)) ** 0.5

    def ema(period: int) -> float:
        alpha, value = 2.0 / (period + 1), closes[0]
        for price in closes[1:]: value = alpha * price + (1 - alpha) * value
        return value

    def rsi(period: int) -> float:
        changes = [closes[j] - closes[j - 1] for j in range(max(1, len(closes) - period), len(closes))]
        gains, losses = sum(max(v, 0.0) for v in changes), sum(max(-v, 0.0) for v in changes)
        return 50.0 if gains + losses == 0 else 100.0 * gains / (gains + losses + eps)

    window = closes[-20:]
    avg = sum(window) / len(window)
    sd = (sum((v - avg) ** 2 for v in window) / len(window)) ** 0.5
    hi, lo = max(highs[-20:]), min(lows[-20:])
    vol_avg = sum(volumes[-24:]) / len(volumes[-24:])
    candle_range = max(highs[-1] - lows[-1], eps)
    op, body = float(history[-1]["open"]), c - float(history[-1]["open"])
    n = min(24, len(closes) - 1)
    positive = sum(1 for j in range(max(1, len(closes)-24), len(closes)) if closes[j] > closes[j-1])
    return [
        ret(1), ret(3), ret(6), ret(12), ret(24), ret(48), ret(72),
        volatility(6), volatility(24), volatility(72),
        c / (ema(12) + eps) - 1, c / (ema(24) + eps) - 1, c / (ema(50) + eps) - 1,
        rsi(14) / 100, rsi(7) / 100, (ema(12) - ema(26)) / (c + eps),
        (c - (avg - 2 * sd)) / (4 * sd + eps), (hi - lo) / (c + eps),
        volumes[-1] / (volumes[-2] + eps) - 1 if len(volumes) > 1 else 0.0,
        volumes[-1] / (vol_avg + eps) - 1, body / (c + eps),
        (highs[-1] - max(op, c)) / candle_range,
        (min(op, c) - lows[-1]) / candle_range,
        positive / max(1, n) * 2 - 1,
    ]

def train_and_predict(candles: list[dict[str, Any]], horizon_hours: int = 6) -> dict[str, Any]:
    """Train four diverse classifiers and report chronological holdout diagnostics."""
    try:
        import numpy as np
        from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss
    except ImportError as exc:
        raise RuntimeError("بسته‌های هوش مصنوعی نصب نیستند. برنامه را با start.ps1 open اجرا کن تا وابستگی‌ها نصب شوند.") from exc

    horizon = max(1, min(int(horizon_hours), 168))
    if len(candles) < max(180, horizon + 100):
        raise ValueError("برای آموزش مدل‌ها حداقل ۱۸۰ کندل ساعتی لازم است.")
    first = 80
    X_all = [_features(candles, i) for i in range(first, len(candles))]
    labeled_indices = list(range(first, len(candles) - horizon))
    if len(labeled_indices) < 100:
        raise ValueError("نمونهٔ کافی برای آموزش و ارزیابی مدل پیدا نشد.")
    X = np.asarray([X_all[i-first] for i in labeled_indices], dtype=float)
    closes = [float(c["close"]) for c in candles]
    y = np.asarray([int(closes[i+horizon] > closes[i]) for i in labeled_indices], dtype=int)
    split = int(len(y) * 0.8)
    train_end = max(40, split - horizon)
    X_train, y_train = X[:train_end], y[:train_end]
    X_test, y_test = X[split:], y[split:]
    if len(X_test) < 15 or len(set(y_train.tolist())) < 2:
        raise ValueError("تاریخچه برای ارزیابی زمانی کافی یا متنوع نیست.")

    def build_models():
        return [
            ("Random Forest", RandomForestClassifier(n_estimators=140, max_depth=7, min_samples_leaf=4, class_weight="balanced_subsample", random_state=17, n_jobs=-1)),
            ("Extra Trees", ExtraTreesClassifier(n_estimators=160, max_depth=8, min_samples_leaf=4, class_weight="balanced", random_state=23, n_jobs=-1)),
            ("Gradient Boosting", HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=15, learning_rate=0.06, l2_regularization=1.5, random_state=31)),
            ("Logistic Regression", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", C=0.35, random_state=41))),
        ]

    test_probabilities, reports = [], []
    for name, model in build_models():
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, list(model.classes_).index(1)]
        test_probabilities.append(probs)
        predicted = (probs >= 0.5).astype(int)
        reports.append({
            "name": name, "accuracy_pct": round(float(accuracy_score(y_test, predicted))*100, 2),
            "balanced_accuracy_pct": round(float(balanced_accuracy_score(y_test, predicted))*100, 2),
            "brier_score": round(float(brier_score_loss(y_test, probs)), 4), "test_samples": int(len(y_test)),
        })
    ensemble_test = np.mean(np.vstack(test_probabilities), axis=0)
    ensemble_pred = (ensemble_test >= 0.5).astype(int)
    accuracy = float(accuracy_score(y_test, ensemble_pred))*100
    balanced = float(balanced_accuracy_score(y_test, ensemble_pred))*100
    brier = float(brier_score_loss(y_test, ensemble_test))
    try: logloss = float(log_loss(y_test, np.clip(ensemble_test, 1e-6, 1-1e-6), labels=[0,1]))
    except ValueError: logloss = None

    current_x = np.asarray([_features(candles, len(candles)-1)], dtype=float)
    final_probs, importances = [], []
    for _, model in build_models():
        model.fit(X, y)
        final_probs.append(float(model.predict_proba(current_x)[0, list(model.classes_).index(1)]))
        if hasattr(model, "feature_importances_"): importances.append(np.asarray(model.feature_importances_, dtype=float))
    p_up = float(np.mean(final_probs))
    importance = np.mean(np.vstack(importances), axis=0) if importances else np.zeros(len(FEATURE_NAMES))
    top_features = [{"name":FEATURE_NAMES[int(i)],"importance_pct":round(float(importance[i])*100,2)} for i in np.argsort(importance)[::-1][:8]]
    direction = "گرایش مدل‌ها به رشد" if p_up >= .58 else "گرایش مدل‌ها به افت" if p_up <= .42 else "سیگنال ترکیبی / نامطمئن"
    current = closes[-1]
    recent = [closes[j]/closes[j-1]-1 for j in range(max(1,len(closes)-24),len(closes))]
    vol_proxy = (sum(v*v for v in recent)/max(1,len(recent)))**.5*(24**.5)*100
    return {
        "horizon_hours":horizon, "current_price":current, "probability_up_pct":round(p_up*100,2),
        "probability_down_pct":round((1-p_up)*100,2), "direction":direction, "model_count":len(reports),
        "models":reports, "validation":{"method":"chronological holdout with horizon-sized purge gap",
        "train_samples":int(len(X_train)),"test_samples":int(len(X_test)),"accuracy_pct":round(accuracy,2),
        "balanced_accuracy_pct":round(balanced,2),"brier_score":round(brier,4),
        "log_loss":round(logloss,4) if logloss is not None else None},
        "top_features":top_features,"feature_count":len(FEATURE_NAMES),"training_samples":int(len(X)),
        "recent_annualized_volatility_proxy_pct":round(vol_proxy,3),
        "caveats":["مدل‌ها در همین اجرا و روی دادهٔ تاریخی دریافت‌شده آموزش دیده‌اند.",
        "احتمال خروجی مدل است و لزوماً احتمال واقعی یا کالیبره‌شدهٔ آینده نیست.",
        "کارمزد، نقدشوندگی، اخبار و تغییر رژیم بازار به‌طور کامل لحاظ نشده‌اند.",
        "این ابزار پژوهشی است، نه توصیهٔ خرید یا فروش."]
    }
