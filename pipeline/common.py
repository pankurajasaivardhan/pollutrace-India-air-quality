"""Shared data loading and leakage-controlled preparation for PolluTrace.

Data source (NOT included in this repository):
  Kaggle "Time Series Air Quality Data of India (2010-2023)" by abhisheksjha,
  licence shown on Kaggle: CC BY-NC-SA 4.0. Download it yourself and point
  POLLUTRACE_RAW_DIR at the folder that contains the per-station CSV files.

Leakage rules enforced here:
  * chronological split per city (train / validation / test), no shuffling
  * every statistic (imputation medians, scaler) is fit on the training part only
  * gap filling is causal (forward fill only, never uses future values)
  * metrics are computed only on days where the target PM2.5 was actually measured
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

CITY_PREFIX = {"DL": "Delhi", "KA": "Bengaluru", "MH": "Mumbai", "TG": "Hyderabad"}
CITIES = ["Delhi", "Bengaluru", "Mumbai", "Hyderabad"]

RAW_COLS = {
    "From Date": "datetime",
    "PM2.5 (ug/m3)": "PM25",
    "PM10 (ug/m3)": "PM10",
    "NO (ug/m3)": "NO",
    "NO2 (ug/m3)": "NO2",
    "NOx (ppb)": "NOx",
    "NH3 (ug/m3)": "NH3",
    "SO2 (ug/m3)": "SO2",
    "CO (mg/m3)": "CO",
    "Ozone (ug/m3)": "Ozone",
    "Benzene (ug/m3)": "Benzene",
}
POLLUTANTS = ["PM25", "PM10", "NO", "NO2", "NOx", "NH3", "SO2", "CO", "Ozone", "Benzene"]
# Features the forecaster sees (target PM25 first). Calendar features are cyclic.
FORECAST_POLLUTANTS = ["PM25", "PM10", "NO2", "NOx", "SO2", "CO", "Ozone"]
TRAIN_FRAC, VAL_FRAC = 0.70, 0.15
MAX_FFILL_DAYS = 3
SEQ_LEN = 30
SEED = 42


def load_city_daily(raw_dir: str) -> pd.DataFrame:
    """Hourly/15-min station files -> daily mean per station -> daily mean per city.

    Missing values are left as NaN here. Note: the set of reporting stations
    changes over time, so the city mean mixes station coverage (a known limit).
    """
    frames = []
    files = sorted(glob.glob(os.path.join(raw_dir, "**", "*.csv"), recursive=True))
    used = 0
    for f in files:
        name = os.path.basename(f)
        prefix = name[:2].upper()
        if prefix not in CITY_PREFIX or name.lower().startswith("stations"):
            continue
        head = pd.read_csv(f, nrows=0)
        cols = [c for c in RAW_COLS if c in head.columns]
        if "From Date" not in cols:
            continue
        df = pd.read_csv(f, usecols=cols, low_memory=False).rename(columns=RAW_COLS)
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"])
        df["date"] = df["datetime"].dt.floor("D")
        num = [c for c in POLLUTANTS if c in df.columns]
        daily = df.groupby("date")[num].mean()
        daily["city"] = CITY_PREFIX[prefix]
        daily["station"] = name[:-4]
        frames.append(daily.reset_index())
        used += 1
    if not frames:
        raise FileNotFoundError(f"no station CSV files with prefixes {list(CITY_PREFIX)} under {raw_dir}")
    station_daily = pd.concat(frames, ignore_index=True)
    for c in POLLUTANTS:
        if c not in station_daily:
            station_daily[c] = np.nan
    city_daily = station_daily.groupby(["city", "date"])[POLLUTANTS].mean().reset_index()
    city_daily.attrs["n_station_files"] = used
    return city_daily


def reindex_daily(city_df: pd.DataFrame) -> pd.DataFrame:
    """Full daily calendar for one city (gaps become NaN rows)."""
    d = city_df.set_index("date").sort_index()
    idx = pd.date_range(d.index.min(), d.index.max(), freq="D")
    return d.reindex(idx).rename_axis("date")


def split_bounds(n: int) -> tuple[int, int]:
    a = int(n * TRAIN_FRAC)
    b = int(n * (TRAIN_FRAC + VAL_FRAC))
    return a, b


def add_calendar(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    doy = d.index.dayofyear.values
    dow = d.index.dayofweek.values
    d["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    d["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    d["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    d["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    return d


def causal_fill(d: pd.DataFrame, cols: list[str], medians: pd.Series) -> pd.DataFrame:
    """Forward fill (<= MAX_FFILL_DAYS) then train medians. Never looks ahead."""
    d = d.copy()
    d[cols] = d[cols].ffill(limit=MAX_FFILL_DAYS)
    d[cols] = d[cols].fillna(medians)
    return d


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    err = y_pred - y_true
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mae": float(np.mean(np.abs(err))),
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "n": int(len(y_true)),
    }
