import React from 'react';

export interface ExperimentHistoryItem {
  id: string;
  created_at: string;
  fold_count?: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | string;
}

interface ExperimentHistoryListProps {
  experiments: ExperimentHistoryItem[];
  activeExperimentId?: string;
  onSelectExperiment: (experiment: ExperimentHistoryItem) => void;
}

export const ExperimentHistoryList: React.FC<ExperimentHistoryListProps> = ({
  experiments,
  activeExperimentId,
  onSelectExperiment,
}) => {
  if (experiments.length === 0) return null;

  return (
    <div className="space-y-2 border-t border-[var(--color-border)] pt-4">
      <div className="text-[11px] uppercase tracking-wider font-bold text-[var(--color-text-muted)]">
        Experiment Runs ({experiments.length})
      </div>
      <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
        {experiments.map((exp) => (
          <button
            key={exp.id}
            onClick={() => onSelectExperiment(exp)}
            className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
              activeExperimentId === exp.id
                ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] text-[var(--color-text)] font-bold'
                : 'bg-[var(--color-surface-card)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]'
            }`}
          >
            <div className="truncate font-mono text-[11px]">
              {new Date(exp.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {exp.fold_count || 5} folds
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
  );
};
