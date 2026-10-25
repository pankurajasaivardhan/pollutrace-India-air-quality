'use client';
import PageShell from '@/components/PageShell';
import { Card, Status, fmt } from '@/components/State';
import { api } from '@/lib/api';
import { useApi } from '@/lib/useApi';

import { MODEL_LABEL as LABEL } from '@/lib/labels';

function Metrics({ city }: { city: string }) {
  const { data, error, loading } = useApi(() => api.metrics(), []);
  const cities = [...new Set((data ?? []).map((r) => r.city))].filter((c) => c === city);
  return (
    <>
      <Status loading={loading} error={error} empty={!!data && cities.length === 0} emptyText="No metrics loaded for this city. Run the pipeline and pipeline/load_db.py." />
      {cities.map((c) => {
        const rows = data!.filter((r) => r.city === c);
        const best = Math.min(...rows.map((r) => r.rmse ?? Infinity));
        return (
          <Card key={c} title={c} note="Held-out chronological test period, scored only on days with a measured PM2.5. RMSE and MAE in µg/m³.">
            <table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Model</th><th className="pr-3">RMSE</th><th className="pr-3">MAE</th><th className="pr-3">R²</th><th>Test days</th></tr></thead>
              <tbody>{rows.map((r) => <tr key={r.model_type} className={`border-t ${r.rmse === best ? 'font-semibold bg-green-50' : ''}`}><td className="py-1">{LABEL[r.model_type] ?? r.model_type}</td><td className="pr-3">{fmt(r.rmse)}</td><td className="pr-3">{fmt(r.mae)}</td><td className="pr-3">{fmt(r.r2_score, 3)}</td><td>{r.n_test_days}</td></tr>)}</tbody></table>
            <p className="text-xs text-slate-500 mt-2">Best RMSE is highlighted.</p>
          </Card>
        );
      })}
    </>
  );
}

export default function Page() {
  return <PageShell page="/metrics" title="Model comparison" subtitle="Every model against the simple persistence baseline">{(c) => <Metrics city={c} />}</PageShell>;
}
