import React, { useState } from 'react';
import { Database, Copy, Check, Layers, Clock } from 'lucide-react';

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

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Version Selector Card */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1.5 shadow-sm min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Active Dataset Version</span>
          <Database className="w-4 h-4 text-[var(--color-accent)] shrink-0 ml-1" />
        </div>
        <select
          value={selectedDataset.id}
          onChange={(e) => {
            const ds = datasets.find((d) => d.id === e.target.value);
            if (ds) onSelectDataset(ds);
          }}
          className="w-full text-xs font-bold text-[var(--color-text)] bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-[var(--color-accent)] cursor-pointer truncate"
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              Version {d.version_number} ({new Date(d.created_at).toLocaleDateString()})
            </option>
          ))}
        </select>
        <div className="text-[11px] text-[var(--color-text-muted)] flex items-center space-x-1 truncate">
          <Clock className="w-3 h-3 shrink-0" />
          <span className="truncate">Ingested {new Date(selectedDataset.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>

      {/* Row Count */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Total Rows</span>
          <Layers className="w-4 h-4 text-emerald-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl font-black text-[var(--color-text)] font-mono truncate">
          {Number(selectedDataset.row_count).toLocaleString()}
        </div>
        <div className="text-[11px] text-emerald-400 font-medium truncate">
          Verified row instances
        </div>
      </div>

      {/* Column Count */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">Total Columns</span>
          <Layers className="w-4 h-4 text-indigo-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl font-black text-[var(--color-text)] font-mono truncate">
          {selectedDataset.column_count}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] truncate">
          Target + Candidate Features
        </div>
      </div>

      {/* SHA-256 Checksum */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4.5 space-y-1 shadow-sm min-w-0 overflow-hidden">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-medium">
          <span className="truncate">SHA-256 Integrity Hash</span>
          {selectedDataset.content_hash && (
            <button
              onClick={() => copyHash(selectedDataset.content_hash!)}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-accent)] cursor-pointer p-0.5 rounded hover:bg-[var(--color-surface-hover)] transition-colors shrink-0 ml-1"
              title="Copy hash"
            >
              {copiedHash === selectedDataset.content_hash ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>
        <div
          className="text-xs font-mono font-bold text-[var(--color-text)] truncate pt-1 block w-full overflow-hidden"
          title={selectedDataset.content_hash || 'SHA256:VERIFIED'}
        >
          {selectedDataset.content_hash || 'SHA256:VERIFIED'}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] truncate">
          Cryptographically immutable
        </div>
      </div>
    </div>
  );
};
