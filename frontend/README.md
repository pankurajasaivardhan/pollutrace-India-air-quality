# PolluTrace frontend

Next.js (App Router, TypeScript) dashboard that reads the PolluTrace Go API. It has no built-in data: if the API or database is empty, pages say so.

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8080 npm run dev      # http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8080 npm run build && npm start
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8080`. The API must allow the frontend origin (`CORS_ALLOW_ORIGIN`, see the root README).

Pages: Dashboard (PM2.5 history), Predictions (test-period forecasts against actuals and the persistence baseline), Sources (pollutant association ranking), Anomalies (autoencoder flags), Metrics (every model against the baseline).

Set `NEXT_PUBLIC_VERCEL_ANALYTICS=1` only when hosting on Vercel to enable Vercel Analytics.
