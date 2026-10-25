"""Unsupervised anomaly flagging with an autoencoder, with a leakage-safe threshold.

There are no ground-truth anomaly labels in the data, so this reports counts and
sanity checks, NOT accuracy. Threshold = 95th percentile of reconstruction error on
the VALIDATION period; the model is trained on the TRAIN period only.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from common import CITIES, SEED, causal_fill, reindex_daily, split_bounds

FEATS = ["PM25", "PM10", "NO2", "NOx", "SO2", "CO", "Ozone"]


def run_city(city_df, city, model_dir):
    from tensorflow.keras import layers, models
    from tensorflow.keras.callbacks import EarlyStopping
    import tensorflow as tf

    d = reindex_daily(city_df)[FEATS]
    n = len(d)
    a, b = split_bounds(n)
    observed = d["PM25"].notna().values
    med = d.iloc[:a].median().fillna(0.0)
    f = causal_fill(d, FEATS, med)
    # log1p tames the heavy right tail before min-max scaling (train-fit)
    L = np.log1p(f.clip(lower=0))
    lo, hi = L.iloc[:a].min(), L.iloc[:a].max()
    span = (hi - lo).replace(0, 1.0)
    X = ((L - lo) / span).values.astype("float32")
    train_ok = observed[:a]
    if train_ok.sum() < 200 or (observed[b:]).sum() < 30:
        return {"skipped": "not enough measured days"}, None

    tf.keras.utils.set_random_seed(SEED)
    ae = models.Sequential([
        layers.Input(shape=(len(FEATS),)),
        layers.Dense(8, activation="relu"), layers.Dense(3, activation="relu"),
        layers.Dense(8, activation="relu"), layers.Dense(len(FEATS), activation="sigmoid"),
    ])
    ae.compile(optimizer="adam", loss="mse")
    Xtr = X[:a][train_ok]
    ae.fit(Xtr, Xtr, epochs=80, batch_size=32, verbose=0, validation_split=0.1,
           callbacks=[EarlyStopping(patience=8, restore_best_weights=True)])
    err = np.mean((ae.predict(X, verbose=0) - X) ** 2, axis=1)
    val_mask = observed.copy(); val_mask[:a] = False; val_mask[b:] = False
    thr = float(np.percentile(err[val_mask], 95))
    te = observed.copy(); te[:b] = False
    flagged = te & (err > thr)
    sev = np.where(err > 3 * thr, "high", np.where(err > 2 * thr, "medium", "low"))
    pm = d["PM25"].values
    p95 = np.nanpercentile(pm[:a], 95)
    res = {
        "threshold_mse": thr, "test_days_measured": int(te.sum()),
        "test_days_flagged": int(flagged.sum()),
        "test_flag_rate": float(flagged.sum() / te.sum()),
        "expected_rate_if_stable_distribution": 0.05,
        "sanity_flagged_with_pm25_above_train_p95": float(np.mean(pm[flagged] > p95)) if flagged.sum() else None,
        "sanity_unflagged_with_pm25_above_train_p95": float(np.mean(pm[te & ~flagged] > p95)) if (te & ~flagged).sum() else None,
        "note": "unsupervised; no ground-truth labels; a flag rate far above the expected rate means the test period differs from validation for this model; the cause is not established",
    }
    os.makedirs(model_dir, exist_ok=True)
    ae.save(os.path.join(model_dir, f"autoencoder_{city.lower()}.keras"))
    with open(os.path.join(model_dir, f"anomaly_{city.lower()}.json"), "w") as fh:
        json.dump({"features": FEATS, "log1p": True, "min": lo.to_dict(), "span": span.to_dict(),
                   "fill_medians": med.to_dict(), "threshold_mse": thr}, fh, indent=1)
    rows = pd.DataFrame({"city": city, "date": d.index[te], "pm25": pm[te],
                         "reconstruction_error": err[te], "threshold": thr,
                         "is_anomaly": flagged[te], "severity": np.where(flagged[te], sev[te], None)})
    return res, rows


def run_all(city_daily, model_dir, out_dir):
    results, tables = {}, []
    for city in CITIES:
        c = city_daily[city_daily["city"] == city]
        if c.empty:
            continue
        print("anomalies", city, flush=True)
        r, rows = run_city(c, city, model_dir)
        results[city] = r
        if rows is not None:
            tables.append(rows)
        print(json.dumps(r, indent=1), flush=True)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "anomaly_summary.json"), "w") as f:
        json.dump(results, f, indent=1)
    if tables:
        pd.concat(tables).to_csv(os.path.join(out_dir, "anomalies_test_period.csv"), index=False)
    return results
