'use client';

import React, { useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  BrainCircuit,
  Cpu,
  Trophy,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

export default function ModelTrainingPage() {
  const [testSize, setTestSize] = useState(30);
  const [randomSeed, setRandomSeed] = useState(42);
  const [cvFolds, setCvFolds] = useState(5);

  const [loading, setLoading] = useState(false);
  const [trainingResult, setTrainingResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTrainModels = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchApi<any>('/model/train', {
        method: 'POST',
        body: JSON.stringify({
          test_size: testSize / 100,
          random_state: randomSeed,
          cv_folds: cvFolds,
        }),
      });
      setTrainingResult(data);
    } catch (err: any) {
      setError(err.message || 'Model training failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
          <BrainCircuit className="w-3.5 h-3.5" />
          <span>Ensemble Machine Learning Architecture</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          🤖 Model Training & Benchmarking
        </h1>
        <p className="mt-1 text-sm text-gray-300">
          Train XGBoost primary classifier and RandomForest benchmark side-by-side with stratified cross-validation and holdout validation.
        </p>
      </div>

      {/* Configuration Card */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-gray-800 space-y-6">
        <h2 className="text-lg font-bold text-white border-b border-gray-800 pb-3 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emerald-400" />
          <span>Training Configuration</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>Holdout Test Size</span>
              <span className="font-bold text-emerald-400">{testSize}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="50"
              step="5"
              value={testSize}
              onChange={(e) => setTestSize(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-gray-900 rounded-lg cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Random Seed</label>
            <input
              type="number"
              value={randomSeed}
              onChange={(e) => setRandomSeed(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Cross-Validation Folds</label>
            <select
              value={cvFolds}
              onChange={(e) => setCvFolds(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:border-emerald-500"
            >
              <option value={3}>3 Folds</option>
              <option value={5}>5 Folds</option>
              <option value={10}>10 Folds</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleTrainModels}
          disabled={loading}
          className="w-full btn-primary py-3 text-sm flex items-center justify-center gap-2 rounded-xl shadow-xl"
        >
          {loading ? (
            <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>🚀 Train Both Models (XGBoost + RandomForest)</span>
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
      {trainingResult && (
        <div className="space-y-8">
          {/* Comparison Metrics Grid */}
          <div className="glass-panel rounded-2xl p-6 border border-gray-800">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-400" />
              <span>Side-by-Side Model Comparison</span>
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Metric</th>
                    <th className="py-3 px-4">XGBoost Primary</th>
                    <th className="py-3 px-4">RandomForest Benchmark</th>
                    <th className="py-3 px-4">Winner</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {Object.entries(trainingResult.comparison || {}).map(([metricKey, data]: [string, any]) => (
                    <tr key={metricKey} className="hover:bg-gray-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white uppercase text-[11px]">
                        {metricKey.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-4 font-bold text-emerald-400">
                        {typeof data.xgboost === 'number' ? data.xgboost.toFixed(3) : data.xgboost}
                      </td>
                      <td className="py-3 px-4 font-bold text-cyan-400">
                        {typeof data.random_forest === 'number' ? data.random_forest.toFixed(3) : data.random_forest}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          🏆 {data.winner?.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Strict Validation & Confusion Matrix */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Holdout Metrics */}
            <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span>Strict Holdout Validation</span>
              </h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
                  <span className="block text-xl font-extrabold text-emerald-400">
                    {(trainingResult.validation?.holdout_metrics?.accuracy * 100).toFixed(1)}%
                  </span>
                  <span className="block text-[10px] text-gray-400 mt-1">Accuracy</span>
                </div>
                <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
                  <span className="block text-xl font-extrabold text-cyan-400">
                    {(trainingResult.validation?.holdout_metrics?.f1 * 100).toFixed(1)}%
                  </span>
                  <span className="block text-[10px] text-gray-400 mt-1">F1 Score</span>
                </div>
                <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800">
                  <span className="block text-xl font-extrabold text-indigo-400">
                    {trainingResult.validation?.holdout_metrics?.roc_auc?.toFixed(3)}
                  </span>
                  <span className="block text-[10px] text-gray-400 mt-1">ROC-AUC</span>
                </div>
              </div>

              {trainingResult.validation?.overfit_warning ? (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
                  ⚠️ {trainingResult.validation.overfit_warning}
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>No overfitting detected on holdout test set</span>
                </div>
              )}
            </div>

            {/* Confusion Matrix */}
            <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                <span>XGBoost Confusion Matrix</span>
              </h3>
              {trainingResult.xgboost?.confusion_matrix && (
                <div className="grid grid-cols-2 gap-3 text-center text-xs font-bold pt-2">
                  <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                    <span className="block text-2xl font-extrabold text-emerald-400">
                      {trainingResult.xgboost.confusion_matrix[0]?.[0]}
                    </span>
                    <span className="block text-[10px] text-gray-400 mt-1">True Negative</span>
                  </div>
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
                    <span className="block text-2xl font-extrabold">
                      {trainingResult.xgboost.confusion_matrix[0]?.[1]}
                    </span>
                    <span className="block text-[10px] text-gray-400 mt-1">False Positive</span>
                  </div>
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
                    <span className="block text-2xl font-extrabold">
                      {trainingResult.xgboost.confusion_matrix[1]?.[0]}
                    </span>
                    <span className="block text-[10px] text-gray-400 mt-1">False Negative</span>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                    <span className="block text-2xl font-extrabold text-emerald-400">
                      {trainingResult.xgboost.confusion_matrix[1]?.[1]}
                    </span>
                    <span className="block text-[10px] text-gray-400 mt-1">True Positive</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Feature Importances Bar List */}
          {trainingResult.feature_importance && (
            <div className="glass-panel rounded-2xl p-6 border border-gray-800 space-y-4">
              <h3 className="text-base font-bold text-white">🎯 Feature Importances (XGBoost)</h3>
              <div className="space-y-2">
                {trainingResult.feature_importance.map((item: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span className="w-44 font-semibold text-gray-300 truncate">{item.feature}</span>
                    <div className="flex-1 bg-gray-900 rounded-full h-3 overflow-hidden border border-gray-800">
                      <div
                        className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${(item.importance * 100).toFixed(1)}%` }}
                      />
                    </div>
                    <span className="w-16 text-right font-mono font-bold text-emerald-400">
                      {(item.importance * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
