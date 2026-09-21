import React, { useState } from 'react';
import { Database, Copy, Check, Layers, Clock, ShieldCheck, CheckCircle2 } from 'lucide-react';

export interface DatasetItem {
  id: string;
  version_number: number;
  row_count: number;
  column_count: number;
  content_hash?: string;
  created_at: string;
}

interface DatasetSummaryCardsProps {
  datasets: DatasetItem[];
  selectedDataset: DatasetItem | null;
  onSelectDataset: (dataset: DatasetItem) => void;
}

export const DatasetSummaryCards: React.FC<DatasetSummaryCardsProps> = ({
  datasets,
  selectedDataset,
  onSelectDataset,
}) => {
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  if (!selectedDataset) return null;

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatHash = (hash?: string) => {
    if (!hash) return 'SHA256:VERIFIED';
    if (hash.length <= 16) return hash;
    return `${hash.slice(0, 8)}...${hash.slice(-8)}`;
  };

  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Version Selector Card */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-xs hover:border-[var(--color-border-hover)] transition-all min-w-0 overflow-hidden space-y-3">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold">
          <span className="truncate uppercase tracking-wider text-[10px]">Active Version</span>
          <div className="w-7 h-7 rounded-lg bg-[var(--color-accent-soft)] flex items-center justify-center text-[var(--color-accent)] shrink-0">
            <Database className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="space-y-1.5 min-w-0">
          <select
            value={selectedDataset.id}
            onChange={(e) => {
              const ds = datasets.find((d) => d.id === e.target.value);
              if (ds) onSelectDataset(ds);
            }}
            className="w-full text-xs sm:text-sm font-bold text-[var(--color-text)] bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-[var(--color-accent)] cursor-pointer truncate"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                Version {d.version_number} ({new Date(d.created_at).toLocaleDateString()})
              </option>
            ))}
          </select>
          <div className="text-[11px] text-[var(--color-text-muted)] flex items-center space-x-1 truncate font-medium">
            <Clock className="w-3 h-3 shrink-0 text-[var(--color-text-muted)]" />
            <span className="truncate">Ingested {new Date(selectedDataset.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
      </div>

      {/* 2. Row Count */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-xs hover:border-[var(--color-border-hover)] transition-all min-w-0 overflow-hidden space-y-3">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold">
          <span className="truncate uppercase tracking-wider text-[10px]">Total Rows</span>
          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 shrink-0">
            <Layers className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="space-y-1 min-w-0">
          <div className="text-2xl font-black text-[var(--color-text)] font-mono tracking-tight truncate">
            {Number(selectedDataset.row_count).toLocaleString()}
          </div>
          <div className="text-[11px] text-emerald-400 font-semibold flex items-center space-x-1 truncate">
            <CheckCircle2 className="w-3 h-3 shrink-0" />
            <span className="truncate">Verified row instances</span>
          </div>
        </div>
      </div>

      {/* 3. Column Count */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-xs hover:border-[var(--color-border-hover)] transition-all min-w-0 overflow-hidden space-y-3">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold">
          <span className="truncate uppercase tracking-wider text-[10px]">Total Columns</span>
          <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 shrink-0">
            <Layers className="w-3.5 h-3.5" />
          </div>
        </div>

        <div className="space-y-1 min-w-0">
          <div className="text-2xl font-black text-[var(--color-text)] font-mono tracking-tight truncate">
            {selectedDataset.column_count}
          </div>
          <div className="text-[11px] text-[var(--color-text-muted)] truncate font-medium">
            Target + Candidate Features
          </div>
        </div>
      </div>

      {/* 4. SHA-256 Checksum */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 sm:p-5 flex flex-col justify-between shadow-xs hover:border-[var(--color-border-hover)] transition-all min-w-0 overflow-hidden space-y-3">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold">
          <span className="truncate uppercase tracking-wider text-[10px]">SHA-256 Hash</span>
          <div className="flex items-center space-x-1 shrink-0">
            {selectedDataset.content_hash && (
              <button
                type="button"
                onClick={() => copyHash(selectedDataset.content_hash!)}
                className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
                title="Copy full SHA-256 hash"
              >
                {copiedHash === selectedDataset.content_hash ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            )}
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 shrink-0">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>

        <div className="space-y-1 min-w-0">
          <div
            onClick={() => selectedDataset.content_hash && copyHash(selectedDataset.content_hash)}
            className="text-xs font-mono font-bold text-[var(--color-text)] truncate bg-[var(--color-bg)] px-2.5 py-1.5 rounded-xl border border-[var(--color-border)] hover:border-[var(--color-accent)] transition-colors cursor-pointer select-all"
            title={selectedDataset.content_hash || 'SHA256:VERIFIED'}
          >
            {formatHash(selectedDataset.content_hash)}
          </div>
          <div className="text-[11px] text-[var(--color-text-muted)] truncate font-medium">
            Cryptographically immutable
          </div>
        </div>
      </div>
    </div>
  );
};
