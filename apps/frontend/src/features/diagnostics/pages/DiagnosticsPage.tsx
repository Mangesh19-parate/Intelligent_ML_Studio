import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDiagnostics } from '../hooks/useDiagnostics';
import { LeakagePanel } from '../components/LeakagePanel';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { Stethoscope, Layers, AlertCircle, Loader2 } from 'lucide-react';

export const DiagnosticsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const projectIdParam = searchParams.get('project_id');

  const {
    projects,
    selectedProjectId,
    setSelectedProjectId,
    currentProject,
    experiments,
    selectedExperimentId,
    setSelectedExperimentId,
    currentExperiment,
    recommendations,
    loading,
    error,
  } = useDiagnostics(projectIdParam);

  const handleProjectChange = (id: string) => {
    setSelectedProjectId(id);
    setSearchParams({ project_id: id });
  };

  if (loading && !currentProject) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-indigo-400 text-sm font-medium mb-1">
            <Stethoscope className="w-4 h-4" />
            <span>Inspection & Governance</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Model & Data Diagnostics</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Audit partition leakage, evaluate fit diagnoses, and review automated pipeline recommendations.
          </p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center space-x-3">
          <label className="text-xs text-slate-400 font-medium whitespace-nowrap">Active Project:</label>
          <select
            value={selectedProjectId}
            onChange={(e) => handleProjectChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.project_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-center space-x-3 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Experiment Selector Bar */}
      {experiments.length > 0 && (
        <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 rounded-lg p-3 px-4">
          <div className="flex items-center space-x-2 text-sm text-slate-300">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Experiment Run:</span>
          </div>
          <select
            value={selectedExperimentId}
            onChange={(e) => setSelectedExperimentId(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white text-xs rounded-md px-3 py-1.5 focus:ring-2 focus:ring-indigo-500"
          >
            {experiments.map((exp) => (
              <option key={exp.id} value={exp.id}>
                {exp.task_type} (Folds: {exp.fold_count}) - Status: {exp.status}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Core Panels */}
      <LeakagePanel experiment={currentExperiment} />
      <RecommendationPanel recommendations={recommendations} />
    </div>
  );
};
