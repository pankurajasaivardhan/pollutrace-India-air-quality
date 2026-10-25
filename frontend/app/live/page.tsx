'use client';
import { useState } from 'react';
import PageShell from '@/components/PageShell';
import { Card, fmt } from '@/components/State';
import { liveStation } from '@/lib/api';
import { useApi } from '@/lib/useApi';

const credit = (a: unknown): string => typeof a === 'string' ? a : a && typeof a === 'object' && 'name' in a ? String((a as {name: unknown}).name) : 'Attribution not supplied';
const date = (s: string) => new Date(s).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' }) + ' IST';
function Station({ city }: { city: string }) {
  const [refresh, setRefresh] = useState(0);
  const { data, loading, error } = useApi(() => liveStation(city), [city, refresh]);
  const current = !loading && !error ? data : null;
  return <>
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-950 text-sm">
      Station observations are separate from the historical research models. One station does not represent the whole city. No model forecasts or inferred AQI appear here.
    </div>
    <button className="rounded-lg bg-slate-900 text-white px-4 py-2 disabled:opacity-50" disabled={loading} onClick={() => setRefresh(v => v + 1)}>Check readings</button>
    <p className="text-xs text-slate-500">No background polling. The server checks OpenAQ at most once an hour per configured city, including failed requests.</p>
    {loading && <p role="status">Loading station readings...</p>}
    {error && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-950"><h2 className="font-semibold">Station readings unavailable</h2><p className="mt-2 break-words">{error}</p><p className="mt-2 text-sm">No historical values or modeled estimates have been substituted. Bengaluru has no cleared ambient monitor in this setup. Hyderabad has no cleared recent reading in this setup. Coverage can change; no city-wide values are inferred.</p></div>}
    {current && <>
      <Card title={current.station_name} note={current.note}>
        <div className="text-sm text-slate-600 space-y-1">
          <p>Provider: {current.provider?.name ?? 'Not supplied'} | Owner: {current.owner?.name ?? 'Not supplied'}</p>
          <p>Retrieved: {date(current.retrieved_at)}</p><p>Next check eligible after: {date(current.next_refresh_at)}</p>
          <a className="text-blue-700 underline" href={current.source_url} target="_blank" rel="noreferrer">Station details and source via OpenAQ</a>
        </div>
      </Card>
      {!current.readings.length && <p className="rounded-lg bg-amber-50 p-4">No valid measurements returned by this station. No values are filled in.</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {current.readings.map(r => <Card key={r.sensor_id} title={r.pollutant || r.parameter}>
          <p className="text-3xl font-bold">{fmt(r.value)} <span className="text-base font-normal text-slate-500">{r.unit || 'unit not supplied'}</span></p>
          <p className="text-sm text-slate-600 mt-2">Measured: {date(r.measured_at)}</p>
          <p className={`text-sm font-semibold mt-2 ${r.stale ? 'text-amber-800' : 'text-slate-700'}`}>{r.stale ? 'Stale reading' : 'Recent reading'} ({fmt(r.age_hours)} hours old at retrieval)</p>
        </Card>)}
      </div>
      <Card title="Data credits and limits">
        <p className="text-sm text-slate-600">Access through <a className="underline" href="https://openaq.org/">OpenAQ</a>. Credit also belongs to the station owner and provider shown above. Readings can be delayed or provisional. Not medical advice or an official pollution alert.</p>
        <ul className="mt-3 text-sm space-y-2">{current.licenses.map(l => <li key={l.id}>{l.sourceUrl ? <a className="underline text-blue-700" href={l.sourceUrl}>{l.name}</a> : l.name}{l.attribution ? <span> | Attribution: {credit(l.attribution)}</span> : null}</li>)}</ul>
      </Card>
    </>}
  </>;
}
export default function Page() { return <PageShell page="/live" title="Station air quality" subtitle="Latest available observations, with source and measurement time">{c => <Station key={c} city={c} />}</PageShell>; }
