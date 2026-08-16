'use client';

import React, { useEffect, useState } from 'react';
import { fetchApi } from '@/lib/api';
import {
  FolderKanban,
  Trash2,
  Calendar,
  Layers,
  Sparkles,
  Award,
  RefreshCw,
} from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<any[]>('/projects');
      setProjects(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch saved projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await fetchApi(`/projects/${id}`, { method: 'DELETE' });
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err: any) {
      alert(`Failed to delete project: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium mb-3">
            <FolderKanban className="w-3.5 h-3.5" />
            <span>Saved Workspaces & History</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            📁 Projects & Saved Screening Runs
          </h1>
          <p className="mt-1 text-sm text-gray-300">
            Manage your saved AI recommendation runs, requirements, and ranked candidate results.
          </p>
        </div>

        <button
          onClick={loadProjects}
          className="btn-secondary text-xs flex items-center gap-2 px-4 py-2 rounded-xl"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Reload Projects</span>
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-xs text-gray-400">
          <span className="inline-block w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-2" />
          <p>Loading saved projects...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <span>{error}</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-gray-800 space-y-3">
          <FolderKanban className="w-12 h-12 text-gray-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No Saved Projects Yet</h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto">
            Go to the Recommend page, run an AI screening pipeline, and click "Save Run" to store your screening results here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projects.map((proj) => {
            const reqs = typeof proj.requirements === 'string' ? JSON.parse(proj.requirements) : (proj.requirements || {});
            const resObj = typeof proj.results === 'string' ? JSON.parse(proj.results) : (proj.results || {});
            const materials = resObj?.ranked_materials || proj.ranked_materials || [];

            return (
              <div key={proj.id} className="glass-card rounded-2xl p-6 border border-gray-800 space-y-4 relative group">
                <div className="flex items-start justify-between gap-4 border-b border-gray-800 pb-3">
                  <div>
                    <h3 className="text-base font-bold text-white group-hover:text-emerald-400 transition-colors">
                      {proj.title || proj.name || 'Untitled Screening Run'}
                    </h3>
                    <span className="text-[11px] text-gray-400 flex items-center gap-1 mt-1">
                      <Calendar className="w-3 h-3 text-gray-500" />
                      {proj.created_at ? new Date(proj.created_at).toLocaleString() : 'Recent'}
                    </span>
                  </div>

                  <button
                    onClick={() => handleDelete(proj.id)}
                    className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Delete Project"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {reqs && (
                  <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-xs text-gray-300 space-y-1">
                    <span className="font-semibold text-emerald-400 block">Target Requirements:</span>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-400">
                      <span>App: <strong className="text-gray-200">{reqs.application_type || 'Wound dressing'}</strong></span>
                      <span>Biocompatibility: <strong className="text-gray-200">{reqs.min_biocompatibility || 7}/10</strong></span>
                      <span>Tensile: <strong className="text-gray-200">{reqs.tensile_strength || 50} MPa</strong></span>
                      <span>Modulus: <strong className="text-gray-200">{reqs.elastic_modulus || 2} GPa</strong></span>
                    </div>
                  </div>
                )}

                {materials && materials.length > 0 && (
                  <div>
                    <span className="text-xs font-bold text-white block mb-2">Top Recommended Candidates:</span>
                    <div className="space-y-1.5 text-xs">
                      {materials.slice(0, 4).map((m: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-900/40 border border-gray-800/80">
                          <span className="font-medium text-gray-200">#{m.rank || i + 1} {m.polymer || m.name}</span>
                          <span className="font-bold text-emerald-400">{Number(m.final_score).toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
