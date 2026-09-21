import React from 'react';
import { X } from 'lucide-react';

export interface MetricItem {
  id: string;
  metric_name: string;
  split: string;
  fold_index?: number | null;
  metric_value?: number | null;
  metric_json?: any;
}

interface ModelMetricsModalProps {
  isOpen: boolean;
  metrics: MetricItem[] | null;
  onClose: () => void;
}

export const ModelMetricsModal: React.FC<ModelMetricsModalProps> = ({ isOpen, metrics, onClose }) => {
  if (!isOpen || !metrics) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-[var(--color-text)]">Full Metric Breakdown</h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              TRAIN, VALIDATION (per fold), CV_MEAN, and LOCKED_TEST records
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6">
          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                <tr>
                  <th className="px-4 py-2.5">Metric</th>
                  <th className="px-4 py-2.5">Split</th>
                  <th className="px-4 py-2.5">Fold</th>
                  <th className="px-4 py-2.5 text-right">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)] font-mono text-[11px]">
                {metrics.map((m) => (
                  <tr key={m.id} className="hover:bg-[var(--color-surface-hover)]">
                    <td className="px-4 py-2 text-[var(--color-text)] font-semibold">{m.metric_name}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          m.split === 'LOCKED_TEST'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : m.split === 'CV_MEAN'
                            ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]'
                            : m.split === 'TEST_REUSED_DIAGNOSTIC'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                        }`}
                      >
                        {m.split}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-[var(--color-text-muted)]">
                      {m.fold_index !== null && m.fold_index !== undefined ? `Fold ${m.fold_index + 1}` : 'Overall'}
                    </td>
                    <td className="px-4 py-2 text-right text-emerald-400 font-bold">
                      {m.metric_value !== null && m.metric_value !== undefined ? (
                        Number(m.metric_value).toFixed(5)
                      ) : (
                        m.metric_json ? JSON.stringify(m.metric_json) : 'null'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
