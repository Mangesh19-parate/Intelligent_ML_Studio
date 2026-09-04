import React, { useState, useEffect, useRef } from 'react';
import { experimentApi, modelApi } from '../api/client';
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

  const renderFitBadge = (diagnosis) => {
    if (!diagnosis) return <span className="text-slate-500 text-[10px]">N/A</span>;

    if (diagnosis === 'GOOD_FIT') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          Good Fit
        </span>
      );
    }
    if (diagnosis === 'POTENTIAL_OVERFIT') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/20 text-amber-400">
          Potential Overfit
        </span>
      );
    }
    if (diagnosis === 'POTENTIAL_UNDERFIT_WEAK_SIGNAL') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/20 text-amber-400">
          Weak Signal / Underfit
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 border border-slate-700 text-slate-400">
        Insufficient Data
      </span>
    );
  };

  if (!taskType || !['REGRESSION', 'CLASSIFICATION'].includes(taskType)) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 mx-auto text-amber-400" />
        <h3 className="text-base font-bold text-white">Task Type Required</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Please confirm the project task type (Regression or Classification) in the Data Profiling tab before running model training.
        </p>
      </div>
    );
  }

  const winningModel = leaderboard?.models?.find((m) => m.is_winner);

  return (
    <div className="space-y-6">
      {/* Leakage Isolation & Locked Test Banner */}
      <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15 text-xs text-indigo-300 flex items-start space-x-3">
        <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-white">Leakage-Safe Protocol & Locked Test Boundary: </strong>
          Inner CV evaluation drives model ranking by primary metric. Upon finalization, the winning model is refit on full Development data and evaluated exactly ONCE against the Locked Test partition.
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Training Configuration */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Training Configuration</h2>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
              {taskType}
            </span>
          </div>

          <form onSubmit={handleStartTraining} className="space-y-5">
            {/* Algorithm Checklist */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-white">
                  Target Algorithms (Fixed 3)
                </label>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-[11px] text-indigo-400 hover:underline"
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
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                        isChecked
                          ? 'bg-indigo-600/15 border-indigo-500/60 text-white'
                          : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 pointer-events-none"
                          />
                          <span className="font-semibold text-xs">{alg.name}</span>
                        </div>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {alg.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 pl-6">
                        {alg.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Primary Selection Metric */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
                <span>Primary Selection Metric (Sort Basis)</span>
                <span className="text-[10px] text-indigo-400">Authoritative</span>
              </label>
              <select
                value={selectionMetric}
                onChange={(e) => setSelectionMetric(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-800 bg-slate-950 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">
                  CV Folds
                </label>
                <select
                  value={folds}
                  onChange={(e) => setFolds(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-800 bg-slate-950 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value={3}>3 Folds (Fast)</option>
                  <option value={5}>5 Folds (Standard)</option>
                  <option value={10}>10 Folds (Thorough)</option>
                </select>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-semibold text-slate-300">
                    CV Seed
                  </label>
                  <button
                    type="button"
                    onClick={handleRandomizeSeed}
                    className="text-[10px] text-indigo-400 hover:underline flex items-center space-x-0.5"
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
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-800 bg-slate-950 text-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || pollingActive || selectedAlgorithms.length === 0}
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
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
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <div className="text-[11px] uppercase tracking-wider font-bold text-slate-400">
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
                    className={`w-full text-left p-2 rounded-lg border text-xs transition-all flex items-center justify-between ${
                      activeExperiment?.id === exp.id
                        ? 'bg-indigo-600/20 border-indigo-500/60 text-white font-semibold'
                        : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="truncate font-mono text-[11px]">
                      {new Date(exp.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {exp.fold_count} folds
                    </div>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        exp.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : exp.status === 'RUNNING'
                          ? 'bg-indigo-500/10 text-indigo-400 animate-pulse'
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
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <Layers className="w-12 h-12 mx-auto text-slate-600" />
              <h3 className="text-sm font-bold text-white">No Model Leaderboard Available</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Configure algorithms and folds on the left, then launch training to populate the authoritative primary-metric leaderboard.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Winner Callout Card */}
              {winningModel && (
                <div className="bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-emerald-500/10 border border-amber-500/30 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          <Trophy className="w-4 h-4" />
                        </span>
                        <span className="text-xs font-bold uppercase tracking-wider text-amber-300">
                          Selected Winner (Primary Metric: {leaderboard.selection_metric.toUpperCase()})
                        </span>
                      </div>
                      <h3 className="text-lg font-extrabold text-white">
                        {winningModel.algorithm_name}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
                        <span>
                          CV Mean {leaderboard.selection_metric.toUpperCase()}:{' '}
                          <strong className="text-white font-mono">
                            {winningModel.primary_metric_value !== null ? Number(winningModel.primary_metric_value).toFixed(5) : 'N/A'}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>
                          Fit: {renderFitBadge(winningModel.fit_diagnosis)}
                        </span>
                      </div>
                    </div>

                    <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 space-y-2 text-right">
                      <div className="flex items-center justify-end space-x-1.5 text-xs text-slate-400">
                        <Lock className="w-3.5 h-3.5 text-rose-400" />
                        <span className="font-semibold text-white">Locked Test Evaluation</span>
                      </div>

                      {leaderboard.locked_test_consumed ? (
                        <div className="space-y-1">
                          <div className="text-lg font-extrabold text-emerald-400 font-mono">
                            {winningModel.locked_test_score !== null
                              ? Number(winningModel.locked_test_score).toFixed(5)
                              : 'Evaluated'}
                          </div>
                          <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px] font-bold">
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
                            className="text-[10px] text-slate-400 hover:text-indigo-300 underline transition-colors cursor-pointer"
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
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden space-y-4 p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-bold text-white">
                        Authoritative Model Leaderboard
                      </h3>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                        Ranked strictly by {leaderboard.selection_metric.toUpperCase()} ({leaderboard.selection_direction})
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Composite score shown for comparison only — never alters rank order.
                    </p>
                  </div>

                  <div className="text-right text-[11px] text-slate-400 font-mono">
                    {leaderboard.models.length} competing models
                  </div>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold text-[10px]">
                      <tr>
                        <th className="px-4 py-3">Rank</th>
                        <th className="px-4 py-3">Algorithm</th>
                        <th className="px-4 py-3 bg-indigo-950/40 text-indigo-300 font-bold border-x border-slate-800">
                          Primary: {leaderboard.selection_metric.toUpperCase()}
                        </th>
                        <th className="px-4 py-3">
                          {isRegression ? 'Secondary: R²' : 'Secondary: ROC-AUC'}
                        </th>
                        <th className="px-4 py-3">Fit Diagnosis</th>
                        <th className="px-4 py-3 text-slate-400">
                          Composite Indicator
                          <div className="text-[9px] lowercase font-normal text-slate-500">(not used for ranking)</div>
                        </th>
                        <th className="px-4 py-3 text-right">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {leaderboard.models.map((model, idx) => {
                        const isWin = model.is_winner;
                        return (
                          <tr
                            key={model.id}
                            className={`transition-colors ${
                              isWin
                                ? 'bg-amber-500/5 hover:bg-amber-500/10'
                                : 'hover:bg-slate-800/40'
                            }`}
                          >
                            <td className="px-4 py-3 font-mono">
                              {isWin ? (
                                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 font-bold text-xs border border-amber-500/30">
                                  1
                                </span>
                              ) : (
                                <span className="text-slate-500 font-semibold pl-1.5">{idx + 1}</span>
                              )}
                            </td>

                            <td className="px-4 py-3">
                              <div className="font-bold text-white flex items-center space-x-1.5">
                                <span>{model.algorithm_name}</span>
                                {isWin && (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 uppercase">
                                    Winner
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono truncate max-w-[160px]">
                                {model.status === 'FAILED' ? (
                                  <span className="text-rose-400">Failed: {model.error_message}</span>
                                ) : (
                                  JSON.stringify(model.hyperparameters) === '{}' ? 'Default params' : JSON.stringify(model.hyperparameters)
                                )}
                              </div>
                            </td>

                            <td className="px-4 py-3 font-mono font-extrabold bg-indigo-950/30 border-x border-slate-800 text-indigo-300 text-sm">
                              {model.primary_metric_value !== null && model.primary_metric_value !== undefined ? (
                                Number(model.primary_metric_value).toFixed(5)
                              ) : (
                                <span className="text-slate-500 text-xs italic font-normal">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3 font-mono text-slate-300">
                              {model.secondary_metric_value !== null && model.secondary_metric_value !== undefined ? (
                                Number(model.secondary_metric_value).toFixed(5)
                              ) : (
                                <span className="text-slate-500 italic font-normal">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3">
                              {renderFitBadge(model.fit_diagnosis)}
                            </td>

                            <td className="px-4 py-3">
                              {model.model_selection_score !== null && model.model_selection_score !== undefined ? (
                                <div className="space-y-1">
                                  <div className="font-mono text-slate-300 text-xs font-semibold">
                                    {Number(model.model_selection_score).toFixed(1)} / 100
                                  </div>
                                  <div className="w-24 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                    <div
                                      className="bg-indigo-500 h-1.5 rounded-full"
                                      style={{ width: `${Math.min(100, Math.max(0, model.model_selection_score))}%` }}
                                    />
                                  </div>
                                </div>
                              ) : (
                                <span className="text-slate-500 italic">N/A</span>
                              )}
                            </td>

                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => handleOpenModelMetrics(model.id)}
                                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Metrics</span>
                              </button>
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
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Full Metric Breakdown</h3>
                <p className="text-xs text-slate-400">
                  TRAIN, VALIDATION (per fold), CV_MEAN, and LOCKED_TEST records
                </p>
              </div>
              <button
                onClick={() => setModelModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Metrics Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold text-[10px]">
                    <tr>
                      <th className="px-4 py-2.5">Metric</th>
                      <th className="px-4 py-2.5">Split</th>
                      <th className="px-4 py-2.5">Fold</th>
                      <th className="px-4 py-2.5 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                    {selectedModelMetrics.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-800/30">
                        <td className="px-4 py-2 text-white font-semibold">{m.metric_name}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              m.split === 'LOCKED_TEST'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : m.split === 'CV_MEAN'
                                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                : m.split === 'TEST_REUSED_DIAGNOSTIC'
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {m.split}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-400">
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
    </div>
  );
};
