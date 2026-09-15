import React from 'react';
import { SlidersHorizontal, Sparkles, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

interface FeatureConfigPanelProps {
  nSplits: number;
  onNSplitsChange: (n: number) => void;
  cvStrategy: string;
  onCvStrategyChange: (strategy: string) => void;
  seed: number;
  onSeedChange: (seed: number) => void;
  method: string;
  onMethodChange: (method: string) => void;
  onRun: () => void;
  running: boolean;
  disabled?: boolean;
}

export const FeatureConfigPanel: React.FC<FeatureConfigPanelProps> = ({
  nSplits,
  onNSplitsChange,
  cvStrategy,
  onCvStrategyChange,
  seed,
  onSeedChange,
  method,
  onMethodChange,
  onRun,
  running,
  disabled = false,
}) => {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-5 shadow-sm">
      <div className="flex items-center space-x-2 border-b border-[var(--color-border)] pb-3.5">
        <SlidersHorizontal className="w-5 h-5 text-[var(--color-accent)]" />
        <h2 className="text-sm font-bold text-[var(--color-text)]">Ensemble Feature Selection</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Method */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--color-text-muted)]">
            Selection Method
          </label>
          <select
            value={method}
            onChange={(e) => onMethodChange(e.target.value)}
            disabled={running || disabled}
            className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="RANK_AGGREGATION">Cross-Fold Rank Aggregation</option>
            <option value="IMPORTANCE_THRESHOLD">Mean Importance Cutoff</option>
            <option value="FORWARD_STABILITY">Forward Stability Elimination</option>
          </select>
        </div>

        {/* CV Strategy */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--color-text-muted)]">
            Partitioning Strategy
          </label>
          <select
            value={cvStrategy}
            onChange={(e) => onCvStrategyChange(e.target.value)}
            disabled={running || disabled}
            className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="AUTO">Auto Detect (Task-Aware)</option>
            <option value="STRATIFIED_K_FOLD">Stratified K-Fold (Classification)</option>
            <option value="K_FOLD">Standard K-Fold (Regression)</option>
          </select>
        </div>

        {/* Folds */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--color-text-muted)]">
            Evaluation Folds (K)
          </label>
          <select
            value={nSplits}
            onChange={(e) => onNSplitsChange(Number(e.target.value))}
            disabled={running || disabled}
            className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value={3}>3 Folds (Fast)</option>
            <option value={5}>5 Folds (Standard)</option>
            <option value={10}>10 Folds (High Rigor)</option>
          </select>
        </div>

        {/* Seed */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-[var(--color-text-muted)]">
            Random Seed
          </label>
          <input
            type="number"
            value={seed}
            onChange={(e) => onSeedChange(Number(e.target.value))}
            disabled={running || disabled}
            className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] font-mono focus:outline-none focus:border-[var(--color-accent)]"
          />
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <Button
          type="button"
          variant="primary"
          size="md"
          onClick={onRun}
          disabled={running || disabled}
          isLoading={running}
          className="rounded-full shadow-md"
        >
          {running ? (
            <span>Computing Fold Importances...</span>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-1.5" />
              <span>Run Ensemble Selection</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
