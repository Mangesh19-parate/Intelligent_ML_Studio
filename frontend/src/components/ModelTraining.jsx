import React, { useState, useEffect, useRef } from 'react';
import { experimentApi, modelApi } from '../api/client';
import { LineageViewer } from './LineageViewer';
import { ExplainabilityViewer } from './ExplainabilityViewer';
import DeploymentGateModal from './DeploymentGateModal';
import ModelPassportModal from './ModelPassportModal';
import ExperimentHealthModal from './ExperimentHealthModal';
import {
  Cpu,
  Play,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Shuffle,
  ShieldCheck,
  Layers,
  Sparkles,
  Info,
  ChevronRight,
  TrendingUp,
  XCircle,
  Trophy,
  Lock,
  Eye,
  Sliders,
  Check,
  AlertCircle,
  HelpCircle,
  FileCode,
  BrainCircuit,
  Download,
  FileText,
  Activity,
  X,
} from 'lucide-react';

const REGRESSION_ALGORITHMS = [
  {
    id: 'LinearRegression',
    name: 'Linear Regression',
    tag: 'Baseline',
    description: 'Ordinary Least Squares baseline without regularization.',
  },
  {
    id: 'Ridge',
    name: 'Ridge Regression',
    tag: 'L2 Regularized',
    description: 'Linear model with L2 regularization to prevent multicollinearity.',
  },
  {
    id: 'RandomForestRegressor',
    name: 'Random Forest Regressor',
    tag: 'Non-Linear Ensemble',
    description: 'Ensemble of decision trees with bootstrap aggregation.',
  },
];

const CLASSIFICATION_ALGORITHMS = [
  {
    id: 'LogisticRegression',
    name: 'Logistic Regression',
    tag: 'Baseline',
    description: 'Log-odds linear classifier baseline.',
  },
  {
    id: 'RandomForestClassifier',
    name: 'Random Forest Classifier',
    tag: 'Non-Linear Ensemble',
    description: 'Bagging ensemble of decision tree classifiers.',
  },
  {
    id: 'GradientBoostingClassifier',
    name: 'Gradient Boosting Classifier',
    tag: 'Sequential Boosting',
    description: 'Sequential boosting ensemble minimizing pseudo-residual loss.',
  },
];

export const ModelTraining = ({ projectId, taskType, targetColumn, onExperimentCompleted }) => {
  const isRegression = taskType === 'REGRESSION';
  const isClassification = taskType === 'CLASSIFICATION';
  const availableAlgs = isRegression
    ? REGRESSION_ALGORITHMS
    : isClassification
    ? CLASSIFICATION_ALGORITHMS
    : [];

  const [selectedAlgorithms, setSelectedAlgorithms] = useState(
    availableAlgs.map((a) => a.id)
  );
  const [folds, setFolds] = useState(5);
  const [seed, setSeed] = useState('');
  const [selectionMetric, setSelectionMetric] = useState(isRegression ? 'rmse' : 'f1_macro');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Active Experiment, Leaderboard & History State
  const [activeExperiment, setActiveExperiment] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [experimentsHistory, setExperimentsHistory] = useState([]);
  const [pollingActive, setPollingActive] = useState(false);
  const [selectedModelMetrics, setSelectedModelMetrics] = useState(null);
  const [modelModalOpen, setModelModalOpen] = useState(false);
  const [lineageModalOpen, setLineageModalOpen] = useState(false);
  const [lineageExperimentId, setLineageExperimentId] = useState(null);
  const [explainModalOpen, setExplainModalOpen] = useState(false);
  const [selectedExplainModel, setSelectedExplainModel] = useState(null);
  const [deploymentModalOpen, setDeploymentModalOpen] = useState(false);
  const [selectedDeploymentModel, setSelectedDeploymentModel] = useState(null);
  const [passportModalOpen, setPassportModalOpen] = useState(false);
  const [selectedPassportModelId, setSelectedPassportModelId] = useState(null);
  const [healthModalOpen, setHealthModalOpen] = useState(false);
  const [healthExperimentId, setHealthExperimentId] = useState(null);
  const [rerunningDiagnostic, setRerunningDiagnostic] = useState(false);

  const pollingTimerRef = useRef(null);

  useEffect(() => {
    setSelectedAlgorithms(availableAlgs.map((a) => a.id));
    setSelectionMetric(isRegression ? 'rmse' : 'f1_macro');
  }, [taskType]);

  const loadLeaderboardData = async (experimentId = null) => {
    try {
      const res = await modelApi.getLeaderboard(projectId, experimentId);
      setLeaderboard(res.data);
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await experimentApi.listByProject(projectId);
      setExperimentsHistory(res.data || []);
      if (res.data && res.data.length > 0) {
        const latest = res.data[0];
        setActiveExperiment(latest);
        await loadLeaderboardData(latest.id);
        if (latest.status === 'RUNNING') {
          startPolling(latest.id);
        }
      }
    } catch (err) {
      console.error('Failed to load experiment history:', err);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadHistory();
    }
    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [projectId]);

  const startPolling = (experimentId) => {
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    setPollingActive(true);

    const poll = async () => {
      try {
        const res = await experimentApi.get(experimentId);
        setActiveExperiment(res.data);
        await loadLeaderboardData(experimentId);

        if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
          clearInterval(pollingTimerRef.current);
          setPollingActive(false);
          loadHistory();
          if (onExperimentCompleted) onExperimentCompleted();
        }
      } catch (err) {
        console.error('Polling error:', err);
        clearInterval(pollingTimerRef.current);
        setPollingActive(false);
      }
    };

    poll();
    pollingTimerRef.current = setInterval(poll, 1500);
  };

  const handleToggleAlgorithm = (algId) => {
    if (selectedAlgorithms.includes(algId)) {
      if (selectedAlgorithms.length === 1) return;
      setSelectedAlgorithms(selectedAlgorithms.filter((id) => id !== algId));
    } else {
      setSelectedAlgorithms([...selectedAlgorithms, algId]);
    }
  };

  const handleSelectAll = () => {
    setSelectedAlgorithms(availableAlgs.map((a) => a.id));
  };

  const handleRandomizeSeed = () => {
    setSeed(Math.floor(Math.random() * 1000000).toString());
  };

  const handleStartTraining = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (selectedAlgorithms.length === 0) {
      setError('Please select at least one algorithm to train.');
      return;
    }

    try {
      setLoading(true);
      const payload = {
        algorithms: selectedAlgorithms,
        folds: Number(folds),
        seed: seed ? Number(seed) : null,
        selection_metric: selectionMetric,
      };

      const res = await experimentApi.create(projectId, payload);
      setSuccessMsg('Cross-validation training & evaluation launched.');
      startPolling(res.data.experiment_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to launch training experiment');
    } finally {
      setLoading(false);
    }
  };

  const handleDiagnosticRerun = async () => {
    if (!activeExperiment) return;
    setError('');
    setSuccessMsg('');
    try {
      setRerunningDiagnostic(true);
      const res = await experimentApi.diagnosticRerun(activeExperiment.id);
      setSuccessMsg(res.data.message || 'Diagnostic rerun completed. Stored as TEST_REUSED_DIAGNOSTIC.');
      await loadLeaderboardData(activeExperiment.id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Diagnostic rerun failed');
    } finally {
      setRerunningDiagnostic(false);
    }
  };

  const handleOpenModelMetrics = async (modelId) => {
    try {
      const res = await modelApi.getMetrics(modelId);
      setSelectedModelMetrics(res.data);
      setModelModalOpen(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownloadModel = async (modelId, algorithmName) => {
    try {
      const resp = await modelApi.download(modelId, 'joblib');
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${algorithmName}_pipeline.joblib`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to download model artifact');
    }
  };

  const renderFitBadge = (diagnosis) => {
    if (!diagnosis) return <span className="text-[var(--color-text-muted)] text-[10px]">N/A</span>;

    if (diagnosis === 'GOOD_FIT') {
      return (
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/25 text-emerald-400"
          title="Generalization gap is within tolerance and model significantly outperforms baseline"
        >
          ✓ Good Fit
        </span>
      );
    }
    if (diagnosis === 'POTENTIAL_OVERFIT') {
      return (
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/25 text-amber-400"
          title="High training score but lower CV validation score indicates generalization gap"
        >
          ⚠ Overfit Gap
        </span>
      );
    }
    if (diagnosis === 'POTENTIAL_UNDERFIT_WEAK_SIGNAL') {
      return (
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 border border-rose-500/25 text-rose-400"
          title="CV validation performance is near naive baseline — weak predictive signal detected"
        >
          ⚠ Weak Signal
        </span>
      );
    }
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-muted)]"
        title="Validation sample count < 20 — insufficient data for reliable diagnosis"
      >
        ℹ Low Data (&lt;20)
      </span>
    );
  };

  if (!taskType || !['REGRESSION', 'CLASSIFICATION'].includes(taskType)) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8 text-center space-y-4 shadow-sm">
        <AlertTriangle className="w-12 h-12 mx-auto text-amber-400" />
        <h3 className="text-base font-bold text-[var(--color-text)]">Task Type Required</h3>
        <p className="text-xs text-[var(--color-text-muted)] max-w-md mx-auto">
          Please confirm the project task type (Regression or Classification) in the Data Profiling tab before running model training.
        </p>
      </div>
    );
  }

  const winningModel = leaderboard?.models?.find((m) => m.is_winner);

  return (
    <div className="space-y-6">
      {/* Leakage Isolation & Locked Test Banner */}
      <div className="p-4 rounded-2xl bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-xs text-[var(--color-text)] flex items-start space-x-3 shadow-sm">
        <ShieldCheck className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
        <div>
          <strong className="font-bold text-[var(--color-text)]">Leakage-Safe Protocol & Locked Test Boundary: </strong>
          <span className="text-[var(--color-text-muted)]">
            Inner CV evaluation drives model ranking by primary metric. Upon finalization, the winning model is refit on full Development data and evaluated exactly ONCE against the Locked Test partition.
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Training Configuration */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3.5">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-[var(--color-accent)]" />
              <h2 className="text-sm font-bold text-[var(--color-text)]">Training Configuration</h2>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] font-mono">
              {taskType}
            </span>
          </div>

          <form onSubmit={handleStartTraining} className="space-y-5">
            {/* Algorithm Checklist */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[var(--color-text)]">
                  Target Algorithms (Fixed 3)
                </label>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-[11px] font-semibold text-[var(--color-accent)] hover:underline cursor-pointer"
                >
                  Select All
                </button>
              </div>

              <div className="space-y-2">
                {availableAlgs.map((alg) => {
                  const isChecked = selectedAlgorithms.includes(alg.id);
                  return (
                    <div
                      key={alg.id}
                      onClick={() => handleToggleAlgorithm(alg.id)}
                      className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        isChecked
                          ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] text-[var(--color-text)]'
                          : 'bg-[var(--color-surface-card)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2.5">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="rounded border-[var(--color-border)] text-[var(--color-accent)] focus:ring-[var(--color-accent)] pointer-events-none"
                          />
                          <span className="font-bold text-xs text-[var(--color-text)]">{alg.name}</span>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)]">
                          {alg.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-muted)] mt-1.5 pl-6">
                        {alg.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Primary Selection Metric */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                <span>Primary Selection Metric (Sort Basis)</span>
                <span className="text-[10px] text-[var(--color-accent)] font-semibold">Authoritative</span>
              </label>
              <select
                value={selectionMetric}
                onChange={(e) => setSelectionMetric(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer font-medium"
              >
                {isRegression ? (
                  <>
                    <option value="rmse">RMSE — Root Mean Squared Error (Minimize)</option>
                    <option value="mae">MAE — Mean Absolute Error (Minimize)</option>
                    <option value="r2">R² — Coefficient of Determination (Maximize)</option>
                    <option value="adjusted_r2">Adjusted R² (Maximize)</option>
                  </>
                ) : (
                  <>
                    <option value="f1_macro">Macro-F1 (Maximize)</option>
                    <option value="f1_weighted">Weighted-F1 (Maximize)</option>
                    <option value="accuracy">Accuracy (Maximize)</option>
                    <option value="roc_auc">ROC-AUC (Maximize)</option>
                  </>
                )}
              </select>
            </div>

            {/* Folds & Seed */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-[var(--color-text-muted)]">
                  CV Folds
                </label>
                <select
                  value={folds}
                  onChange={(e) => setFolds(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer font-medium"
                >
                  <option value={3}>3 Folds (Fast)</option>
                  <option value={5}>5 Folds (Standard)</option>
                  <option value={10}>10 Folds (Thorough)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-[var(--color-text-muted)]">
                    CV Seed
                  </label>
                  <button
                    type="button"
                    onClick={handleRandomizeSeed}
                    className="text-[10px] text-[var(--color-accent)] hover:underline flex items-center space-x-0.5 cursor-pointer"
                  >
                    <Shuffle className="w-2.5 h-2.5" />
                    <span>Rand</span>
                  </button>
                </div>
                <input
                  type="number"
                  placeholder="Auto seed"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] font-mono focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || pollingActive || selectedAlgorithms.length === 0}
              className="w-full py-3 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold rounded-full shadow-md shadow-[var(--color-accent-soft)] transition-all flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
            >
              {pollingActive ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Evaluating Cross-Validation Folds...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Start Model Training & Selection</span>
                </>
              )}
            </button>
          </form>

          {/* Past Experiments Selector */}
          {experimentsHistory.length > 0 && (
            <div className="space-y-2 border-t border-[var(--color-border)] pt-4">
              <div className="text-[11px] uppercase tracking-wider font-bold text-[var(--color-text-muted)]">
                Experiment Runs ({experimentsHistory.length})
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                {experimentsHistory.map((exp) => (
                  <button
                    key={exp.id}
                    onClick={() => {
                      setActiveExperiment(exp);
                      loadLeaderboardData(exp.id);
                    }}
                    className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
                      activeExperiment?.id === exp.id
                        ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] text-[var(--color-text)] font-bold'
                        : 'bg-[var(--color-surface-card)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]'
                    }`}
                  >
                    <div className="truncate font-mono text-[11px]">
                      {new Date(exp.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {exp.fold_count} folds
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        exp.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : exp.status === 'RUNNING'
                          ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] animate-pulse'
                          : 'bg-rose-500/10 text-rose-400'
                      }`}
                    >
                      {exp.status}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 2 Columns: Official Leaderboard & Winner Callout */}
        <div className="lg:col-span-2 space-y-5">
          {!leaderboard || !activeExperiment ? (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center space-y-3 shadow-sm">
              <Layers className="w-12 h-12 mx-auto text-[var(--color-text-muted)] opacity-50" />
              <h3 className="text-sm font-bold text-[var(--color-text)]">No Model Leaderboard Available</h3>
              <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto">
                Configure algorithms and folds on the left, then launch training to populate the authoritative primary-metric leaderboard.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Winner Callout Card */}
              {winningModel && (
                <div className="bg-[var(--color-surface)] border-2 border-[var(--color-accent)] rounded-2xl p-6 shadow-md relative overflow-hidden space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="p-1.5 rounded-lg bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
                          <Trophy className="w-4 h-4" />
                        </span>
                        <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                          Selected Winner (Primary Metric: {leaderboard.selection_metric.toUpperCase()})
                        </span>
                      </div>
                      <h3 className="text-xl font-extrabold text-[var(--color-text)]">
                        {winningModel.algorithm_name}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--color-text-muted)]">
                        <span>
                          CV Mean {leaderboard.selection_metric.toUpperCase()}:{' '}
                          <strong className="text-[var(--color-text)] font-mono">
                            {winningModel.primary_metric_value !== null ? Number(winningModel.primary_metric_value).toFixed(5) : 'N/A'}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>
                          Fit: {renderFitBadge(winningModel.fit_diagnosis)}
                        </span>
                        {winningModel.decision_threshold !== null && winningModel.decision_threshold !== undefined && (
                          <>
                            <span>•</span>
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]" title="Binary classification decision threshold optimized on out-of-fold predictions">
                              <span>τ = {Number(winningModel.decision_threshold).toFixed(4)}</span>
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="bg-[var(--color-surface-card)] p-4 rounded-xl border border-[var(--color-border)] space-y-2 text-right">
                      <div className="flex items-center justify-end space-x-1.5 text-xs text-[var(--color-text-muted)]">
                        <Lock className="w-3.5 h-3.5 text-rose-400" />
                        <span className="font-bold text-[var(--color-text)]">Locked Test Evaluation</span>
                      </div>

                      {leaderboard.locked_test_consumed ? (
                        <div className="space-y-1">
                          <div className="text-lg font-extrabold text-emerald-400 font-mono">
                            {winningModel.locked_test_score !== null
                              ? Number(winningModel.locked_test_score).toFixed(5)
                              : 'Evaluated'}
                          </div>
                          <div className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-bold">
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span>Evaluated once, now consumed</span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs text-amber-400 font-semibold">
                          Pending final refit
                        </div>
                      )}

                      {leaderboard.locked_test_consumed && (
                        <div className="pt-1">
                          <button
                            onClick={handleDiagnosticRerun}
                            disabled={rerunningDiagnostic}
                            className="text-[10px] text-[var(--color-accent)] hover:underline transition-colors cursor-pointer"
                            title="Rerun locked test data for diagnostic/debugging only. Labeled as TEST_REUSED_DIAGNOSTIC."
                          >
                            {rerunningDiagnostic ? 'Running Diagnostic...' : 'Diagnostic Rerun (Non-authoritative)'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Leaderboard Table Card */}
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3.5">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-bold text-[var(--color-text)]">
                        Authoritative Model Leaderboard
                      </h3>
                      <span className="px-3 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-[var(--color-accent)]">
                        Ranked strictly by {leaderboard.selection_metric.toUpperCase()} ({leaderboard.selection_direction})
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                      Composite score shown for comparison only — never alters rank order.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => {
                        setHealthExperimentId(activeExperiment.id);
                        setHealthModalOpen(true);
                      }}
                      className="px-3.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface-card)] text-[var(--color-text)] border border-[var(--color-border)] text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
                      title="Inspect Experiment Health Report"
                    >
                      <Activity className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Health Report</span>
                    </button>
                    <button
                      onClick={() => {
                        setLineageExperimentId(activeExperiment.id);
                        setLineageModalOpen(true);
                      }}
                      className="px-3.5 py-1.5 rounded-full bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] border border-[var(--color-accent-border)] text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer"
                      title="Inspect full experiment lineage, software environment, and artifact checksums"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Lineage & Integrity</span>
                    </button>
                    <div className="text-right text-[11px] text-[var(--color-text-muted)] font-mono pl-1">
                      {leaderboard.models.length} models
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                      <tr>
                        <th className="px-4 py-3">Rank</th>
                        <th className="px-4 py-3">Algorithm</th>
                        <th className="px-4 py-3 bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold border-x border-[var(--color-border)]">
                          Primary: {leaderboard.selection_metric.toUpperCase()}
                        </th>
                        <th className="px-4 py-3">
                          {isRegression ? 'Secondary: R²' : 'Secondary: ROC-AUC'}
                        </th>
                        <th className="px-4 py-3">Fit Diagnosis</th>
                        <th className="px-4 py-3 text-[var(--color-text-muted)]">
                          Composite Indicator
                          <div className="text-[9px] lowercase font-normal opacity-70">(not used for ranking)</div>
                        </th>
                        <th className="px-4 py-3 text-right">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {leaderboard.models.map((model, idx) => {
                        const isWin = model.is_winner;
                        return (
                          <tr
                            key={model.id}
                            className={`transition-colors ${
                              isWin
                                ? 'bg-[var(--color-accent-soft)]/20'
                                : 'hover:bg-[var(--color-surface-hover)]'
                            }`}
                          >
                            <td className="px-4 py-3 font-mono">
                              {isWin ? (
                                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold text-xs border border-[var(--color-accent-border)]">
                                  1
                                </span>
                              ) : (
                                <span className="text-[var(--color-text-muted)] font-semibold pl-1.5">{idx + 1}</span>
                              )}
                            </td>

                            <td className="px-4 py-3">
                              <div className="font-bold text-[var(--color-text)] flex items-center space-x-1.5">
                                <span>{model.algorithm_name}</span>
                                {isWin && (
                                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] uppercase">
                                    Winner
                                  </span>
                                )}
                                {model.decision_threshold !== null && model.decision_threshold !== undefined && (
                                  <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)]" title="Optimized decision threshold">
                                    τ={Number(model.decision_threshold).toFixed(3)}
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-[var(--color-text-muted)] font-mono truncate max-w-[160px]">
                                {model.status === 'FAILED' ? (
                                  <span className="text-rose-400">Failed: {model.error_message}</span>
                                ) : (
                                  JSON.stringify(model.hyperparameters) === '{}' ? 'Default params' : JSON.stringify(model.hyperparameters)
                                )}
                              </div>
                            </td>

                            <td className="px-4 py-3 font-mono font-extrabold bg-[var(--color-accent-soft)]/30 border-x border-[var(--color-border)] text-[var(--color-accent)] text-sm">
                              {model.primary_metric_value !== null && model.primary_metric_value !== undefined ? (
                                Number(model.primary_metric_value).toFixed(5)
                              ) : (
                                <span className="text-[var(--color-text-muted)] text-xs italic font-normal">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3 font-mono text-[var(--color-text)]">
                              {model.secondary_metric_value !== null && model.secondary_metric_value !== undefined ? (
                                Number(model.secondary_metric_value).toFixed(5)
                              ) : (
                                <span className="text-[var(--color-text-muted)] italic font-normal">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3">
                              {renderFitBadge(model.fit_diagnosis)}
                            </td>

                            <td className="px-4 py-3">
                              {model.model_selection_score !== null && model.model_selection_score !== undefined ? (
                                <div className="space-y-1">
                                  <div className="font-mono text-[var(--color-text)] text-xs font-semibold">
                                    {Number(model.model_selection_score).toFixed(1)} / 100
                                  </div>
                                  <div className="w-24 bg-[var(--color-surface-hover)] rounded-full h-1.5 overflow-hidden">
                                    <div
                                      className="bg-[var(--color-accent)] h-1.5 rounded-full"
                                      style={{ width: `${Math.min(100, Math.max(0, model.model_selection_score))}%` }}
                                    />
                                  </div>
                                </div>
                              ) : (
                                <span className="text-[var(--color-text-muted)] italic">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end space-x-1.5">
                                <button
                                  onClick={() => handleOpenModelMetrics(model.id)}
                                  className="px-2.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer border border-[var(--color-border)]"
                                  title="View complete cross-validation and fold metric records"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                  <span>Metrics</span>
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedExplainModel(model);
                                    setExplainModalOpen(true);
                                  }}
                                  disabled={!isWin && !model.artifact_path}
                                  title={
                                    !isWin && !model.artifact_path
                                      ? 'This model has no persisted artifact — explainability is only available for the winning model of a completed experiment'
                                      : 'Inspect SHAP feature attributions and global/local explanations'
                                  }
                                  className={`px-2.5 py-1.5 rounded-full text-xs font-semibold transition-colors inline-flex items-center space-x-1 border ${
                                    isWin || model.artifact_path
                                      ? 'bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] border-[var(--color-accent-border)] cursor-pointer'
                                      : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border-[var(--color-border)] cursor-not-allowed opacity-50'
                                  }`}
                                >
                                  <BrainCircuit className="w-3.5 h-3.5" />
                                  <span>Explain</span>
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedPassportModelId(model.id);
                                    setPassportModalOpen(true);
                                  }}
                                  title="View technical model passport, lineage provenance & governance records"
                                  className="px-2.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer"
                                >
                                  <FileText className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                                  <span>Passport</span>
                                </button>
                                <button
                                  onClick={() => handleDownloadModel(model.id, model.algorithm_name)}
                                  disabled={!isWin && !model.artifact_path}
                                  title={
                                    !isWin && !model.artifact_path
                                      ? 'Artifact download is only available for persisted models'
                                      : 'Download serialized joblib model pipeline artifact'
                                  }
                                  className={`px-2.5 py-1.5 rounded-full text-xs font-semibold transition-colors inline-flex items-center space-x-1 border ${
                                    isWin || model.artifact_path
                                      ? 'bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border-[var(--color-border)] cursor-pointer'
                                      : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border-[var(--color-border)] cursor-not-allowed opacity-50'
                                  }`}
                                >
                                  <Download className="w-3.5 h-3.5" />
                                  <span>Artifact</span>
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedDeploymentModel(model);
                                    setDeploymentModalOpen(true);
                                  }}
                                  disabled={!isWin && !model.artifact_path}
                                  title={
                                    !isWin && !model.artifact_path
                                      ? 'Deployment is only available for the winning model with a persisted artifact'
                                      : 'Evaluate pre-deployment gate conditions and manage production deployment'
                                  }
                                  className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all inline-flex items-center space-x-1 ${
                                    isWin || model.artifact_path
                                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm cursor-pointer'
                                      : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border border-[var(--color-border)] cursor-not-allowed opacity-50'
                                  }`}
                                >
                                  <ShieldCheck className="w-3.5 h-3.5" />
                                  <span>Deploy & Gate</span>
                                </button>
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
        </div>
      </div>

      {/* Model Metrics Modal */}
      {modelModalOpen && selectedModelMetrics && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[var(--color-text)]">Full Metric Breakdown</h3>
                <p className="text-xs text-[var(--color-text-muted)]">
                  TRAIN, VALIDATION (per fold), CV_MEAN, and LOCKED_TEST records
                </p>
              </div>
              <button
                onClick={() => setModelModalOpen(false)}
                className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Metrics Table */}
              <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                    <tr>
                      <th className="px-4 py-2.5">Metric</th>
                      <th className="px-4 py-2.5">Split</th>
                      <th className="px-4 py-2.5">Fold</th>
                      <th className="px-4 py-2.5 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)] font-mono text-[11px]">
                    {selectedModelMetrics.map((m) => (
                      <tr key={m.id} className="hover:bg-[var(--color-surface-hover)]">
                        <td className="px-4 py-2 text-[var(--color-text)] font-semibold">{m.metric_name}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              m.split === 'LOCKED_TEST'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : m.split === 'CV_MEAN'
                                ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]'
                                : m.split === 'TEST_REUSED_DIAGNOSTIC'
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                            }`}
                          >
                            {m.split}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-[var(--color-text-muted)]">
                          {m.fold_index !== null ? `Fold ${m.fold_index + 1}` : 'Overall'}
                        </td>
                        <td className="px-4 py-2 text-right text-emerald-400 font-bold">
                          {m.metric_value !== null ? Number(m.metric_value).toFixed(5) : (
                            m.metric_json ? JSON.stringify(m.metric_json) : 'null'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lineage & Integrity Modal */}
      {lineageModalOpen && lineageExperimentId && (
        <LineageViewer
          experimentId={lineageExperimentId}
          onClose={() => setLineageModalOpen(false)}
        />
      )}

      {/* Model Explainability Modal */}
      {explainModalOpen && selectedExplainModel && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <ExplainabilityViewer
            modelId={selectedExplainModel.id}
            algorithmName={selectedExplainModel.algorithm_name}
            isWinner={selectedExplainModel.is_winner || activeExperiment?.selected_model_id === selectedExplainModel.id}
            hasArtifact={Boolean(selectedExplainModel.artifact_path)}
            onClose={() => {
              setExplainModalOpen(false);
              setSelectedExplainModel(null);
            }}
          />
        </div>
      )}

      {/* Model Deployment & Gate Modal */}
      {deploymentModalOpen && selectedDeploymentModel && (
        <DeploymentGateModal
          model={selectedDeploymentModel}
          isOpen={deploymentModalOpen}
          onClose={() => {
            setDeploymentModalOpen(false);
            setSelectedDeploymentModel(null);
          }}
          onDeploymentSuccess={(dep) => {
            setSuccessMsg(`Model successfully deployed into production at ${dep.endpoint_path}`);
          }}
        />
      )}

      {/* Model Passport Governance Modal */}
      {passportModalOpen && selectedPassportModelId && (
        <ModelPassportModal
          modelId={selectedPassportModelId}
          isOpen={passportModalOpen}
          onClose={() => {
            setPassportModalOpen(false);
            setSelectedPassportModelId(null);
          }}
        />
      )}

      {/* Experiment Health Report Modal (SRS v9 §13) */}
      {healthModalOpen && healthExperimentId && (
        <ExperimentHealthModal
          experimentId={healthExperimentId}
          onClose={() => {
            setHealthModalOpen(false);
            setHealthExperimentId(null);
          }}
        />
      )}
    </div>
  );
};

export default ModelTraining;
