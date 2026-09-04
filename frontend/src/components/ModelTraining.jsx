import React, { useState, useEffect, useRef } from 'react';
import { experimentApi } from '../api/client';
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Active Experiment & History State
  const [activeExperiment, setActiveExperiment] = useState(null);
  const [experimentsHistory, setExperimentsHistory] = useState([]);
  const [pollingActive, setPollingActive] = useState(false);
  const pollingTimerRef = useRef(null);

  useEffect(() => {
    setSelectedAlgorithms(availableAlgs.map((a) => a.id));
  }, [taskType]);

  const loadHistory = async () => {
    try {
      const res = await experimentApi.listByProject(projectId);
      setExperimentsHistory(res.data || []);
      if (res.data && res.data.length > 0 && !activeExperiment) {
        setActiveExperiment(res.data[0]);
        if (res.data[0].status === 'RUNNING') {
          startPolling(res.data[0].id);
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
      if (selectedAlgorithms.length === 1) return; // Keep at least one
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
      };

      const res = await experimentApi.create(projectId, payload);
      setSuccessMsg('Cross-validation training experiment launched.');
      startPolling(res.data.experiment_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to launch training experiment');
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="space-y-6">
      {/* Leakage Isolation Banner */}
      <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15 text-xs text-indigo-300 flex items-start space-x-3">
        <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-white">Leakage-Controlled CV Harness: </strong>
          Feature preprocessing and rank-aggregation selection are fit once per CV fold on the training slice only. Models compete on top of the shared selected features with zero Locked Test data leakage.
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
        {/* Left 1 Column: Training Configuration */}
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
                  <span>Cross-Validation in Progress...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Start Model Training</span>
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
                    onClick={() => setActiveExperiment(exp)}
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

        {/* Right 2 Columns: Live Experiment Results & Sanity Metric Cards */}
        <div className="lg:col-span-2 space-y-5">
          {!activeExperiment ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <Layers className="w-12 h-12 mx-auto text-slate-600" />
              <h3 className="text-sm font-bold text-white">No Training Runs Yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Configure algorithms and folds on the left, then click Start Model Training to execute cross-validation.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Header Status Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-bold text-white">
                        Experiment Run
                      </h3>
                      <span className="font-mono text-[11px] text-slate-500">
                        ({activeExperiment.id.slice(0, 8)})
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Task: <strong className="text-white">{activeExperiment.task_type}</strong> • CV: <strong className="text-white">{activeExperiment.fold_count}-fold</strong> • Seed: <strong className="text-white font-mono">{activeExperiment.cv_seed ?? 'N/A'}</strong>
                    </p>
                  </div>

                  <span
                    className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                      activeExperiment.status === 'COMPLETED'
                        ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                        : activeExperiment.status === 'RUNNING'
                        ? 'bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 animate-pulse'
                        : 'bg-rose-500/15 border border-rose-500/30 text-rose-400'
                    }`}
                  >
                    {activeExperiment.status === 'COMPLETED' && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {activeExperiment.status === 'RUNNING' && <RotateCw className="w-3.5 h-3.5 animate-spin" />}
                    {activeExperiment.status === 'FAILED' && <XCircle className="w-3.5 h-3.5" />}
                    <span>{activeExperiment.status}</span>
                  </span>
                </div>

                {/* Day 6 / Day 7 Scope Clarification Box */}
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                  <div className="flex items-center space-x-1 text-slate-300 font-semibold">
                    <Info className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Preliminary Sanity Validation Metric</span>
                  </div>
                  <p>
                    The score below ({isRegression ? 'R² Coefficient of Determination' : 'Accuracy Score'}) validates the fit $\to$ predict roundtrip across temporary CV folds. Full multi-metric evaluation (MAE/RMSE/F1/ROC-AUC/Confusion Matrix) and model selection will be established on Day 7.
                  </p>
                </div>
              </div>

              {/* Models Comparison Cards */}
              <div className="space-y-3">
                <div className="text-xs uppercase tracking-wider font-bold text-slate-400">
                  Trained Algorithm Outcomes ({activeExperiment.trained_models?.length || 0})
                </div>

                {activeExperiment.status === 'RUNNING' && (!activeExperiment.trained_models || activeExperiment.trained_models.length === 0) ? (
                  <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-2">
                    <RotateCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
                    <p className="text-xs font-semibold text-white">Fitting ColumnTransformers, Feature Selectors, and Estimators...</p>
                    <p className="text-[11px] text-slate-400">Iterating across {activeExperiment.fold_count} cross-validation folds.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3">
                    {activeExperiment.trained_models?.map((model) => {
                      const isModelCompleted = model.status === 'COMPLETED';
                      return (
                        <div
                          key={model.id}
                          className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm flex items-center justify-between hover:border-slate-700 transition-colors"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-sm text-white">
                                {model.algorithm_name}
                              </span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  isModelCompleted
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                }`}
                              >
                                {model.status}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              Hyperparameters: {JSON.stringify(model.hyperparameters) === '{}' ? 'scikit-learn defaults' : JSON.stringify(model.hyperparameters)}
                            </div>
                            {model.error_message && (
                              <p className="text-[11px] text-rose-400 mt-1">
                                Error: {model.error_message}
                              </p>
                            )}
                          </div>

                          <div className="text-right pl-4">
                            <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                              Quick CV Score ({isRegression ? 'R²' : 'Accuracy'})
                            </div>
                            <div className="text-lg font-extrabold text-white font-mono">
                              {model.quick_cv_score !== null && model.quick_cv_score !== undefined ? (
                                <span className={model.quick_cv_score >= 0 ? 'text-indigo-400' : 'text-rose-400'}>
                                  {Number(model.quick_cv_score).toFixed(5)}
                                </span>
                              ) : (
                                <span className="text-slate-500 text-xs italic">N/A</span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
