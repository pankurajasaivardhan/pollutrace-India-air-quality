'use client';
import PageShell from '@/components/PageShell';
import { Card, Status, fmt } from '@/components/State';
import { api } from '@/lib/api';
import { useApi } from '@/lib/useApi';

function Anomalies({ city }: { city: string }) {
  const { data, error, loading } = useApi(() => api.anomalies(city), [city]);
  const flagged = data?.filter((r) => r.is_anomaly) ?? [];
  return (
    <>
      <Status loading={loading} error={error} empty={!!data && data.length === 0}
        emptyText="No anomaly results loaded (needs anomalies_test_period.csv from the pipeline)." />
      {data && data.length > 0 && (
        <Card title={`${flagged.length} of ${data.length} test-period days flagged`}
          note="Unsupervised autoencoder with no ground-truth labels, so this is not an accuracy figure. The threshold is the 95th percentile of validation-period reconstruction error; the last column is a flagged day's error as a multiple of it. A flag means the reconstruction error exceeds the validation-derived threshold. It does not establish a cause or a distribution shift.">
          <div className="max-h-96 overflow-auto"><table className="w-full text-sm min-w-[340px]"><thead className="sticky top-0 bg-white"><tr className="text-left text-slate-500"><th className="pr-4 whitespace-nowrap">Date</th><th className="pr-4 whitespace-nowrap">PM2.5</th><th className="whitespace-nowrap">Error / threshold</th></tr></thead>
            <tbody>{flagged.map((r) => <tr key={r.date} className="border-t"><td className="py-1 pr-4 whitespace-nowrap">{r.date}</td><td className="pr-4">{fmt(r.pm25)}</td><td>{BAND[r.severity ?? ''] ?? ''}</td></tr>)}</tbody></table></div>
        </Card>
      )}
    </>
  );
}

const BAND: Record<string, string> = { low: '1x to 2x', medium: '2x to 3x', high: 'above 3x' };

export default function Page() {
  return <PageShell page="/anomalies" title="Unusual days" subtitle="Autoencoder reconstruction-error flags on the test period">{(c) => <Anomalies city={c} />}</PageShell>;
}
