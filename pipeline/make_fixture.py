"""Writes a SYNTHETIC fixture in the raw-station-CSV format, only to smoke-test the code.
Results from it mean nothing; it is not air-quality data."""
import os, sys
import numpy as np, pandas as pd
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(0)
for prefix, base in [("DL", 120), ("KA", 40), ("MH", 55), ("TG", 50)]:
    idx = pd.date_range("2016-01-01", "2020-12-31 23:00", freq="h")
    seas = 1 + 0.5*np.cos(2*np.pi*(idx.dayofyear-15)/365.25)
    pm = np.abs(base*seas + 15*rng.standard_normal(len(idx)))
    df = pd.DataFrame({"From Date": idx.strftime("%Y-%m-%d %H:%M:%S"),
        "PM2.5 (ug/m3)": pm, "PM10 (ug/m3)": pm*1.6, "NO (ug/m3)": pm*0.1, "NO2 (ug/m3)": pm*0.3,
        "NOx (ppb)": pm*0.4, "NH3 (ug/m3)": pm*0.2, "SO2 (ug/m3)": pm*0.1, "CO (mg/m3)": pm*0.01,
        "Ozone (ug/m3)": 30+0*pm, "Benzene (ug/m3)": pm*0.02})
    df.loc[rng.random(len(df)) < 0.3, "PM2.5 (ug/m3)"] = np.nan
    df.to_csv(os.path.join(out, f"{prefix}001.csv"), index=False)
