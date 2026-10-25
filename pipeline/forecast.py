"""Next-day PM2.5 forecasting per city with honest, leakage-controlled evaluation.

Compares against baselines so the LSTM must earn its place:
  persistence  : tomorrow = today (causally filled)
  xgboost_lags : gradient boosting on the same 30-day window, flattened
  lstm         : the original 2-layer LSTM architecture
All numbers are computed on the held-out chronological TEST period, only on days
where PM2.5 was really measured.
"""
from __future__ import annotations

import json
import os
import random

import numpy as np
import pandas as pd

from common import (CITIES, FORECAST_POLLUTANTS, SEED, SEQ_LEN, add_calendar,
                    causal_fill, regression_metrics, reindex_daily, split_bounds)

CAL = ["doy_sin", "doy_cos", "dow_sin", "dow_cos"]
FEATURES = FORECAST_POLLUTANTS + CAL


def build_city(city_df: pd.DataFrame):
    d = add_calendar(reindex_daily(city_df)[FORECAST_POLLUTANTS])
    n = len(d)
    a, b = split_bounds(n)
    observed = d["PM25"].notna().values
    medians = d.iloc[:a][FORECAST_POLLUTANTS].median()
    medians = medians.fillna(0.0)
    filled = causal_fill(d, FORECAST_POLLUTANTS, medians)
    lo = filled.iloc[:a][FEATURES].min()
    hi = filled.iloc[:a][FEATURES].max()
    span = (hi - lo).replace(0, 1.0)
    X_all = ((filled[FEATURES] - lo) / span).values.astype("float32")
    return d, filled, observed, X_all, lo, span, medians, (a, b, n)


def windows(X_all, filled_pm25, observed, a, b, n):
    xs, ys, tgt_idx, keep = [], [], [], []
    for t in range(SEQ_LEN - 1, n - 1):  # window ends at t, target is day t+1
        xs.append(X_all[t - SEQ_LEN + 1:t + 1])
        ys.append(filled_pm25[t + 1])
        tgt_idx.append(t + 1)
        keep.append(observed[t + 1])
    xs, ys = np.array(xs), np.array(ys, dtype="float32")
    tgt_idx, keep = np.array(tgt_idx), np.array(keep)
    part = np.where(tgt_idx < a, "train", np.where(tgt_idx < b, "val", "test"))
    return xs, ys, tgt_idx, keep, part


def run_city(city_df, city, model_dir, epochs=60):
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.callbacks import EarlyStopping
    import xgboost as xgb

    d, filled, observed, X_all, lo, span, medians, (a, b, n) = build_city(city_df)
    pm = filled["PM25"].values
    xs, ys, tgt_idx, keep, part = windows(X_all, pm, observed, a, b, n)

    tr, va, te = part == "train", part == "val", part == "test"
    # Train only on real targets; the model never learns from imputed PM2.5.
    tr_fit, va_fit = tr & keep, va & keep
    te_eval = te & keep
    out = {"n_days": int(n), "date_start": str(d.index[0].date()), "date_end": str(d.index[-1].date()),
           "train_end": str(d.index[a - 1].date()), "val_end": str(d.index[b - 1].date()),
           "n_train": int(tr_fit.sum()), "n_val": int(va_fit.sum()), "n_test": int(te_eval.sum())}
    if te_eval.sum() < 30 or tr_fit.sum() < 200:
        out["skipped"] = "not enough measured days"
        return out, None

    y_test = ys[te_eval]
    # persistence: yesterday's (causally filled) PM2.5 for the target day
    prev = pm[tgt_idx - 1]
    out["persistence"] = regression_metrics(y_test, prev[te_eval])

    # mean baseline (train mean) for reference
    out["train_mean_baseline"] = regression_metrics(y_test, np.full(te_eval.sum(), ys[tr_fit].mean()))

    # xgboost on flattened window
    flat = xs.reshape(len(xs), -1)
    gb = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                          colsample_bytree=0.8, random_state=SEED, n_jobs=2)
    gb.fit(flat[tr_fit], ys[tr_fit], eval_set=[(flat[va_fit], ys[va_fit])], verbose=False)
    out["xgboost_lags"] = regression_metrics(y_test, gb.predict(flat[te_eval]))

    # LSTM (scaled target = PM25 column scaled with the same train min/max)
    pm_lo, pm_span = float(lo["PM25"]), float(span["PM25"])
    ys_s = (ys - pm_lo) / pm_span
    tf.keras.utils.set_random_seed(SEED)
    model = models.Sequential([
        layers.Input(shape=(SEQ_LEN, len(FEATURES))),
        layers.LSTM(64, return_sequences=True), layers.Dropout(0.2),
        layers.LSTM(32), layers.Dropout(0.2),
        layers.Dense(16, activation="relu"), layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    hist = model.fit(xs[tr_fit], ys_s[tr_fit], validation_data=(xs[va_fit], ys_s[va_fit]),
                     epochs=epochs, batch_size=32, verbose=0,
                     callbacks=[EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)])
    pred = model.predict(xs[te_eval], verbose=0).ravel() * pm_span + pm_lo
    out["lstm"] = regression_metrics(y_test, pred)
    out["lstm"]["epochs_run"] = len(hist.history["loss"])
    # honest verdict
    out["lstm_beats_persistence"] = bool(out["lstm"]["rmse"] < out["persistence"]["rmse"])

    os.makedirs(model_dir, exist_ok=True)
    model.save(os.path.join(model_dir, f"lstm_{city.lower()}.keras"))
    with open(os.path.join(model_dir, f"scaler_{city.lower()}.json"), "w") as f:
        json.dump({"features": FEATURES, "seq_len": SEQ_LEN, "min": lo.to_dict(), "span": span.to_dict(),
                   "fill_medians": medians.to_dict(), "target": "PM25_next_day",
                   "trained_through": out["train_end"]}, f, indent=1)
    gb.save_model(os.path.join(model_dir, f"xgb_lags_{city.lower()}.json"))
    extra = {"test_dates": [str(x.date()) for x in d.index[tgt_idx[te_eval]]],
             "test_actual": y_test.tolist(), "test_pred_lstm": pred.tolist(),
             "test_pred_persistence": prev[te_eval].tolist(),
             "test_pred_xgboost": gb.predict(flat[te_eval]).tolist()}
    return out, extra


def run_all(city_daily: pd.DataFrame, model_dir: str, out_dir: str, epochs=60):
    random.seed(SEED)
    np.random.seed(SEED)
    results, extras = {}, {}
    for city in CITIES:
        c = city_daily[city_daily["city"] == city]
        if c.empty:
            continue
        print("forecast", city, flush=True)
        r, e = run_city(c, city, model_dir, epochs)
        results[city] = r
        if e:
            extras[city] = e
        print(json.dumps(r, indent=1), flush=True)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "forecast_metrics.json"), "w") as f:
        json.dump(results, f, indent=1)
    with open(os.path.join(out_dir, "forecast_test_predictions.json"), "w") as f:
        json.dump(extras, f)
    return results
