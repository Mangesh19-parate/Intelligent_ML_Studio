import React from 'react';
import { Trophy, Lock, Check } from 'lucide-react';
import { FitDiagnosisBadge } from './FitDiagnosisBadge';

export interface WinningModelData {
  id: string;
  algorithm_name: string;
  is_winner?: boolean;
  primary_metric_value?: number | null;
  secondary_metric_value?: number | null;
  fit_diagnosis?: string | null;
  decision_threshold?: number | null;
  locked_test_score?: number | null;
  artifact_path?: string | null;
  hyperparameters?: Record<string, any>;
}

export interface LeaderboardSummary {
  selection_metric: string;
  selection_direction: string;
  locked_test_consumed: boolean;
  models: WinningModelData[];
}

interface WinnerCalloutCardProps {
  winningModel: WinningModelData;
  leaderboard: LeaderboardSummary;
  onDiagnosticRerun: () => void;
  rerunningDiagnostic: boolean;
}

export const WinnerCalloutCard: React.FC<WinnerCalloutCardProps> = ({
  winningModel,
  leaderboard,
  onDiagnosticRerun,
  rerunningDiagnostic,
}) => {
  return (
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
                {winningModel.primary_metric_value !== null && winningModel.primary_metric_value !== undefined
                  ? Number(winningModel.primary_metric_value).toFixed(5)
                  : 'N/A'}
              </strong>
            </span>
            <span>•</span>
            <div className="flex items-center space-x-1">
              <span>Fit:</span>
              <FitDiagnosisBadge diagnosis={winningModel.fit_diagnosis} />
            </div>
            {winningModel.decision_threshold !== null && winningModel.decision_threshold !== undefined && (
              <>
                <span>•</span>
                <span
                  className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]"
                  title="Binary classification decision threshold optimized on out-of-fold predictions"
                >
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
                {winningModel.locked_test_score !== null && winningModel.locked_test_score !== undefined
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
                onClick={onDiagnosticRerun}
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
  );
};
