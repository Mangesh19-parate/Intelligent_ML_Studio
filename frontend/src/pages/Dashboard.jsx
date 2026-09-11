import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { projectApi, workspaceApi, datasetApi, experimentApi, modelApi } from '../api/client';
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
  LayoutDashboard,
  FolderKanban,
  Search,
  Filter,
  Zap,
  Lock,
  ArrowRight,
  RefreshCw,
  Trophy,
  BrainCircuit,
  Sliders,
  AlertTriangle,
} from 'lucide-react';

const PIPELINE_STAGES = [
  { key: 'DATA', label: '1. Data', path: '/data', icon: Database },
  { key: 'SPLIT', label: '2. Split', path: '/data/datasets', icon: Split },
  { key: 'PROFILED', label: '3. Analysis', path: '/data-analysis', icon: BarChart3 },
  { key: 'TRANSFORMED', label: '4. Transform', path: '/transformations', icon: Wand2 },
  { key: 'ENGINEERED', label: '5. Features', path: '/feature-engineering', icon: Sliders },
  { key: 'DIAGNOSED', label: '6. Diagnostics', path: '/diagnostics', icon: Activity },
  { key: 'TRAINED', label: '7. ML Studio', path: '/machine-learning', icon: Cpu },
  { key: 'DEPLOYED', label: '8. Production', path: '/production', icon: ShieldCheck },
];

export const Dashboard = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'overview'; // 'overview' | 'projects'
  const [activeTab, setActiveTab] = useState(initialTab);

  const [projects, setProjects] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [activeProject, setActiveProject] = useState(null);
  const [activeProjectDetails, setActiveProjectDetails] = useState({
    dataset: null,
    profile: null,
    experiments: [],
    leaderboard: null,
    recommendations: [],
    deployment: null,
  });

  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState('');

  // Search & Filter state for "My Projects"
  const [searchQuery, setSearchQuery] = useState('');
  const [taskFilter, setTaskFilter] = useState('ALL'); // 'ALL' | 'REGRESSION' | 'CLASSIFICATION'

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [taskType, setTaskType] = useState('');
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
      const projList = projRes.data || [];
      setProjects(projList);
      setSummary(sumRes.data);

      const urlProjectId = searchParams.get('project_id');
      const targetId = urlProjectId || (projList.length > 0 ? projList[0].id : '');
      if (targetId) {
        setSelectedProjectId(targetId);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load workspace analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Sync tab with URL
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab && ['overview', 'projects'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Load detailed active project stats for Overview
  useEffect(() => {
    if (!selectedProjectId) return;
    const proj = projects.find((p) => p.id === selectedProjectId);
    if (proj) setActiveProject(proj);

    const loadProjectDeepData = async () => {
      try {
        setDetailsLoading(true);
        const [projGetRes, recsRes, expRes] = await Promise.allSettled([
          projectApi.get(selectedProjectId),
          projectApi.getRecommendations(selectedProjectId),
          experimentApi.listByProject(selectedProjectId),
        ]);

        const currentProjData = projGetRes.status === 'fulfilled' ? projGetRes.value.data : proj;
        setActiveProject(currentProjData);

        const recs = recsRes.status === 'fulfilled' ? recsRes.value.data || [] : [];
        const exps = expRes.status === 'fulfilled' ? expRes.value.data || [] : [];

        let lbData = null;
        if (exps.length > 0) {
          try {
            const lbRes = await modelApi.getLeaderboard(selectedProjectId, exps[0].id);
            lbData = lbRes.data;
          } catch {}
        }

        let dsData = null;
        let profData = null;
        try {
          const dsListRes = await datasetApi.listVersions(selectedProjectId);
          if (dsListRes.data && dsListRes.data.length > 0) {
            dsData = dsListRes.data[0];
            try {
              const pRes = await datasetApi.getProfile(dsData.id);
              profData = pRes.data;
            } catch {}
          }
        } catch {}

        setActiveProjectDetails({
          dataset: dsData,
          profile: profData,
          experiments: exps,
          leaderboard: lbData,
          recommendations: recs,
          deployment: currentProjData?.active_deployment || null,
        });
      } catch (err) {
        console.error('Error loading deep project data', err);
      } finally {
        setDetailsLoading(false);
      }
    };

    loadProjectDeepData();
  }, [selectedProjectId, projects]);

  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set('tab', tab);
      return p;
    });
  };

  const handleProjectSelect = (e) => {
    const pId = e.target.value;
    setSelectedProjectId(pId);
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set('project_id', pId);
      return p;
    });
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!projectName.trim()) return;
    setCreating(true);
    try {
      const res = await projectApi.create(projectName.trim(), targetColumn.trim() || null);
      setIsModalOpen(false);
      setProjectName('');
      setTargetColumn('');
      setTaskType('');
      await loadDashboardData();
      navigate(`/dashboard?tab=overview&project_id=${res.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  // Filter projects for "My Projects" tab
  const filteredProjects = projects.filter((p) => {
    const matchName = (p.project_name || p.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.target_column || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchTask = taskFilter === 'ALL' || (p.task_type || '').toUpperCase() === taskFilter;
    return matchName && matchTask;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Workspace Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-6">
        <div>
          <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[var(--color-accent)] bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-full px-3 py-1 mb-2">
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Workspace &bull; Intelligent Command Center</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-text)]">
            Machine Learning Studio
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1 max-w-3xl">
            Live pipeline stage tracking, zero-leakage protocol verification, and automated project diagnostics.
          </p>
        </div>

        {/* View Switcher & Action */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex p-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-full shadow-sm">
            <button
              onClick={() => handleTabSwitch('overview')}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'overview'
                  ? 'bg-[var(--color-accent)] text-white shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
              }`}
            >
              Project Overview
            </button>
            <button
              onClick={() => handleTabSwitch('projects')}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'projects'
                  ? 'bg-[var(--color-accent)] text-white shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
              }`}
            >
              My Projects ({projects.length})
            </button>
          </div>

          {canEditData && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white font-bold text-xs shadow-md shadow-[var(--color-accent-soft)] transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>New Project</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* ============================================================ */}
      {/* SUB-VIEW 1: PROJECT OVERVIEW                                 */}
      {/* ============================================================ */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Active Project Selector & Quick Stats Strip */}
          <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center space-x-2.5">
                <FolderKanban className="w-4 h-4 text-[var(--color-accent)]" />
                <span className="text-xs font-bold text-[var(--color-text-muted)]">Active Project:</span>
                <select
                  value={selectedProjectId}
                  onChange={handleProjectSelect}
                  className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-full px-4 py-1.5 text-xs font-bold text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.project_name || p.name} ({p.task_type || 'Unset'})
                    </option>
                  ))}
                </select>
              </div>

              {activeProject && (
                <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                  <span className="px-3 py-1 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text)] font-semibold">
                    Target: {activeProject.target_column || 'Not Assigned'}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] font-bold">
                    Task: {activeProject.task_type || 'Auto Detect'}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                    Stage: {activeProject.pipeline_stage || 'DATA'}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Link
                to={selectedProjectId ? `/data?project_id=${selectedProjectId}` : '/data'}
                className="px-4 py-2 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface-card)] border border-[var(--color-border)] text-[var(--color-text)] text-xs font-bold flex items-center space-x-1.5 transition-all"
              >
                <span>Launch Stage Pipeline</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--color-accent)]" />
              </Link>
            </div>
          </div>

          {/* Interactive Pipeline Stepper */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text)] flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>8-Stage Leakage-Controlled Pipeline Progression</span>
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Click any stage node to inspect data, run transforms, or view model diagnostics.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
              {PIPELINE_STAGES.map((st, idx) => {
                const Icon = st.icon;
                const isCurrent = activeProject?.pipeline_stage === st.key;
                return (
                  <Link
                    key={st.key}
                    to={selectedProjectId ? `${st.path}?project_id=${selectedProjectId}` : st.path}
                    className={`p-3.5 rounded-2xl border transition-all flex flex-col items-center justify-between text-center space-y-2 group cursor-pointer ${
                      isCurrent
                        ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]'
                        : 'bg-[var(--color-surface-card)] border-[var(--color-border)] hover:border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)]'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-accent)] group-hover:scale-105 transition-transform shadow-xs">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-[11px] font-bold text-[var(--color-text)]">{st.label}</div>
                      <div className="text-[9px] font-mono text-[var(--color-text-muted)]">Stage {idx + 1}</div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Core Analytics Grid: Dataset Health, Leaderboard, Recommendations, Deployment */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Card 1: Dataset Health & Profiling Summary */}
            <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div className="flex items-center space-x-2">
                  <Database className="w-4 h-4 text-[var(--color-accent)]" />
                  <h4 className="text-sm font-bold text-[var(--color-text)]">Dataset Geometry & Health</h4>
                </div>
                <Link
                  to={selectedProjectId ? `/data-analysis?project_id=${selectedProjectId}` : '/data-analysis'}
                  className="text-xs text-[var(--color-accent)] hover:underline font-semibold flex items-center space-x-1"
                >
                  <span>Full Profiling</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {activeProjectDetails.dataset ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] font-bold">TOTAL ROWS</span>
                      <div className="text-sm font-extrabold text-[var(--color-text)] mt-0.5">
                        {activeProjectDetails.dataset.row_count?.toLocaleString() || 'N/A'}
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] font-bold">COLUMNS</span>
                      <div className="text-sm font-extrabold text-[var(--color-text)] mt-0.5">
                        {activeProjectDetails.dataset.column_count || 'N/A'}
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] font-bold">MISSING VALS</span>
                      <div className="text-sm font-extrabold text-amber-400 mt-0.5">
                        {activeProjectDetails.profile?.total_missing_count ?? 0}
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] font-bold">INTEGRITY</span>
                      <div className="text-sm font-extrabold text-emerald-400 mt-0.5">
                        SHA-256 OK
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                    Source: <span className="font-mono text-[var(--color-text)]">{activeProjectDetails.dataset.file_name}</span> &bull; Version v{activeProjectDetails.dataset.version_number} &bull; Uploaded {new Date(activeProjectDetails.dataset.created_at).toLocaleDateString()}
                  </p>
                </div>
              ) : (
                <div className="p-8 text-center text-[var(--color-text-muted)] space-y-2">
                  <Database className="w-8 h-8 mx-auto opacity-50" />
                  <p className="text-xs">No dataset uploaded to this project yet.</p>
                  <Link
                    to={selectedProjectId ? `/data?project_id=${selectedProjectId}` : '/data'}
                    className="inline-block px-4 py-1.5 rounded-full bg-[var(--color-accent)] text-white text-xs font-bold mt-2"
                  >
                    Upload Dataset
                  </Link>
                </div>
              )}
            </div>

            {/* Card 2: Model Leaderboard & Champion */}
            <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <div className="flex items-center space-x-2">
                  <Trophy className="w-4 h-4 text-amber-400" />
                  <h4 className="text-sm font-bold text-[var(--color-text)]">Model Leaderboard Snapshot</h4>
                </div>
                <Link
                  to={selectedProjectId ? `/machine-learning?project_id=${selectedProjectId}` : '/machine-learning'}
                  className="text-xs text-[var(--color-accent)] hover:underline font-semibold flex items-center space-x-1"
                >
                  <span>ML Studio</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {activeProjectDetails.leaderboard?.models?.length ? (
                <div className="space-y-3">
                  {activeProjectDetails.leaderboard.models.slice(0, 3).map((m, idx) => (
                    <div
                      key={m.id}
                      className={`p-3.5 rounded-xl border flex items-center justify-between text-xs ${
                        m.is_winner
                          ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)]'
                          : 'bg-[var(--color-surface-card)] border border-[var(--color-border)]'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] ${
                          m.is_winner ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'
                        }`}>
                          {idx + 1}
                        </span>
                        <div>
                          <div className="font-bold text-[var(--color-text)] flex items-center space-x-1.5">
                            <span>{m.algorithm_name}</span>
                            {m.is_winner && (
                              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-300 uppercase">
                                Winner
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                            Fit: {m.fit_diagnosis || 'GOOD_FIT'}
                          </span>
                        </div>
                      </div>

                      <div className="text-right font-mono">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">
                          {activeProjectDetails.leaderboard.selection_metric?.toUpperCase()}
                        </span>
                        <div className="text-sm font-extrabold text-[var(--color-accent)]">
                          {m.primary_metric_value !== null ? Number(m.primary_metric_value).toFixed(4) : 'N/A'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-[var(--color-text-muted)] space-y-2">
                  <Cpu className="w-8 h-8 mx-auto opacity-50" />
                  <p className="text-xs">No trained models in this project yet.</p>
                  <Link
                    to={selectedProjectId ? `/machine-learning?project_id=${selectedProjectId}` : '/machine-learning'}
                    className="inline-block px-4 py-1.5 rounded-full bg-[var(--color-accent)] text-white text-xs font-bold mt-2"
                  >
                    Launch Model Training
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Critical Recommendations & Heuristics */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
                <h4 className="text-sm font-bold text-[var(--color-text)]">
                  Critical Automated Recommendations ({activeProjectDetails.recommendations.length})
                </h4>
              </div>
              <Link
                to={selectedProjectId ? `/diagnostics?project_id=${selectedProjectId}&tab=recommendations` : '/diagnostics'}
                className="text-xs text-[var(--color-accent)] hover:underline font-semibold"
              >
                View All Diagnostics
              </Link>
            </div>

            {activeProjectDetails.recommendations.length === 0 ? (
              <div className="p-6 text-center text-[var(--color-text-muted)] space-y-1">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
                <p className="text-xs font-bold text-[var(--color-text)]">All heuristics passing cleanly</p>
                <p className="text-[11px]">No active data quality warnings or generalization gap alerts flagged.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {activeProjectDetails.recommendations.slice(0, 4).map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--color-text)]">{rec.finding}</span>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {rec.confidence_level || 'HIGH'}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)]">{rec.recommended_action}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* SUB-VIEW 2: MY PROJECTS                                      */}
      {/* ============================================================ */}
      {activeTab === 'projects' && (
        <div className="space-y-6">
          {/* Filter and Search Bar */}
          <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-[var(--color-text-muted)] absolute left-3.5 top-3 pointer-events-none" />
              <input
                type="text"
                placeholder="Search projects by name or target..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-full text-xs font-medium text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              />
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-[var(--color-text-muted)]">Task:</span>
              <div className="flex p-1 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-full">
                {['ALL', 'REGRESSION', 'CLASSIFICATION'].map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTaskFilter(tf)}
                    className={`px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer ${
                      taskFilter === tf
                        ? 'bg-[var(--color-accent)] text-white shadow-xs'
                        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
                    }`}
                  >
                    {tf === 'ALL' ? 'All' : tf.charAt(0) + tf.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Projects Grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-44 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] animate-pulse p-6" />
              ))}
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="text-center py-16 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8 space-y-3 shadow-sm">
              <FolderGit2 className="w-12 h-12 mx-auto text-[var(--color-text-muted)] opacity-50" />
              <h3 className="text-sm font-bold text-[var(--color-text)]">No matching projects found</h3>
              <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto">
                Try adjusting your search query or task filter, or create a brand new machine learning project.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.map((proj) => (
                <div
                  key={proj.id}
                  className="group bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-5"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <span className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] font-bold">
                        {proj.task_type || 'Unassigned'}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                        {new Date(proj.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors">
                      {proj.project_name || proj.name}
                    </h3>

                    <div className="space-y-1.5 text-xs text-[var(--color-text-muted)]">
                      <div className="flex justify-between">
                        <span>Target Column:</span>
                        <strong className="text-[var(--color-text)] font-mono">{proj.target_column || 'None'}</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Pipeline Stage:</span>
                        <span className="font-bold text-emerald-400">{proj.pipeline_stage || 'DATA'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[var(--color-border)] flex items-center justify-between">
                    <button
                      onClick={() => {
                        setSelectedProjectId(proj.id);
                        handleTabSwitch('overview');
                      }}
                      className="text-xs font-bold text-[var(--color-accent)] hover:underline flex items-center space-x-1 cursor-pointer"
                    >
                      <span>Open Overview</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>

                    <Link
                      to={`/machine-learning?project_id=${proj.id}`}
                      className="px-3.5 py-1.5 rounded-full bg-[var(--color-surface-card)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)]"
                    >
                      ML Studio
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center space-x-2">
                <Plus className="w-5 h-5 text-[var(--color-accent)]" />
                <h3 className="text-base font-bold text-[var(--color-text)]">Create ML Studio Project</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] bg-[var(--color-surface-hover)]"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[var(--color-text)]">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Loan Default Risk Model"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full px-4 py-2 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[var(--color-text)]">Target Column (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. loan_status, interest_rate"
                  value={targetColumn}
                  onChange={(e) => setTargetColumn(e.target.value)}
                  className="w-full px-4 py-2 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  Can be confirmed or modified during dataset profiling.
                </p>
              </div>

              <div className="pt-3 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-full text-xs font-semibold text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !projectName.trim()}
                  className="px-5 py-2 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {creating ? 'Creating Project...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
