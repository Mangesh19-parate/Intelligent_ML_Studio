import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { projectApi, datasetApi, datasetSplitApi } from '../api/client';
import {
  Database,
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ShieldCheck,
  Split,
  Shuffle,
  Copy,
  Check,
  ArrowRight,
  RefreshCw,
  Eye,
  Table,
  Layers,
  Sparkles,
  Info,
  Clock,
  Plus,
} from 'lucide-react';

export const DataStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialProjectId = searchParams.get('project_id');

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);

  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [columns, setColumns] = useState([]);
  const [splitSummary, setSplitSummary] = useState(null);
  const [devPreview, setDevPreview] = useState(null);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [creatingSplit, setCreatingSplit] = useState(false);
  const [lockedTestPct, setLockedTestPct] = useState(20);
  const [splitSeed, setSplitSeed] = useState('42');
  const [dragOver, setDragOver] = useState(false);
  const [copiedHash, setCopiedHash] = useState(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Quick Create Project Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newTargetCol, setNewTargetCol] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  // Load projects list
  const loadProjects = async () => {
    try {
      const res = await projectApi.list();
      const list = res.data?.items || res.data || [];
      setProjects(list);

      let targetId = selectedProjectId;
      if (!targetId && list.length > 0) {
        targetId = list[0].id;
        setSelectedProjectId(targetId);
        setSearchParams({ project_id: targetId });
      }
      return targetId;
    } catch (err) {
      console.error('Failed to load projects', err);
      return null;
    }
  };

  // Load dataset split and preview
  const loadSplitAndPreview = async (datasetId) => {
    try {
      const splitRes = await datasetSplitApi.getSplit(datasetId);
      setSplitSummary(splitRes.data);

      const previewRes = await datasetSplitApi.getDevelopmentPreview(datasetId, 10);
      setDevPreview(previewRes.data);
    } catch (err) {
      setSplitSummary(null);
      setDevPreview(null);
    }
  };

  // Load project details and its datasets
  const loadProjectData = async (projId) => {
    if (!projId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError('');
      const projRes = await projectApi.get(projId);
      setCurrentProject(projRes.data);

      const dsRes = await datasetApi.listVersions(projId);
      const dsList = dsRes.data || [];
      setDatasets(dsList);

      if (dsList.length > 0) {
        const latest = dsList[0];
        setSelectedDataset(latest);
        const colRes = await datasetApi.getColumns(latest.id);
        setColumns(colRes.data || []);
        await loadSplitAndPreview(latest.id);
      } else {
        setSelectedDataset(null);
        setColumns([]);
        setSplitSummary(null);
        setDevPreview(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load project datasets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      const targetId = await loadProjects();
      if (targetId) {
        await loadProjectData(targetId);
      } else {
        setLoading(false);
      }
    })();
  }, []);

  const handleProjectChange = async (newId) => {
    setSelectedProjectId(newId);
    setSearchParams({ project_id: newId });
    await loadProjectData(newId);
  };

  const handleSelectDataset = async (dataset) => {
    setSelectedDataset(dataset);
    setError('');
    setSuccessMsg('');
    try {
      const colRes = await datasetApi.getColumns(dataset.id);
      setColumns(colRes.data || []);
      await loadSplitAndPreview(dataset.id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file || !selectedProjectId) return;
    setUploading(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await datasetApi.upload(selectedProjectId, file);
      setSuccessMsg(`Dataset uploaded successfully as Version ${res.data.version_number}. Structural metadata and content hash computed.`);
      await loadProjectData(selectedProjectId);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload or structural schema detection failed');
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
      setSuccessMsg(`Outer split partition locked successfully (${res.data.development_rows} Dev rows, ${res.data.locked_test_rows} Locked Test rows).`);

      const previewRes = await datasetSplitApi.getDevelopmentPreview(selectedDataset.id, 10);
      setDevPreview(previewRes.data);

      const projRes = await projectApi.get(selectedProjectId);
      setCurrentProject(projRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create outer split partition');
    } finally {
      setCreatingSplit(false);
    }
  };

  const handleRandomizeSeed = () => {
    const randomVal = Math.floor(Math.random() * 1000000) + 1;
    setSplitSeed(randomVal.toString());
  };

  const handleCopyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    try {
      const res = await projectApi.create(newProjectName.trim(), newTargetCol.trim() || null);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewTargetCol('');
      await loadProjects();
      setSelectedProjectId(res.data.id);
      setSearchParams({ project_id: res.data.id });
      await loadProjectData(res.data.id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setCreatingProject(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stage Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-[var(--color-border)] gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 2 of 8</span>
            <span>&bull;</span>
            <span>Structural Ingestion & Outer Split</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Data Ingestion & Outer Split</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Upload raw tabular datasets (CSV, XLSX, JSON) with strict structural schema validation, SHA-256 deduplication, and immutable row_uid outer partitioning.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {selectedProjectId && (
            <Link
              to={`/data-analysis?project_id=${selectedProjectId}`}
              className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition cursor-pointer"
            >
              <span>Next: Data Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Project Selector Bar */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <Layers className="w-5 h-5 text-[var(--color-accent)] shrink-0" />
          <div className="flex-1 sm:flex-initial">
            <label className="block text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider mb-0.5">
              Active Project
            </label>
            <select
              value={selectedProjectId}
              onChange={(e) => handleProjectChange(e.target.value)}
              className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs font-semibold text-text focus:outline-none focus:border-[var(--color-accent)]"
            >
              {projects.length === 0 ? (
                <option value="">No projects available</option>
              ) : (
                projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.project_name} ({p.task_type || 'UNDETERMINED'})
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-xs text-[var(--color-text-muted)] w-full sm:w-auto justify-between sm:justify-end">
          {currentProject && (
            <>
              <span className="hidden md:inline">
                Target: <strong className="text-text font-mono">{currentProject.target_column || 'None'}</strong>
              </span>
              <span>
                Stage: <strong className="text-emerald-500 font-mono font-bold">{currentProject.pipeline_stage}</strong>
              </span>
              <span>
                Versions: <strong className="text-text font-bold">{datasets.length}</strong>
              </span>
            </>
          )}

          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] hover:bg-[var(--color-border)] text-text text-xs font-semibold transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Error & Success Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Architecture Invariant Callout */}
      <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15 text-xs text-indigo-400 flex items-start space-x-3">
        <ShieldCheck className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-text">Pre-Split Leakage Barrier (SRS v9 §2.0, §2.2): </strong>
          Structural metadata detection strictly infers column data types and missing percentages without running descriptive profiling, correlation, or target-aware logic. Row identities are permanently secured via immutable <code className="bg-[var(--color-bg)] px-1 py-0.5 rounded font-mono">row_uid</code> hashes.
        </div>
      </div>

      {/* Main Grid: Upload & Versions on Left, Split & Preview on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Upload Widget & Version History Table */}
        <div className="space-y-6 lg:col-span-1">
          {/* Upload Widget */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-text flex items-center space-x-2">
              <Upload className="w-4 h-4 text-[var(--color-accent)]" />
              <span>Upload Dataset</span>
            </h2>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const file = e.dataTransfer.files?.[0];
                if (file) handleFileUpload(file);
              }}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                dragOver
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5'
                  : 'border-[var(--color-border)] hover:border-[var(--color-text-muted)]'
              }`}
            >
              <FileSpreadsheet className="w-10 h-10 mx-auto text-[var(--color-text-muted)] mb-2" />
              <p className="text-xs font-semibold text-text mb-1">
                Drag & drop CSV, XLSX, or JSON
              </p>
              <p className="text-[11px] text-[var(--color-text-muted)] mb-3">
                Max 100MB &bull; Auto SHA-256 deduplicated
              </p>

              <label className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold shadow-sm transition cursor-pointer">
                <span>{uploading ? 'Processing...' : 'Browse Files'}</span>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls,.json"
                  className="hidden"
                  disabled={uploading || !selectedProjectId}
                  onChange={(e) => handleFileUpload(e.target.files?.[0])}
                />
              </label>
            </div>
          </div>

          {/* Dataset Version Table */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-3">
            <h2 className="text-sm font-bold text-text flex items-center justify-between">
              <span className="flex items-center space-x-2">
                <Database className="w-4 h-4 text-[var(--color-accent)]" />
                <span>Dataset Versions</span>
              </span>
              <span className="text-xs font-normal text-[var(--color-text-muted)]">
                {datasets.length} version{datasets.length === 1 ? '' : 's'}
              </span>
            </h2>

            {datasets.length === 0 ? (
              <p className="text-xs text-[var(--color-text-muted)] italic py-4 text-center">
                No dataset versions uploaded for this project yet.
              </p>
            ) : (
              <div className="space-y-2">
                {datasets.map((ds) => {
                  const isSelected = selectedDataset?.id === ds.id;
                  return (
                    <div
                      key={ds.id}
                      onClick={() => handleSelectDataset(ds)}
                      className={`p-3 rounded-xl border text-xs transition-all cursor-pointer space-y-2 ${
                        isSelected
                          ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)] font-semibold text-text'
                          : 'bg-[var(--color-bg)]/40 border-[var(--color-border)] text-text hover:bg-[var(--color-surface-hover)]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[var(--color-accent)] text-white">
                            v{ds.version_number}
                          </span>
                          <span className="font-bold text-text truncate max-w-[120px]">
                            {ds.file_path ? ds.file_path.split('/').pop().split('\\').pop() : `dataset_v${ds.version_number}`}
                          </span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)]">
                          {ds.stage}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-[var(--color-text-muted)]">
                        <span>{ds.row_count} rows &bull; {ds.column_count} cols</span>
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(ds.created_at).toLocaleDateString()}</span>
                        </span>
                      </div>

                      {ds.content_hash && (
                        <div className="flex items-center justify-between text-[10px] font-mono bg-[var(--color-bg)] px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)]">
                          <span className="truncate max-w-[180px]">SHA: {ds.content_hash}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyHash(ds.content_hash);
                            }}
                            className="text-[var(--color-accent)] hover:underline ml-1 cursor-pointer"
                            title="Copy full SHA-256 hash"
                          >
                            {copiedHash === ds.content_hash ? (
                              <Check className="w-3 h-3 text-emerald-500" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Schema Inspector, Outer Split & Development Preview */}
        <div className="space-y-6 lg:col-span-2">
          {selectedDataset ? (
            <>
              {/* Outer Split Widget */}
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Split className="w-5 h-5 text-[var(--color-accent)]" />
                    <h2 className="text-base font-bold text-text">Outer Split (Development / Locked Test)</h2>
                  </div>
                  {splitSummary ? (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center space-x-1.5">
                      <Lock className="w-3.5 h-3.5" />
                      <span>SPLIT_LOCKED</span>
                    </span>
                  ) : (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center space-x-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>OUTER SPLIT REQUIRED</span>
                    </span>
                  )}
                </div>

                {splitSummary ? (
                  /* Locked Split State Summary */
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)]">
                          Development Partition
                        </span>
                        <div className="text-xl font-extrabold text-emerald-500 mt-1">
                          {splitSummary.development_rows} <span className="text-xs text-[var(--color-text-muted)] font-normal">rows ({100 - splitSummary.locked_test_pct}%)</span>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)]">
                          Locked Test Partition
                        </span>
                        <div className="text-xl font-extrabold text-amber-500 mt-1">
                          {splitSummary.locked_test_rows} <span className="text-xs text-[var(--color-text-muted)] font-normal">rows ({splitSummary.locked_test_pct}%)</span>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)]">
                          Partition Seed
                        </span>
                        <div className="text-xl font-mono font-extrabold text-text mt-1">
                          {splitSummary.split_seed}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] pt-2 border-t border-[var(--color-border)]">
                      <span>Stratified Split: <strong className="text-text">{splitSummary.is_stratified ? 'Yes (Target Distribution Preserved)' : 'Standard Random'}</strong></span>
                      <span className="flex items-center space-x-1 text-emerald-500 font-semibold">
                        <ShieldCheck className="w-4 h-4" />
                        <span>Locked Test Partition Structurally Isolated</span>
                      </span>
                    </div>
                  </div>
                ) : (
                  /* Split Creation Form */
                  <form onSubmit={handleCreateSplit} className="space-y-4 pt-2">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <div className="flex justify-between items-center text-xs font-semibold text-text mb-1">
                          <span>Locked Test Partition Size:</span>
                          <span className="font-mono text-[var(--color-accent)] font-bold">{lockedTestPct}%</span>
                        </div>
                        <input
                          type="range"
                          min="5"
                          max="50"
                          step="5"
                          value={lockedTestPct}
                          onChange={(e) => setLockedTestPct(e.target.value)}
                          className="w-full accent-[var(--color-accent)] cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-0.5">
                          <span>5% (Small Test)</span>
                          <span>20% (Standard)</span>
                          <span>50% (Equal)</span>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-text mb-1">
                          Random Seed (Deterministic Reproducibility)
                        </label>
                        <div className="flex space-x-2">
                          <input
                            type="number"
                            value={splitSeed}
                            onChange={(e) => setSplitSeed(e.target.value)}
                            placeholder="e.g. 42"
                            className="w-full px-3 py-1.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-text focus:outline-none focus:border-[var(--color-accent)] font-mono"
                          />
                          <button
                            type="button"
                            onClick={handleRandomizeSeed}
                            className="px-3 py-1.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs hover:bg-[var(--color-border)] transition flex items-center space-x-1 cursor-pointer"
                            title="Generate Random Seed"
                          >
                            <Shuffle className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={creatingSplit}
                      className="w-full py-2.5 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold shadow-md transition disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-2"
                    >
                      <Lock className="w-4 h-4" />
                      <span>{creatingSplit ? 'Locking Outer Split...' : 'Lock Outer Split (Development / Locked Test)'}</span>
                    </button>
                  </form>
                )}
              </div>

              {/* Structural Schema Inspector (Stage A Metadata) */}
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-text flex items-center space-x-2">
                    <Table className="w-4 h-4 text-[var(--color-accent)]" />
                    <span>Structural Schema (Stage A Metadata)</span>
                  </h2>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {columns.length} columns detected
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--color-border)] text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                        <th className="py-2.5 px-3">Column Name</th>
                        <th className="py-2.5 px-3">Inferred Type</th>
                        <th className="py-2.5 px-3">Missing %</th>
                        <th className="py-2.5 px-3">Unique Values</th>
                        <th className="py-2.5 px-3">Role</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {columns.map((col) => {
                        const isTarget = col.is_target;
                        const missingVal = parseFloat(col.missing_percentage) || 0;
                        return (
                          <tr key={col.id || col.column_name} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                            <td className="py-2.5 px-3 font-semibold text-text font-mono">
                              {col.column_name}
                            </td>
                            <td className="py-2.5 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                                col.data_type === 'NUMERIC'
                                  ? 'bg-blue-500/10 text-blue-500 border border-blue-500/20'
                                  : col.data_type === 'CATEGORICAL'
                                  ? 'bg-purple-500/10 text-purple-500 border border-purple-500/20'
                                  : col.data_type === 'DATETIME'
                                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                                  : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                              }`}>
                                {col.data_type}
                              </span>
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex items-center space-x-2">
                                <span className={missingVal > 0 ? 'text-amber-500 font-semibold' : 'text-text'}>
                                  {missingVal.toFixed(1)}%
                                </span>
                                {missingVal > 0 && (
                                  <div className="w-12 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                                    <div
                                      className="h-full bg-amber-500"
                                      style={{ width: `${Math.min(missingVal, 100)}%` }}
                                    />
                                  </div>
                                )}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-text font-mono">
                              {col.unique_count ?? 'N/A'}
                            </td>
                            <td className="py-2.5 px-3">
                              {isTarget ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-500/10 border border-rose-500/30 text-rose-500">
                                  TARGET
                                </span>
                              ) : (
                                <span className="text-[var(--color-text-muted)] text-[10px]">Feature</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Development Partition Preview (Day 2/3 Endpoint) */}
              {devPreview && devPreview.preview_rows && devPreview.preview_rows.length > 0 && (
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-text flex items-center space-x-2">
                      <Eye className="w-4 h-4 text-emerald-500" />
                      <span>Development Partition Preview (First 10 Rows)</span>
                    </h2>
                    <span className="text-xs text-[var(--color-text-muted)] font-mono">
                      {devPreview.total_development_rows} Development Rows Total
                    </span>
                  </div>

                  <div className="overflow-x-auto border border-[var(--color-border)] rounded-xl">
                    <table className="w-full text-left text-xs border-collapse font-mono">
                      <thead>
                        <tr className="bg-[var(--color-bg)] border-b border-[var(--color-border)] text-[10px] font-bold text-[var(--color-text-muted)] uppercase">
                          {devPreview.columns.map((c) => (
                            <th key={c} className="py-2 px-3 whitespace-nowrap">
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--color-border)]">
                        {devPreview.preview_rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-[var(--color-surface-hover)]">
                            {devPreview.columns.map((c) => (
                              <td key={c} className="py-1.5 px-3 whitespace-nowrap text-text text-[11px]">
                                {row[c] === null || row[c] === undefined ? (
                                  <span className="text-slate-500 italic">null</span>
                                ) : (
                                  String(row[c])
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
            </>
          ) : (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center space-y-3">
              <Database className="w-12 h-12 text-[var(--color-text-muted)] mx-auto" />
              <h3 className="text-base font-bold text-text">No Dataset Selected</h3>
              <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto">
                Upload a raw tabular file on the left or choose an existing dataset version to inspect its schema and configure the outer split.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-text">Create New Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Customer Churn Prediction"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-text focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  Target Column (Optional)
                </label>
                <input
                  type="text"
                  value={newTargetCol}
                  onChange={(e) => setNewTargetCol(e.target.value)}
                  placeholder="e.g. churn"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-text focus:outline-none focus:border-[var(--color-accent)] font-mono"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl border border-[var(--color-border)] text-text text-xs hover:bg-[var(--color-surface-hover)] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingProject || !newProjectName.trim()}
                  className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold transition disabled:opacity-50 cursor-pointer"
                >
                  {creatingProject ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataStage;
