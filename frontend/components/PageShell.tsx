'use client';
import { useState } from 'react';
import Navigation from '@/components/Navigation';
import { api } from '@/lib/api';
import { useApi } from '@/lib/useApi';

export default function PageShell({ page, title, subtitle, children }: {
  page: string; title: string; subtitle?: string;
  children: (city: string) => React.ReactNode;
}) {
  const [city, setCity] = useState('Delhi');
  const cities = useApi(() => api.cities(), []);
  return (
    <div className="min-h-screen">
      <Navigation selectedCity={city} onCityChange={setCity} currentPage={page} cities={cities.data ?? undefined} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header>
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          {subtitle && <p className="text-slate-600 mt-1">{subtitle}</p>}
          <p className="text-sm text-slate-500 mt-1">City: <b>{city}</b></p>
        </header>
        {children(city)}
      </main>
    </div>
  );
}
