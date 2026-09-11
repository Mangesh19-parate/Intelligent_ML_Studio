import React, { useState } from 'react';
import { Activity, Info } from 'lucide-react';

export const CorrelationHeatmap = ({ correlationData }) => {
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!correlationData || !correlationData.columns || correlationData.columns.length === 0) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 text-center text-[var(--color-text-muted)] text-sm shadow-sm">
        <Activity className="w-8 h-8 mx-auto mb-2 text-[var(--color-text-muted)]" />
        No numeric columns available to compute Pearson correlation matrix.
      </div>
    );
  }

  const { columns, matrix } = correlationData;

  const getColor = (value) => {
    if (value === null || value === undefined) return 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]';
    // Diverging palette: Darker Accent / Orange / Neutral / Teal
    if (value >= 0.8) return 'bg-emerald-600 text-white font-bold';
    if (value >= 0.5) return 'bg-emerald-500/60 text-emerald-950 dark:text-emerald-100 font-bold';
    if (value >= 0.2) return 'bg-emerald-500/25 text-emerald-900 dark:text-emerald-200';
    if (value > -0.2) return 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]';
    if (value > -0.5) return 'bg-[#CF4500]/25 text-[#CF4500] font-medium';
    if (value > -0.8) return 'bg-[#CF4500]/60 text-white font-bold';
    return 'bg-[#CF4500] text-white font-bold';
  };

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-500">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-bold text-[var(--color-text)]">Pearson Correlation Matrix</h4>
            <p className="text-xs text-[var(--color-text-muted)]">
              Pairwise linear relationships across {columns.length} numeric features
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 text-[11px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] px-3 py-1.5 rounded-full border border-[var(--color-border)]">
          <span className="flex items-center gap-1 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-[#CF4500] inline-block" /> -1.0 (Inverse)
          </span>
          <span className="text-[var(--color-border)]">|</span>
          <span className="flex items-center gap-1 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-text-muted)] inline-block" /> 0.0
          </span>
          <span className="text-[var(--color-border)]">|</span>
          <span className="flex items-center gap-1 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block" /> +1.0 (Direct)
          </span>
        </div>
      </div>

      {/* Heatmap Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left text-xs font-mono text-[var(--color-text-muted)] border-b border-[var(--color-border)] sticky left-0 bg-[var(--color-surface)] z-10 min-w-[120px] font-bold">
                Feature
              </th>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className="p-2 text-center text-xs font-mono text-[var(--color-text)] border-b border-[var(--color-border)] min-w-[80px] font-bold"
                  title={col}
                >
                  <span className="truncate max-w-[90px] block mx-auto">{col}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {columns.map((rowCol, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                <td className="p-2 text-xs font-mono font-bold text-[var(--color-text)] border-r border-[var(--color-border)] sticky left-0 bg-[var(--color-surface)] z-10 truncate max-w-[140px]" title={rowCol}>
                  {rowCol}
                </td>
                {columns.map((col, colIdx) => {
                  const val = matrix[rowIdx]?.[colIdx];
                  const isDiagonal = rowIdx === colIdx;
                  return (
                    <td
                      key={colIdx}
                      onMouseEnter={() => setHoveredCell({ row: rowCol, col, val })}
                      onMouseLeave={() => setHoveredCell(null)}
                      className={`p-2.5 text-center text-xs font-mono transition-all duration-150 border border-[var(--color-border)]/50 ${getColor(val)} ${
                        isDiagonal ? 'ring-1 ring-inset ring-[var(--color-border)]' : 'cursor-pointer hover:scale-105 hover:z-20'
                      }`}
                    >
                      {val !== null && val !== undefined ? val.toFixed(2) : '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hoveredCell && (
        <div className="mt-3 p-3 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs font-mono flex items-center justify-between text-[var(--color-text)] animate-fadeIn">
          <span>
            Correlation (<strong className="text-[var(--color-accent)]">{hoveredCell.row}</strong> vs <strong className="text-emerald-600 dark:text-emerald-400">{hoveredCell.col}</strong>):
          </span>
          <strong className="text-sm font-bold text-[var(--color-text)]">
            {hoveredCell.val !== null ? hoveredCell.val.toFixed(4) : 'N/A'}
          </strong>
        </div>
      )}
    </div>
  );
};
