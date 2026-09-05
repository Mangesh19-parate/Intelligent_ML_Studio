import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { projectApi, datasetApi, datasetSplitApi } from '../api/client';
import { DataQualityCard } from '../components/DataQualityCard';
import { TaskTypeSelector } from '../components/TaskTypeSelector';
import { CorrelationHeatmap } from '../components/CorrelationHeatmap';
import { RecommendationsList } from '../components/RecommendationsList';
import { ColumnStatsTable } from '../components/ColumnStatsTable';
import { TransformationsTable } from '../components/TransformationsTable';
import { ModelTraining } from '../components/ModelTraining';
import {
  Upload,
  Database,
  ArrowLeft,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  Info,
  Clock,
  Lock,
  ShieldCheck,
  Split,
  Sliders,
  Shuffle,
  Hash,
  Eye,
  Check,
  BarChart3,
  RefreshCw,
  Lightbulb,
  Table,
  Activity,
  Flame,
  Wand2,
  Cpu
} from 'lucide-react';

export const ProjectDetail = () => {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get('tab');
  const [project, setProject] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [columns, setColumns] = useState([]);
  const [splitSummary, setSplitSummary] = useState(null);
  const [devPreview, setDevPreview] = useState(null);
  
  // Profiling & Diagnostics State
  const [profilingReport, setProfilingReport] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [profilingRunning, setProfilingRunning] = useState(false);
  const [activeTab, setActiveTab] = useState(urlTab || 'PROFILING');

  useEffect(() => {
    if (urlTab) {
      setActiveTab(urlTab);
    }
  }, [urlTab]);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [creatingSplit, setCreatingSplit] = useState(false);
  const [lockedTestPct, setLockedTestPct] = useState(20);
  const [splitSeed, setSplitSeed] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadSplitAndPreview = async (datasetId) => {
    try {
      const splitRes = await datasetSplitApi.getSplit(datasetId);
      setSplitSummary(splitRes.data);

      const previewRes = await datasetSplitApi.getDevelopmentPreview(datasetId, 10);
      setDevPreview(previewRes.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setSplitSummary(null);
        setDevPreview(null);
      }
    }
  };

  const loadProfilingAndRecs = async (datasetId) => {
    try {
      const profRes = await datasetApi.getProfile(datasetId);
      setProfilingReport(profRes.data);
    } catch (err) {
      setProfilingReport(null);
    }

    try {
      const recsRes = await projectApi.getRecommendations(id);
      setRecommendations(recsRes.data || []);
    } catch (err) {
      setRecommendations([]);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const projRes = await projectApi.get(id);
      setProject(projRes.data);

      const dsRes = await datasetApi.listVersions(id);
      setDatasets(dsRes.data);

      if (dsRes.data.length > 0) {
        const latest = dsRes.data[0];
        setSelectedDataset(latest);
        const colRes = await datasetApi.getColumns(latest.id);
        setColumns(colRes.data);
        await loadSplitAndPreview(latest.id);
        await loadProfilingAndRecs(latest.id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleSelectDataset = async (dataset) => {
    setSelectedDataset(dataset);
    setError('');
    setSuccessMsg('');
    try {
      const colRes = await datasetApi.getColumns(dataset.id);
      setColumns(colRes.data);
      await loadSplitAndPreview(dataset.id);
      await loadProfilingAndRecs(dataset.id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await datasetApi.upload(id, file);
      setSuccessMsg('Dataset uploaded and structural metadata inferred successfully.');
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload and structural parse failed');
    } finally {
      setUploading(false);
    }
  };

  const handleCreateSplit = async (e) => {
    e.preventDefault();
    if (!selectedDataset) return;
    setCreatingSplit(true);
    setError('');
    setSuccessMsg('');
    try {
      const payload = {
        locked_test_pct: Number(lockedTestPct),
        seed: splitSeed ? Number(splitSeed) : null,
      };
      const res = await datasetSplitApi.createSplit(selectedDataset.id, payload);
      setSplitSummary(res.data);
      setSuccessMsg(`Outer split partition created successfully (${res.data.development_rows} Dev rows, ${res.data.locked_test_rows} Locked Test rows).`);
      
      const previewRes = await datasetSplitApi.getDevelopmentPreview(selectedDataset.id, 10);
      setDevPreview(previewRes.data);

      // Refresh project
      const projRes = await projectApi.get(id);
      setProject(projRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create outer split');
    } finally {
      setCreatingSplit(false);
    }
  };

  const handleRandomizeSeed = () => {
    const randomVal = Math.floor(Math.random() * 1000000) + 1;
    setSplitSeed(randomVal.toString());
  };

  const handleTriggerProfile = async () => {
    if (!selectedDataset) return;
    setProfilingRunning(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await datasetApi.profile(selectedDataset.id);
      setProfilingReport(res.data);
      setSuccessMsg('Data profiling and DQI diagnostics completed successfully on the Development partition.');
      
      // Reload project and recommendations
      const projRes = await projectApi.get(id);
      setProject(projRes.data);

      const recsRes = await projectApi.getRecommendations(id);
      setRecommendations(recsRes.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Profiling execution failed');
    } finally {
      setProfilingRunning(false);
    }
  };

  const handleTaskTypeConfirmed = async (taskType) => {
    const projRes = await projectApi.updateTaskType(id, taskType);
    setProject(projRes.data);
    setSuccessMsg(`Task type confirmed as ${taskType}.`);
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="h-64 rounded-2xl bg-slate-900 border border-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Nav Back */}
      <div className="flex items-center space-x-3">
        <Link
          to="/dashboard"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Projects</span>
        </Link>
      </div>

      {/* Project Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-extrabold text-white">{project?.project_name}</h1>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                {project?.task_type}
              </span>
              {project?.task_type_confidence && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                  {project.task_type_confidence} CONFIDENCE
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
              {project?.target_column && (
                <span>Target Column: <strong className="text-white font-mono">{project.target_column}</strong></span>
              )}
              <span>Pipeline Stage: <strong className="text-emerald-400 font-mono font-bold">{project?.pipeline_stage}</strong></span>
              {project?.data_quality_index !== null && project?.data_quality_index !== undefined && (
                <span>Overall DQI: <strong className="text-indigo-300 font-mono font-bold">{Number(project.data_quality_index).toFixed(1)}/100</strong></span>
              )}
              <span>Dataset Versions: <strong className="text-white">{datasets.length}</strong></span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {splitSummary && (
              <button
                onClick={handleTriggerProfile}
                disabled={profilingRunning}
                className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${profilingRunning ? 'animate-spin' : ''}`} />
                <span>{profilingRunning ? 'Profiling Development Data...' : 'Run Data Profiling & DQI'}</span>
              </button>
            )}

            <label className="cursor-pointer inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all">
              <Upload className="w-4 h-4" />
              <span>{uploading ? 'Validating...' : 'Upload Dataset'}</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.json"
                className="hidden"
                disabled={uploading}
                onChange={(e) => handleFileUpload(e.target.files?.[0])}
              />
            </label>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Sixth Invariant Info Callout */}
      <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15 text-xs text-indigo-300 flex items-start space-x-3">
        <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-white">The Sixth Invariant (Strict Locked-Test Isolation): </strong>
          No data-dependent decisions, descriptive profiling, or feature engineering occur before the Outer Split. Profiling operates exclusively on <code className="text-indigo-300 bg-slate-950 px-1 py-0.5 rounded font-mono">DatasetSplitService.get_development_data()</code>.
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left: Version History & Upload Drag Zone */}
        <div className="space-y-6">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-4">
              Version History
            </h3>
            {datasets.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No datasets uploaded yet.</p>
            ) : (
              <div className="space-y-2">
                {datasets.map((ds) => (
                  <button
                    key={ds.id}
                    onClick={() => handleSelectDataset(ds)}
                    className={`w-full text-left p-3 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
                      selectedDataset?.id === ds.id
                        ? 'bg-indigo-600/15 border-indigo-500 font-semibold text-indigo-300'
                        : 'bg-slate-950/40 border-slate-800 text-slate-300 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <FileSpreadsheet className="w-4 h-4 shrink-0" />
                      <span>Version {ds.version_number}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">
                      {ds.row_count} rows
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Upload Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFileUpload(e.dataTransfer.files?.[0]);
            }}
            className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all ${
              dragOver
                ? 'border-indigo-500 bg-indigo-500/5'
                : 'border-slate-800 bg-slate-900/60'
            }`}
          >
            <Upload className="w-8 h-8 mx-auto text-slate-500 mb-2" />
            <p className="text-xs font-semibold text-white">Drag & drop dataset</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Supports .csv, .xlsx, .json
            </p>
          </div>

          {/* Dataset Integrity Card */}
          {selectedDataset && selectedDataset.content_hash && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm text-xs space-y-2">
              <div className="flex items-center space-x-1.5 text-white font-semibold">
                <Hash className="w-3.5 h-3.5 text-indigo-400" />
                <span>SHA-256 Content Hash</span>
              </div>
              <p className="font-mono text-[10px] text-slate-400 break-all bg-slate-950 p-2 rounded-lg border border-slate-800">
                {selectedDataset.content_hash}
              </p>
            </div>
          )}
        </div>

        {/* Right Area: Tabs Navigation & Workflows */}
        <div className="lg:col-span-3 space-y-6">
          {/* Tabs */}
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 overflow-x-auto">
            <button
              onClick={() => setActiveTab('PROFILING')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                activeTab === 'PROFILING'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Data Profiling & DQI</span>
              {profilingReport && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </button>

            <button
              onClick={() => setActiveTab('TRANSFORMATIONS')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                activeTab === 'TRANSFORMATIONS'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Wand2 className="w-4 h-4" />
              <span>Feature Transformations</span>
            </button>

            <button
              onClick={() => setActiveTab('TRAINING')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                activeTab === 'TRAINING'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>Model Training</span>
            </button>

            <button
              onClick={() => setActiveTab('SPLIT')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                activeTab === 'SPLIT'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Split className="w-4 h-4" />
              <span>Outer Split Partition</span>
            </button>

            <button
              onClick={() => setActiveTab('SCHEMA')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                activeTab === 'SCHEMA'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Table className="w-4 h-4" />
              <span>Structural Schema</span>
            </button>
          </div>

          {/* TAB 1: DATA PROFILING & DQI */}
          {activeTab === 'PROFILING' && (
            <div className="space-y-6">
              {!splitSummary ? (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
                  <Split className="w-12 h-12 mx-auto text-amber-400" />
                  <h3 className="text-base font-bold text-white">Outer Split Required Before Profiling</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    To enforce leakage prevention, Data Profiling and DQI calculations require an active train/test split.
                  </p>
                  <button
                    onClick={() => setActiveTab('SPLIT')}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl"
                  >
                    Configure Outer Split
                  </button>
                </div>
              ) : !profilingReport ? (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
                  <Sparkles className="w-12 h-12 mx-auto text-indigo-400" />
                  <h3 className="text-base font-bold text-white">Development Partition Ready to Profile</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Run Stage B distributional profiling, compute the Data Quality Index (DQI), and infer optimal task type.
                  </p>
                  <button
                    onClick={handleTriggerProfile}
                    disabled={profilingRunning}
                    className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-emerald-500/20"
                  >
                    {profilingRunning ? 'Computing DQI...' : 'Run Data Profiling Now'}
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Task Type Suggestion / Choice */}
                  <TaskTypeSelector
                    projectId={id}
                    currentTaskType={project?.task_type}
                    taskTypeConfidence={project?.task_type_confidence}
                    taskTypeSuggestion={profilingReport.task_type_suggestion}
                    onTaskTypeConfirmed={handleTaskTypeConfirmed}
                  />

                  {/* Data Quality Index (DQI) Card */}
                  <DataQualityCard dqiData={profilingReport.data_quality_index} />

                  {/* Recommendations */}
                  <RecommendationsList recommendations={recommendations} />

                  {/* Pearson Correlation Heatmap */}
                  <CorrelationHeatmap correlationData={profilingReport.correlation_matrix} />

                  {/* Column Stats Table */}
                  <ColumnStatsTable columnStats={profilingReport.column_stats} />
                </div>
              )}
            </div>
          )}

          {/* TAB 2: OUTER SPLIT */}
          {activeTab === 'SPLIT' && selectedDataset && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                    <Split className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">Outer Split: Development / Locked Test Partition</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Freeze and isolate the final test partition before Stage B profiling and training.
                    </p>
                  </div>
                </div>

                {splitSummary ? (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                    <Check className="w-3.5 h-3.5" />
                    <span>Partition Established</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
                    <Clock className="w-3.5 h-3.5" />
                    <span>Split Pending</span>
                  </span>
                )}
              </div>

              {!splitSummary ? (
                <form onSubmit={handleCreateSplit} className="space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div className="space-y-2 bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
                          <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Locked Test Percentage</span>
                        </label>
                        <span className="font-mono text-xs font-bold text-indigo-400">
                          {lockedTestPct}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="5"
                        max="50"
                        step="1"
                        value={lockedTestPct}
                        onChange={(e) => setLockedTestPct(Number(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                      <div className="flex justify-between text-[10px] text-slate-500">
                        <span>5% (Minimal)</span>
                        <span>20% (Default)</span>
                        <span>50% (Equal)</span>
                      </div>
                    </div>

                    <div className="space-y-2 bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-white flex items-center space-x-1.5">
                          <Shuffle className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Partition Seed (Optional)</span>
                        </label>
                        <button
                          type="button"
                          onClick={handleRandomizeSeed}
                          className="text-[11px] text-indigo-400 hover:underline flex items-center space-x-1"
                        >
                          <Shuffle className="w-3 h-3" />
                          <span>Randomize</span>
                        </button>
                      </div>
                      <input
                        type="number"
                        placeholder="Leave blank for auto-generated seed"
                        value={splitSeed}
                        onChange={(e) => setSplitSeed(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg border border-slate-800 bg-slate-900 text-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                      <p className="text-[10px] text-slate-500">
                        Guarantees deterministic, reproducible partition sampling.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-slate-400">
                      Stratification is automatically applied when the target column is categorical.
                    </p>
                    <button
                      type="submit"
                      disabled={creatingSplit}
                      className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
                    >
                      <Split className="w-4 h-4" />
                      <span>{creatingSplit ? 'Creating Partition...' : 'Create Train/Test Split'}</span>
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Development Partition
                      </div>
                      <div className="text-xl font-extrabold text-white font-mono">
                        {splitSummary.development_rows.toLocaleString()}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({100 - splitSummary.locked_test_pct}%)
                        </span>
                      </div>
                      <div className="inline-flex items-center space-x-1 text-[10px] text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Authorized for Days 3–6</span>
                      </div>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Locked Test Partition
                      </div>
                      <div className="text-xl font-extrabold text-white font-mono">
                        {splitSummary.locked_test_rows.toLocaleString()}{' '}
                        <span className="text-xs font-normal text-slate-400">
                          ({splitSummary.locked_test_pct}%)
                        </span>
                      </div>
                      <div className="inline-flex items-center space-x-1 text-[10px] text-rose-400 font-semibold">
                        <Lock className="w-3 h-3" />
                        <span>Sealed Until Day 7 Eval</span>
                      </div>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Stratification
                      </div>
                      <div className="text-xl font-extrabold text-white">
                        {splitSummary.is_stratified ? (
                          <span className="text-indigo-400">Yes (Target)</span>
                        ) : (
                          <span className="text-slate-400">No (Random)</span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {splitSummary.is_stratified ? 'Proportional class balance' : 'Uniform random partition'}
                      </div>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Partition Seed
                      </div>
                      <div className="text-xl font-extrabold text-white font-mono">
                        {splitSummary.split_seed}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        Deterministic & reproducible
                      </div>
                    </div>
                  </div>

                  {devPreview && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Eye className="w-4 h-4 text-indigo-400" />
                          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                            Development Partition Data Preview (Top {devPreview.preview_rows.length} rows)
                          </h3>
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">
                          Total Dev Rows: {devPreview.total_development_rows}
                        </span>
                      </div>

                      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold text-[10px]">
                            <tr>
                              <th className="px-4 py-2.5">#</th>
                              {devPreview.columns.map((col) => (
                                <th key={col} className="px-4 py-2.5 font-mono text-white">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                            {devPreview.preview_rows.map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                                <td className="px-4 py-2.5 text-slate-500 font-bold">
                                  {idx + 1}
                                </td>
                                {devPreview.columns.map((col) => (
                                  <td key={col} className="px-4 py-2.5 text-slate-200 truncate max-w-[200px]">
                                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : (
                                      <span className="text-slate-500 italic">null</span>
                                    )}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB: FEATURE TRANSFORMATIONS */}
          {activeTab === 'TRANSFORMATIONS' && (
            <div className="space-y-6">
              {!selectedDataset ? (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
                  <Database className="w-12 h-12 mx-auto text-amber-400" />
                  <h3 className="text-base font-bold text-white">Dataset Required</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Please upload or select a dataset version to configure column transformations.
                  </p>
                </div>
              ) : (
                <TransformationsTable
                  projectId={id}
                  isTargetColumn={(colName) => project?.target_column === colName}
                  onTransformationChanged={async () => {
                    const projRes = await projectApi.get(id);
                    setProject(projRes.data);
                  }}
                />
              )}
            </div>
          )}

          {/* TAB: MODEL TRAINING */}
          {activeTab === 'TRAINING' && (
            <div className="space-y-6">
              <ModelTraining
                projectId={id}
                taskType={project?.task_type}
                targetColumn={project?.target_column}
                onExperimentCompleted={async () => {
                  const projRes = await projectApi.get(id);
                  setProject(projRes.data);
                }}
              />
            </div>
          )}

          {/* TAB 3: STRUCTURAL SCHEMA */}
          {activeTab === 'SCHEMA' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
              <div className="p-5 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Structural Schema Metadata {selectedDataset && `(Version ${selectedDataset.version_number})`}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedDataset
                      ? `${selectedDataset.row_count} rows × ${selectedDataset.column_count} columns`
                      : 'Select or upload a dataset to inspect structural schema'}
                  </p>
                </div>
              </div>

              {columns.length === 0 ? (
                <div className="text-center py-16 text-xs text-slate-500">
                  No column metadata available. Upload a dataset to begin.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                      <tr>
                        <th className="px-6 py-3.5">Column Name</th>
                        <th className="px-6 py-3.5">Inferred DType</th>
                        <th className="px-6 py-3.5">Unique Count</th>
                        <th className="px-6 py-3.5">Missing (%)</th>
                        <th className="px-6 py-3.5">Role</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 font-sans">
                      {columns.map((col) => (
                        <tr key={col.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-6 py-4 font-mono font-semibold text-white">
                            {col.column_name}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                              col.data_type === 'NUMERIC'
                                ? 'bg-blue-500/10 text-blue-400'
                                : col.data_type === 'DATETIME'
                                ? 'bg-purple-500/10 text-purple-400'
                                : col.data_type === 'CATEGORICAL'
                                ? 'bg-amber-500/10 text-amber-400'
                                : 'bg-rose-500/10 text-rose-400'
                            }`}>
                              {col.data_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-mono text-slate-200">
                            {col.unique_count.toLocaleString()}
                          </td>
                          <td className="px-6 py-4 font-mono text-slate-200">
                            {col.missing_percentage}%
                          </td>
                          <td className="px-6 py-4">
                            {col.is_target ? (
                              <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-bold text-[10px] border border-indigo-500/30">
                                TARGET
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[11px]">Feature</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
