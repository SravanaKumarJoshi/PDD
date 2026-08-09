'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  Target,
  Sparkles,
  Award,
  BarChart3,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react';

export default function OptimizationPage() {
  const [topN, setTopN] = useState(15);
  const [generations, setGenerations] = useState(50);
  const [minBio, setMinBio] = useState(6);

  const [loading, setLoading] = useState(false);
  const [optResult, setOptResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunOptimization = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchApi<any>('/optimization/pareto', {
        method: 'POST',
        body: JSON.stringify({
          top_n: topN,
          n_generations: generations,
          min_biocompatibility: minBio,
        }),
      });
      setOptResult(data);
    } catch (err: any) {
      setError(err.message || 'NSGA-II optimization execution failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
          <Target className="w-3.5 h-3.5" />
          <span>Non-dominated Sorting Genetic Algorithm II (NSGA-II)</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          🎯 Multi-Objective Optimization
        </h1>
        <p className="mt-1 text-sm text-gray-300">
          Explore Pareto-optimal trade-offs between competing biomedical objectives: Tensile Strength (maximize), Biodegradability (optimize), and Biocompatibility (maximize).
        </p>
      </div>

      {/* Configuration Card */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-gray-800 space-y-6">
        <h2 className="text-lg font-bold text-white border-b border-gray-800 pb-3 flex items-center gap-2">
          <Target className="w-5 h-5 text-emerald-400" />
          <span>NSGA-II Genetic Algorithm Settings</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>Top-N Candidates</span>
              <span className="font-bold text-emerald-400">{topN}</span>
            </div>
            <input
              type="range"
              min="5"
              max="50"
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-gray-900 rounded-lg cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>Generations</span>
              <span className="font-bold text-cyan-400">{generations}</span>
            </div>
            <input
              type="range"
              min="10"
              max="200"
              step="10"
              value={generations}
              onChange={(e) => setGenerations(Number(e.target.value))}
              className="w-full accent-cyan-500 bg-gray-900 rounded-lg cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>Min Biocompatibility Filter</span>
              <span className="font-bold text-teal-400">{minBio}/10</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={minBio}
              onChange={(e) => setMinBio(Number(e.target.value))}
              className="w-full accent-teal-500 bg-gray-900 rounded-lg cursor-pointer"
            />
          </div>
        </div>

        <button
          onClick={handleRunOptimization}
          disabled={loading}
          className="w-full btn-primary py-3 text-sm flex items-center justify-center gap-2 rounded-xl shadow-xl"
        >
          {loading ? (
            <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>Run NSGA-II Optimization</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Render */}
      {optResult && (
        <div className="space-y-8">
          {/* Summary Banner */}
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-xs flex items-center justify-between">
            <span className="font-bold text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Found {optResult.pareto_count} Pareto-Optimal Materials out of {optResult.total_evaluated} Candidates
            </span>
            <span className="text-gray-400 text-[11px]">3 Competing Objectives Evaluated</span>
          </div>

          {/* Pareto Candidates Grid */}
          <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" />
              <span>⭐ Pareto-Optimal Candidate Materials</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Polymer</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Tensile Strength (MPa)</th>
                    <th className="py-3 px-4">Biodegradation Days</th>
                    <th className="py-3 px-4">Biocompatibility</th>
                    <th className="py-3 px-4">Pareto Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {optResult.candidates?.map((c: any, idx: number) => (
                    <tr
                      key={idx}
                      className={c.is_pareto ? 'bg-emerald-500/10 font-medium hover:bg-emerald-500/20' : 'hover:bg-gray-800/40'}
                    >
                      <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                        {c.is_pareto && <span className="text-amber-400">⭐</span>}
                        {c.polymer}
                      </td>
                      <td className="py-3 px-4 text-emerald-400">{c.category}</td>
                      <td className="py-3 px-4 font-bold">{c.tensile_strength}</td>
                      <td className="py-3 px-4">{c.biodegradation_days}</td>
                      <td className="py-3 px-4 font-bold text-teal-300">{c.biocompatibility}/10</td>
                      <td className="py-3 px-4">
                        {c.is_pareto ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            Pareto-Optimal
                          </span>
                        ) : (
                          <span className="text-gray-500">Dominated</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Explanation Banner */}
          <div className="p-4 rounded-2xl bg-gray-900/80 border border-gray-800 text-xs text-gray-300 leading-relaxed">
            <strong className="text-emerald-400">About Pareto Optimality: </strong>
            Pareto-optimal means no other material in the candidate set is superior in all three objectives simultaneously. These candidate materials represent the best possible trade-offs between structural strength, biodegradation timeframe, and biological toxicity safety.
          </div>
        </div>
      )}
    </div>
  );
}
