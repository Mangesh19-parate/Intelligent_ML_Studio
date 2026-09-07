import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, experimentApi, datasetApi, datasetSplitApi } from '../api/client';
import { ModelTraining } from '../components/ModelTraining';
import {
  Cpu,
  Trophy,
  ShieldCheck,
  FolderOpen,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Layers,
  Database,
  RefreshCw,
  AlertTriangle,
  Info,
  CheckCircle2,
  Lock,
} from 'lucide-react';

export const MLStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get('project_id');

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);
  const [experimentsCount, setExperimentsCount] = useState(0);
  const [splitInfo, setSplitInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load project list
  const loadProjects = async () => {
    try {
      const resp = await projectApi.list();
      const projList = resp.data || [];
      setProjects(projList);

      if (!selectedProjectId && projList.length > 0) {
        const firstId = projList[0].id;
        setSelectedProjectId(firstId);
        setSearchParams({ project_id: firstId });
      }
    } catch (err) {
      console.error('Failed to load projects', err);
      setError('Failed to fetch workspace projects.');
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // When selectedProjectId changes, load details
  useEffect(() => {
    if (!selectedProjectId) {
      setLoading(false);
      return;
    }

    const loadProjectData = async () => {
      setLoading(true);
      setError('');
      try {
        const projResp = await projectApi.get(selectedProjectId);
        setCurrentProject(projResp.data);

        // Load experiments count
        try {
          const expResp = await experimentApi.listByProject(selectedProjectId);
          setExperimentsCount(expResp.data?.length || 0);
        } catch {
          setExperimentsCount(0);
        }

        // Load split info
        try {
          const dsResp = await datasetApi.listVersions(selectedProjectId);
          if (dsResp.data && dsResp.data.length > 0) {
            const splitResp = await datasetSplitApi.getSplit(dsResp.data[0].id);
            setSplitInfo(splitResp.data);
          } else {
            setSplitInfo(null);
          }
        } catch {
          setSplitInfo(null);
        }
      } catch (err) {
        console.error('Failed to load project data', err);
        setError('Failed to load project details.');
      } finally {
        setLoading(false);
      }
    };

    loadProjectData();
  }, [selectedProjectId]);

  const handleProjectSelect = (e) => {
    const id = e.target.value;
    setSelectedProjectId(id);
    if (id) {
      setSearchParams({ project_id: id });
    } else {
      setSearchParams({});
    }
  };

  const handleRefresh = () => {
    if (selectedProjectId) {
      const load = async () => {
        try {
          const expResp = await experimentApi.listByProject(selectedProjectId);
          setExperimentsCount(expResp.data?.length || 0);
        } catch (e) {
          console.error(e);
        }
      };
      load();
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header & Stage Progress Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-indigo-400 mb-1">
            <Cpu className="w-4 h-4 text-indigo-400" />
            <span>Stage 7 of 8 • Machine Learning Studio</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span>Model Training & Leaderboard</span>
            <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Zero Leakage Protocol
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Train baseline and non-linear ensemble models with strict out-of-fold cross-validation. Rank models strictly by primary metric and evaluate the winning model against the Locked Test partition.
          </p>
        </div>

        {/* Project Selector & Actions */}
        <div className="flex items-center space-x-3">
          <div className="relative min-w-[240px]">
            <select
              value={selectedProjectId}
              onChange={handleProjectSelect}
              className="w-full pl-9 pr-8 py-2.5 bg-slate-900 border border-slate-700 hover:border-slate-600 rounded-xl text-xs font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 cursor-pointer appearance-none transition-colors"
            >
              <option value="">-- Select Active Project --</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.task_type ? `(${p.task_type})` : ''}
                </option>
              ))}
            </select>
            <FolderOpen className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
          </div>

          <button
            onClick={handleRefresh}
            className="p-2.5 bg-slate-900 border border-slate-700 hover:border-slate-600 rounded-xl text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Refresh Stage Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      {selectedProjectId && currentProject && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="p-2.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20 text-indigo-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Task & Target
              </div>
              <div className="text-sm font-bold text-white flex items-center gap-1.5 mt-0.5">
                <span>{currentProject.task_type || 'Unassigned'}</span>
                {currentProject.target_column && (
                  <span className="text-xs text-indigo-300 font-mono">
                    ({currentProject.target_column})
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="p-2.5 bg-amber-500/10 rounded-lg border border-amber-500/20 text-amber-400">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Experiment Runs
              </div>
              <div className="text-sm font-bold text-white font-mono mt-0.5">
                {experimentsCount} Completed
              </div>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="p-2.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Leakage Guard
              </div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                Strict CV Isolation
              </div>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="p-2.5 bg-rose-500/10 rounded-lg border border-rose-500/20 text-rose-400">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Locked Test Partition
              </div>
              <div className="text-sm font-bold text-slate-200 mt-0.5">
                {splitInfo ? `${Math.round((splitInfo.test_rows / (splitInfo.train_rows + splitInfo.test_rows)) * 100)}% Holdout` : 'Configured'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {!selectedProjectId ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-4 shadow-xl">
          <Database className="w-12 h-12 mx-auto text-slate-600" />
          <h3 className="text-base font-bold text-white">Select a Project to View Leaderboard</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Choose a workspace project from the dropdown above to configure training algorithms, launch cross-validation experiments, and view the authoritative model leaderboard.
          </p>
        </div>
      ) : !currentProject?.task_type ? (
        <div className="bg-slate-900/90 border border-amber-500/30 rounded-2xl p-8 text-center space-y-4 shadow-xl">
          <AlertTriangle className="w-12 h-12 mx-auto text-amber-400" />
          <h3 className="text-base font-bold text-white">Task Type Not Configured</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Project <strong className="text-white">{currentProject?.name}</strong> does not have a confirmed task type (Regression or Classification) or target column yet.
          </p>
          <div className="pt-2">
            <Link
              to={`/data-analysis?project_id=${selectedProjectId}`}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-colors"
            >
              <span>Go to Data Analysis & Profiling</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      ) : (
        <ModelTraining
          projectId={selectedProjectId}
          taskType={currentProject.task_type}
          targetColumn={currentProject.target_column}
          onExperimentCompleted={handleRefresh}
        />
      )}

      {/* Stage Navigation Footer */}
      <div className="flex items-center justify-between pt-6 border-t border-slate-800">
        <Link
          to={selectedProjectId ? `/diagnostics?project_id=${selectedProjectId}` : '/diagnostics'}
          className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Stage 6: Diagnostics & Pre-Flight</span>
        </Link>

        <Link
          to={selectedProjectId ? `/production?project_id=${selectedProjectId}` : '/production'}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-colors"
        >
          <span>Proceed to Stage 8: Production</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
};

export default MLStage;
