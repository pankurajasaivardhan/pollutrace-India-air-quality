'use client';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PageShell from '@/components/PageShell';
import { Card, Status, fmt } from '@/components/State';
import { api } from '@/lib/api';
import { useApi } from '@/lib/useApi';

function Sources({ city }: { city: string }) {
  const { data, error, loading } = useApi(() => api.sources(city), [city]);
  return (
    <>
      <Status loading={loading} error={error} />
      {data && (
        <>
          <div className="rounded-lg border border-amber-200 bg-amber-50 text-amber-900 p-4 text-sm">
            This ranks which co-measured pollutants are most associated with PM2.5 in a statistical model. It does <b>not</b> identify emission sources or causes.
          </div>
          <Card title="Association with PM2.5 (mean |SHAP|, µg/m³)" note={`Model fit on the held-out test period: R² = ${fmt(data.model_test_r2, 3)}. R² measures how well the model predicts PM2.5 here. It does not validate the ranking as causal.`}>
            <div style={{ height: 60 + data.ranking.length * 34 }}><ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.ranking} layout="vertical" margin={{ left: 8, right: 24 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" /><YAxis type="category" dataKey="pollutant" width={76} interval={0} /><Tooltip />
                <Bar dataKey="mean_abs_shap" fill="#2563eb" /></BarChart>
            </ResponsiveContainer></div>
          </Card>
        </>
      )}
    </>
  );
}

export default function Page() {
  return <PageShell page="/sources" title="Pollutants associated with PM2.5" subtitle="Statistical association, not source apportionment">{(c) => <Sources city={c} />}</PageShell>;
}
