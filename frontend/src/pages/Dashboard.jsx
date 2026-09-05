import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectApi, workspaceApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Plus,
  FolderGit2,
  ArrowUpRight,
  Database,
  Layers,
  Cpu,
  ShieldCheck,
  Activity,
  BarChart3,
  Split,
  Wand2,
  CheckCircle2,
  Clock,
  Sparkles,
  AlertCircle,
  Tag,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

const PIPELINE_STAGES = [
  { key: 'DATA', label: '1. Data Prep', icon: Database, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { key: 'SPLIT', label: '2. Outer Split', icon: Split, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
  { key: 'PROFILED', label: '3. Profiled & DQI', icon: BarChart3, color: 'text-teal-400 bg-teal-500/10 border-teal-500/20' },
  { key: 'TRANSFORMED', label: '4. Transformed', icon: Wand2, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { key: 'TRAINING', label: '5. Training CV', icon: Clock, color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' },
  { key: 'TRAINED', label: '6. Trained', icon: Cpu, color: 'text-violet-400 bg-violet-500/10 border-violet-500/20' },
  { key: 'EVALUATED', label: '7. Evaluated', icon: CheckCircle2, color: 'text-pink-400 bg-pink-500/10 border-pink-500/20' },
  { key: 'GATE_PASSED', label: '8. Gate Passed', icon: ShieldCheck, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  { key: 'DEPLOYED', label: '9. Deployed LIVE', icon: Activity, color: 'text-emerald-500 bg-emerald-500/20 border-emerald-500/40' },
];

export const Dashboard = () => {
  const [projects, setProjects] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [creating, setCreating] = useState(false);

  const { user } = useAuth();
  const navigate = useNavigate();

  const userPerms = new Set(
    user?.permissions ||
    (user?.role?.permissions ? user.role.permissions.map((p) => (typeof p === 'string' ? p : p.permission_key)) : [])
  );
  const isAdmin = user?.role === 'ADMIN' || userPerms.has('MANAGE_USERS');
  const canEditData = isAdmin || userPerms.has('EDIT_DATA');

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [projRes, sumRes] = await Promise.all([
        projectApi.list(),
        workspaceApi.getSummary(),
      ]);
      setProjects(projRes.data);
      setSummary(sumRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load workspace analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!projectName.trim()) return;
    setCreating(true);
    try {
      const res = await projectApi.create(projectName.trim(), targetColumn.trim() || null);
      setIsModalOpen(false);
      setProjectName('');
      setTargetColumn('');
      await loadDashboardData();
      navigate(`/projects/${res.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  const getStageRoutingPath = (proj) => {
    const stage = proj.pipeline_stage;
    switch (stage) {
      case 'DATA':
        return `/projects/${proj.id}?tab=SCHEMA`;
      case 'SPLIT':
        return `/projects/${proj.id}?tab=SPLIT`;
      case 'PROFILED':
        return `/projects/${proj.id}?tab=PROFILING`;
      case 'TRANSFORMED':
        return `/projects/${proj.id}?tab=TRANSFORMATIONS`;
      case 'TRAINING':
      case 'TRAINED':
      case 'EVALUATED':
      case 'GATE_PASSED':
        return `/projects/${proj.id}?tab=TRAINING`;
      case 'DEPLOYED':
        return `/projects/${proj.id}?tab=TRAINING`;
      default:
        return `/projects/${proj.id}`;
    }
  };

  const stageCounts = summary?.projects_by_stage || {};

  return (
    <div className="space-y-8">
      {/* Workspace Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Workspace Analytics &bull; Day 11 Integrated Hub</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text mt-1">
            Machine Learning Studio
          </h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Live pipeline stage derivation, strict leakage isolation, and production observability
          </p>
        </div>

        {/* Create Project Button: Genuinely omitted if user lacks EDIT_DATA */}
        {canEditData && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white font-semibold text-xs shadow-md shadow-indigo-500/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Summary KPI Counters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Total Projects
          </div>
          <div className="text-2xl font-black font-mono text-text">
            {summary?.total_projects ?? projects.length}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Datasets
          </div>
          <div className="text-2xl font-black font-mono text-blue-400">
            {summary?.datasets_uploaded ?? 0}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Experiments
          </div>
          <div className="text-2xl font-black font-mono text-indigo-400">
            {summary?.experiments_completed ?? 0}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Models Trained
          </div>
          <div className="text-2xl font-black font-mono text-purple-400">
            {summary?.models_trained ?? 0}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Gate Passed
          </div>
          <div className="text-2xl font-black font-mono text-pink-400">
            {summary?.models_gate_passed ?? 0}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-1">
          <div className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            LIVE Endpoints
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400">
            {summary?.live_deployments ?? 0}
          </div>
        </div>
      </div>

      {/* Pipeline Stage Funnel Breakdown */}
      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-text flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[var(--color-accent)]" />
              <span>Pipeline Stage Funnel (Live DB Derived)</span>
            </h2>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Live computed progression derived dynamically from dataset splits, profiling, transformations, models, and gates
            </p>
          </div>
          {summary?.is_platform_wide && (
            <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              PLATFORM-WIDE (ADMIN)
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2.5">
          {PIPELINE_STAGES.map((st) => {
            const count = stageCounts[st.key] || 0;
            const Icon = st.icon;
            return (
              <div
                key={st.key}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center justify-between ${st.color}`}
              >
                <div className="flex items-center space-x-1 mb-1 opacity-80">
                  <Icon className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-bold truncate">{st.label}</span>
                </div>
                <div className="text-xl font-black font-mono mt-1">
                  {count}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Projects Grid Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-text flex items-center space-x-2">
            <FolderGit2 className="w-4 h-4 text-[var(--color-accent)]" />
            <span>Active Projects</span>
          </h2>
          <span className="text-xs text-[var(--color-text-muted)] font-mono">
            {projects.length} {projects.length === 1 ? 'project' : 'projects'}
          </span>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-44 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] animate-pulse p-6" />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-16 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8">
            <FolderGit2 className="w-12 h-12 mx-auto text-[var(--color-text-muted)] mb-3 opacity-50" />
            <h3 className="text-sm font-bold text-text">No projects available</h3>
            <p className="text-xs text-[var(--color-text-muted)] mt-1 mb-4">
              Get started by creating a new tabular machine learning project.
            </p>
            {canEditData && (
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-[var(--color-accent)] text-white text-xs font-semibold cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Create Project</span>
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((proj) => {
              const jumpPath = getStageRoutingPath(proj);
              return (
                <div
                  key={proj.id}
                  className="group relative bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between mb-3">
                      <div
                        onClick={() => navigate(`/projects/${proj.id}`)}
                        className="w-10 h-10 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-accent)] cursor-pointer"
                      >
                        <FolderGit2 className="w-5 h-5" />
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
                        {proj.task_type}
                      </span>
                    </div>

                    <h3
                      onClick={() => navigate(`/projects/${proj.id}`)}
                      className="text-base font-bold text-text group-hover:text-[var(--color-accent)] transition-colors cursor-pointer"
                    >
                      {proj.project_name}
                    </h3>

                    {proj.target_column && (
                      <div className="flex items-center space-x-1.5 mt-2 text-xs text-[var(--color-text-muted)]">
                        <Tag className="w-3.5 h-3.5" />
                        <span>Target: <strong className="text-text font-mono">{proj.target_column}</strong></span>
                      </div>
                    )}
                  </div>

                  <div className="mt-6 pt-4 border-t border-[var(--color-border)] space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[var(--color-text-muted)]">Derived Stage:</span>
                      <span className="px-2.5 py-0.5 rounded-full font-mono text-[11px] font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        {proj.pipeline_stage}
                      </span>
                    </div>

                    {/* Jump to current stage action button */}
                    <button
                      onClick={() => navigate(jumpPath)}
                      className="w-full inline-flex items-center justify-center space-x-2 py-2 px-3 rounded-xl bg-[var(--color-bg)] hover:bg-[var(--color-accent)] text-text hover:text-white border border-[var(--color-border)] hover:border-[var(--color-accent)] text-xs font-semibold transition-all cursor-pointer"
                    >
                      <span>Jump to Current Stage ({proj.pipeline_stage})</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {isModalOpen && canEditData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl p-6">
            <h3 className="text-lg font-bold text-text mb-1">Create New Project</h3>
            <p className="text-xs text-[var(--color-text-muted)] mb-5">
              Set up your project workspace. Task type starts as UNDETERMINED.
            </p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Customer Churn Prediction"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1">
                  Target Column (Optional)
                </label>
                <input
                  type="text"
                  value={targetColumn}
                  onChange={(e) => setTargetColumn(e.target.value)}
                  placeholder="e.g. churn or price"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 rounded-xl bg-[var(--color-accent)] text-white text-xs font-semibold shadow-sm hover:bg-[var(--color-accent-hover)] disabled:opacity-50 cursor-pointer"
                >
                  {creating ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
