import React, { useState, useEffect } from 'react';
import { Lightbulb, ArrowRight, ShieldAlert, CheckCircle2, XCircle, Check, RotateCcw } from 'lucide-react';
import { projectApi } from '../api/client';
import { TransformationRecommendation } from '../types/api';

export interface RecommendationsListProps {
  recommendations?: TransformationRecommendation[];
  projectId?: string | null;
  onStatusChange?: ((recId: string, newStatus: string) => void) | null;
}

export const RecommendationsList: React.FC<RecommendationsListProps> = ({
  recommendations = [],
  projectId = null,
  onStatusChange = null,
}) => {
  const [localRecs, setLocalRecs] = useState<TransformationRecommendation[]>(recommendations);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  // Sync state if prop changes
  useEffect(() => {
    setLocalRecs(recommendations);
  }, [recommendations]);

  if (!localRecs || localRecs.length === 0) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 text-center text-[var(--color-text-muted)] text-sm shadow-sm">
        <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/80" />
        No critical data quality risks detected. Dataset satisfies baseline health checks.
      </div>
    );
  }

  const handleStatusUpdate = async (recId: string, newStatus: string): Promise<void> => {
    if (!projectId || !recId) return;
    setUpdatingId(recId);
    try {
      await projectApi.updateRecommendationStatus(projectId, recId, newStatus);
      setLocalRecs((prev) =>
        prev.map((r) => (r.id === recId ? { ...r, status: newStatus as TransformationRecommendation['status'] } : r))
      );
      if (onStatusChange) onStatusChange(recId, newStatus);
    } catch (err) {
      console.error('Failed to update recommendation status:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const getConfidenceBadge = (confidence?: string): React.ReactNode => {
    switch (confidence) {
      case 'HIGH':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-mono">HIGH CONFIDENCE</span>;
      case 'MEDIUM':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-mono">MEDIUM CONFIDENCE</span>;
      default:
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)] font-mono">LOW CONFIDENCE</span>;
    }
  };

  const getStatusBadge = (status?: string): React.ReactNode => {
    switch (status) {
      case 'APPLIED':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-mono flex items-center gap-1"><Check className="w-3 h-3" /> APPLIED</span>;
      case 'IGNORED':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-zinc-500/10 text-zinc-500 border border-zinc-500/20 font-mono flex items-center gap-1"><XCircle className="w-3 h-3" /> IGNORED</span>;
      default:
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-mono">SUGGESTED</span>;
    }
  };

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm transition-colors">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-500">
            <Lightbulb className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-bold text-[var(--color-text)]">Diagnostics & Transformation Recommendations</h4>
            <p className="text-xs text-[var(--color-text-muted)]">
              Traceable prescriptive actions generated from DQI diagnostics (SRS §2.16)
            </p>
          </div>
        </div>
        <span className="text-xs font-mono px-3 py-1 rounded-full bg-[var(--color-surface-hover)] text-[var(--color-text)] border border-[var(--color-border)] font-bold">
          {localRecs.length} Actionable Items
        </span>
      </div>

      <div className="space-y-4">
        {localRecs.map((rec, idx) => (
          <div
            key={rec.id || idx}
            className={`bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl p-4 transition-all duration-200 hover:border-[var(--color-accent)]/40 shadow-2xs ${
              rec.status === 'IGNORED' ? 'opacity-60 bg-[var(--color-surface-hover)]/30' : ''
            }`}
          >
            {/* Header: Finding & Badges */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-[var(--color-border)]">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${rec.status === 'APPLIED' ? 'bg-blue-500' : rec.status === 'IGNORED' ? 'bg-zinc-400' : 'bg-amber-500'} shrink-0`} />
                <h5 className="text-sm font-bold text-[var(--color-text)]">{rec.finding}</h5>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(rec.status)}
                {getConfidenceBadge(rec.confidence)}
              </div>
            </div>

            {/* Grid for Evidence & Recommended Action */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-3 text-xs">
              <div className="bg-[var(--color-surface-hover)] p-3 rounded-xl border border-[var(--color-border)]">
                <span className="text-[var(--color-text-muted)] uppercase font-mono text-[10px] tracking-wider block mb-1 font-bold">
                  Empirical Evidence
                </span>
                <p className="text-[var(--color-text)] leading-relaxed font-sans">{rec.evidence}</p>
              </div>

              <div className="bg-[var(--color-accent-soft)] p-3 rounded-xl border border-[var(--color-accent)]/20">
                <span className="text-[var(--color-accent)] uppercase font-mono text-[10px] tracking-wider block mb-1 flex items-center gap-1 font-bold">
                  <ArrowRight className="w-3 h-3" /> Recommended Action (Day 4+)
                </span>
                <p className="text-[var(--color-text)] leading-relaxed font-medium">{rec.recommended_action}</p>
              </div>
            </div>

            {/* Risk Note */}
            {rec.risk_note && (
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400 mb-3">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-500 shrink-0 mt-0.5" />
                <span>
                  <strong className="font-bold">Risk / Tradeoff:</strong> {rec.risk_note}
                </span>
              </div>
            )}

            {/* Interactive Decision Actions */}
            {projectId && rec.id && (
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--color-border)] text-xs">
                {rec.status !== 'APPLIED' && (
                  <button
                    onClick={() => handleStatusUpdate(rec.id, 'APPLIED')}
                    disabled={updatingId === rec.id}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium flex items-center gap-1 transition-colors disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5" /> Apply Action
                  </button>
                )}
                {rec.status !== 'IGNORED' && (
                  <button
                    onClick={() => handleStatusUpdate(rec.id, 'IGNORED')}
                    disabled={updatingId === rec.id}
                    className="px-3 py-1.5 rounded-lg bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface-card)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] font-medium flex items-center gap-1 border border-[var(--color-border)] transition-colors disabled:opacity-50"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Ignore / Dismiss
                  </button>
                )}
                {rec.status !== 'SUGGESTED' && (
                  <button
                    onClick={() => handleStatusUpdate(rec.id, 'SUGGESTED')}
                    disabled={updatingId === rec.id}
                    className="px-2.5 py-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] font-medium flex items-center gap-1 text-[11px] transition-colors disabled:opacity-50"
                    title="Reset to Suggested"
                  >
                    <RotateCcw className="w-3 h-3" /> Reset
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
