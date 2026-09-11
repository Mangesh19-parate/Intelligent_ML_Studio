import React from 'react';
import { Lightbulb, AlertCircle, ArrowRight, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const RecommendationsList = ({ recommendations = [] }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 text-center text-[var(--color-text-muted)] text-sm shadow-sm">
        <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/80" />
        No critical data quality risks detected. Dataset satisfies baseline health checks.
      </div>
    );
  }

  const getConfidenceBadge = (confidence) => {
    switch (confidence) {
      case 'HIGH':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-mono">HIGH CONFIDENCE</span>;
      case 'MEDIUM':
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-mono">MEDIUM CONFIDENCE</span>;
      default:
        return <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)] font-mono">LOW CONFIDENCE</span>;
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
          {recommendations.length} Actionable Items
        </span>
      </div>

      <div className="space-y-4">
        {recommendations.map((rec, idx) => (
          <div
            key={rec.id || idx}
            className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl p-4 transition-all duration-200 hover:border-[var(--color-accent)]/40 shadow-2xs"
          >
            {/* Header: Finding & Confidence */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-[var(--color-border)]">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
                <h5 className="text-sm font-bold text-[var(--color-text)]">{rec.finding}</h5>
              </div>
              <div>{getConfidenceBadge(rec.confidence)}</div>
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
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-500 flex-shrink-0 mt-0.5" />
                <span>
                  <strong className="font-bold">Risk / Tradeoff:</strong> {rec.risk_note}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
