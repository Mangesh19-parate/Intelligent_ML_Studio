import React, { useState, useEffect, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, datasetApi, featureSelectionApi } from '../api/client';
import { useProject } from '../context/ProjectContext';
import {
  StabilityRanker,
  FeatureConfigPanel,
  FeatureImportanceTable,
  FoldInspectionModal,
  FeatureScoreItem,
} from '../components/features';
import { EmptyState } from '../components/feedback/EmptyState';
import { ErrorState } from '../components/feedback/ErrorState';
import { Skeleton } from '../components/feedback/Skeleton';
import {
  Sparkles,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  Sliders,
  FolderOpen,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '../components/ui/Button';

export const FeatureEngineeringStage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentProject, currentProjectId, projects, selectProject } = useProject();

  const urlProjectId = searchParams.get('project_id');
  const activeProjectId = urlProjectId || currentProjectId;

  const [activeDataset, setActiveDataset] = useState<any>(null);

  // Feature selection state
  const [importanceData, setImportanceData] = useState<any>(null);
  const [foldData, setFoldData] = useState<any>(null);
  const [experimentId, setExperimentId] = useState<string | null>(null);

  // Configuration parameters
  const [nSplits, setNSplits] = useState<number>(5);
  const [cvStrategy, setCvStrategy] = useState<string>('AUTO');
  const [seed, setSeed] = useState<number>(42);
  const [method, setMethod] = useState<string>('RANK_AGGREGATION');

  // Interactive selection threshold & search
  const [threshold, setThreshold] = useState<number>(0.0);
  const [selectedFeaturesMap, setSelectedFeaturesMap] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterMode, setFilterMode] = useState<'ALL' | 'SELECTED' | 'EXCLUDED'>('ALL');
  const [sortBy, setSortBy] = useState<'SCORE_DESC' | 'SCORE_ASC' | 'NAME_ASC'>('SCORE_DESC');

  // UI state
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [updatingThreshold, setUpdatingThreshold] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [showFoldModal, setShowFoldModal] = useState<boolean>(false);

  // Sync URL project_id with ProjectContext
  useEffect(() => {
    if (urlProjectId && urlProjectId !== currentProjectId) {
      selectProject(urlProjectId);
    } else if (!currentProjectId && projects.length > 0) {
      const firstId = String(projects[0].id);
      selectProject(firstId);
      setSearchParams({ project_id: firstId }, { replace: true });
    }
  }, [urlProjectId, currentProjectId, projects, selectProject, setSearchParams]);

  // Load project datasets and feature selection scores
  useEffect(() => {
    if (!activeProjectId) {
      setLoading(false);
      return;
    }

    const loadProjectData = async () => {
      setLoading(true);
      setError('');
      setSuccessMsg('');
      try {
        // Fetch datasets
        const dsResp = await datasetApi.listVersions(activeProjectId);
        const dsList = dsResp.data || [];
        if (dsList.length > 0) {
          setActiveDataset(dsList[0]);
        } else {
          setActiveDataset(null);
        }

        // Fetch current feature importance scores if previously run
        try {
          const impResp = await featureSelectionApi.getImportance(activeProjectId);
          const imp = impResp.data;
          setImportanceData(imp);
          setExperimentId(imp.experiment_id || null);

          if (imp && imp.features) {
            const selMap: Record<string, boolean> = {};
            imp.features.forEach((f: any) => {
              selMap[f.column_name] = f.is_selected;
            });
            setSelectedFeaturesMap(selMap);

            if (imp.experiment_id) {
              try {
                const foldsResp = await featureSelectionApi.getFolds(activeProjectId, imp.experiment_id);
                setFoldData(foldsResp.data);
              } catch (foldErr) {
                console.warn('No fold details found for experiment', foldErr);
              }
            }
          }
        } catch (impErr) {
          // Feature selection hasn't run yet
          setImportanceData(null);
          setSelectedFeaturesMap({});
          setFoldData(null);
        }
      } catch (err: any) {
        console.error('Failed to load project feature selection data', err);
        setError(err.response?.data?.detail || 'Failed to load project feature engineering data.');
      } finally {
        setLoading(false);
      }
    };

    loadProjectData();
  }, [activeProjectId]);

  const handleSelectProject = (projId: string) => {
    selectProject(projId);
    setSearchParams({ project_id: projId });
  };

  // Execute Cross-Validation Feature Selection Ensemble
  const handleRunFeatureSelection = async () => {
    if (!activeProjectId) return;
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

      const resp = await featureSelectionApi.run(activeProjectId, payload);
      const data = resp.data;
      setImportanceData(data);
      setExperimentId(data.experiment_id || null);

      if (data && data.features) {
        const selMap: Record<string, boolean> = {};
        data.features.forEach((f: any) => {
          selMap[f.column_name] = f.is_selected;
        });
        setSelectedFeaturesMap(selMap);
      }

      if (data.experiment_id) {
        try {
          const foldsResp = await featureSelectionApi.getFolds(activeProjectId, data.experiment_id);
          setFoldData(foldsResp.data);
        } catch (foldErr) {
          console.warn('Failed to load fold details', foldErr);
        }
      }

      setSuccessMsg(`Ensemble Feature Selection executed successfully across ${nSplits} folds!`);
    } catch (err: any) {
      console.error('Error running feature selection', err);
      const msg = err.response?.data?.detail || err.message || 'Feature selection run failed.';
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  // Toggle individual feature
  const handleToggleFeature = (colName: string) => {
    setSelectedFeaturesMap((prev) => ({
      ...prev,
      [colName]: !prev[colName],
    }));
  };

  const handleSelectAll = () => {
    if (!importanceData?.features) return;
    const newMap: Record<string, boolean> = {};
    importanceData.features.forEach((f: any) => {
      newMap[f.column_name] = true;
    });
    setSelectedFeaturesMap(newMap);
  };

  const handleDeselectAll = () => {
    if (!importanceData?.features) return;
    const newMap: Record<string, boolean> = {};
    importanceData.features.forEach((f: any) => {
      newMap[f.column_name] = false;
    });
    setSelectedFeaturesMap(newMap);
  };

  const handleThresholdSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setThreshold(val);
    if (importanceData?.features) {
      const newMap: Record<string, boolean> = {};
      importanceData.features.forEach((f: any) => {
        newMap[f.column_name] = f.avg_rank_score >= val;
      });
      setSelectedFeaturesMap(newMap);
    }
  };

  const handleSaveSelection = async () => {
    if (!activeProjectId) return;
    setUpdatingThreshold(true);
    setError('');
    setSuccessMsg('');

    try {
      const selectedList = Object.entries(selectedFeaturesMap)
        .filter(([_, isSel]) => isSel)
        .map(([col]) => col);

      const resp = await featureSelectionApi.updateThreshold(activeProjectId, {
        threshold: threshold,
        selected_features: selectedList,
      });

      setImportanceData(resp.data);
      setSuccessMsg(`Feature selection saved: ${selectedList.length} features active for model training.`);
    } catch (err: any) {
      console.error('Failed to save selection', err);
      setError(err.response?.data?.detail || 'Failed to update selection threshold.');
    } finally {
      setUpdatingThreshold(false);
    }
  };

  // Derived filtered & sorted features
  const displayedFeatures: FeatureScoreItem[] = useMemo(() => {
    if (!importanceData?.features) return [];
    let items = [...importanceData.features];

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      items = items.filter((f: any) => f.column_name.toLowerCase().includes(q));
    }

    if (filterMode === 'SELECTED') {
      items = items.filter((f: any) => !!selectedFeaturesMap[f.column_name]);
    } else if (filterMode === 'EXCLUDED') {
      items = items.filter((f: any) => !selectedFeaturesMap[f.column_name]);
    }

    items.sort((a: any, b: any) => {
      if (sortBy === 'SCORE_DESC') return b.avg_rank_score - a.avg_rank_score;
      if (sortBy === 'SCORE_ASC') return a.avg_rank_score - b.avg_rank_score;
      if (sortBy === 'NAME_ASC') return a.column_name.localeCompare(b.column_name);
      return 0;
    });

    return items;
  }, [importanceData, searchTerm, filterMode, sortBy, selectedFeaturesMap]);

  const selectedCount = Object.values(selectedFeaturesMap).filter(Boolean).length;
  const totalCount = importanceData?.features?.length || 0;

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto p-6">
        <Skeleton variant="rectangular" height="120px" className="rounded-2xl" />
        <Skeleton variant="rectangular" height="300px" className="rounded-2xl" />
      </div>
    );
  }

  if (!activeProjectId) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <EmptyState
          title="No Project Selected"
          description="Please select or create a project to inspect and engineer tabular feature spaces."
        />
      </div>
    );
  }

  const hasMissingPrerequisites = !currentProject?.target_column || !currentProject?.task_type || currentProject?.task_type === 'UNDETERMINED';

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Header Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
              <Sparkles className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-black text-[var(--color-text)]">
              Feature Selection & Ranking
            </h1>
          </div>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Leakage-controlled ensemble feature ranking evaluated strictly inside cross-validation splits.
          </p>
        </div>

        <div className="flex items-center space-x-3 flex-wrap gap-2">
          {/* Project Selector Dropdown */}
          {projects.length > 0 && (
            <div className="flex items-center gap-2 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 shadow-xs">
              <FolderOpen className="w-4 h-4 text-[var(--color-accent)]" />
              <select
                id="project-select"
                value={activeProjectId || ''}
                onChange={(e) => handleSelectProject(e.target.value)}
                className="bg-transparent text-xs font-semibold text-[var(--color-text)] border-none focus:outline-none cursor-pointer pr-2"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-[var(--color-surface)] text-[var(--color-text)]">
                    {p.project_name || (p as any).name || p.id}
                  </option>
                ))}
              </select>
            </div>
          )}

          {activeProjectId && (
            <Link
              to={`/ml?project_id=${activeProjectId}`}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-full bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] text-xs font-bold transition-all border border-[var(--color-accent-border)]"
            >
              <span>Proceed to Model Training</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Target Column / Task Type Warning Banner if not yet set */}
      {hasMissingPrerequisites && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <span className="font-bold">Project Target Column or Task Type Not Configured: </span>
              <span>Feature selection requires a target column and valid task type (Classification or Regression).</span>
            </div>
          </div>
          <Link
            to={`/data-analysis?project_id=${activeProjectId}`}
            className="px-3.5 py-1.5 rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-bold text-xs whitespace-nowrap transition-colors inline-flex items-center gap-1.5 border border-amber-500/30 self-start sm:self-auto"
          >
            <span>Run Data Profiling & Auto-Detect</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {error && (
        <ErrorState
          title="Feature Selection Error"
          message={error}
          onRetry={() => setError('')}
        />
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Stability Metrics Banner (if run) */}
      {importanceData && importanceData.features && importanceData.features.length > 0 && (
        <StabilityRanker
          totalFeatures={totalCount}
          selectedFeaturesCount={selectedCount}
          selectionMethod={method}
          foldCount={nSplits}
          averageStabilityScore={importanceData.stability_score}
          onOpenFoldModal={() => setShowFoldModal(true)}
        />
      )}

      {/* Configuration Panel */}
      <FeatureConfigPanel
        nSplits={nSplits}
        onNSplitsChange={setNSplits}
        cvStrategy={cvStrategy}
        onCvStrategyChange={setCvStrategy}
        seed={seed}
        onSeedChange={setSeed}
        method={method}
        onMethodChange={setMethod}
        onRun={handleRunFeatureSelection}
        running={running}
        disabled={hasMissingPrerequisites}
      />

      {/* Feature Importance Table */}
      {importanceData ? (
        <FeatureImportanceTable
          features={displayedFeatures}
          selectedFeaturesMap={selectedFeaturesMap}
          onToggleFeature={handleToggleFeature}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          threshold={threshold}
          onThresholdChange={handleThresholdSliderChange}
          searchTerm={searchTerm}
          onSearchTermChange={setSearchTerm}
          filterMode={filterMode}
          onFilterModeChange={setFilterMode}
          sortBy={sortBy}
          onSortByChange={setSortBy}
          onSaveSelection={handleSaveSelection}
          saving={updatingThreshold}
        />
      ) : (
        <EmptyState
          title="No Feature Importance Computed"
          description="Configure your ensemble parameters above and click 'Run Ensemble Selection' to compute fold-stratified feature ranks."
        />
      )}

      {/* Fold Modal */}
      <FoldInspectionModal
        isOpen={showFoldModal}
        foldData={foldData}
        onClose={() => setShowFoldModal(false)}
      />
    </div>
  );
};

export default FeatureEngineeringStage;
