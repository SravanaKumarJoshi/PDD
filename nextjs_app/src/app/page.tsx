'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchApi } from '@/lib/api';
import {
  Dna,
  Database,
  BrainCircuit,
  Microscope,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Cpu,
  Layers,
  FlaskConical,
  Activity,
  Zap,
} from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalMaterials: 210,
    literatureSourced: 210,
    categories: 6,
    avgBiocompatibility: 7.8,
    modelStatus: 'Ready',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const materials = await fetchApi<any[]>('/materials?limit=500');
        if (Array.isArray(materials) && materials.length > 0) {
          const total = materials.length;
          const real = materials.filter((m) => m.is_augmented === 0).length;
          const cats = new Set(materials.map((m) => m.category)).size;
          const bioVals = materials.map((m) => Number(m.biocompatibility)).filter((v) => !isNaN(v));
          const avgBio = bioVals.length ? (bioVals.reduce((a, b) => a + b, 0) / bioVals.length).toFixed(1) : '7.8';

          setStats({
            totalMaterials: total,
            literatureSourced: real,
            categories: cats,
            avgBiocompatibility: Number(avgBio),
            modelStatus: 'Ready',
          });
        }
      } catch (e) {
        console.log('Using default system overview stats');
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const pipelineSteps = [
    { num: '1', title: 'User Requirements', desc: 'Parse & validate biomedical target properties and sterilization criteria.', color: 'from-blue-500/15 to-indigo-500/15', border: 'border-blue-500/30' },
    { num: '2', title: 'Safety Gate', desc: 'Hard-reject toxic or non-compliant materials before ML evaluation.', color: 'from-red-500/15 to-rose-500/15', border: 'border-red-500/30' },
    { num: '3', title: 'FAISS Vector Similarity', desc: 'Retrieve K nearest neighbor candidate biopolymers via embedding distance.', color: 'from-cyan-500/15 to-teal-500/15', border: 'border-cyan-500/30' },
    { num: '4', title: 'XGBoost + RF Ensemble', desc: 'Predict suitability probability using calibrated 70/30 weighted ensemble.', color: 'from-emerald-500/15 to-teal-500/15', border: 'border-emerald-500/30' },
    { num: '5', title: 'NSGA-II Optimization', desc: 'Identify Pareto-optimal trade-offs across strength, biodegradability, biocompatibility.', color: 'from-amber-500/15 to-yellow-500/15', border: 'border-amber-500/30' },
    { num: '6', title: 'SHAP Explainability', desc: 'Generate waterfall plots and human-readable feature importance reasons.', color: 'from-purple-500/15 to-violet-500/15', border: 'border-purple-500/30' },
    { num: '7', title: 'Confidence & Risk', desc: 'Assign Platt-calibrated confidence score and risk categorization.', color: 'from-emerald-500/15 to-cyan-500/15', border: 'border-emerald-500/30' },
  ];

  const [activeTab, setActiveTab] = useState<'models' | 'safety' | 'explain'>('models');

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="rounded-2xl bg-[#111827] p-8 sm:p-10 border border-[#1f293d] shadow-sm">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-blue-600/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Biomedical Material Decision Support Engine</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight leading-tight">
            BioPolymer <span className="text-blue-400">AI Screening</span> Platform
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            AI-powered material selection for biomedical packaging applications using XGBoost ensemble predictions, vector similarity search, multi-objective Pareto optimization, and SHAP explainability.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link href="/recommend" className="btn-primary flex items-center gap-2 text-xs">
              <FlaskConical className="w-4 h-4" />
              <span>Start Recommendation Pipeline</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/dataset" className="btn-secondary flex items-center gap-2 text-xs">
              <Database className="w-4 h-4" />
              <span>Explore Materials Catalog</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Clinical Disclaimer */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-xs flex items-start gap-3">
        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
        <div className="leading-relaxed">
          <strong className="font-semibold text-slate-200">Clinical Disclaimer:</strong> This system provides AI-assisted decision support for biomedical material research. Recommendations do not replace clinical or lab testing. Experimental validation is required prior to medical application.
        </div>
      </div>

      {/* Metrics Grid */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-blue-400" />
          <span>System Overview</span>
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          <div className="glass-card rounded-xl p-4 border border-[#222d44] text-center">
            <span className="block text-2xl font-bold text-white">{stats.totalMaterials}</span>
            <span className="block text-[11px] text-slate-400 mt-1 font-medium uppercase tracking-wider">Total Materials</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#222d44] text-center">
            <span className="block text-2xl font-bold text-blue-400">{stats.literatureSourced}</span>
            <span className="block text-[11px] text-slate-400 mt-1 font-medium uppercase tracking-wider">Literature Sourced</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#222d44] text-center">
            <span className="block text-2xl font-bold text-slate-200">{stats.categories}</span>
            <span className="block text-[11px] text-slate-400 mt-1 font-medium uppercase tracking-wider">Categories</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#222d44] text-center">
            <span className="block text-2xl font-bold text-emerald-400">{stats.avgBiocompatibility}/10</span>
            <span className="block text-[11px] text-slate-400 mt-1 font-medium uppercase tracking-wider">Avg Biocompatibility</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#222d44] text-center flex flex-col items-center justify-center">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              {stats.modelStatus}
            </span>
            <span className="block text-[11px] text-slate-400 mt-2 font-medium uppercase tracking-wider">AI Engine Status</span>
          </div>
        </div>
      </div>

      {/* 7-Step Pipeline Diagram */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>7-Step AI Recommendation Pipeline</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {pipelineSteps.map((step) => (
            <div
              key={step.num}
              className="bg-[#151c2c] rounded-xl p-5 border border-[#222d44] hover:border-slate-600 transition-colors"
            >
              <div className="w-7 h-7 rounded-md bg-slate-800 text-blue-400 font-bold text-xs flex items-center justify-center mb-3">
                {step.num}
              </div>
              <h3 className="text-xs font-bold text-white mb-1">
                {step.title}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Highlights Tabs */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-white/[0.08]">
        <div className="flex border-b border-gray-800 gap-6 mb-6">
          <button
            onClick={() => setActiveTab('models')}
            className={`pb-3 text-sm font-bold border-b-2 transition-all duration-200 ${
              activeTab === 'models'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            🔬 AI Models
          </button>
          <button
            onClick={() => setActiveTab('safety')}
            className={`pb-3 text-sm font-bold border-b-2 transition-all duration-200 ${
              activeTab === 'safety'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            🛡️ Safety & Trust
          </button>
          <button
            onClick={() => setActiveTab('explain')}
            className={`pb-3 text-sm font-bold border-b-2 transition-all duration-200 ${
              activeTab === 'explain'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            📈 Explainability
          </button>
        </div>

        {activeTab === 'models' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-300">
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>XGBoost</strong> primary suitability prediction model</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>RandomForest</strong> benchmarking with side-by-side metric comparison</span>
              </p>
            </div>
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>FAISS</strong> vector similarity search across property embeddings</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>NSGA-II</strong> multi-objective optimization for trade-off Pareto fronts</span>
              </p>
            </div>
          </div>
        )}

        {activeTab === 'safety' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-300">
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Pre-ML Safety Gate:</strong> Hard-rejects toxic or non-biocompatible materials</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Confidence Scoring:</strong> Platt-calibrated probabilities & risk levels</span>
              </p>
            </div>
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Data Provenance:</strong> Literature-sourced vs synthetic data flagging</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Model Versioning:</strong> Checkpoint versioning & rollback capability</span>
              </p>
            </div>
          </div>
        )}

        {activeTab === 'explain' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-300">
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>SHAP Explanations</strong> computed for every candidate biopolymer</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Feature Contribution</strong> waterfall plots & ranking breakdown</span>
              </p>
            </div>
            <div className="space-y-3">
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Global Importance</strong> summary across all dataset materials</span>
              </p>
              <p className="flex items-center gap-2.5 p-2.5 rounded-xl bg-gray-900/60 border border-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Natural Language Text:</strong> "Selected due to high biocompatibility (+0.34)..."</span>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

