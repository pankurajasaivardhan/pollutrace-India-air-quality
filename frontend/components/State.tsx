import { Loader2 } from 'lucide-react';

export function Status({ loading, error, empty, emptyText }: { loading: boolean; error: string | null; empty?: boolean; emptyText?: string }) {
  if (loading) return <div className="flex items-center gap-2 text-slate-500 py-10"><Loader2 className="animate-spin" size={18} /> Loading…</div>;
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 text-red-800 p-4">Could not load data from the API ({error}). Is the Go server running and the database loaded?</div>;
  if (empty) return <div className="rounded-lg border border-amber-200 bg-amber-50 text-amber-900 p-4">{emptyText ?? 'No data for this selection.'}</div>;
  return null;
}

export function Card({ title, children, note }: { title: string; children: React.ReactNode; note?: string }) {
  return (
    <section className="rounded-xl bg-white shadow-sm border border-slate-200 p-5">
      <h2 className="font-semibold text-slate-900 mb-3">{title}</h2>
      {children}
      {note && <p className="text-xs text-slate-500 mt-3">{note}</p>}
    </section>
  );
}

export const fmt = (n: number | null | undefined, d = 1) => (n == null ? '–' : n.toFixed(d));
