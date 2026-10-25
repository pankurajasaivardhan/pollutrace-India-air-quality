"""Next-day PM2.5 from saved models and a city_daily.csv.

  python pipeline/predict.py --models outputs/models --city-daily outputs/city_daily.csv --city Delhi
  python pipeline/predict.py ... --city Delhi --verify   # re-score the saved test period

Uses the window of the last 30 days ending at the latest date in the file and the saved
train-only scaler and fill medians. Output is JSON with the LSTM and XGBoost estimates.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from common import FORECAST_POLLUTANTS, add_calendar, causal_fill, regression_metrics, reindex_daily, split_bounds


def load_bundle(models, city):
    with open(os.path.join(models, f"scaler_{city.lower()}.json")) as f:
        sc = json.load(f)
    import xgboost as xgb
    import keras
    gb = xgb.XGBRegressor()
    gb.load_model(os.path.join(models, f"xgb_lags_{city.lower()}.json"))
    # Files saved by newer Keras add a key some older Keras versions reject; ignore it.
    if not getattr(keras.layers.Dense, "_pt_patched", False):
        orig = keras.layers.Dense.__init__
        keras.layers.Dense.__init__ = lambda self, *a, quantization_config=None, **k: orig(self, *a, **k)
        keras.layers.Dense._pt_patched = True
    lstm = keras.models.load_model(os.path.join(models, f"lstm_{city.lower()}.keras"), compile=False)
    return sc, lstm, gb


def xgb_test_predictions(city_df, sc, models, city):
    """XGBoost next-day predictions for the chronological test period (measured target days only)."""
    import xgboost as xgb
    gb = xgb.XGBRegressor()
    gb.load_model(os.path.join(models, f"xgb_lags_{city.lower()}.json"))
    d, filled, X = scaled_matrix(city_df, sc)
    n, seq = len(d), sc["seq_len"]
    a, b = split_bounds(n)
    observed = d["PM25"].notna().values
    idx = [t for t in range(seq - 1, n - 1) if t + 1 >= b and observed[t + 1]]
    xs = np.array([X[t - seq + 1:t + 1] for t in idx]).reshape(len(idx), -1)
    return {str(d.index[t + 1].date()): float(v) for t, v in zip(idx, gb.predict(xs))}


def scaled_matrix(city_df, sc):
    d = add_calendar(reindex_daily(city_df)[FORECAST_POLLUTANTS])
    med = pd.Series(sc["fill_medians"])
    filled = causal_fill(d, FORECAST_POLLUTANTS, med)
    lo, span = pd.Series(sc["min"]), pd.Series(sc["span"])
    X = ((filled[sc["features"]] - lo[sc["features"]]) / span[sc["features"]]).values.astype("float32")
    return d, filled, X


def predict_next(city_df, sc, lstm, gb):
    d, filled, X = scaled_matrix(city_df, sc)
    n = sc["seq_len"]
    w = X[-n:][None]
    lstm_pred = float(lstm.predict(w, verbose=0).ravel()[0] * sc["span"]["PM25"] + sc["min"]["PM25"])
    xgb_pred = float(gb.predict(w.reshape(1, -1))[0])
    return {"as_of": str(d.index[-1].date()), "forecast_for": str((d.index[-1] + pd.Timedelta(days=1)).date()),
            "lstm_pm25": round(lstm_pred, 1), "xgboost_pm25": round(xgb_pred, 1),
            "persistence_pm25": round(float(filled["PM25"].iloc[-1]), 1)}


def verify(city_df, sc, lstm):
    """Re-score the saved LSTM on the test period; must match forecast_metrics.json."""
    d, filled, X = scaled_matrix(city_df, sc)
    n, seq = len(d), sc["seq_len"]
    a, b = split_bounds(n)
    observed = d["PM25"].notna().values
    idx = [t for t in range(seq - 1, n - 1) if t + 1 >= b and observed[t + 1]]
    xs = np.array([X[t - seq + 1:t + 1] for t in idx])
    y = filled["PM25"].values[[t + 1 for t in idx]]
    pred = lstm.predict(xs, verbose=0).ravel() * sc["span"]["PM25"] + sc["min"]["PM25"]
    return regression_metrics(y, pred)



class InputError(ValueError):
    """Bad user input (maps to HTTP 400/422 in the service)."""


FIELDS = FORECAST_POLLUTANTS  # PM25, PM10, NO2, NOx, SO2, CO, Ozone
MAX_VALUE = 5000.0
MAX_ROWS = 3660
MIN_PM25_DAYS = 15


def rows_to_frame(rows):
    if not isinstance(rows, list) or not rows:
        raise InputError("'rows' must be a non-empty list of daily records")
    if len(rows) > MAX_ROWS:
        raise InputError(f"too many rows (max {MAX_ROWS})")
    recs = {}
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise InputError(f"row {i + 1} is not an object")
        try:
            day = pd.Timestamp(str(r.get("date")))
        except Exception:
            raise InputError(f"row {i + 1}: 'date' must be YYYY-MM-DD")
        if pd.isna(day) or day.normalize() != day:
            raise InputError(f"row {i + 1}: 'date' must be a calendar date (YYYY-MM-DD)")
        if day in recs:
            raise InputError(f"duplicate date {day.date()}")
        rec = {}
        for k in FIELDS:
            v = r.get(k)
            if v is None or v == "":
                rec[k] = np.nan
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise InputError(f"row {i + 1}: {k} must be a number or empty")
            v = float(v)
            if not np.isfinite(v) or v < 0 or v > MAX_VALUE:
                raise InputError(f"row {i + 1}: {k}={v} is outside 0..{MAX_VALUE:g}")
            rec[k] = v
        recs[day] = rec
    df = pd.DataFrame.from_dict(recs, orient="index").sort_index()
    df.index.name = "date"
    return df


def predict_rows(rows, sc, lstm, gb):
    """Next-day PM2.5 from user-supplied daily rows (any gaps are forward filled, then train medians)."""
    df = rows_to_frame(rows)
    n = sc["seq_len"]
    span_days = (df.index[-1] - df.index[0]).days + 1
    if span_days < n:
        raise InputError(f"need at least {n} calendar days of history, got {span_days}")
    d = add_calendar(df.reindex(pd.date_range(df.index[0], df.index[-1], freq="D"))[FIELDS].rename_axis("date"))
    have = int(d["PM25"].iloc[-n:].notna().sum())
    if have < MIN_PM25_DAYS:
        raise InputError(f"need PM25 on at least {MIN_PM25_DAYS} of the last {n} days, got {have}")
    last_pm_missing = bool(d["PM25"].iloc[-1] != d["PM25"].iloc[-1])
    filled = causal_fill(d, FIELDS, pd.Series(sc["fill_medians"]))
    lo, sp = pd.Series(sc["min"]), pd.Series(sc["span"])
    X = ((filled[sc["features"]] - lo[sc["features"]]) / sp[sc["features"]]).values.astype("float32")
    w = X[-n:][None]
    window = d.iloc[-n:]
    missing = int(window[FIELDS].isna().sum().sum())
    lstm_pred = float(lstm.predict(w, verbose=0).ravel()[0] * sc["span"]["PM25"] + sc["min"]["PM25"])
    xgb_pred = float(gb.predict(w.reshape(1, -1))[0])
    return {"as_of": str(d.index[-1].date()), "forecast_for": str((d.index[-1] + pd.Timedelta(days=1)).date()),
            "lstm_pm25": round(max(lstm_pred, 0.0), 1), "xgboost_pm25": round(max(xgb_pred, 0.0), 1),
            "persistence_pm25": round(float(filled["PM25"].iloc[-1]), 1),
            "window_days": n, "missing_values_in_window": missing,
            "last_pm25_was_missing": last_pm_missing,
            "trained_through": sc.get("trained_through")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="outputs/models")
    ap.add_argument("--city-daily", default="outputs/city_daily.csv")
    ap.add_argument("--city", required=True)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    df = pd.read_csv(a.city_daily, parse_dates=["date"])
    cdf = df[df["city"] == a.city].drop(columns="city")
    sc, lstm, gb = load_bundle(a.models, a.city)
    print(json.dumps(verify(cdf, sc, lstm) if a.verify else predict_next(cdf, sc, lstm, gb), indent=1))
