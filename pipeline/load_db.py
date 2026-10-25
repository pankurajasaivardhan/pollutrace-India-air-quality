"""Load pipeline results into PostgreSQL for the Go API.

  python pipeline/load_db.py --results outputs --db "$DB_URL"

Expects the files written by run_all.py. Optional files (city_daily.csv,
forecast_test_predictions.json, anomalies_test_period.csv) are loaded when present.
Creates the schema from sql/schema/*.sql and replaces existing rows.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply_schema(cur):
    """Recreate every table from the goose 'Up' sections (drops existing data)."""
    files = sorted(glob.glob(os.path.join(ROOT, "sql", "schema", "*.sql")))
    for f in files:
        text = open(f).read()
        for line in text.split("-- +goose Down")[-1].splitlines():
            if line.strip().upper().startswith("DROP TABLE"):
                cur.execute(line.replace("DROP TABLE", "DROP TABLE IF EXISTS", 1)
                            if "IF EXISTS" not in line.upper() else line)
    for f in files:
        cur.execute(open(f).read().split("-- +goose Down")[0])


def load(results: str, db_url: str) -> dict:
    counts = {}
    con = psycopg2.connect(db_url)
    con.autocommit = False
    with con, con.cursor() as cur:
        apply_schema(cur)

        fm = json.load(open(os.path.join(results, "forecast_metrics.json")))
        rows = []
        for city, r in fm.items():
            if "skipped" in r:
                continue
            for key in ("persistence", "train_mean_baseline", "xgboost_lags", "lstm"):
                m = r[key]
                rows.append((city, key, m["rmse"], m["mae"], m["r2"], m["n"]))
        execute_values(cur, "INSERT INTO model_metrics(city,model_type,rmse,mae,r2_score,n_test_days) VALUES %s", rows)
        counts["model_metrics"] = len(rows)

        sa = json.load(open(os.path.join(results, "source_association.json")))
        rows = []
        for city, r in sa.items():
            if "skipped" in r:
                continue
            for i, x in enumerate(r["ranking"], 1):
                rows.append((city, i, x["pollutant"], x["mean_abs_shap"], r["test_fit"]["r2"]))
        execute_values(cur, "INSERT INTO source_analysis(city,rank,pollutant,mean_abs_shap,model_test_r2) VALUES %s", rows)
        counts["source_analysis"] = len(rows)

        p = os.path.join(results, "forecast_test_predictions.json")
        if os.path.exists(p):
            ex = json.load(open(p))
            rows = []
            for city, e in ex.items():
                xg = e.get("test_pred_xgboost")
                xmap = dict(zip(e["test_dates"], xg)) if xg else _xgb_from_models(results, city)
                for d, a, l, ps in zip(e["test_dates"], e["test_actual"], e["test_pred_lstm"], e["test_pred_persistence"]):
                    rows.append((city, d, a, l, ps, xmap.get(d)))
            execute_values(cur, "INSERT INTO lstm_predictions(city,date,actual_pm25,predicted_pm25_lstm,predicted_pm25_persistence,predicted_pm25_xgboost) VALUES %s", rows)
            counts["lstm_predictions"] = len(rows)

        p = os.path.join(results, "anomalies_test_period.csv")
        if os.path.exists(p):
            import pandas as pd
            d = pd.read_csv(p)
            rows = [(r.city, r.date, _n(r.pm25), _n(r.reconstruction_error), _n(r.threshold),
                     bool(r.is_anomaly), None if pd.isna(r.severity) else r.severity) for r in d.itertuples()]
            execute_values(cur, "INSERT INTO anomalies(city,date,pm25,reconstruction_error,threshold,is_anomaly,severity) VALUES %s", rows)
            counts["anomalies"] = len(rows)

        p = os.path.join(results, "city_daily.csv")
        if os.path.exists(p):
            import pandas as pd
            d = pd.read_csv(p)
            d["date"] = pd.to_datetime(d["date"])
            rows = [(r.city, r.date.date(), _n(r.PM25), _n(r.PM10), _n(r.NO), _n(r.NO2), _n(r.NOx), _n(r.NH3),
                     _n(r.SO2), _n(r.CO), _n(r.Ozone), _n(r.Benzene), r.date.month, r.date.dayofweek, r.date.year)
                    for r in d.itertuples()]
            execute_values(cur, "INSERT INTO city_pollution(city,date,pm25,pm10,no,no2,nox,nh3,so2,co,ozone,benzene,month,day_of_week,year) VALUES %s", rows)
            counts["city_pollution"] = len(rows)
    con.close()
    return counts


def _xgb_from_models(results, city):
    """Older result folders lack XGBoost test predictions: recompute them from the saved model.
    Returns {} (column left empty) when the models or city_daily.csv are not next to the results."""
    import sys
    mdir, cdv = os.path.join(results, "models"), os.path.join(results, "city_daily.csv")
    if not (os.path.exists(os.path.join(mdir, f"xgb_lags_{city.lower()}.json")) and os.path.exists(cdv)):
        return {}
    sys.path.insert(0, os.path.dirname(__file__))
    import predict
    df = pd.read_csv(cdv, parse_dates=["date"])
    sc = json.load(open(os.path.join(mdir, f"scaler_{city.lower()}.json")))
    return predict.xgb_test_predictions(df[df["city"] == city].drop(columns="city"), sc, mdir, city)


def _n(x):
    import math
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="outputs")
    ap.add_argument("--db", default=os.environ.get("DB_URL"))
    a = ap.parse_args()
    print(json.dumps(load(a.results, a.db)))
