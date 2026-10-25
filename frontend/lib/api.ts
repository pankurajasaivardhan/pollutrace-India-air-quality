// Real API client. Set NEXT_PUBLIC_API_URL (default http://localhost:8080).
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080').replace(/\/$/, '');

export interface PollutionRow { city: string; date: string | null; pm25: number | null; pm10: number | null; no2: number | null; co: number | null; nox: number | null; so2: number | null; ozone: number | null }
export interface PredictionRow { date: string; actual_pm25: number | null; predicted_pm25_lstm: number | null; predicted_pm25_persistence: number | null; predicted_pm25_xgboost: number | null }
export interface AnomalyRow { city: string; date: string; pm25: number | null; is_anomaly: boolean | null; severity: string | null }
export interface SourceItem { rank: number; pollutant: string; mean_abs_shap: number | null }
export interface SourceResult { city: string; model_test_r2: number | null; ranking: SourceItem[]; note: string }
export interface MetricRow { city: string; model_type: string; rmse: number | null; mae: number | null; r2_score: number | null; n_test_days: number | null }

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: 'no-store' });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error ?? msg; } catch { /* keep status text */ }
    throw new Error(`${res.status}: ${msg}`);
  }
  return res.json() as Promise<T>;
}

export interface ForecastInput { city: string; rows: Record<string, string | number | null>[] }
export interface ForecastResult { city: string; as_of: string; forecast_for: string; lstm_pm25: number; xgboost_pm25: number; persistence_pm25: number; window_days: number; missing_values_in_window: number; last_pm25_was_missing: boolean; trained_through: string | null }

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  } catch {
    throw new Error('could not reach the API');
  }
  let data: unknown = null;
  try { data = await res.json(); } catch { /* non-JSON error body */ }
  if (!res.ok) throw new Error((data as { error?: string } | null)?.error ?? `${res.status} ${res.statusText}`);
  return data as T;
}

const q = (city: string) => `?city=${encodeURIComponent(city)}`;
export const api = {
  cities: () => get<string[]>('/api/cities'),
  pollution: (city: string) => get<PollutionRow[]>(`/api/pollution${q(city)}`),
  predictions: (city: string) => get<PredictionRow[]>(`/api/predictions${q(city)}`),
  anomalies: (city: string) => get<AnomalyRow[]>(`/api/anomalies${q(city)}`),
  sources: (city: string) => get<SourceResult>(`/api/sources${q(city)}`),
  forecast: (input: ForecastInput) => post<ForecastResult>('/api/predict', input),
  metrics: () => get<MetricRow[]>('/api/metrics'),
};

export interface StationReading { sensor_id: number; pollutant: string; parameter: string; unit: string; value: number; measured_at: string; age_hours: number; stale: boolean }
export interface LiveStation { city: string; kind: string; station_id: number; station_name: string; locality: string; source: string; source_url: string; retrieved_at: string; next_refresh_at: string; provider: { name?: string }; owner: { name?: string }; licenses: { id: number; name: string; sourceUrl?: string; attribution?: unknown }[]; readings: StationReading[]; note: string }
export const liveStation = (city: string) => get<LiveStation>(`/api/live${q(city)}`);
