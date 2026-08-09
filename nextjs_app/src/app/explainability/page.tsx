'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  Microscope,
  HelpCircle,
  ArrowRightLeft,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';

export default function ExplainabilityPage() {
  const [globalFeatures, setGlobalFeatures] = useState<any[]>([]);
  const [materialsList, setMaterialsList] = useState<string[]>([]);
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [materialExplanation, setMaterialExplanation] = useState<any | null>(null);

  // Material Comparison
  const [matA, setMatA] = useState<string>('');
  const [matB, setMatB] = useState<string>('');
  const [comparisonResult, setComparisonResult] = useState<any | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        const [glob, matData] = await Promise.all([
          fetchApi<any>('/explainability/global'),
          fetchApi<any[]>('/materials?limit=500'),
        ]);

        if (glob?.features) {
          setGlobalFeatures(glob.features);
        }

        if (Array.isArray(matData) && matData.length > 0) {
          const names = matData.map((m) => m.polymer).filter(Boolean);
          setMaterialsList(names);
          if (names.length > 0) {
            setSelectedMaterial(names[0]);
            setMatA(names[0]);
            setMatB(names[1] || names[0]);
          }
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load SHAP explainability dataset.');
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  // Fetch per-material SHAP
  useEffect(() => {
    if (!selectedMaterial) return;
    async function loadMatExplanation() {
      try {
        const data = await fetchApi<any>(`/explainability/material/${encodeURIComponent(selectedMaterial)}`);
        setMaterialExplanation(data);
      } catch (e) {
        console.error(e);
      }
    }
    loadMatExplanation();
  }, [selectedMaterial]);

  // Run Material Comparison
  const handleCompare = async () => {
    if (!matA || !matB || matA === matB) return;
    try {
      const data = await fetchApi<any>('/explainability/compare', {
        method: 'POST',
        body: JSON.stringify({ polymer_a: matA, polymer_b: matB }),
      });
      setComparisonResult(data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
          <Microscope className="w-3.5 h-3.5" />
          <span>SHapley Additive exPlanations (SHAP)</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          🔍 SHAP Explainability Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-300">
          Understand why the machine learning models recommend specific natural polysaccharides over others with feature attribution scores.
        </p>
      </div>

      {/* About SHAP Banner */}
      <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-start gap-3">
        <Info className="w-5 h-5 shrink-0 mt-0.5 text-indigo-400" />
        <div>
          <strong className="font-semibold text-indigo-200">How SHAP Works:</strong> SHAP values quantify the marginal contribution of each physical feature to the model's suitability prediction. Positive SHAP values (+0.35) increase predicted suitability, while negative values (-0.20) penalize suitability.
        </div>
      </div>

      {/* Global Feature Importance */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          <span>🌍 Global Feature Importance Across All Materials</span>
        </h2>
        <div className="space-y-2">
          {globalFeatures.map((item, i) => (
            <div key={i} className="flex items-center gap-3 text-xs">
              <span className="w-48 font-semibold text-gray-300 truncate">{item.label}</span>
              <div className="flex-1 bg-gray-900 rounded-full h-3 overflow-hidden border border-gray-800">
                <div
                  className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(item.importance * 400, 100).toFixed(1)}%` }}
                />
              </div>
              <span className="w-20 text-right font-mono font-bold text-emerald-400">
                +{item.importance?.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-Material Explanation */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Microscope className="w-5 h-5 text-cyan-400" />
            <span>🔬 Per-Material SHAP Breakdown</span>
          </h2>

          <div className="w-64">
            <select
              value={selectedMaterial}
              onChange={(e) => setSelectedMaterial(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
            >
              {materialsList.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
        </div>

        {materialExplanation && (
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 text-xs text-gray-200 leading-relaxed">
              <strong className="text-emerald-400">Human-Readable Reason: </strong>
              {materialExplanation.explanation_text}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Feature</th>
                    <th className="py-3 px-4">SHAP Value</th>
                    <th className="py-3 px-4">Direction</th>
                    <th className="py-3 px-4">Actual Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {materialExplanation.contributions?.map((c: any, idx: number) => (
                    <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">{c.label}</td>
                      <td className="py-3 px-4 font-mono font-bold">
                        <span className={c.shap_value > 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {c.shap_value > 0 ? `+${c.shap_value.toFixed(4)}` : c.shap_value.toFixed(4)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {c.direction === 'positive' ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            ✅ Positive Impact
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                            ❌ Negative Impact
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-bold text-gray-200">{c.actual_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Compare Two Materials */}
      <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-6">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <ArrowRightLeft className="w-5 h-5 text-indigo-400" />
          <span>⚖️ Compare SHAP Attribution Between Two Materials</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Material A</label>
            <select
              value={matA}
              onChange={(e) => setMatA(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:border-emerald-500"
            >
              {materialsList.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Material B</label>
            <select
              value={matB}
              onChange={(e) => setMatB(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:border-emerald-500"
            >
              {materialsList.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleCompare}
          className="btn-primary text-xs flex items-center gap-2 px-6 py-2.5 rounded-xl"
        >
          <ArrowRightLeft className="w-4 h-4" />
          <span>Compare {matA} vs {matB}</span>
        </button>

        {comparisonResult && (
          <div className="overflow-x-auto pt-2">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                <tr>
                  <th className="py-3 px-4">Feature</th>
                  <th className="py-3 px-4">SHAP {matA}</th>
                  <th className="py-3 px-4">SHAP {matB}</th>
                  <th className="py-3 px-4">Difference</th>
                  <th className="py-3 px-4">Favors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {comparisonResult.comparisons?.map((c: any, idx: number) => (
                  <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-white">{c.label}</td>
                    <td className="py-3 px-4 font-mono">{c.shap_a?.toFixed(4)}</td>
                    <td className="py-3 px-4 font-mono">{c.shap_b?.toFixed(4)}</td>
                    <td className="py-3 px-4 font-mono font-bold text-emerald-400">{c.difference > 0 ? `+${c.difference.toFixed(4)}` : c.difference.toFixed(4)}</td>
                    <td className="py-3 px-4 font-bold text-teal-300">🏆 {c.favors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
