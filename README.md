# PolluTrace: PM2.5 Forecasting and Pollutant-Pattern Analysis for Four Indian Cities

PolluTrace looks at daily PM2.5 for Delhi, Mumbai, Bengaluru and Hyderabad (2010 to March 2023). It has a reproducible historical research pipeline, a PostgreSQL schema, a Go JSON API and a Next.js dashboard. A separate station-readings page accesses recent observations through OpenAQ, where verified coverage is available.

**Honest summary of the results**

- On a held-out, chronological test period the LSTM does **not** beat the trivial "tomorrow equals today" baseline in any of the four cities. XGBoost on the same 30-day window beats it only in Delhi, and only slightly.
- The autoencoder anomaly flags are unsupervised (no ground-truth labels). The test-period flag rates are far from the 5% the threshold was set for in two cities, and the cause has not been investigated.
- The pollutant ranking is a statistical association inside a predictive model. It is not source apportionment and not causal.

## Free current station readings (new)

The **Station readings** page (`/live`) calls the Go server's `/api/live?city=Delhi` endpoint. It shows actual PM2.5 station observations, not CAMS estimates, city averages, an Indian AQI, or output from our historical LSTM/XGBoost. No values are invented when a source fails.

Coverage verified on 25 October 2026:

| City | Configured station | Source and rights | Limit |
|---|---|---|---|
| Delhi | OpenAQ 8118, New Delhi | AirNow; OpenAQ license 33, US Public Domain | One government monitor; not a city average |
| Mumbai | OpenAQ 8039, Mumbai | AirNow; same license | One government monitor; not a city average |
| Bengaluru | Unavailable | Recent sensor owner name indicated indoor ambiguity; not accepted as ambient city monitoring | No substitute values |
| Hyderabad | Unavailable | CPCB candidates were about 46 hours old and location license metadata was missing; AirNow candidate was older | No substitute values |

Coverage and delays can change. The page always shows the actual measurement time (IST), retrieval time, units, station, provider, owner and license. A measurement older than 3 hours is marked stale. This is a project display rule, not an official freshness standard. Readings are provisional and not medical advice or an official alert.

**Free local setup, without Postgres, model downloads or TensorFlow:**

1. Create your own [free OpenAQ account](https://explore.openaq.org/register), verify its email and obtain the key from the account page. Keep your key private. If using the owner's private bundle, the owner already has an account and saved key; do not register duplicate keys.
2. With Go 1.25+ and Python 3 installed, run `python3 pipeline/start_live.py`. Paste the key at its hidden prompt. This does not write the key to disk. Alternatively set `OPENAQ_API_KEY`, `LIVE_ONLY=true` and `CORS_ALLOW_ORIGIN=http://localhost:3000` server-side and run `go run .`.
3. In another terminal: `cd frontend && npm ci && npm run dev`. Open `http://localhost:3000/live`.
4. The historical pages need the full database setup below. Their absence in live-only mode does not affect station readings.

The free API permits [60 requests/minute and 2,000/hour](https://docs.openaq.org/using-the-api/rate-limits). This single-process server caches successes and errors for one hour per configured city (no retries on a 429), and the page has no background polling. One uncached request uses at most three provider calls: location metadata, license and latest measurement. Multi-process deployments need a shared cache/rate limiter. No card, subscription, billing setup or paid hosting is part of this project. There is no guaranteed uptime, comprehensive coverage, or completed public deployment.

API keys never enter browser bundles, output JSON, code, archives or git. Only city/station queries go to the provider. Do not expose a public high-traffic proxy with this private owner's key. For a public multiuser deployment, configure authentication, abuse protection and shared quota controls first.

Data credits: [OpenAQ](https://openaq.org/) and [AirNow](https://www.airnow.gov/). OpenAQ license metadata labels these stations US Public Domain; underlying owner metadata is "Unknown Governmental Organization", which is preserved rather than guessed. License source supplied by OpenAQ: http://www.usa.gov/publicdomain/label/1.0/ . See [OpenAQ terms](https://docs.openaq.org/about/terms) and [station metadata](https://docs.openaq.org/resources/locations). These station rights do not clear redistribution of the separate historical Kaggle dataset/models.

## Results

All numbers below come from one run of `pipeline/run_all.py` (seed 42, Kaggle CPU notebook, 134 station files, 19,018 city-days; Python 3.13.15, TensorFlow 2.20.0). Raw output is in `results/`. Each city is split chronologically 70/15/15 into train, validation and test:

- Delhi: 2010-01-01 to 2023-03-31; train through 2019-04-09, validation through 2021-04-04, test after that
- Bengaluru: 2010-01-01 to 2023-03-31; train through 2019-04-09, validation through 2021-04-04, test after that
- Mumbai: 2010-01-01 to 2023-03-31; train through 2019-04-09, validation through 2021-04-04, test after that
- Hyderabad: 2010-12-01 to 2023-03-31; train through 2019-07-18, validation through 2021-05-24, test after that

Imputation medians and scalers are fit on the training part only, gap filling looks backwards only (up to 3 days, then training medians), and every score uses only days where PM2.5 was actually measured. The test period had already been looked at before this table was written, so do not read these numbers as a one-shot unseen result after any later tuning.

### Next-day PM2.5 (µg/m³), test period

| City | Model | RMSE | MAE | R² | Test days |
|---|---|---|---|---|---|
| Delhi | Persistence (tomorrow = today) | 33.4 | 21.5 | 0.780 | 726 |
| Delhi | XGBoost, 30-day window | 31.0 | 20.2 | 0.811 | 726 |
| Delhi | LSTM | 34.1 | 25.4 | 0.771 | 726 |
| Bengaluru | Persistence (tomorrow = today) | 5.9 | 3.8 | 0.792 | 726 |
| Bengaluru | XGBoost, 30-day window | 14.3 | 12.1 | -0.216 | 726 |
| Bengaluru | LSTM | 9.9 | 8.4 | 0.410 | 726 |
| Mumbai | Persistence (tomorrow = today) | 10.6 | 6.9 | 0.846 | 726 |
| Mumbai | XGBoost, 30-day window | 11.0 | 7.5 | 0.836 | 726 |
| Mumbai | LSTM | 12.5 | 8.8 | 0.788 | 726 |
| Hyderabad | Persistence (tomorrow = today) | 7.5 | 5.2 | 0.848 | 676 |
| Hyderabad | XGBoost, 30-day window | 12.5 | 9.0 | 0.574 | 676 |
| Hyderabad | LSTM | 9.7 | 7.5 | 0.744 | 676 |

The results folder also has the training-mean baseline. Regression metrics here use measured days only, and the set of reporting stations may differ over the years (not examined here); both are limits (no per-station modelling, no meteorology).

### Anomaly flags (test period, autoencoder)

| City | Measured days | Flagged | Rate |
|---|---|---|---|
| Delhi | 726 | 22 | 3.0% |
| Bengaluru | 726 | 137 | 18.9% |
| Mumbai | 726 | 1 | 0.1% |
| Hyderabad | 676 | 137 | 20.3% |

The threshold is the 95th percentile of reconstruction error on the validation period. There are no labels, so this is a count, not an accuracy.

### Pollutant association with PM2.5

| City | Model test R² | Top 3 pollutants (mean absolute SHAP) |
|---|---|---|
| Delhi | 0.80 | PM10, Benzene, CO |
| Bengaluru | 0.27 | PM10, NO2, Benzene |
| Mumbai | 0.87 | PM10, NO2, Benzene |
| Hyderabad | 0.54 | PM10, Ozone, CO |

XGBoost predicts same-day PM2.5 from the other pollutants; the table lists the three largest mean absolute SHAP values. R² describes predictive fit only.

## Data and rights

The raw data is **not** in this repository. It is the Kaggle dataset
[Time Series Air Quality Data of India (2010-2023)](https://www.kaggle.com/datasets/abhisheksjha/time-series-air-quality-data-of-india-2010-2023)
by abhisheksjha. Kaggle shows its licence as CC BY-NC-SA 4.0 and says the data was collected from the Central Pollution Control Board (CPCB). I did not find a reuse licence on CPCB's own terms page, so the rights to redistribute the data, or files derived from it, are unresolved. This project uses only the station files whose names start with `DL`, `KA`, `MH` or `TG`.

What this repository contains, given that:
- Code (`pipeline/`, `internal/`, `frontend/`, `sql/`): the project's own.
- `results/`: four small JSON files of aggregate research results (test metrics, pollutant ranking, anomaly counts, run info). No per-day data.
- `legacy/notebooks/`: the original notebooks with their executed outputs (5-row previews, logs, figures).
- Not included: raw data, the derived `city_daily.csv`, trained model files, per-day predictions. Run the pipeline yourself to produce them. A private bundle that includes them exists for the project owner. It is not cleared for public sharing.

## Repository layout

```
pipeline/    leakage-controlled data prep, forecasting, anomalies, pollutant association, DB loader
sql/         PostgreSQL schema (sql/schema) and sqlc queries (sql/queries)
internal/    Go API (internal/api) and sqlc-generated DB code (internal/database)
main.go      API entry point
frontend/    Next.js dashboard (reads the Go API)
results/     result JSON from the run above
legacy/      original notebooks, kept unchanged for provenance (not used); the old model binaries are not included
```

## Run it

Requirements: Python 3.10+, Go 1.25+, Node 20+, PostgreSQL 14+.

Tested environment: Python 3.10, TensorFlow 2.21 and Keras 3.12.4 from a clean virtualenv (`pip install -r requirements.txt`, resolved versions in `requirements-lock.txt`). The shipped Kaggle models were trained with TensorFlow 2.20 on Python 3.13 and load and re-score identically here.

1. **Get the data.** Download the Kaggle dataset and unzip it. Note the folder holding the station CSVs.
2. **Run the pipeline.**
   ```bash
   pip install -r requirements.txt
   python pipeline/run_all.py --raw-dir /path/to/station/csvs --out outputs
   ```
   This writes metrics, predictions, trained models (`outputs/models`) and a derived `city_daily.csv`. On a 2-core CPU, expect on the order of ten minutes (371 s on the Kaggle CPU run above; not measured elsewhere).
3. **Load PostgreSQL.**
   ```bash
   createdb pollutrace
   python pipeline/load_db.py --results outputs --db "postgresql://localhost/pollutrace"
   ```
   This recreates the tables from `sql/schema` and replaces their contents.
4. **Start the inference service** (only needed for the historical-model demonstration form; it serves the saved models):
   ```bash
   python pipeline/serve.py --models outputs/models --port 8100
   ```
5. **Start the API.** Export the variables from `.env.example` (at least `DB_URL`, and `INFERENCE_URL=http://127.0.0.1:8100` to enable forecasting), then `go run .` (port 8080).
6. **Start the dashboard.**
   ```bash
   cd frontend && npm ci && NEXT_PUBLIC_API_URL=http://localhost:8080 npm run dev
   ```

Command-line forecast from saved models (needs `outputs/models` and `outputs/city_daily.csv` from step 2):
```bash
python pipeline/predict.py --models outputs/models --city-daily outputs/city_daily.csv --city Delhi            # next-day estimate
python pipeline/predict.py --models outputs/models --city-daily outputs/city_daily.csv --city Delhi --verify   # re-score the test period
```
`--verify` reproduced the stored LSTM test RMSE and R² for all four cities (agreement to about 1e-5) when loading the files from the Kaggle run. The estimate is for the day after the last date in the file, with no live data feed, and the LSTM loses to persistence on the test period, so treat it as a demonstration.

API endpoints: `GET /api/healthz`, `/api/cities`, `/api/pollution?city=`, `/api/predictions?city=`, `/api/anomalies?city=`, `/api/sources?city=`, `/api/metrics`, and `POST /api/predict` (forwarded to the inference service).

`POST /api/predict` takes `{"city":"Delhi","rows":[{"date":"2023-03-01","PM25":80,"PM10":150,"NO2":40,"NOx":50,"SO2":10,"CO":1.2,"Ozone":30}, ...]}` with at least 30 calendar days and PM25 on at least 15 of the last 30. It returns 422 with a message for bad input, 503 if `INFERENCE_URL` is unset and 502 if the service is down. The dashboard's Predictions page has a form for it. The inference service has no authentication and binds to 127.0.0.1: do not expose it directly.

## Tests

The Go tests run against a real PostgreSQL server and are skipped without `TEST_DB_URL`. They create and drop tables, so use an empty database:

```bash
TEST_DB_URL="postgresql://localhost/pollutrace_test?sslmode=disable" go test ./...
```

## Known limits

- The forecast needs the Python inference service running next to the API. Without it `/api/predict` returns 503 and the rest of the dashboard still works.
- The forecast is a demonstration: it uses only the 30 days you supply, and on the test period the the LSTM had a higher RMSE than the persistence baseline in all four cities (XGBoost was lower only in Delhi).
- The city value is a mean over whichever stations report that day, so coverage changes over time.
- No weather inputs, so the forecaster has little to learn beyond recent PM2.5.
- Trained model files and derived data (including the old models from the first version of this project) are not published in this repository. The dataset's reuse terms are unresolved, so a model/data bundle is not offered publicly. See "Data".
