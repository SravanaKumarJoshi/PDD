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
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-blue-600/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-3">
            <FolderKanban className="w-3.5 h-3.5" />
            <span>Saved Workspaces & Audit Trail</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Projects Workspace
          </h1>
          <p className="mt-1 text-sm text-slate-300">
            Manage your saved AI screening runs, property specifications, and ranked output reports.
          </p>
        </div>

        <button
          onClick={loadProjects}
          className="btn-secondary text-xs flex items-center gap-2 px-4 py-2 rounded-lg font-medium"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Reload Projects</span>
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-xs text-slate-400">
          <span className="inline-block w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-2" />
          <p>Loading saved projects...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
          <span>{error}</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-[#111827] rounded-2xl p-12 text-center border border-[#1f293d] space-y-3 shadow-sm">
          <FolderKanban className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-bold text-white">No Saved Projects Yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Navigate to the Recommend page, execute a screening pipeline, and click "Save Project" to store your screening results here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {projects.map((proj) => {
            const reqs = typeof proj.requirements === 'string' ? JSON.parse(proj.requirements) : (proj.requirements || {});
            const resObj = typeof proj.results === 'string' ? JSON.parse(proj.results) : (proj.results || {});
            const materials = resObj?.ranked_materials || proj.ranked_materials || [];

            return (
              <div key={proj.id} className="bg-[#111827] rounded-2xl p-6 border border-[#1f293d] space-y-4 relative group hover:border-slate-700 transition-colors shadow-sm">
                <div className="flex items-start justify-between gap-4 border-b border-[#1f293d] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors">
                      {proj.title || proj.name || 'Untitled Screening Run'}
                    </h3>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1.5 mt-1 font-medium">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      {proj.created_at ? new Date(proj.created_at).toLocaleString() : 'Recent'}
                    </span>
                  </div>

                  <button
                    onClick={() => handleDelete(proj.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    title="Delete Project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {reqs && (
                  <div className="p-3 rounded-xl bg-[#151c2c] border border-[#222d44] text-xs text-slate-300 space-y-1">
                    <span className="font-semibold text-blue-400 block uppercase text-[10px] tracking-wider">Target Specification</span>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 font-mono">
                      <span>App: <strong className="text-slate-200">{reqs.application_type || 'Wound dressing'}</strong></span>
                      <span>Biocompat: <strong className="text-slate-200">{reqs.min_biocompatibility || 7}/10</strong></span>
                      <span>Tensile: <strong className="text-slate-200">{reqs.tensile_strength || 50} MPa</strong></span>
                      <span>Modulus: <strong className="text-slate-200">{reqs.elastic_modulus || 2} GPa</strong></span>
                    </div>
                  </div>
                )}

                {materials && materials.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-slate-300 block mb-2">Top Ranked Biopolymers:</span>
                    <div className="space-y-1.5 text-xs">
                      {materials.slice(0, 4).map((m: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-[#151c2c] border border-[#222d44]">
                          <span className="font-semibold text-slate-200">#{m.rank || i + 1} {m.polymer || m.name}</span>
                          <span className="font-bold text-blue-400 bg-blue-600/10 px-2 py-0.5 rounded border border-blue-500/20">{Number(m.final_score).toFixed(1)}%</span>
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
