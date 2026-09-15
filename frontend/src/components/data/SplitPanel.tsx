import React from 'react';
import { Lock, Split, Shuffle, Check, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/Button';

export interface SplitSummaryData {
  id?: string;
  split_type?: string;
  split_seed?: number;
  dev_row_count?: number;
  locked_test_row_count?: number;
  is_locked?: boolean;
}

interface SplitPanelProps {
  splitSummary: SplitSummaryData | null;
  totalRows: number;
  lockedTestPct: number;
  onLockedTestPctChange: (pct: number) => void;
  splitSeed: string;
  onSplitSeedChange: (seed: string) => void;
  onRandomizeSeed: () => void;
  onCreateSplit: () => void;
  creatingSplit: boolean;
  disabled?: boolean;
}

export const SplitPanel: React.FC<SplitPanelProps> = ({
  splitSummary,
  totalRows,
  lockedTestPct,
  onLockedTestPctChange,
  splitSeed,
  onSplitSeedChange,
  onRandomizeSeed,
  onCreateSplit,
  creatingSplit,
  disabled = false,
}) => {
  const isSplitCreated = Boolean(splitSummary);

  const devRows = isSplitCreated
    ? splitSummary?.dev_row_count ?? Math.round(totalRows * ((100 - lockedTestPct) / 100))
    : Math.round(totalRows * ((100 - lockedTestPct) / 100));

  const testRows = isSplitCreated
    ? splitSummary?.locked_test_row_count ?? Math.round(totalRows * (lockedTestPct / 100))
    : Math.round(totalRows * (lockedTestPct / 100));

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3.5">
        <div className="flex items-center space-x-2">
          <Split className="w-5 h-5 text-[var(--color-accent)]" />
          <h2 className="text-sm font-bold text-[var(--color-text)]">
            Leakage Partitioning & Locked Test Boundary
          </h2>
        </div>
        {isSplitCreated && (
          <span className="inline-flex items-center space-x-1.5 px-3 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Lock className="w-3 h-3" />
            <span>Partition Locked & Sealed</span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Split Configuration Form */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-bold text-[var(--color-text)]">
              <span>Locked Test Partition Ratio</span>
              <span className="text-[var(--color-accent)] font-mono">{lockedTestPct}% Test</span>
            </div>
            <input
              type="range"
              min="10"
              max="40"
              step="5"
              value={lockedTestPct}
              onChange={(e) => onLockedTestPctChange(Number(e.target.value))}
              disabled={isSplitCreated || creatingSplit || disabled}
              className="w-full h-1.5 bg-[var(--color-surface-hover)] rounded-lg appearance-none cursor-pointer accent-[var(--color-accent)] disabled:opacity-50"
            />
            <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] font-mono">
              <span>10% (Minimal)</span>
              <span>20% (Standard)</span>
              <span>40% (Large)</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label className="font-bold text-[var(--color-text)]">Deterministic Split Seed</label>
              {!isSplitCreated && (
                <button
                  type="button"
                  onClick={onRandomizeSeed}
                  disabled={creatingSplit || disabled}
                  className="text-[10px] text-[var(--color-accent)] hover:underline flex items-center space-x-1 cursor-pointer"
                >
                  <Shuffle className="w-2.5 h-2.5" />
                  <span>Rand</span>
                </button>
              )}
            </div>
            <input
              type="number"
              value={splitSeed}
              onChange={(e) => onSplitSeedChange(e.target.value)}
              disabled={isSplitCreated || creatingSplit || disabled}
              placeholder="e.g. 42"
              className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] font-mono focus:outline-none focus:border-[var(--color-accent)] disabled:opacity-50"
            />
          </div>

          {!isSplitCreated && (
            <Button
              type="button"
              variant="primary"
              size="md"
              onClick={onCreateSplit}
              disabled={creatingSplit || disabled || totalRows === 0}
              isLoading={creatingSplit}
              fullWidth
              className="rounded-full shadow-md"
            >
              <Lock className="w-4 h-4 mr-2" />
              <span>Lock Partition Boundary</span>
            </Button>
          )}
        </div>

        {/* Right: Partition Breakdown Visual */}
        <div className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
          <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">
            Partition Volume Distribution
          </h3>

          <div className="space-y-3">
            {/* Development Partition */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[var(--color-text)]">Development Partition (100 - {lockedTestPct}%)</span>
                <span className="font-mono text-emerald-400 font-bold">{Number(devRows).toLocaleString()} rows</span>
              </div>
              <div className="w-full bg-[var(--color-surface-hover)] rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-2 rounded-full"
                  style={{ width: `${100 - lockedTestPct}%` }}
                />
              </div>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                Used for EDA, feature selection, transformation fitting, and cross-validation training.
              </p>
            </div>

            {/* Locked Test Partition */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-rose-400 flex items-center space-x-1">
                  <Lock className="w-3 h-3" />
                  <span>Locked Test Partition ({lockedTestPct}%)</span>
                </span>
                <span className="font-mono text-rose-400 font-bold">{Number(testRows).toLocaleString()} rows</span>
              </div>
              <div className="w-full bg-[var(--color-surface-hover)] rounded-full h-2 overflow-hidden">
                <div
                  className="bg-rose-500 h-2 rounded-full"
                  style={{ width: `${lockedTestPct}%` }}
                />
              </div>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                Isolated behind cryptographic gate. Evaluated exactly once during final model promotion.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
