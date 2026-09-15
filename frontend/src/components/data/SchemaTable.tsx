import React, { useState } from 'react';
import { Table, Eye, Layers } from 'lucide-react';

export interface ColumnSchemaItem {
  id: string;
  column_name: string;
  data_type: string;
  is_target?: boolean;
}

interface SchemaTableProps {
  columns: ColumnSchemaItem[];
  targetColumn?: string | null;
  previewData?: Record<string, any>[] | null;
}

export const SchemaTable: React.FC<SchemaTableProps> = ({
  columns,
  targetColumn,
  previewData,
}) => {
  const [activeTab, setActiveTab] = useState<'SCHEMA' | 'PREVIEW'>('SCHEMA');

  if (columns.length === 0) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3.5">
        <div className="flex items-center space-x-2">
          <Table className="w-5 h-5 text-[var(--color-accent)]" />
          <h3 className="text-sm font-bold text-[var(--color-text)]">
            Dataset Schema & Partition Preview
          </h3>
        </div>

        <div className="flex items-center space-x-2 bg-[var(--color-surface-hover)] p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab('SCHEMA')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'SCHEMA'
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            Column Schema ({columns.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('PREVIEW')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'PREVIEW'
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            Development Preview
          </button>
        </div>
      </div>

      {activeTab === 'SCHEMA' ? (
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Column Name</th>
                <th className="px-4 py-3">Inferred Physical Type</th>
                <th className="px-4 py-3 text-right">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {columns.map((col, idx) => {
                const isTarget = col.column_name === targetColumn || col.is_target;
                return (
                  <tr
                    key={col.id || col.column_name}
                    className={`hover:bg-[var(--color-surface-hover)] transition-colors ${
                      isTarget ? 'bg-[var(--color-accent-soft)]/20' : ''
                    }`}
                  >
                    <td className="px-4 py-2.5 font-mono text-[var(--color-text-muted)]">{idx + 1}</td>
                    <td className="px-4 py-2.5 font-mono font-bold text-[var(--color-text)] flex items-center space-x-2">
                      <span>{col.column_name}</span>
                      {isTarget && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] uppercase">
                          Target
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)]">
                        {col.data_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold">
                      {isTarget ? (
                        <span className="text-[var(--color-accent)] font-bold">Supervised Label</span>
                      ) : (
                        <span className="text-[var(--color-text-muted)]">Feature Input</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
          {(() => {
            const rows: Record<string, any>[] = Array.isArray(previewData)
              ? previewData
              : (previewData as any)?.preview_rows || [];

            if (rows.length === 0) {
              return (
                <div className="p-8 text-center text-xs text-[var(--color-text-muted)]">
                  No development partition preview records available. Please ensure a train/test split has been created.
                </div>
              );
            }

            return (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                  <tr>
                    {Object.keys(rows[0]).map((col) => (
                      <th key={col} className="px-3 py-2.5 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)] text-[11px]">
                  {rows.slice(0, 10).map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-[var(--color-surface-hover)]">
                      {Object.entries(row).map(([k, v]) => (
                        <td key={k} className="px-3 py-2 whitespace-nowrap text-[var(--color-text)]">
                          {v !== null && v !== undefined ? String(v) : <span className="text-[var(--color-text-muted)] italic">null</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </div>
      )}
    </div>
  );
};
