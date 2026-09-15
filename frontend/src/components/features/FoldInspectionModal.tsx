import React, { useState } from 'react';
import { X, Layers } from 'lucide-react';

interface FoldData {
  folds: Array<{
    fold_index: number;
    features: Array<{
      column_name: string;
      importance_score: number;
      rank: number;
    }>;
  }>;
}

interface FoldInspectionModalProps {
  isOpen: boolean;
  foldData: FoldData | null;
  onClose: () => void;
}

export const FoldInspectionModal: React.FC<FoldInspectionModalProps> = ({
  isOpen,
  foldData,
  onClose,
}) => {
  const [activeFoldTab, setActiveFoldTab] = useState(0);

  if (!isOpen || !foldData || !foldData.folds || foldData.folds.length === 0) return null;

  const currentFold = foldData.folds[activeFoldTab] || foldData.folds[0];

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-[var(--color-text)] flex items-center space-x-2">
              <Layers className="w-5 h-5 text-[var(--color-accent)]" />
              <span>Cross-Validation Fold Details</span>
            </h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              Per-fold feature importances computed strictly within training splits
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Fold Tabs */}
        <div className="flex border-b border-[var(--color-border)] bg-[var(--color-surface-card)] px-5 pt-3 overflow-x-auto space-x-2">
          {foldData.folds.map((f, idx) => (
            <button
              key={f.fold_index}
              onClick={() => setActiveFoldTab(idx)}
              className={`px-4 py-2 text-xs font-bold rounded-t-xl transition-all border-t border-x cursor-pointer ${
                activeFoldTab === idx
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] border-[var(--color-border)] border-b-transparent'
                  : 'bg-transparent text-[var(--color-text-muted)] border-transparent hover:text-[var(--color-text)]'
              }`}
            >
              Fold {f.fold_index + 1}
            </button>
          ))}
        </div>

        <div className="p-6 overflow-y-auto space-y-4">
          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                <tr>
                  <th className="px-4 py-2.5">Rank</th>
                  <th className="px-4 py-2.5">Feature Name</th>
                  <th className="px-4 py-2.5 text-right">Fold Importance Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)] font-mono text-[11px]">
                {currentFold.features.map((feat) => (
                  <tr key={feat.column_name} className="hover:bg-[var(--color-surface-hover)]">
                    <td className="px-4 py-2 text-[var(--color-text-muted)]">{feat.rank}</td>
                    <td className="px-4 py-2 font-bold text-[var(--color-text)]">{feat.column_name}</td>
                    <td className="px-4 py-2 text-right font-extrabold text-[var(--color-accent)]">
                      {Number(feat.importance_score).toFixed(5)}
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
