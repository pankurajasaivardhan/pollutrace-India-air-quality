'use client';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PageShell from '@/components/PageShell';
import { Card, Status, fmt } from '@/components/State';
import { api } from '@/lib/api';
import { useApi } from '@/lib/useApi';
import { MODEL_LABEL } from '@/lib/labels';
import ForecastForm from '@/components/ForecastForm';

function Predictions({ city }: { city: string }) {
  const { data, error, loading } = useApi(() => api.predictions(city), [city]);
  const m = useApi(() => api.metrics(), []);
  const rows = (m.data ?? []).filter((r) => r.city === city);
  return (
    <>
      <Status loading={loading} error={error} empty={!!data && data.length === 0}
        emptyText="No test-period predictions loaded (needs forecast_test_predictions.json from the pipeline)." />
      {data && data.length > 0 && (
        <Card title="Next-day PM2.5 on the held-out test period (µg/m³)"
          note="Each point is a forecast for that day made from the previous 30 days. The test period was never used for training or early stopping. Persistence means 'tomorrow equals today' and is the baseline to beat.">
          <div className="h-96"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" minTickGap={50} /><YAxis /><Tooltip /><Legend />
              <Line dataKey="actual_pm25" name="Actual" stroke="#111827" dot={false} />
              <Line dataKey="predicted_pm25_lstm" name="LSTM" stroke="#2563eb" dot={false} />
              <Line dataKey="predicted_pm25_xgboost" name="XGBoost" stroke="#16a34a" dot={false} />
              <Line dataKey="predicted_pm25_persistence" name="Persistence" stroke="#f59e0b" dot={false} strokeDasharray="4 3" /></LineChart>
          </ResponsiveContainer></div>
        </Card>
      )}
      <ForecastForm city={city} />
      {rows.length > 0 && (
        <Card title="Test-period error for this city" note="Lower RMSE and MAE are better. The LSTM must beat persistence to be useful; see the Metrics page.">
          <table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Model</th><th className="pr-3">RMSE</th><th className="pr-3">MAE</th><th className="pr-3">R²</th><th>Days</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.model_type} className="border-t"><td className="py-1">{MODEL_LABEL[r.model_type] ?? r.model_type}</td><td className="pr-3">{fmt(r.rmse)}</td><td className="pr-3">{fmt(r.mae)}</td><td className="pr-3">{fmt(r.r2_score, 3)}</td><td>{r.n_test_days}</td></tr>)}</tbody></table>
        </Card>
      )}
    </>
  );
}

export default function Page() {
  return <PageShell page="/predictions" title="Next-day PM2.5 forecast" subtitle="Forecasts versus what was measured, with the persistence baseline">{(c) => <Predictions city={c} />}</PageShell>;
}
