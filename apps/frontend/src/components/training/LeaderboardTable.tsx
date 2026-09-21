import React from 'react';
import { Eye, BrainCircuit, FileText, Download, ShieldCheck, Activity } from 'lucide-react';
import { FitDiagnosisBadge } from './FitDiagnosisBadge';
import { Button } from '../ui/Button';

export interface LeaderboardModel {
  id: string;
  algorithm_name: string;
  is_winner?: boolean;
  status?: string;
  error_message?: string;
  primary_metric_value?: number | null;
  secondary_metric_value?: number | null;
  fit_diagnosis?: string | null;
  decision_threshold?: number | null;
  model_selection_score?: number | null;
  artifact_path?: string | null;
  hyperparameters?: Record<string, any>;
}

interface LeaderboardTableProps {
  models: LeaderboardModel[];
  selectionMetric: string;
  selectionDirection: string;
  isRegression: boolean;
  onOpenMetrics: (modelId: string) => void;
  onOpenExplain: (model: LeaderboardModel) => void;
  onOpenPassport: (modelId: string) => void;
  onDownloadArtifact: (modelId: string, algorithmName: string) => void;
  onOpenDeploymentGate: (model: LeaderboardModel) => void;
  onOpenHealthReport: () => void;
  onOpenLineage: () => void;
}

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({
  models,
  selectionMetric,
  selectionDirection,
  isRegression,
  onOpenMetrics,
  onOpenExplain,
  onOpenPassport,
  onDownloadArtifact,
  onOpenDeploymentGate,
  onOpenHealthReport,
  onOpenLineage,
}) => {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3.5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-[var(--color-text)]">
              Authoritative Model Leaderboard
            </h3>
            <span className="px-3 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-[var(--color-accent)]">
              Ranked strictly by {selectionMetric.toUpperCase()} ({selectionDirection})
            </span>
          </div>
          <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
            Composite score shown for comparison only — never alters rank order.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onOpenHealthReport}
            className="rounded-full text-xs font-semibold"
            title="Inspect Experiment Health Report"
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400 mr-1.5" />
            <span>Health Report</span>
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onOpenLineage}
            className="rounded-full text-xs font-semibold text-[var(--color-accent)] border-[var(--color-accent-border)] bg-[var(--color-accent-soft)]"
            title="Inspect full experiment lineage, software environment, and artifact checksums"
          >
            <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
            <span>Lineage & Integrity</span>
          </Button>
          <div className="text-right text-[11px] text-[var(--color-text-muted)] font-mono pl-1">
            {models.length} models
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-4 py-3">Rank</th>
              <th className="px-4 py-3">Algorithm</th>
              <th className="px-4 py-3 bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold border-x border-[var(--color-border)]">
                Primary: {selectionMetric.toUpperCase()}
              </th>
              <th className="px-4 py-3">
                {isRegression ? 'Secondary: R²' : 'Secondary: ROC-AUC'}
              </th>
              <th className="px-4 py-3">Fit Diagnosis</th>
              <th className="px-4 py-3 text-[var(--color-text-muted)]">
                Composite Indicator
                <div className="text-[9px] lowercase font-normal opacity-70">(not used for ranking)</div>
              </th>
              <th className="px-4 py-3 text-right">Details & Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {models.map((model, idx) => {
              const isWin = Boolean(model.is_winner);
              const hasArtifact = Boolean(model.artifact_path);
              const isActionable = isWin || hasArtifact;

              return (
                <tr
                  key={model.id}
                  className={`transition-colors ${
                    isWin
                      ? 'bg-[var(--color-accent-soft)]/20'
                      : 'hover:bg-[var(--color-surface-hover)]'
                  }`}
                >
                  <td className="px-4 py-3 font-mono">
                    {isWin ? (
                      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold text-xs border border-[var(--color-accent-border)]">
                        1
                      </span>
                    ) : (
                      <span className="text-[var(--color-text-muted)] font-semibold pl-1.5">{idx + 1}</span>
                    )}
                  </td>

                  <td className="px-4 py-3">
                    <div className="font-bold text-[var(--color-text)] flex items-center space-x-1.5">
                      <span>{model.algorithm_name}</span>
                      {isWin && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] uppercase">
                          Winner
                        </span>
                      )}
                      {model.decision_threshold !== null && model.decision_threshold !== undefined && (
                        <span
                          className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)]"
                          title="Optimized decision threshold"
                        >
                          τ={Number(model.decision_threshold).toFixed(3)}
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-muted)] font-mono truncate max-w-[160px]">
                      {model.status === 'FAILED' ? (
                        <span className="text-rose-400">Failed: {model.error_message}</span>
                      ) : (
                        !model.hyperparameters || JSON.stringify(model.hyperparameters) === '{}'
                          ? 'Default params'
                          : JSON.stringify(model.hyperparameters)
                      )}
                    </div>
                  </td>

                  <td className="px-4 py-3 font-mono font-extrabold bg-[var(--color-accent-soft)]/30 border-x border-[var(--color-border)] text-[var(--color-accent)] text-sm">
                    {model.primary_metric_value !== null && model.primary_metric_value !== undefined ? (
                      Number(model.primary_metric_value).toFixed(5)
                    ) : (
                      <span className="text-[var(--color-text-muted)] text-xs italic font-normal">N/A</span>
                    )}
                  </td>

                  <td className="px-4 py-3 font-mono text-[var(--color-text)]">
                    {model.secondary_metric_value !== null && model.secondary_metric_value !== undefined ? (
                      Number(model.secondary_metric_value).toFixed(5)
                    ) : (
                      <span className="text-[var(--color-text-muted)] italic font-normal">N/A</span>
                    )}
                  </td>

                  <td className="px-4 py-3">
                    <FitDiagnosisBadge diagnosis={model.fit_diagnosis} />
                  </td>

                  <td className="px-4 py-3">
                    {model.model_selection_score !== null && model.model_selection_score !== undefined ? (
                      <div className="space-y-1">
                        <div className="font-mono text-[var(--color-text)] text-xs font-semibold">
                          {Number(model.model_selection_score).toFixed(1)} / 100
                        </div>
                        <div className="w-24 bg-[var(--color-surface-hover)] rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-[var(--color-accent)] h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, Math.max(0, model.model_selection_score))}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-[var(--color-text-muted)] italic">N/A</span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => onOpenMetrics(model.id)}
                        className="px-2.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer border border-[var(--color-border)]"
                        title="View complete cross-validation and fold metric records"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Metrics</span>
                      </button>

                      <button
                        onClick={() => onOpenExplain(model)}
                        disabled={!isActionable}
                        title={
                          !isActionable
                            ? 'This model has no persisted artifact — explainability is only available for the winning model of a completed experiment'
                            : 'Inspect SHAP feature attributions and global/local explanations'
                        }
                        className={`px-2.5 py-1.5 rounded-full text-xs font-semibold transition-colors inline-flex items-center space-x-1 border ${
                          isActionable
                            ? 'bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] border-[var(--color-accent-border)] cursor-pointer'
                            : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border-[var(--color-border)] cursor-not-allowed opacity-50'
                        }`}
                      >
                        <BrainCircuit className="w-3.5 h-3.5" />
                        <span>Explain</span>
                      </button>

                      <button
                        onClick={() => onOpenPassport(model.id)}
                        title="View technical model passport, lineage provenance & governance records"
                        className="px-2.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer"
                      >
                        <FileText className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                        <span>Passport</span>
                      </button>

                      <button
                        onClick={() => onDownloadArtifact(model.id, model.algorithm_name)}
                        disabled={!isActionable}
                        title={
                          !isActionable
                            ? 'Artifact download is only available for persisted models'
                            : 'Download serialized joblib model pipeline artifact'
                        }
                        className={`px-2.5 py-1.5 rounded-full text-xs font-semibold transition-colors inline-flex items-center space-x-1 border ${
                          isActionable
                            ? 'bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border-[var(--color-border)] cursor-pointer'
                            : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border-[var(--color-border)] cursor-not-allowed opacity-50'
                        }`}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Artifact</span>
                      </button>

                      <button
                        onClick={() => onOpenDeploymentGate(model)}
                        disabled={!isActionable}
                        title={
                          !isActionable
                            ? 'Deployment is only available for the winning model with a persisted artifact'
                            : 'Evaluate pre-deployment gate conditions and manage production deployment'
                        }
                        className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all inline-flex items-center space-x-1 ${
                          isActionable
                            ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm cursor-pointer'
                            : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border border-[var(--color-border)] cursor-not-allowed opacity-50'
                        }`}
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>Deploy & Gate</span>
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
