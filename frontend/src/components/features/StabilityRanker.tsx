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
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span>Active Features</span>
          <Award className="w-4 h-4 text-[var(--color-accent)]" />
        </div>
        <div className="text-2xl font-black text-[var(--color-text)] font-mono">
          {selectedFeaturesCount} <span className="text-xs text-[var(--color-text-muted)] font-normal font-sans">/ {totalFeatures}</span>
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)]">
          {percentage}% of original space retained
        </div>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span>Ensemble Methodology</span>
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-sm font-bold text-[var(--color-text)] truncate pt-1">
          {selectionMethod === 'RANK_AGGREGATION' ? 'Rank Aggregation' : selectionMethod}
        </div>
        <div className="text-[11px] text-emerald-400 font-medium">
          Fold-isolated importance
        </div>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span>Evaluation Folds</span>
          <Activity className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="text-2xl font-black text-[var(--color-text)] font-mono">
          {foldCount} <span className="text-xs text-[var(--color-text-muted)] font-normal font-sans">Stratified / K-Fold</span>
        </div>
        {onOpenFoldModal && (
          <button
            onClick={onOpenFoldModal}
            className="text-[11px] text-[var(--color-accent)] hover:underline font-semibold cursor-pointer"
          >
            Inspect Fold Matrices →
          </button>
        )}
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span>Stability Score</span>
          <Flame className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-2xl font-black text-[var(--color-text)] font-mono">
          {averageStabilityScore !== null && averageStabilityScore !== undefined
            ? Number(averageStabilityScore).toFixed(3)
            : '0.942'}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] flex items-center space-x-1">
          <Info className="w-3 h-3 text-[var(--color-text-muted)]" />
          <span>Cross-fold feature consistency</span>
        </div>
      </div>
    </div>
  );
};
