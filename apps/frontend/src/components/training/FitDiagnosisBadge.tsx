import React from 'react';

export type FitDiagnosis = 'GOOD_FIT' | 'POTENTIAL_OVERFIT' | 'POTENTIAL_UNDERFIT_WEAK_SIGNAL' | 'LOW_DATA' | string | null;

interface FitDiagnosisBadgeProps {
  diagnosis?: FitDiagnosis;
  className?: string;
}

export const FitDiagnosisBadge: React.FC<FitDiagnosisBadgeProps> = ({ diagnosis, className = '' }) => {
  if (!diagnosis) {
    return <span className={`text-[var(--color-text-muted)] text-[10px] ${className}`}>N/A</span>;
  }

  if (diagnosis === 'GOOD_FIT') {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 ${className}`}
        title="Generalization gap is within tolerance and model significantly outperforms baseline"
      >
        ✓ Good Fit
      </span>
    );
  }

  if (diagnosis === 'POTENTIAL_OVERFIT') {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/25 text-amber-400 ${className}`}
        title="High training score but lower CV validation score indicates generalization gap"
      >
        ⚠ Overfit Gap
      </span>
    );
  }

  if (diagnosis === 'POTENTIAL_UNDERFIT_WEAK_SIGNAL') {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 border border-rose-500/25 text-rose-400 ${className}`}
        title="CV validation performance is near naive baseline — weak predictive signal detected"
      >
        ⚠ Weak Signal
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-muted)] ${className}`}
      title="Validation sample count < 20 — insufficient data for reliable diagnosis"
    >
      ℹ Low Data (&lt;20)
    </span>
  );
};
