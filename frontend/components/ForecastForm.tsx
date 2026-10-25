'use client';
import { useState } from 'react';
import { Card, fmt } from '@/components/State';
import { api, ForecastResult } from '@/lib/api';

const COLS = ['date', 'PM25', 'PM10', 'NO2', 'NOx', 'SO2', 'CO', 'Ozone'] as const;
const SHOWN = 'Columns: date, PM25, PM10, NO2, NOx, SO2, CO, Ozone (µg/m³, CO in mg/m³). Leave a value empty if unknown.';

function toCsv(rows: Record<string, unknown>[]) {
  return [COLS.join(','), ...rows.map((r) => COLS.map((c) => (typeof r[c] === 'number' ? Math.round((r[c] as number) * 100) / 100 : (r[c] ?? '')) as string).join(','))].join('\n');
}

function parseCsv(text: string) {
  const lines = text.trim().split(/\r?\n/).filter((l) => l.trim() !== '');
  if (lines.length < 2) throw new Error('Paste a header line and at least one data line.');
  const head = lines[0].split(',').map((h) => h.trim());
  if (head[0] !== 'date') throw new Error('The first column must be "date".');
  const bad = head.filter((h) => !(COLS as readonly string[]).includes(h));
  if (bad.length) throw new Error(`Unknown column(s): ${bad.join(', ')}.`);
  return lines.slice(1).map((l, i) => {
    const cells = l.split(',').map((c) => c.trim());
    const row: Record<string, string | number | null> = {};
    head.forEach((h, j) => {
      const v = cells[j] ?? '';
      if (h === 'date') row[h] = v;
      else if (v === '') row[h] = null;
      else if (!Number.isFinite(Number(v))) throw new Error(`Line ${i + 2}: ${h} is not a number ("${v}").`);
      else row[h] = Number(v);
    });
    return row;
  });
}

export default function ForecastForm({ city }: { city: string }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<ForecastResult | null>(null);

  async function loadStored() {
    setErr(null); setRes(null); setBusy(true);
    try {
      const all = await api.pollution(city);
      const dated = all.filter((r) => r.date).slice(-30);
      if (dated.length === 0) throw new Error('No stored readings for this city.');
      setText(toCsv(dated.map((r) => ({ date: r.date, PM25: r.pm25, PM10: r.pm10, NO2: r.no2, NOx: r.nox, SO2: r.so2, CO: r.co, Ozone: r.ozone }))));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  async function run() {
    setErr(null); setRes(null); setBusy(true);
    try { setRes(await api.forecast({ city, rows: parseCsv(text) })); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Card title={`Forecast tomorrow's PM2.5 for ${city} from daily readings`}
      note="The models only use the last 30 days of readings you give. They are the models from the evaluation above: on the test period the LSTM had a higher RMSE than persistence in all four cities, and XGBoost had a lower RMSE than persistence only in Delhi. Treat this as a demonstration, not an air quality forecast service.">
      <p className="text-xs text-slate-500 mb-2">{SHOWN} At least 30 calendar days and PM2.5 on at least 15 of the last 30 days are required.</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} spellCheck={false}
        placeholder={'date,PM25,PM10,NO2,NOx,SO2,CO,Ozone\n2023-03-01,80,150,40,50,10,1.2,30'}
        wrap="off" className="w-full rounded border border-slate-300 p-2 font-mono text-xs whitespace-pre overflow-x-auto" aria-label="Daily readings CSV" />
      <div className="flex flex-wrap gap-2 mt-2">
        <button onClick={loadStored} disabled={busy} className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50">Load last 30 stored days</button>
        <button onClick={run} disabled={busy || text.trim() === ''} className="rounded bg-blue-600 text-white px-3 py-1.5 text-sm hover:bg-blue-700 disabled:opacity-50">{busy ? 'Working…' : 'Forecast'}</button>
      </div>
      {err && <div role="alert" className="mt-3 rounded border border-red-200 bg-red-50 text-red-800 p-3 text-sm">{err}</div>}
      {res && (
        <div className="mt-3 text-sm">
          <p className="font-semibold">Estimate for {res.forecast_for} (µg/m³)</p>
          <table className="text-sm mt-1"><tbody>
            <tr><td className="pr-6 py-0.5">LSTM</td><td>{fmt(res.lstm_pm25)}</td></tr>
            <tr><td className="pr-6 py-0.5">XGBoost</td><td>{fmt(res.xgboost_pm25)}</td></tr>
            <tr><td className="pr-6 py-0.5">Persistence (last PM2.5{res.last_pm25_was_missing ? ', carried forward' : ''})</td><td>{fmt(res.persistence_pm25)}</td></tr>
          </tbody></table>
          <p className="text-xs text-slate-500 mt-2">
            {res.missing_values_in_window} of {res.window_days * 7} values in the window were empty and filled from earlier days or training medians. Models were trained on data up to {res.trained_through ?? 'unknown'}; your last date is {res.as_of}.
          </p>
        </div>
      )}
    </Card>
  );
}
