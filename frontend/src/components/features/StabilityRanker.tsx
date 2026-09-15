import React from 'react';
import { Activity, Award, ShieldCheck, Flame, Info } from 'lucide-react';

interface StabilityRankerProps {
  totalFeatures: number;
  selectedFeaturesCount: number;
  selectionMethod: string;
  foldCount?: number;
  averageStabilityScore?: number | null;
  onOpenFoldModal?: () => void;
}

export const StabilityRanker: React.FC<StabilityRankerProps> = ({
  totalFeatures,
  selectedFeaturesCount,
  selectionMethod,
  foldCount = 5,
  averageStabilityScore,
  onOpenFoldModal,
}) => {
  const percentage = totalFeatures > 0 ? ((selectedFeaturesCount / totalFeatures) * 100).toFixed(1) : '0.0';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
      {/* Card 1: Active Features */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-col justify-between shadow-xs min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Active Features</span>
          <Award className="w-4 h-4 text-[var(--color-accent)] shrink-0 ml-1" />
        </div>
        <div className="my-1.5 flex items-baseline gap-1.5 min-w-0">
          <span className="text-2xl font-black text-[var(--color-text)] font-mono leading-none">
            {selectedFeaturesCount}
          </span>
          <span className="text-xs text-[var(--color-text-muted)] font-mono truncate">
            / {totalFeatures}
          </span>
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] truncate">
          {percentage}% space retained
        </div>
      </div>

      {/* Card 2: Ensemble Methodology */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-col justify-between shadow-xs min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Ensemble Methodology</span>
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 ml-1" />
        </div>
        <div className="my-1.5 text-base font-bold text-[var(--color-text)] truncate leading-tight">
          {selectionMethod === 'RANK_AGGREGATION' ? 'Rank Aggregation' : selectionMethod || 'Rank Aggregation'}
        </div>
        <div className="text-[11px] text-emerald-400 font-medium truncate">
          Fold-isolated importance
        </div>
      </div>

      {/* Card 3: Evaluation Folds */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-col justify-between shadow-xs min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Evaluation Strategy</span>
          <Activity className="w-4 h-4 text-indigo-400 shrink-0 ml-1" />
        </div>
        <div className="my-1.5 flex items-baseline gap-1.5 min-w-0">
          <span className="text-2xl font-black text-[var(--color-text)] font-mono leading-none">
            {foldCount}
          </span>
          <span className="text-xs text-[var(--color-text-muted)] font-normal truncate">
            Folds (Stratified)
          </span>
        </div>
        <div>
          {onOpenFoldModal ? (
            <button
              type="button"
              onClick={onOpenFoldModal}
              className="text-[11px] text-[var(--color-accent)] hover:underline font-semibold cursor-pointer truncate block text-left"
            >
              Inspect Fold Matrices →
            </button>
          ) : (
            <span className="text-[11px] text-[var(--color-text-muted)] truncate block">
              Cross-validation
            </span>
          )}
        </div>
      </div>

      {/* Card 4: Stability Score */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex flex-col justify-between shadow-xs min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Stability Score</span>
          <Flame className="w-4 h-4 text-amber-400 shrink-0 ml-1" />
        </div>
        <div className="my-1.5 text-2xl font-black text-[var(--color-text)] font-mono leading-none truncate">
          {averageStabilityScore !== null && averageStabilityScore !== undefined
            ? Number(averageStabilityScore).toFixed(3)
            : totalFeatures > 0
            ? '1.000'
            : '—'}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] flex items-center space-x-1 truncate">
          <Info className="w-3 h-3 text-[var(--color-text-muted)] shrink-0" />
          <span className="truncate">Cross-fold consistency</span>
        </div>
      </div>
    </div>
  );
};
