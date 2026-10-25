'use client';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PageShell from '@/components/PageShell';
import { Card, Status, fmt } from '@/components/State';
import { api, PollutionRow } from '@/lib/api';
import { useApi } from '@/lib/useApi';

function monthly(rows: PollutionRow[]) {
  const acc = new Map<string, { s: number; n: number }>();
  for (const r of rows) {
    if (!r.date || r.pm25 == null) continue;
    const k = r.date.slice(0, 7);
    const a = acc.get(k) ?? { s: 0, n: 0 };
    a.s += r.pm25; a.n += 1; acc.set(k, a);
  }
  return [...acc.entries()].sort().map(([month, a]) => ({ month, pm25: +(a.s / a.n).toFixed(1) }));
}

function Dashboard({ city }: { city: string }) {
  const { data, error, loading } = useApi(() => api.pollution(city), [city]);
  const series = data ? monthly(data) : [];
  const measured = data?.filter((r) => r.pm25 != null) ?? [];
  const last = measured[measured.length - 1];
  return (
    <>
      <Status loading={loading} error={error} empty={!!data && measured.length === 0}
        emptyText="No PM2.5 history loaded. Load pipeline outputs with pipeline/load_db.py (needs city_daily.csv)." />
      {series.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card title="Latest historical day"><p className="text-3xl font-bold">{fmt(last?.pm25)} <span className="text-base font-normal text-slate-500">µg/m³</span></p><p className="text-sm text-slate-500">{last?.date}</p></Card>
            <Card title="Days with PM2.5"><p className="text-3xl font-bold">{measured.length}</p></Card>
            <Card title="Period"><p className="text-xl font-semibold">{series[0].month} to {series[series.length - 1].month}</p></Card>
          </div>
          <Card title="Monthly mean PM2.5 (µg/m³)" note="City-level daily mean of the reporting stations (their set changes over time), then averaged per month. Months with no measurements are omitted.">
            <div className="h-80"><ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month" minTickGap={40} /><YAxis /><Tooltip />
                <Line type="monotone" dataKey="pm25" stroke="#2563eb" dot={false} strokeWidth={2} /></LineChart>
            </ResponsiveContainer></div>
          </Card>
        </>
      )}
    </>
  );
}

export default function Page() {
  return <PageShell page="/" title="PM2.5 history" subtitle="Historical measurements, 2010 to 2023. For current station data, use Station readings.">{(c) => <Dashboard city={c} />}</PageShell>;
}
