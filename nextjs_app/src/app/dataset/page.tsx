'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  Database,
  Search,
  Download,
  Filter,
  BarChart3,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

export default function DatasetBrowserPage() {
  const [materials, setMaterials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [sourceFilter, setSourceFilter] = useState('All');
  const [bioMin, setBioMin] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const loadDataset = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<any[]>('/materials?limit=500');
      setMaterials(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch materials dataset.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDataset();
  }, []);

  // Filtered dataset logic
  const filteredMaterials = materials.filter((m) => {
    if (categoryFilter !== 'All' && m.category !== categoryFilter) return false;
    if (sourceFilter === 'Literature Only' && m.is_augmented === 1) return false;
    if (sourceFilter === 'Augmented Only' && m.is_augmented === 0) return false;
    if (Number(m.biocompatibility) < bioMin) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const nameMatch = m.polymer?.toLowerCase().includes(q);
      const catMatch = m.category?.toLowerCase().includes(q);
      if (!nameMatch && !catMatch) return false;
    }
    return true;
  });

  // Calculate statistics
  const totalCount = materials.length;
  const filteredCount = filteredMaterials.length;
  const literatureCount = materials.filter((m) => m.is_augmented === 0).length;

  const categories = Array.from(new Set(materials.map((m) => m.category).filter(Boolean)));

  const getPropStats = (key: string) => {
    const vals = filteredMaterials.map((m) => Number(m[key])).filter((v) => !isNaN(v));
    if (!vals.length) return { min: 0, mean: 0, max: 0 };
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    return { min: min.toFixed(1), mean: mean.toFixed(1), max: max.toFixed(1) };
  };

  const tsStats = getPropStats('tensile_strength');
  const bioStats = getPropStats('biocompatibility');
  const flexStats = getPropStats('flexibility');
  const biodegStats = getPropStats('biodegradation_days');

  // CSV Export Download
  const handleDownloadCSV = () => {
    if (!filteredMaterials.length) return;
    const headers = ['polymer', 'category', 'tensile_strength', 'elastic_modulus', 'flexibility', 'biocompatibility', 'biodegradation_days', 'is_augmented'];
    const rows = filteredMaterials.map((m) =>
      headers.map((h) => JSON.stringify(m[h] ?? '')).join(',')
    );
    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `biopolymers_filtered_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
            <Database className="w-3.5 h-3.5" />
            <span>MySQL-Backed Catalog Source of Truth</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            📊 Dataset Browser
          </h1>
          <p className="mt-1 text-sm text-gray-300">
            View, filter, and export the material properties dataset across literature-sourced and augmented biopolymers.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={loadDataset}
            className="btn-secondary text-xs flex items-center gap-2 px-4 py-2 rounded-xl"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Reload</span>
          </button>
          <button
            onClick={handleDownloadCSV}
            disabled={!filteredMaterials.length}
            className="btn-primary text-xs flex items-center gap-2 px-5 py-2 rounded-xl"
          >
            <Download className="w-4 h-4" />
            <span>Download CSV ({filteredCount})</span>
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-4 border border-gray-800 text-center">
          <span className="block text-2xl font-extrabold text-white">{totalCount}</span>
          <span className="block text-[11px] text-gray-400 font-medium">Total Catalog Materials</span>
        </div>
        <div className="glass-card rounded-2xl p-4 border border-gray-800 text-center">
          <span className="block text-2xl font-extrabold text-cyan-400">{literatureCount}</span>
          <span className="block text-[11px] text-gray-400 font-medium">Literature Sourced</span>
        </div>
        <div className="glass-card rounded-2xl p-4 border border-gray-800 text-center">
          <span className="block text-2xl font-extrabold text-emerald-400">{filteredCount}</span>
          <span className="block text-[11px] text-gray-400 font-medium">Matching Filters</span>
        </div>
        <div className="glass-card rounded-2xl p-4 border border-gray-800 text-center">
          <span className="block text-2xl font-extrabold text-teal-400">{categories.length}</span>
          <span className="block text-[11px] text-gray-400 font-medium">Distinct Categories</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Filter className="w-4 h-4 text-emerald-400" />
          <span>Filters & Search</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-[11px] font-medium text-gray-300 mb-1">Category</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:border-emerald-500 focus:outline-none"
            >
              <option value="All">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-gray-300 mb-1">Data Source</label>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:border-emerald-500 focus:outline-none"
            >
              <option value="All">All Sources</option>
              <option value="Literature Only">Literature Only</option>
              <option value="Augmented Only">Augmented Only</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between text-[11px] text-gray-300 mb-1">
              <span>Min Biocompatibility</span>
              <span className="font-bold text-emerald-400">{bioMin}/10</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={bioMin}
              onChange={(e) => setBioMin(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-gray-900 rounded-lg cursor-pointer mt-1"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-gray-300 mb-1">Search Polymer Name</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-500 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="e.g. Chitosan, Alginate"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-gray-100 placeholder-gray-600 focus:border-emerald-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Material Catalog Data Table */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800">
        <h3 className="text-base font-bold text-white mb-4">📜 Material Catalog ({filteredCount} Records)</h3>

        {loading ? (
          <div className="py-12 text-center text-xs text-gray-400">
            <span className="inline-block w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-2" />
            <p>Loading catalog from MySQL database...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                <tr>
                  <th className="py-3 px-4">Polymer</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Tensile (MPa)</th>
                  <th className="py-3 px-4">Modulus (GPa)</th>
                  <th className="py-3 px-4">Flexibility</th>
                  <th className="py-3 px-4">Biocompat.</th>
                  <th className="py-3 px-4">Biodeg (Days)</th>
                  <th className="py-3 px-4">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {filteredMaterials.slice(0, 50).map((mat: any, idx: number) => (
                  <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-white">{mat.polymer}</td>
                    <td className="py-3 px-4 text-emerald-400">{mat.category}</td>
                    <td className="py-3 px-4">{mat.tensile_strength ?? 'N/A'}</td>
                    <td className="py-3 px-4">{mat.elastic_modulus ?? 'N/A'}</td>
                    <td className="py-3 px-4">{mat.flexibility ?? 'N/A'}</td>
                    <td className="py-3 px-4 font-bold text-teal-300">{mat.biocompatibility ?? 'N/A'}/10</td>
                    <td className="py-3 px-4">{mat.biodegradation_days ?? 'N/A'}</td>
                    <td className="py-3 px-4">
                      {mat.is_augmented === 1 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          Augmented
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Literature
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Numeric Properties Summary Stats */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          <span>Numeric Feature Statistics (Filtered Set)</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <span className="font-bold text-gray-200 block mb-2">Tensile Strength (MPa)</span>
            <div className="flex justify-between text-gray-400">
              <span>Min: <strong className="text-white">{tsStats.min}</strong></span>
              <span>Mean: <strong className="text-emerald-400">{tsStats.mean}</strong></span>
              <span>Max: <strong className="text-white">{tsStats.max}</strong></span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <span className="font-bold text-gray-200 block mb-2">Biocompatibility (1-10)</span>
            <div className="flex justify-between text-gray-400">
              <span>Min: <strong className="text-white">{bioStats.min}</strong></span>
              <span>Mean: <strong className="text-emerald-400">{bioStats.mean}</strong></span>
              <span>Max: <strong className="text-white">{bioStats.max}</strong></span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <span className="font-bold text-gray-200 block mb-2">Flexibility Score (1-10)</span>
            <div className="flex justify-between text-gray-400">
              <span>Min: <strong className="text-white">{flexStats.min}</strong></span>
              <span>Mean: <strong className="text-emerald-400">{flexStats.mean}</strong></span>
              <span>Max: <strong className="text-white">{flexStats.max}</strong></span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs">
            <span className="font-bold text-gray-200 block mb-2">Biodegradation Days</span>
            <div className="flex justify-between text-gray-400">
              <span>Min: <strong className="text-white">{biodegStats.min}</strong></span>
              <span>Mean: <strong className="text-emerald-400">{biodegStats.mean}</strong></span>
              <span>Max: <strong className="text-white">{biodegStats.max}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
