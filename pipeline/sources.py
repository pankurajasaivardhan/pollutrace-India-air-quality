"""Which co-measured pollutants are most associated with PM2.5 (NOT source apportionment).

Gradient boosting predicts same-day PM2.5 from the other pollutants, chronological
split, fit quality reported on the held-out test period. TreeSHAP values (from XGBoost pred_contribs) give mean |value|
importances on the test period. The model cannot identify emission sources, and the
ranking says nothing about causes.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from common import CITIES, SEED, causal_fill, regression_metrics, reindex_daily, split_bounds

OTHERS = ["PM10", "NO", "NO2", "NOx", "NH3", "SO2", "CO", "Ozone", "Benzene"]


def run_city(city_df, city):
    import xgboost as xgb
    d = reindex_daily(city_df)[["PM25"] + OTHERS]
    n = len(d)
    a, b = split_bounds(n)
    obs_pm = d["PM25"].notna().values
    med = d.iloc[:a][OTHERS].median().fillna(0.0)
    X = causal_fill(d[OTHERS], OTHERS, med)
    y = d["PM25"].values
    tr = obs_pm.copy(); tr[a:] = False
    va = obs_pm.copy(); va[:a] = False; va[b:] = False
    te = obs_pm.copy(); te[:b] = False
    if tr.sum() < 200 or te.sum() < 30:
        return {"skipped": "not enough measured days"}
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                         colsample_bytree=0.8, random_state=SEED, n_jobs=2)
    m.fit(X[tr], y[tr], eval_set=[(X[va], y[va])], verbose=False)
    met = regression_metrics(y[te], m.predict(X[te]))
    # exact TreeSHAP values computed natively by XGBoost (last column is the bias term)
    contrib = m.get_booster().predict(xgb.DMatrix(X[te]), pred_contribs=True)
    imp = np.abs(contrib[:, :-1]).mean(axis=0)
    order = np.argsort(-imp)
    top = [{"pollutant": OTHERS[i], "mean_abs_shap": float(imp[i])}
           for i in order]
    return {"test_fit": met, "ranking": top,
            "note": "statistical association in a predictive model; not causal, not source apportionment"}


def run_all(city_daily, out_dir):
    results = {}
    for city in CITIES:
        c = city_daily[city_daily["city"] == city]
        if c.empty:
            continue
        print("sources", city, flush=True)
        results[city] = run_city(c, city)
        print(json.dumps(results[city], indent=1)[:600], flush=True)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "source_association.json"), "w") as f:
        json.dump(results, f, indent=1)
    return results
