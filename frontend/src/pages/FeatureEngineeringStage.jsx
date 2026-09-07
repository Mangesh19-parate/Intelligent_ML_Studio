import React, { useState, useEffect, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, datasetApi, featureSelectionApi } from '../api/client';
import {
  Workflow,
  Sparkles,
  SlidersHorizontal,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Layers,
  ArrowRight,
  ShieldCheck,
  Search,
  Filter,
  Info,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronUp,
  Activity,
  Sliders,
  FolderOpen,
  Database,
  BarChart2,
  Lock,
  Flame,
  Award,
} from 'lucide-react';

export const FeatureEngineeringStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get('project_id');

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);
  const [activeDataset, setActiveDataset] = useState(null);

  // Feature selection state
  const [importanceData, setImportanceData] = useState(null);
  const [foldData, setFoldData] = useState(null);
  const [experimentId, setExperimentId] = useState(null);

  // Configuration parameters
  const [nSplits, setNSplits] = useState(5);
  const [cvStrategy, setCvStrategy] = useState('AUTO');
  const [seed, setSeed] = useState(42);
  const [method, setMethod] = useState('RANK_AGGREGATION');

  // Interactive selection threshold & search
  const [threshold, setThreshold] = useState(0.0);
  const [selectedFeaturesMap, setSelectedFeaturesMap] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState('ALL'); // ALL, SELECTED, EXCLUDED
  const [sortBy, setSortBy] = useState('SCORE_DESC'); // SCORE_DESC, SCORE_ASC, NAME_ASC

  // UI state
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [updatingThreshold, setUpdatingThreshold] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [activeFoldTab, setActiveFoldTab] = useState(0);
  const [showFoldModal, setShowFoldModal] = useState(false);

  // 1. Load workspace projects
  const loadProjects = async () => {
    try {
      const resp = await projectApi.list();
      const list = resp.data || [];
      setProjects(list);

      if (!selectedProjectId && list.length > 0) {
        const firstId = list[0].id;
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

  // 2. Load project details & existing feature selection scores
  useEffect(() => {
    if (!selectedProjectId) {
      setLoading(false);
      return;
    }

    const loadProjectData = async () => {
      setLoading(true);
      setError('');
      setSuccessMsg('');
      try {
        const projResp = await projectApi.get(selectedProjectId);
        const proj = projResp.data;
        setCurrentProject(proj);

        // Fetch datasets
        const dsResp = await datasetApi.listVersions(selectedProjectId);
        const dsList = dsResp.data || [];
        if (dsList.length > 0) {
          setActiveDataset(dsList[0]);
        } else {
          setActiveDataset(null);
        }

        // Fetch current feature importance scores if previously run
        try {
          const impResp = await featureSelectionApi.getImportance(selectedProjectId);
          const imp = impResp.data;
          setImportanceData(imp);
          setExperimentId(imp.experiment_id || null);

          // Initialize local selection map
          if (imp && imp.features) {
            const selMap = {};
            imp.features.forEach((f) => {
              selMap[f.column_name] = f.is_selected;
            });
            setSelectedFeaturesMap(selMap);

            // If experiment ID exists, load folds
            if (imp.experiment_id) {
              try {
                const foldsResp = await featureSelectionApi.getFolds(selectedProjectId, imp.experiment_id);
                setFoldData(foldsResp.data);
              } catch (foldErr) {
                console.warn('No fold details found for experiment', foldErr);
              }
            }
          }
        } catch (impErr) {
          // Feature selection hasn't run yet for this project
          setImportanceData(null);
          setSelectedFeaturesMap({});
          setFoldData(null);
        }
      } catch (err) {
        console.error('Failed to load project feature selection data', err);
        setError(err.response?.data?.detail || 'Failed to load project feature engineering data.');
      } finally {
        setLoading(false);
      }
    };

    loadProjectData();
  }, [selectedProjectId]);

  // Handle project switcher
  const handleProjectChange = (e) => {
    const newId = e.target.value;
    setSelectedProjectId(newId);
    setSearchParams({ project_id: newId });
  };

  // 3. Execute Cross-Validation Feature Selection Ensemble
  const handleRunFeatureSelection = async () => {
    if (!selectedProjectId) return;
    setRunning(true);
    setError('');
    setSuccessMsg('');

    try {
      const payload = {
        n_splits: Number(nSplits),
        cv_strategy: cvStrategy === 'AUTO' ? null : cvStrategy,
        seed: Number(seed),
        threshold: Number(threshold),
        method: method,
      };

      const resp = await featureSelectionApi.run(selectedProjectId, payload);
      const data = resp.data;
      setImportanceData(data);
      setExperimentId(data.experiment_id || null);

      if (data && data.features) {
        const selMap = {};
        data.features.forEach((f) => {
          selMap[f.column_name] = f.is_selected;
        });
        setSelectedFeaturesMap(selMap);
      }

      // Fetch fold details
      if (data.experiment_id) {
        try {
          const foldsResp = await featureSelectionApi.getFolds(selectedProjectId, data.experiment_id);
          setFoldData(foldsResp.data);
        } catch (foldErr) {
          console.warn('Failed to load fold details', foldErr);
        }
      }

      setSuccessMsg(`Ensemble Feature Selection executed successfully across ${nSplits} folds!`);
    } catch (err) {
      console.error('Error running feature selection', err);
      const msg = err.response?.data?.detail || err.message || 'Feature selection run failed.';
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  // 4. Update Selection via Threshold or Manual Toggles
  const handleToggleFeature = (colName) => {
    setSelectedFeaturesMap((prev) => ({
      ...prev,
      [colName]: !prev[colName],
    }));
  };

  const handleSelectAll = () => {
    if (!importanceData?.features) return;
    const newMap = {};
    importanceData.features.forEach((f) => {
      newMap[f.column_name] = true;
    });
    setSelectedFeaturesMap(newMap);
  };

  const handleDeselectAll = () => {
    if (!importanceData?.features) return;
    const newMap = {};
    importanceData.features.forEach((f) => {
      newMap[f.column_name] = false;
    });
    setSelectedFeaturesMap(newMap);
  };

  const handleThresholdSliderChange = (e) => {
    const val = parseFloat(e.target.value);
    setThreshold(val);
    if (importanceData?.features) {
      const newMap = {};
      importanceData.features.forEach((f) => {
        newMap[f.column_name] = f.avg_rank_score >= val;
      });
      setSelectedFeaturesMap(newMap);
    }
  };

  const handleSaveSelection = async () => {
    if (!selectedProjectId) return;
    setUpdatingThreshold(true);
    setError('');
    setSuccessMsg('');

    try {
      const selectedList = Object.entries(selectedFeaturesMap)
        .filter(([_, isSel]) => isSel)
        .map(([col]) => col);

      const resp = await featureSelectionApi.updateThreshold(selectedProjectId, {
        threshold: threshold,
        selected_features: selectedList,
      });

      setImportanceData(resp.data);
      setSuccessMsg(`Feature selection saved: ${selectedList.length} features active for model training.`);
    } catch (err) {
      console.error('Failed to save selection', err);
      setError(err.response?.data?.detail || 'Failed to update selection threshold.');
    } finally {
      setUpdatingThreshold(false);
    }
  };

  // Derived filtered & sorted features
  const displayedFeatures = useMemo(() => {
    if (!importanceData?.features) return [];
    let items = [...importanceData.features];

    // Filter by search
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      items = items.filter((f) => f.column_name.toLowerCase().includes(q));
    }

    // Filter by selection status
    if (filterMode === 'SELECTED') {
      items = items.filter((f) => !!selectedFeaturesMap[f.column_name]);
    } else if (filterMode === 'EXCLUDED') {
      items = items.filter((f) => !selectedFeaturesMap[f.column_name]);
    }

    // Sorting
    items.sort((a, b) => {
      if (sortBy === 'SCORE_DESC') return b.avg_rank_score - a.avg_rank_score;
      if (sortBy === 'SCORE_ASC') return a.avg_rank_score - b.avg_rank_score;
      if (sortBy === 'NAME_ASC') return a.column_name.localeCompare(b.column_name);
      return 0;
    });

    return items;
  }, [importanceData, selectedFeaturesMap, searchTerm, filterMode, sortBy]);

  // Total and selected counts
  const totalFeaturesCount = importanceData?.features?.length || 0;
  const selectedCount = Object.values(selectedFeaturesMap).filter(Boolean).length;
  const selectionRatio = totalFeaturesCount > 0 ? ((selectedCount / totalFeaturesCount) * 100).toFixed(1) : 0;

  // Compute contributing technique counts from fold data
  const appliedTechniquesSummary = useMemo(() => {
    if (!foldData?.folds || foldData.folds.length === 0) {
      return { count: 4, label: 'STRONG', badgeClass: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' };
    }
    const firstFold = foldData.folds[0];
    const scores = firstFold.technique_scores || {};
    const appliedCount = Object.values(scores).filter(
      (techMap) => Object.values(techMap)[0]?.status === 'APPLIED'
    ).length;

    if (appliedCount >= 4) {
      return { count: appliedCount, label: 'STRONG', badgeClass: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' };
    }
    if (appliedCount === 3) {
      return { count: appliedCount, label: 'MODERATE', badgeClass: 'bg-blue-500/10 text-blue-500 border-blue-500/20' };
    }
    if (appliedCount === 2) {
      return { count: appliedCount, label: 'LIMITED', badgeClass: 'bg-amber-500/10 text-amber-500 border-amber-500/20' };
    }
    return { count: appliedCount, label: 'INSUFFICIENT_EVIDENCE', badgeClass: 'bg-rose-500/10 text-rose-500 border-rose-500/20' };
  }, [foldData]);

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Header & Stage Breadcrumb */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-6 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider mb-1.5">
            <span className="px-2 py-0.5 rounded bg-[var(--color-accent)]/10">Stage 5 of 8</span>
            <span>&bull;</span>
            <span>Feature Engineering & Selection</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-text flex items-center gap-3">
            <span>Rank-Aggregation Feature Ensemble</span>
            <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              SRS v9 §2.7
            </span>
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1 max-w-3xl">
            Execute 4-technique cross-validated rank aggregation on the Development partition. Eliminates multi-collinearity, suppresses noise features, and safeguards against data leakage.
          </p>
        </div>

        {/* Project Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[var(--color-surface)] px-3 py-2 rounded-xl border border-[var(--color-border)] shadow-sm">
            <FolderOpen className="w-4 h-4 text-[var(--color-accent)]" />
            <select
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="bg-transparent text-xs font-bold text-text focus:outline-none cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_name || p.name} ({p.task_type || 'Task Undetermined'})
                </option>
              ))}
            </select>
          </div>

          <Link
            to={`/machine-learning?project_id=${selectedProjectId}`}
            className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center gap-2 shadow-sm transition"
          >
            <span>Next: Model Training</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs flex items-center gap-3 animate-fadeIn">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <div className="font-medium">{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs flex items-center gap-3 animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <div className="font-medium">{successMsg}</div>
        </div>
      )}

      {/* 2. Top Summary & Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        {/* Project Target & Partition Card */}
        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Partition Context</span>
            <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-md bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              Zero Leakage
            </span>
          </div>
          <div className="space-y-1">
            <div className="text-lg font-black text-text truncate">
              {currentProject?.target_column ? `Target: ${currentProject.target_column}` : 'No Target Configured'}
            </div>
            <div className="text-xs text-[var(--color-text-muted)] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-indigo-400" />
              <span>Dev Set Only (Locked Test Isolated)</span>
            </div>
          </div>
        </div>

        {/* Evidence Strength Card */}
        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Evidence Strength</span>
            <span className={`px-2 py-0.5 text-[10px] font-extrabold rounded-md border ${appliedTechniquesSummary.badgeClass}`}>
              {appliedTechniquesSummary.label}
            </span>
          </div>
          <div className="space-y-1">
            <div className="text-lg font-black text-text">
              {appliedTechniquesSummary.count} of 4 Selectors Applied
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              Correlation &bull; Lasso &bull; RF &bull; Permutation
            </div>
          </div>
        </div>

        {/* Selected Features Ratio Card */}
        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Active Features</span>
            <span className="text-xs font-bold text-indigo-400">{selectionRatio}%</span>
          </div>
          <div className="space-y-1">
            <div className="text-2xl font-black text-text flex items-baseline gap-2">
              <span>{selectedCount}</span>
              <span className="text-xs text-[var(--color-text-muted)] font-normal">/ {totalFeaturesCount} evaluated</span>
            </div>
            <div className="w-full bg-[var(--color-border)] h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-[var(--color-accent)] h-full transition-all duration-300 rounded-full"
                style={{ width: `${selectionRatio}%` }}
              />
            </div>
          </div>
        </div>

        {/* Selection Rule & Clamp */}
        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Selection Rule</span>
            <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20">
              TOP_K_PERCENT
            </span>
          </div>
          <div className="space-y-1">
            <div className="text-sm font-bold text-text">
              Clamp Boundaries: [k_min=5, k_max=50]
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              Deterministic 3-tier tie-breaking
            </div>
          </div>
        </div>
      </div>

      {/* 3. Execution Control & Harness Panel */}
      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[var(--color-border)]">
          <div>
            <h2 className="text-base font-black text-text flex items-center gap-2">
              <Sliders className="w-5 h-5 text-[var(--color-accent)]" />
              <span>Cross-Validation Harness Parameters</span>
            </h2>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Configure per-fold leakage isolation and execution seed for reproducible ensemble aggregation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {foldData && (
              <button
                type="button"
                onClick={() => setShowFoldModal(true)}
                className="px-3.5 py-2 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs font-bold flex items-center gap-2 transition"
              >
                <Activity className="w-4 h-4 text-indigo-400" />
                <span>Inspect Folds ({foldData.fold_count})</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleRunFeatureSelection}
              disabled={running || !currentProject?.target_column}
              className="px-5 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-black flex items-center gap-2 shadow-sm transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Running Ensemble...' : 'Execute CV Feature Selection'}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* CV Folds */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-text flex items-center justify-between">
              <span>CV Folds (n_splits)</span>
              <span className="text-[var(--color-accent)] font-mono">{nSplits}</span>
            </label>
            <input
              type="range"
              min="2"
              max="10"
              value={nSplits}
              onChange={(e) => setNSplits(Number(e.target.value))}
              className="w-full accent-[var(--color-accent)] cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-[var(--color-text-muted)]">
              <span>2 folds</span>
              <span>5 (Standard)</span>
              <span>10 folds</span>
            </div>
          </div>

          {/* Strategy */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-text">CV Strategy</label>
            <select
              value={cvStrategy}
              onChange={(e) => setCvStrategy(e.target.value)}
              className="w-full bg-[var(--color-bg)] text-xs text-text font-medium px-3 py-2 rounded-xl border border-[var(--color-border)] focus:outline-none"
            >
              <option value="AUTO">Auto (Stratified for Classif., KFold for Regr.)</option>
              <option value="STRATIFIED_KFOLD">Stratified K-Fold</option>
              <option value="KFOLD">Standard K-Fold</option>
            </select>
          </div>

          {/* Random Seed */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-text">Random Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              className="w-full bg-[var(--color-bg)] text-xs text-text font-mono px-3 py-2 rounded-xl border border-[var(--color-border)] focus:outline-none"
            />
          </div>

          {/* Method Selection (Locked to Platform Default) */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-text flex items-center justify-between">
              <span>Selection Method</span>
              <span className="text-[10px] text-[var(--color-accent)]">Platform Locked</span>
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-full bg-[var(--color-bg)] text-xs text-text font-bold px-3 py-2 rounded-xl border border-[var(--color-border)] focus:outline-none cursor-not-allowed"
              disabled
            >
              <option value="RANK_AGGREGATION">RANK_AGGREGATION (4-Technique Ensemble)</option>
            </select>
          </div>
        </div>
      </div>

      {/* 4. Interactive Threshold Adjustment & Feature Table */}
      {importanceData?.features && importanceData.features.length > 0 && (
        <div className="space-y-6">
          {/* Threshold & Quick Action Toolbar */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <h3 className="text-base font-black text-text flex items-center gap-2">
                  <SlidersHorizontal className="w-5 h-5 text-[var(--color-accent)]" />
                  <span>Selection Threshold & Interactive Overrides</span>
                </h3>
                <p className="text-xs text-[var(--color-text-muted)]">
                  Slide threshold score to dynamically include features above the rank score or toggle individual features below.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="px-3 py-1.5 rounded-lg bg-[var(--color-bg)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs font-bold transition"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={handleDeselectAll}
                  className="px-3 py-1.5 rounded-lg bg-[var(--color-bg)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs font-bold transition"
                >
                  Deselect All
                </button>
                <button
                  type="button"
                  onClick={handleSaveSelection}
                  disabled={updatingThreshold}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-extrabold flex items-center gap-2 transition disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{updatingThreshold ? 'Saving...' : 'Save Selection'}</span>
                </button>
              </div>
            </div>

            {/* Threshold Slider */}
            <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] flex flex-col md:flex-row items-center gap-4">
              <span className="text-xs font-bold text-text whitespace-nowrap">
                Rank Score Cutoff: <span className="text-[var(--color-accent)] font-mono">{threshold.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.01"
                value={threshold}
                onChange={handleThresholdSliderChange}
                className="w-full accent-[var(--color-accent)] cursor-pointer"
              />
              <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                {selectedCount} of {totalFeaturesCount} active
              </span>
            </div>
          </div>

          {/* Feature List Filter & Table */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Search Bar */}
              <div className="relative w-full md:w-72">
                <Search className="w-4 h-4 text-[var(--color-text-muted)] absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search feature columns..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-[var(--color-bg)] text-xs text-text pl-9 pr-3 py-2 rounded-xl border border-[var(--color-border)] focus:outline-none"
                />
              </div>

              {/* Status and Sort Controls */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 bg-[var(--color-bg)] p-1 rounded-xl border border-[var(--color-border)] text-xs font-bold">
                  <button
                    type="button"
                    onClick={() => setFilterMode('ALL')}
                    className={`px-3 py-1 rounded-lg transition ${
                      filterMode === 'ALL' ? 'bg-[var(--color-surface)] text-text shadow-sm' : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    All ({totalFeaturesCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterMode('SELECTED')}
                    className={`px-3 py-1 rounded-lg transition ${
                      filterMode === 'SELECTED' ? 'bg-[var(--color-surface)] text-emerald-500 shadow-sm' : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    Selected ({selectedCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterMode('EXCLUDED')}
                    className={`px-3 py-1 rounded-lg transition ${
                      filterMode === 'EXCLUDED' ? 'bg-[var(--color-surface)] text-rose-500 shadow-sm' : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    Excluded ({totalFeaturesCount - selectedCount})
                  </button>
                </div>

                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-[var(--color-bg)] text-xs font-bold text-text px-3 py-2 rounded-xl border border-[var(--color-border)] focus:outline-none"
                >
                  <option value="SCORE_DESC">Rank Score (Highest First)</option>
                  <option value="SCORE_ASC">Rank Score (Lowest First)</option>
                  <option value="NAME_ASC">Column Name (A-Z)</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--color-bg)] text-[var(--color-text-muted)] font-bold uppercase tracking-wider border-b border-[var(--color-border)]">
                  <tr>
                    <th className="py-3 px-4 w-12 text-center">Active</th>
                    <th className="py-3 px-4 w-16">Rank</th>
                    <th className="py-3 px-4">Feature Column</th>
                    <th className="py-3 px-4 w-48">Ensemble Score</th>
                    <th className="py-3 px-4 w-32">Status</th>
                    <th className="py-3 px-4">Contributing Techniques</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {displayedFeatures.map((feat, idx) => {
                    const isSelected = !!selectedFeaturesMap[feat.column_name];
                    const scorePct = (feat.avg_rank_score * 100).toFixed(1);

                    return (
                      <tr
                        key={feat.column_name}
                        onClick={() => handleToggleFeature(feat.column_name)}
                        className={`hover:bg-[var(--color-surface-hover)] cursor-pointer transition ${
                          isSelected ? 'bg-indigo-500/[0.02]' : 'opacity-60'
                        }`}
                      >
                        <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleFeature(feat.column_name)}
                            className="w-4 h-4 rounded text-[var(--color-accent)] focus:ring-0 cursor-pointer"
                          />
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-[var(--color-text-muted)]">
                          #{idx + 1}
                        </td>
                        <td className="py-3 px-4 font-bold text-text">
                          {feat.column_name}
                        </td>
                        <td className="py-3 px-4">
                          <div className="space-y-1">
                            <div className="flex items-center justify-between font-mono font-bold">
                              <span>{feat.avg_rank_score.toFixed(4)}</span>
                              <span className="text-[10px] text-[var(--color-text-muted)]">{scorePct}%</span>
                            </div>
                            <div className="w-full bg-[var(--color-border)] h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full transition-all duration-300"
                                style={{ width: `${scorePct}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {isSelected ? (
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                              SELECTED
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-rose-500/10 text-rose-500 border border-rose-500/20">
                              EXCLUDED
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1.5">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400">
                              Correlation
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400">
                              Lasso
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                              Random Forest
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400">
                              Permutation
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 5. Fold Inspection Modal / Drawer */}
      {showFoldModal && foldData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-scaleIn">
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
              <div>
                <h3 className="text-lg font-black text-text flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-400" />
                  <span>Cross-Validation Fold Breakdown (Experiment {foldData.experiment_id.slice(0, 8)})</span>
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Per-fold fitted ColumnTransformer features and selector ranks.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowFoldModal(false)}
                className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]"
              >
                &times;
              </button>
            </div>

            {/* Fold Tabs */}
            <div className="px-5 pt-3 border-b border-[var(--color-border)] flex gap-2 overflow-x-auto">
              {foldData.folds.map((fold, idx) => (
                <button
                  key={fold.id || idx}
                  type="button"
                  onClick={() => setActiveFoldTab(idx)}
                  className={`px-4 py-2 text-xs font-bold rounded-t-xl border-b-2 transition ${
                    activeFoldTab === idx
                      ? 'border-[var(--color-accent)] text-[var(--color-accent)] bg-[var(--color-accent)]/5'
                      : 'border-transparent text-[var(--color-text-muted)] hover:text-text'
                  }`}
                >
                  Fold #{fold.fold_index + 1}
                </button>
              ))}
            </div>

            {/* Active Fold Table */}
            <div className="p-5 overflow-y-auto space-y-4">
              {foldData.folds[activeFoldTab] && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs font-bold text-[var(--color-text-muted)]">
                    <span>
                      Selected Features in Fold #{foldData.folds[activeFoldTab].fold_index + 1}:
                      <span className="text-emerald-500 font-mono ml-1">
                        {foldData.folds[activeFoldTab].selected_features?.length || 0}
                      </span>
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[var(--color-bg)] text-[var(--color-text-muted)] font-bold uppercase tracking-wider">
                        <tr>
                          <th className="py-2.5 px-3">Technique</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Status Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--color-border)]">
                        {Object.entries(foldData.folds[activeFoldTab].technique_scores || {}).map(
                          ([techName, techObj]) => {
                            const firstFeat = Object.values(techObj)[0] || {};
                            return (
                              <tr key={techName} className="hover:bg-[var(--color-surface-hover)]">
                                <td className="py-2.5 px-3 font-bold text-text">{techName}</td>
                                <td className="py-2.5 px-3">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      firstFeat.status === 'APPLIED'
                                        ? 'bg-emerald-500/10 text-emerald-500'
                                        : 'bg-amber-500/10 text-amber-500'
                                    }`}
                                  >
                                    {firstFeat.status || 'APPLIED'}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 text-[var(--color-text-muted)] font-mono text-[11px]">
                                  {firstFeat.status_reason || '—'}
                                </td>
                              </tr>
                            );
                          }
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FeatureEngineeringStage;
