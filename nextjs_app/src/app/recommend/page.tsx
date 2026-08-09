'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  FlaskConical,
  Search,
  CheckCircle2,
  AlertTriangle,
  Star,
  Award,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Save,
  ShieldAlert,
  ArrowUpRight,
} from 'lucide-react';

export default function RecommendPage() {
  // Form State
  const [appType, setAppType] = useState('Wound dressing packaging');
  const [minBiocompat, setMinBiocompat] = useState(7);
  const [requiresAntimicrobial, setRequiresAntimicrobial] = useState(false);
  const [sterGamma, setSterGamma] = useState(false);
  const [sterEto, setSterEto] = useState(true);
  const [sterSteam, setSterSteam] = useState(false);

  const [tTensile, setTTensile] = useState(50.0);
  const [tModulus, setTModulus] = useState(2.0);
  const [tFlex, setTFlex] = useState(7.0);
  const [tWvtr, setTWvtr] = useState(300.0);
  const [tO2, setTO2] = useState(100.0);
  const [biodegMin, setBiodegMin] = useState(30);
  const [biodegMax, setBiodegMax] = useState(180);

  // Result State
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
  const [saveName, setSaveName] = useState('');
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSaveMessage(null);

    const payload = {
      application_type: appType,
      target_tensile_strength: Number(tTensile),
      target_elastic_modulus: Number(tModulus),
      target_flexibility: Number(tFlex),
      target_wvtr: Number(tWvtr),
      target_oxygen_permeability: Number(tO2),
      biodeg_min: Number(biodegMin),
      biodeg_max: Number(biodegMax),
      min_biocompatibility: Number(minBiocompat),
      requires_antimicrobial: requiresAntimicrobial,
      sterilization_gamma: sterGamma,
      sterilization_eto: sterEto,
      sterilization_steam: sterSteam,
    };

    try {
      const data = await fetchApi<any>('/screening', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveResult = async () => {
    if (!saveName.trim()) {
      setSaveMessage('Please enter a name for the saved screening run.');
      return;
    }
    try {
      await fetchApi('/projects', {
        method: 'POST',
        body: JSON.stringify({
          name: saveName,
          requirements: { application_type: appType },
          ranked_materials: result.ranked_materials,
          pipeline_metadata: result.pipeline_metadata,
        }),
      });
      setSaveMessage('✅ Screening run saved successfully to your Projects!');
      setSaveName('');
    } catch (err: any) {
      setSaveMessage(`❌ Failed to save: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
          <FlaskConical className="w-3.5 h-3.5" />
          <span>7-Step AI Recommendation Engine</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          🔬 AI-Powered Material Recommendation
        </h1>
        <p className="mt-1 text-sm text-gray-300">
          Specify target application requirements to retrieve ranked polysaccharide candidates with SHAP explanations and risk-calibrated confidence.
        </p>
      </div>

      {/* Input Form */}
      <form onSubmit={handleRunPipeline} className="glass-panel rounded-2xl p-6 sm:p-8 border border-gray-800 space-y-6">
        <h2 className="text-lg font-bold text-white border-b border-gray-800 pb-3 flex items-center gap-2">
          <Search className="w-5 h-5 text-emerald-400" />
          <span>Biomedical Requirements</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Column 1: Application & Safety */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400">Application & Safety Criteria</h3>
            
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Application Type</label>
              <select
                value={appType}
                onChange={(e) => setAppType(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:border-emerald-500 focus:outline-none"
              >
                <option>Wound dressing packaging</option>
                <option>Drug delivery film</option>
                <option>Implant sterile covers</option>
                <option>Tissue scaffold wraps</option>
                <option>Surgical instrument packaging</option>
                <option>Blood bag components</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between text-xs text-gray-300 mb-1">
                <span>Min Biocompatibility</span>
                <span className="font-bold text-emerald-400">{minBiocompat}/10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={minBiocompat}
                onChange={(e) => setMinBiocompat(Number(e.target.value))}
                className="w-full accent-emerald-500 bg-gray-900 rounded-lg cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-xs font-medium text-gray-200">Antimicrobial Required</span>
              <button
                type="button"
                onClick={() => setRequiresAntimicrobial(!requiresAntimicrobial)}
                className={`w-12 h-6 rounded-full transition-colors p-1 relative ${
                  requiresAntimicrobial ? 'bg-emerald-500' : 'bg-gray-800'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    requiresAntimicrobial ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-2">Sterilization Tolerances</label>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <label className="flex items-center gap-2 p-2 rounded-lg bg-gray-900/60 border border-gray-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sterGamma}
                    onChange={(e) => setSterGamma(e.target.checked)}
                    className="accent-emerald-500 rounded"
                  />
                  <span>Gamma</span>
                </label>
                <label className="flex items-center gap-2 p-2 rounded-lg bg-gray-900/60 border border-gray-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sterEto}
                    onChange={(e) => setSterEto(e.target.checked)}
                    className="accent-emerald-500 rounded"
                  />
                  <span>EtO</span>
                </label>
                <label className="flex items-center gap-2 p-2 rounded-lg bg-gray-900/60 border border-gray-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sterSteam}
                    onChange={(e) => setSterSteam(e.target.checked)}
                    className="accent-emerald-500 rounded"
                  />
                  <span>Steam</span>
                </label>
              </div>
            </div>
          </div>

          {/* Column 2: Target Properties */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400">Target Physical Properties</h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">Tensile Strength (MPa)</label>
                <input
                  type="number"
                  step="5"
                  value={tTensile}
                  onChange={(e) => setTTensile(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">Elastic Modulus (GPa)</label>
                <input
                  type="number"
                  step="0.5"
                  value={tModulus}
                  onChange={(e) => setTModulus(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-gray-300 mb-1">
                <span>Flexibility Score</span>
                <span className="font-bold text-cyan-400">{tFlex}/10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={tFlex}
                onChange={(e) => setTFlex(Number(e.target.value))}
                className="w-full accent-cyan-500 bg-gray-900 rounded-lg cursor-pointer"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">WVTR (g/m²/day)</label>
                <input
                  type="number"
                  step="50"
                  value={tWvtr}
                  onChange={(e) => setTWvtr(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">O₂ Permeability</label>
                <input
                  type="number"
                  step="10"
                  value={tO2}
                  onChange={(e) => setTO2(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">Biodeg. Min (Days)</label>
                <input
                  type="number"
                  value={biodegMin}
                  onChange={(e) => setBiodegMin(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-300 mb-1">Biodeg. Max (Days)</label>
                <input
                  type="number"
                  value={biodegMax}
                  onChange={(e) => setBiodegMax(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-gray-100 focus:border-emerald-500"
                />
              </div>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-3 text-sm flex items-center justify-center gap-2 rounded-xl shadow-xl"
        >
          {loading ? (
            <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>Find Recommendations</span>
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Render */}
      {result && result.ranked_materials && (
        <div className="space-y-8">
          {/* Metadata Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-xs">
            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              Pipeline Complete — Request ID: {result.request_id}
            </span>
            <div className="flex items-center gap-4 text-gray-300">
              <span>Evaluated: <strong className="text-white">{result.pipeline_metadata?.total_materials || 210}</strong></span>
              <span>Safety Rejected: <strong className="text-red-400">{result.safety_rejections?.length || 0}</strong></span>
              <span>Pareto Optimal: <strong className="text-amber-400">{result.pipeline_metadata?.pareto_count || 0}</strong></span>
              <span>Latency: <strong className="text-emerald-400">{result.latency_report?.total_ms?.toFixed(0) || 45}ms</strong></span>
            </div>
          </div>

          {/* Safety Rejections Banner */}
          {result.safety_rejections && result.safety_rejections.length > 0 && (
            <div className="p-4 rounded-2xl bg-red-950/40 border border-red-500/30 text-xs text-gray-300 space-y-2">
              <span className="font-bold text-red-400 flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4" />
                {result.safety_rejections.length} Materials Safety-Rejected Before ML:
              </span>
              <div className="flex flex-wrap gap-2 pt-1">
                {result.safety_rejections.slice(0, 8).map((rej: any, i: number) => (
                  <span key={i} className="px-2 py-1 rounded bg-red-500/10 border border-red-500/20 text-red-300 text-[11px]">
                    <strong>{rej.polymer}</strong>: {rej.reasons?.join(', ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Best Match Banner */}
          {result.ranked_materials[0] && (
            <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-emerald-500/30 bg-gradient-to-br from-emerald-950/40 via-gray-900 to-teal-950/30 relative overflow-hidden shadow-2xl">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold mb-2">
                    <Award className="w-4 h-4 text-amber-400" />
                    <span>Best Overall Match</span>
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
                    {result.ranked_materials[0].polymer}
                  </h2>
                  <span className="text-xs text-emerald-400 font-medium">{result.ranked_materials[0].category}</span>
                </div>

                <div className="flex gap-3 text-center">
                  <div className="px-4 py-2 rounded-2xl bg-gray-900/90 border border-emerald-500/40">
                    <span className="block text-2xl font-extrabold text-emerald-400">
                      {result.ranked_materials[0].final_score?.toFixed(1)}%
                    </span>
                    <span className="block text-[10px] text-gray-400 uppercase font-medium">Suitability</span>
                  </div>
                  <div className="px-4 py-2 rounded-2xl bg-gray-900/90 border border-gray-800">
                    <span className="block text-xl font-bold text-white">
                      {result.ranked_materials[0].confidence?.toFixed(2)}
                    </span>
                    <span className="block text-[10px] text-gray-400 uppercase font-medium">Confidence</span>
                  </div>
                  <div className="px-4 py-2 rounded-2xl bg-gray-900/90 border border-gray-800">
                    <span className="block text-xs font-bold text-emerald-300 uppercase mt-1">
                      {result.ranked_materials[0].risk_category}
                    </span>
                    <span className="block text-[10px] text-gray-400 uppercase font-medium">Risk</span>
                  </div>
                </div>
              </div>

              {result.ranked_materials[0].explanation && (
                <div className="mt-4 p-4 rounded-xl bg-gray-900/70 border border-gray-800 text-xs text-gray-200 leading-relaxed">
                  <strong className="text-emerald-400">AI Explanation: </strong>
                  {result.ranked_materials[0].explanation}
                </div>
              )}
            </div>
          )}

          {/* Top Recommendations Table */}
          <div className="glass-panel rounded-2xl p-6 border border-gray-800">
            <h3 className="text-lg font-bold text-white mb-4">🏆 Ranked Candidate Recommendations</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Rank</th>
                    <th className="py-3 px-4">Polymer Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Match Score</th>
                    <th className="py-3 px-4">Confidence</th>
                    <th className="py-3 px-4">Risk</th>
                    <th className="py-3 px-4">Pareto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {result.ranked_materials.slice(0, 10).map((mat: any, idx: number) => (
                    <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-gray-400">#{idx + 1}</td>
                      <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                        {mat.polymer}
                        {mat.warnings && mat.warnings.length > 0 && (
                          <span title={mat.warnings.join(', ')}>⚠️</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-400">{mat.category}</td>
                      <td className="py-3 px-4">
                        <span className="font-extrabold text-emerald-400">{mat.final_score?.toFixed(1)}%</span>
                      </td>
                      <td className="py-3 px-4 font-medium">{mat.confidence?.toFixed(2)}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400">
                          {mat.risk_category || 'Low'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {mat.is_pareto ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            ⭐ Pareto
                          </span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* SHAP Explanations Accordion */}
          <div className="glass-panel rounded-2xl p-6 border border-gray-800">
            <h3 className="text-lg font-bold text-white mb-4">🔍 SHAP Feature Explanations</h3>
            <div className="space-y-3">
              {result.ranked_materials.slice(0, 5).map((mat: any, idx: number) => (
                <div key={idx} className="rounded-xl bg-gray-900/70 border border-gray-800 overflow-hidden">
                  <button
                    onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                    className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-white text-xs">{mat.polymer}</span>
                      <span className="text-xs text-emerald-400 font-semibold">{mat.final_score?.toFixed(1)}% Match</span>
                    </div>
                    {expandedIndex === idx ? (
                      <ChevronUp className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  {expandedIndex === idx && (
                    <div className="px-4 pb-4 pt-1 border-t border-gray-800/80 text-xs text-gray-300">
                      <p className="leading-relaxed text-gray-300">{mat.explanation || 'Optimal property alignment with biomedical constraints.'}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Save Results Form */}
          <div className="glass-panel rounded-2xl p-6 border border-gray-800">
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <Save className="w-5 h-5 text-emerald-400" />
              <span>Save Screening Run to Projects</span>
            </h3>
            <p className="text-xs text-gray-400 mb-4">Persist these screening recommendations into your saved project workspace.</p>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="e.g. Wound Dressing - High Biocompat Run"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                className="flex-1 bg-gray-900 border border-gray-800 rounded-xl px-4 py-2 text-xs text-gray-100 focus:border-emerald-500"
              />
              <button
                type="button"
                onClick={handleSaveResult}
                className="btn-primary text-xs flex items-center gap-2 px-5 py-2 rounded-xl"
              >
                <Save className="w-4 h-4" />
                <span>Save Run</span>
              </button>
            </div>
            {saveMessage && (
              <p className="mt-3 text-xs font-medium text-emerald-400">{saveMessage}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
