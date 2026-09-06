import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, datasetApi, datasetSplitApi } from '../api/client';
import { DataQualityCard } from '../components/DataQualityCard';
import { TaskTypeSelector } from '../components/TaskTypeSelector';
import { RecommendationsList } from '../components/RecommendationsList';
import { CorrelationHeatmap } from '../components/CorrelationHeatmap';
import { ColumnStatsTable } from '../components/ColumnStatsTable';
import {
  BarChart3,
  ShieldCheck,
  Sparkles,
  Split,
  ArrowRight,
  RefreshCw,
  FolderOpen,
  AlertTriangle,
  Layers,
  Database,
  Info,
} from 'lucide-react';

export const DataAnalysisStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get('project_id');

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);

  const [selectedDataset, setSelectedDataset] = useState(null);
  const [splitSummary, setSplitSummary] = useState(null);
  const [profilingReport, setProfilingReport] = useState(null);
  const [recommendations, setRecommendations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [profilingRunning, setProfilingRunning] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Load projects
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

  // When selected project changes, load dataset, split, and profiling report
  useEffect(() => {
    if (!selectedProjectId) {
      setLoading(false);
      return;
    }

    const loadProjectAnalysis = async () => {
      setLoading(true);
      setError('');
      try {
        const projResp = await projectApi.get(selectedProjectId);
        const proj = projResp.data;
        setCurrentProject(proj);

        // Load dataset versions
        const dsResp = await datasetApi.listVersions(selectedProjectId);
        const dsList = dsResp.data || [];

        if (dsList.length === 0) {
          setSelectedDataset(null);
          setSplitSummary(null);
          setProfilingReport(null);
          setRecommendations([]);
          setLoading(false);
          return;
        }

        const activeDataset = dsList[0];
        setSelectedDataset(activeDataset);

        // Check outer split
        try {
          const splitResp = await datasetSplitApi.getSplit(activeDataset.id);
          setSplitSummary(splitResp.data);

          // If split exists, attempt to load profiling report
          try {
            const profResp = await datasetApi.getProfile(activeDataset.id);
            setProfilingReport(profResp.data);
          } catch {
            setProfilingReport(null);
          }

          // Load recommendations
          try {
            const recsResp = await projectApi.getRecommendations(selectedProjectId);
            setRecommendations(recsResp.data || []);
          } catch {
            setRecommendations([]);
          }
        } catch {
          setSplitSummary(null);
          setProfilingReport(null);
          setRecommendations([]);
        }
      } catch (err) {
        console.error('Error loading project analysis data', err);
        setError('Failed to load analysis metrics for the active project.');
      } finally {
        setLoading(false);
      }
    };

    loadProjectAnalysis();
  }, [selectedProjectId]);

  const handleSelectProject = (projectId) => {
    setSelectedProjectId(projectId);
    setSearchParams({ project_id: projectId });
  };

  const handleTriggerProfile = async () => {
    if (!selectedDataset) return;
    setProfilingRunning(true);
    setError('');
    setSuccessMsg('');
    try {
      const resp = await datasetApi.profile(selectedDataset.id);
      setProfilingReport(resp.data);

      const projResp = await projectApi.get(selectedProjectId);
      setCurrentProject(projResp.data);

      const recsResp = await projectApi.getRecommendations(selectedProjectId);
      setRecommendations(recsResp.data || []);

      setSuccessMsg('Development data profiling and DQI diagnostics completed successfully.');
    } catch (err) {
      console.error('Failed to run profiling', err);
      setError(err.response?.data?.detail || 'Failed to execute data profiling.');
    } finally {
      setProfilingRunning(false);
    }
  };

  const handleTaskTypeConfirmed = (confirmedType) => {
    if (currentProject) {
      setCurrentProject({
        ...currentProject,
        task_type: confirmedType,
        task_type_confidence: 'MANUAL',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-400 font-medium">Loading Data Analysis & DQI diagnostics...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
            <span>Stage 3 of 8</span>
            <span>&bull;</span>
            <span>Development Profiling & DQI</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-3">
            <span>Data Analysis & Quality Diagnostics</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Distributional profiling, Pearson correlations, task-type inference, and the multi-factor Data Quality Index.
          </p>
        </div>

        {/* Project Selector & Next Stage Action */}
        <div className="flex items-center gap-3 flex-wrap">
          {projects.length > 0 && (
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
              <FolderOpen className="w-4 h-4 text-slate-400" />
              <select
                id="project-select"
                value={selectedProjectId}
                onChange={(e) => handleSelectProject(e.target.value)}
                className="bg-transparent text-xs font-medium text-white border-none focus:outline-none cursor-pointer pr-2"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-slate-900 text-white">
                    {p.project_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Link
            to={`/transformations?project_id=${selectedProjectId}`}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition shadow-indigo-600/20"
          >
            <span>Next: Transformations</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Alert Banners */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-xl text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <p>{error}</p>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded-xl text-xs flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 shrink-0 text-emerald-400" />
          <p>{successMsg}</p>
        </div>
      )}

      {/* Main Analysis Stage Flow */}
      {!selectedDataset ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-4 max-w-lg mx-auto shadow-xl">
          <Database className="w-12 h-12 mx-auto text-slate-500" />
          <h3 className="text-base font-bold text-white">No Dataset Uploaded Yet</h3>
          <p className="text-xs text-slate-400">
            Upload your tabular dataset in Stage 2 (Data) to generate schemas and compute data quality diagnostics.
          </p>
          <Link
            to={`/data?project_id=${selectedProjectId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl"
          >
            <span>Go to Data Ingestion</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : !splitSummary ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-4 max-w-lg mx-auto shadow-xl">
          <Split className="w-12 h-12 mx-auto text-amber-400" />
          <h3 className="text-base font-bold text-white">Outer Split Required Before Profiling</h3>
          <p className="text-xs text-slate-400">
            To enforce strict leakage prevention (The Sixth Invariant), Data Profiling and DQI operate exclusively on the isolated Development partition.
          </p>
          <Link
            to={`/data?project_id=${selectedProjectId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl"
          >
            <span>Configure Outer Split in Stage 2</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : !profilingReport ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-5 max-w-xl mx-auto shadow-xl">
          <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl w-16 h-16 mx-auto flex items-center justify-center text-indigo-400">
            <Sparkles className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Development Partition Ready for Analysis</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Execute Stage B distributional profiling, compute the multi-factor Data Quality Index (DQI), and evaluate task-type confidence.
            </p>
          </div>
          <button
            onClick={handleTriggerProfile}
            disabled={profilingRunning}
            id="run-profiling-btn"
            className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-500/20 transition-all cursor-pointer inline-flex items-center gap-2"
          >
            {profilingRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Computing DQI & Distributional Metrics...</span>
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4" />
                <span>Run Data Profiling & DQI Now</span>
              </>
            )}
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {/* 1. Task Type Suggestion & Confidence Selector */}
          <TaskTypeSelector
            projectId={selectedProjectId}
            currentTaskType={currentProject?.task_type}
            taskTypeConfidence={currentProject?.task_type_confidence}
            taskTypeSuggestion={profilingReport.task_type_suggestion}
            onTaskTypeConfirmed={handleTaskTypeConfirmed}
          />

          {/* 2. Data Quality Index (DQI) with Effective Weights */}
          <DataQualityCard dqiData={profilingReport.data_quality_index} />

          {/* 3. Traceable Prescriptive Recommendation Cards */}
          <RecommendationsList recommendations={recommendations} />

          {/* 4. Pearson Correlation Matrix Heatmap */}
          <CorrelationHeatmap correlationData={profilingReport.correlation_matrix} />

          {/* 5. Column Distribution Statistics Table */}
          <ColumnStatsTable columnStats={profilingReport.column_stats} />
        </div>
      )}
    </div>
  );
};

export default DataAnalysisStage;
