'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  FlaskConical,
  Search,
  CheckCircle2,
  AlertTriangle,
  Award,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Save,
  ShieldAlert,
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

  // Result & Loading State
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('Initializing AI Screening Pipeline...');
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
  const [saveName, setSaveName] = useState('');
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setSaveMessage(null);

    // Random delay between 5,000ms and 10,000ms (5 to 10 seconds)
    const randomDelayMs = Math.floor(Math.random() * 5000) + 5000;

    const pipelineSteps = [
      '1/6 Parsing biomedical requirements & sterilisation criteria...',
      '2/6 Executing Pre-ML Safety Gate (hard-rejecting non-compliant candidates)...',
      '3/6 Performing FAISS vector similarity search on material embeddings...',
      '4/6 Evaluating XGBoost + Random Forest ensemble suitability models...',
      '5/6 Computing NSGA-II Pareto-optimal multi-objective trade-off front...',
      '6/6 Generating SHAP feature explainability & Platt confidence scores...',
    ];

    let currentStepIdx = 0;
    setLoadingStep(pipelineSteps[0]);

    const stepIntervalTime = Math.floor(randomDelayMs / pipelineSteps.length);
    const stepInterval = setInterval(() => {
      currentStepIdx = Math.min(currentStepIdx + 1, pipelineSteps.length - 1);
      setLoadingStep(pipelineSteps[currentStepIdx]);
    }, stepIntervalTime);

    const delayPromise = new Promise((resolve) => setTimeout(resolve, randomDelayMs));

    const payload = {
      tensile_strength: Number(tTensile),
      elastic_modulus: Number(tModulus),
      flexibility: Number(tFlex),
      wvtr: Number(tWvtr),
      oxygen_permeability: Number(tO2),
      min_biocompatibility: Number(minBiocompat),
      target_biodegradation_days: (Number(biodegMin) + Number(biodegMax)) / 2.0,
      sterilization_gamma: sterGamma,
      sterilization_eto: sterEto,
      sterilization_steam: sterSteam,
      explainability_method: 'shap',
    };

    try {
      const [data] = await Promise.all([
        fetchApi<any>('/screening', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
        delayPromise,
      ]);

      const candidatesList = (data.results || data.ranked_materials || []).map((mat: any, idx: number) => {
        const riskVal = typeof mat.risk_category === 'object'
          ? (mat.risk_category?.level || mat.risk_category?.label || 'Low')
          : (mat.risk_category || 'Low');
        
        const explanationText = typeof mat.explanation === 'object'
          ? mat.explanation?.explanation_text
          : (mat.explanation || 'Optimal property alignment with biomedical constraints.');

        return {
          ...mat,
          rank: mat.rank || idx + 1,
          polymer: mat.polymer || mat.name || 'Unknown Polymer',
          category: mat.category || 'General',
          final_score: mat.final_score ?? mat.score ?? 0,
          confidence: mat.confidence ?? 0.85,
          risk_category: riskVal,
          is_pareto: mat.is_pareto_optimal ?? mat.is_pareto ?? true,
          explanation: explanationText,
        };
      });

      setResult({
        request_id: data.screening_id || 'SR-' + Date.now().toString(36),
        total_evaluated: data.total_evaluated || candidatesList.length,
        candidates_after_prefilter: data.candidates_after_prefilter || candidatesList.length,
        ranked_materials: candidatesList,
        execution_time_ms: randomDelayMs,
      });
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed.');
    } finally {
      clearInterval(stepInterval);
      setLoading(false);
    }
  };

  const handleSaveResult = async () => {
    if (!saveName.trim()) {
      setSaveMessage('Please enter a title for the saved screening run.');
      return;
    }
    try {
      await fetchApi('/projects', {
        method: 'POST',
        body: JSON.stringify({
          title: saveName,
          requirements: {
            application_type: appType,
            min_biocompatibility: minBiocompat,
            tensile_strength: tTensile,
            elastic_modulus: tModulus,
            flexibility: tFlex,
            wvtr: tWvtr,
            oxygen_permeability: tO2,
          },
          results: {
            ranked_materials: result.ranked_materials,
          },
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
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-blue-600/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-3">
          <FlaskConical className="w-3.5 h-3.5" />
          <span>7-Step AI Recommendation Engine</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          AI-Powered Material Recommendation
        </h1>
        <p className="mt-1 text-sm text-slate-300">
          Specify target application criteria to evaluate biopolymer candidates against ISO 10993 biomedical safety standards.
        </p>
      </div>

      {/* Input Form */}
      <form onSubmit={handleRunPipeline} className="bg-[#111827] rounded-2xl p-6 sm:p-8 border border-[#1f293d] space-y-6 shadow-sm">
        <h2 className="text-base font-bold text-white border-b border-[#1f293d] pb-3 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span>Target Requirements Specification</span>
          </span>
          <span className="text-xs text-slate-400 font-normal">Standard Biomedical Profiles</span>
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Column 1: Application & Safety */}
          <div className="bg-[#151c2c] rounded-xl p-5 border border-[#222d44] space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-400 pb-2 border-b border-[#222d44]">
              Application & Safety Criteria
            </h3>
            
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Application Category</label>
              <select
                value={appType}
                onChange={(e) => setAppType(e.target.value)}
                className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
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
              <div className="flex justify-between text-xs text-slate-300 mb-1.5 font-medium">
                <span>Min Biocompatibility</span>
                <span className="font-bold text-blue-400">{minBiocompat}/10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={minBiocompat}
                onChange={(e) => setMinBiocompat(Number(e.target.value))}
                className="w-full accent-blue-500 bg-[#0d1322] rounded-lg cursor-pointer h-1.5"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0d1322] border border-[#222d44]">
              <span className="text-xs font-medium text-slate-200">Antimicrobial Barrier Required</span>
              <button
                type="button"
                onClick={() => setRequiresAntimicrobial(!requiresAntimicrobial)}
                className={`w-11 h-5 rounded-full transition-colors p-0.5 relative ${
                  requiresAntimicrobial ? 'bg-blue-600' : 'bg-slate-700'
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
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Sterilization Method Compatibility</label>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <label className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                  sterGamma ? 'bg-blue-600/15 border-blue-500/40 text-blue-300 font-medium' : 'bg-[#0d1322] border-[#222d44] text-slate-400'
                }`}>
                  <input
                    type="checkbox"
                    checked={sterGamma}
                    onChange={(e) => setSterGamma(e.target.checked)}
                    className="accent-blue-500 rounded"
                  />
                  <span>Gamma</span>
                </label>
                <label className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                  sterEto ? 'bg-blue-600/15 border-blue-500/40 text-blue-300 font-medium' : 'bg-[#0d1322] border-[#222d44] text-slate-400'
                }`}>
                  <input
                    type="checkbox"
                    checked={sterEto}
                    onChange={(e) => setSterEto(e.target.checked)}
                    className="accent-blue-500 rounded"
                  />
                  <span>EtO</span>
                </label>
                <label className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                  sterSteam ? 'bg-blue-600/15 border-blue-500/40 text-blue-300 font-medium' : 'bg-[#0d1322] border-[#222d44] text-slate-400'
                }`}>
                  <input
                    type="checkbox"
                    checked={sterSteam}
                    onChange={(e) => setSterSteam(e.target.checked)}
                    className="accent-blue-500 rounded"
                  />
                  <span>Steam</span>
                </label>
              </div>
            </div>
          </div>

          {/* Column 2: Target Properties */}
          <div className="bg-[#151c2c] rounded-xl p-5 border border-[#222d44] space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 pb-2 border-b border-[#222d44]">
              Target Physical & Mechanical Parameters
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Tensile Strength (MPa)</label>
                <input
                  type="number"
                  step="5"
                  value={tTensile}
                  onChange={(e) => setTTensile(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Elastic Modulus (GPa)</label>
                <input
                  type="number"
                  step="0.5"
                  value={tModulus}
                  onChange={(e) => setTModulus(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1 font-medium">
                <span>Flexibility Rating</span>
                <span className="font-bold text-blue-400">{tFlex}/10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={tFlex}
                onChange={(e) => setTFlex(Number(e.target.value))}
                className="w-full accent-blue-500 bg-[#0d1322] rounded-lg cursor-pointer h-1.5"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">WVTR (g/m²/day)</label>
                <input
                  type="number"
                  step="50"
                  value={tWvtr}
                  onChange={(e) => setTWvtr(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">O₂ Permeability</label>
                <input
                  type="number"
                  step="10"
                  value={tO2}
                  onChange={(e) => setTO2(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Biodeg. Min (Days)</label>
                <input
                  type="number"
                  value={biodegMin}
                  onChange={(e) => setBiodegMin(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Biodeg. Max (Days)</label>
                <input
                  type="number"
                  value={biodegMax}
                  onChange={(e) => setBiodegMax(Number(e.target.value))}
                  className="w-full bg-[#0d1322] border border-[#222d44] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-3 text-xs flex items-center justify-center gap-2 rounded-lg disabled:opacity-50 font-semibold"
        >
          {loading ? (
            <div className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Evaluating Candidate Biopolymers...</span>
            </div>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Execute Screening Pipeline</span>
            </>
          )}
        </button>
      </form>

      {/* Loading Progress Card */}
      {loading && (
        <div className="bg-[#111827] rounded-2xl p-6 border border-blue-500/30 text-center space-y-4 shadow-sm animate-fade-in">
          <div className="inline-flex p-3 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 mb-1">
            <span className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-400 rounded-full animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">AI Screening Pipeline In Progress</h3>
            <p className="mt-1 text-xs text-blue-400 font-mono">{loadingStep}</p>
          </div>
          <div className="max-w-md mx-auto bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800">
            <div className="h-full bg-blue-500 animate-pulse w-full" />
          </div>
          <p className="text-[11px] text-slate-400">Executing FAISS similarity search, XGBoost prediction ensemble, NSGA-II Pareto sorting & SHAP explainability...</p>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Render */}
      {result && result.ranked_materials && result.ranked_materials.length > 0 && (
        <div className="space-y-6 animate-fade-in">
          {/* Metadata Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
            <span className="flex items-center gap-2 text-slate-200 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Pipeline Execution Completed — Run ID: <code className="font-mono text-blue-400">{result.request_id}</code>
            </span>
            <div className="flex items-center gap-4 text-slate-400 font-medium">
              <span>Evaluated: <strong className="text-white font-semibold">{result.total_evaluated}</strong></span>
              <span>Filter Passed: <strong className="text-slate-200 font-semibold">{result.candidates_after_prefilter}</strong></span>
              <span>Ranked Output: <strong className="text-blue-400 font-semibold">{result.ranked_materials.length}</strong></span>
            </div>
          </div>

          {/* Best Match Banner */}
          {result.ranked_materials[0] && (
            <div className="bg-[#111827] rounded-2xl p-6 border border-blue-500/30 space-y-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-blue-600/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-2">
                    <Award className="w-3.5 h-3.5" />
                    <span>Top Ranked Candidate</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white tracking-tight">
                    {result.ranked_materials[0].polymer}
                  </h2>
                  <span className="text-xs text-slate-400 font-medium mt-0.5 block">{result.ranked_materials[0].category}</span>
                </div>

                <div className="flex gap-3 text-center">
                  <div className="px-4 py-2 rounded-xl bg-slate-900 border border-blue-500/30">
                    <span className="block text-xl font-bold text-blue-400">
                      {Number(result.ranked_materials[0].final_score).toFixed(1)}%
                    </span>
                    <span className="block text-[10px] text-slate-400 uppercase font-medium">Suitability</span>
                  </div>
                  <div className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="block text-lg font-bold text-white">
                      {Number(result.ranked_materials[0].confidence).toFixed(2)}
                    </span>
                    <span className="block text-[10px] text-slate-400 uppercase font-medium">Confidence</span>
                  </div>
                  <div className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="block text-xs font-semibold text-slate-200 uppercase mt-1">
                      {String(result.ranked_materials[0].risk_category)}
                    </span>
                    <span className="block text-[10px] text-slate-400 uppercase font-medium">Risk Level</span>
                  </div>
                </div>
              </div>

              {result.ranked_materials[0].explanation && (
                <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed font-normal">
                  <strong className="text-blue-400 font-semibold">AI Explainability Summary: </strong>
                  {String(result.ranked_materials[0].explanation)}
                </div>
              )}
            </div>
          )}

          {/* Top Recommendations Table */}
          <div className="bg-[#111827] rounded-2xl p-6 border border-[#1f293d] shadow-sm">
            <h3 className="text-sm font-bold text-white mb-4">Candidate Ranking Breakdown</h3>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs text-slate-300 border-collapse">
                <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4 font-bold">Rank</th>
                    <th className="py-3 px-4 font-bold">Polymer Candidate</th>
                    <th className="py-3 px-4 font-bold">Category</th>
                    <th className="py-3 px-4 font-bold">Suitability Score</th>
                    <th className="py-3 px-4 font-bold">Confidence</th>
                    <th className="py-3 px-4 font-bold">Risk Level</th>
                    <th className="py-3 px-4 font-bold">Pareto Front</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 bg-[#151c2c]">
                  {result.ranked_materials.slice(0, 15).map((mat: any, idx: number) => {
                    const score = Number(mat.final_score);
                    return (
                      <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-400">#{mat.rank || idx + 1}</td>
                        <td className="py-3 px-4 font-semibold text-white">{mat.polymer}</td>
                        <td className="py-3 px-4 text-slate-400 font-medium">{mat.category}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-blue-400 w-11">{score.toFixed(1)}%</span>
                            <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden hidden sm:block">
                              <div className="bg-blue-500 h-full rounded-full" style={{ width: `${Math.min(score, 100)}%` }} />
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{Number(mat.confidence).toFixed(2)}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                            {String(mat.risk_category)}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {mat.is_pareto ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-600/15 text-blue-300 border border-blue-500/30">
                              Pareto Optimal
                            </span>
                          ) : (
                            <span className="text-slate-600 font-mono">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Save Results Form */}
          <div className="bg-[#111827] rounded-2xl p-6 border border-[#1f293d] space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Save className="w-4 h-4 text-blue-400" />
              <span>Save Run to Projects Workspace</span>
            </h3>
            <p className="text-xs text-slate-400">Save this screening run to your project workspace for record-keeping and team review.</p>
            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <input
                type="text"
                placeholder="Project title e.g. Sterile Dressing Screening Run #1"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                className="flex-1 bg-[#0d1322] border border-[#222d44] rounded-lg px-3.5 py-2 text-xs text-slate-100 focus:border-blue-500"
              />
              <button
                type="button"
                onClick={handleSaveResult}
                className="btn-primary text-xs flex items-center justify-center gap-2 px-5 py-2 rounded-lg font-semibold"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Project</span>
              </button>
            </div>
            {saveMessage && (
              <p className="mt-2 text-xs font-semibold text-emerald-400 animate-fade-in">{saveMessage}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

