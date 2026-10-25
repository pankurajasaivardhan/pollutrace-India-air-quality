'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface NavigationProps {
  selectedCity: string;
  onCityChange: (city: string) => void;
  currentPage: string;
  cities?: string[];
}

export default function Navigation({
  selectedCity,
  onCityChange,
  currentPage,
  cities: cityList,
}: NavigationProps) {
  const [isOpen, setIsOpen] = useState(false);

  const cities = cityList && cityList.length ? cityList : ['Delhi', 'Mumbai', 'Bengaluru', 'Hyderabad'];
  const pages = [
    { name: 'Dashboard', href: '/' },
    { name: 'Predictions', href: '/predictions' },
    { name: 'Sources', href: '/sources' },
    { name: 'Anomalies', href: '/anomalies' },
    { name: 'Metrics', href: '/metrics' },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 shadow-2xl border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-lg flex items-center justify-center transform group-hover:scale-110 transition-transform shadow-lg">
              <span className="text-white font-bold text-lg">P</span>
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-white font-bold text-sm">PolluTrace</span>
              <span className="text-cyan-400 text-xs font-semibold">AI</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {pages.map((page) => (
              <Link
                key={page.href}
                href={page.href}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  currentPage === page.href
                    ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/50'
                    : 'text-gray-300 hover:text-white hover:bg-slate-700'
                }`}
              >
                {page.name}
              </Link>
            ))}
          </div>

          {/* City Selector and Mobile Menu */}
          <div className="flex items-center space-x-4">
            {/* City Dropdown */}
            <div className="relative group">
              <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors flex items-center space-x-2 border border-slate-600 hover:border-cyan-400">
                <span>{selectedCity}</span>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  />
                </svg>
              </button>

              {/* Dropdown Menu */}
              <div className="absolute right-0 mt-0 w-40 bg-slate-800 rounded-lg shadow-xl border border-slate-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 transform origin-top">
                {cities.map((city) => (
                  <button
                    key={city}
                    onClick={() => onCityChange(city)}
                    className={`block w-full text-left px-4 py-3 font-medium transition-colors ${
                      selectedCity === city
                        ? 'bg-cyan-500 text-white'
                        : 'text-gray-300 hover:bg-slate-700 hover:text-white'
                    }`}
                  >
                    {city}
                  </button>
                ))}
              </div>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="md:hidden text-white hover:bg-slate-700 p-2 rounded-lg"
            >
              {isOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden pb-4 space-y-2 border-t border-slate-700 pt-4">
            {pages.map((page) => (
              <Link
                key={page.href}
                href={page.href}
                className={`block px-4 py-2 rounded-lg font-medium transition-all ${
                  currentPage === page.href
                    ? 'bg-cyan-500 text-white'
                    : 'text-gray-300 hover:bg-slate-700'
                }`}
                onClick={() => setIsOpen(false)}
              >
                {page.name}
              </Link>
            ))}

            {/* Mobile City Selector */}
            <div className="px-4 py-2 border-t border-slate-700 mt-4 pt-4">
              <p className="text-gray-400 text-sm mb-2">Select City:</p>
              <div className="grid grid-cols-2 gap-2">
                {cities.map((city) => (
                  <button
                    key={city}
                    onClick={() => {
                      onCityChange(city);
                      setIsOpen(false);
                    }}
                    className={`px-3 py-2 rounded-lg font-medium transition-colors ${
                      selectedCity === city
                        ? 'bg-cyan-500 text-white'
                        : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                    }`}
                  >
                    {city}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
