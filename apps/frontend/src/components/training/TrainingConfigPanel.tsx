import React from 'react';
import { Cpu, Play, RotateCw, Shuffle } from 'lucide-react';
import { Button } from '../ui/Button';

export interface AlgorithmOption {
  id: string;
  name: string;
  tag: string;
  description: string;
}

export const REGRESSION_ALGORITHMS: AlgorithmOption[] = [
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

export const CLASSIFICATION_ALGORITHMS: AlgorithmOption[] = [
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

interface TrainingConfigPanelProps {
  taskType: 'REGRESSION' | 'CLASSIFICATION' | string;
  selectedAlgorithms: string[];
  onToggleAlgorithm: (id: string) => void;
  onSelectAllAlgorithms: () => void;
  selectionMetric: string;
  onSelectionMetricChange: (metric: string) => void;
  folds: number;
  onFoldsChange: (folds: number) => void;
  seed: string;
  onSeedChange: (seed: string) => void;
  onRandomizeSeed: () => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
  pollingActive: boolean;
}

export const TrainingConfigPanel: React.FC<TrainingConfigPanelProps> = ({
  taskType,
  selectedAlgorithms,
  onToggleAlgorithm,
  onSelectAllAlgorithms,
  selectionMetric,
  onSelectionMetricChange,
  folds,
  onFoldsChange,
  seed,
  onSeedChange,
  onRandomizeSeed,
  onSubmit,
  loading,
  pollingActive,
}) => {
  const isRegression = taskType === 'REGRESSION';
  const availableAlgs = isRegression ? REGRESSION_ALGORITHMS : CLASSIFICATION_ALGORITHMS;

  return (
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

      <form onSubmit={onSubmit} className="space-y-5">
        {/* Algorithm Checklist */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-[var(--color-text)]">
              Target Algorithms ({availableAlgs.length})
            </label>
            <button
              type="button"
              onClick={onSelectAllAlgorithms}
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
                  onClick={() => onToggleAlgorithm(alg.id)}
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
            onChange={(e) => onSelectionMetricChange(e.target.value)}
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
              onChange={(e) => onFoldsChange(Number(e.target.value))}
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
                onClick={onRandomizeSeed}
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
              onChange={(e) => onSeedChange(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] font-mono focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          disabled={loading || pollingActive || selectedAlgorithms.length === 0}
          className="rounded-full shadow-md"
        >
          {pollingActive ? (
            <>
              <RotateCw className="w-4 h-4 animate-spin mr-2" />
              <span>Evaluating Cross-Validation Folds...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current mr-2" />
              <span>Start Model Training & Selection</span>
            </>
          )}
        </Button>
      </form>
    </div>
  );
};
