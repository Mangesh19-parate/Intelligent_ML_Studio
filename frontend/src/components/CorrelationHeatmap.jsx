import React, { useState } from 'react';
import { Activity, Info } from 'lucide-react';

export const CorrelationHeatmap = ({ correlationData }) => {
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!correlationData || !correlationData.columns || correlationData.columns.length === 0) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 text-center text-slate-500 text-sm">
        <Activity className="w-8 h-8 mx-auto mb-2 text-slate-600" />
        No numeric columns available to compute Pearson correlation matrix.
      </div>
    );
  }

  const { columns, matrix } = correlationData;

  const getColor = (value) => {
    if (value === null || value === undefined) return 'bg-slate-800/40 text-slate-500';
    // Diverging palette: Blue (-1) -> Slate (0) -> Emerald (+1)
    if (value >= 0.8) return 'bg-emerald-500/80 text-white font-bold';
    if (value >= 0.5) return 'bg-emerald-500/50 text-emerald-100 font-semibold';
    if (value >= 0.2) return 'bg-emerald-500/25 text-emerald-200';
    if (value > -0.2) return 'bg-slate-800/60 text-slate-400';
    if (value > -0.5) return 'bg-indigo-500/30 text-indigo-200';
    if (value > -0.8) return 'bg-indigo-500/60 text-indigo-100 font-semibold';
    return 'bg-indigo-600/90 text-white font-bold';
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-white">Pearson Correlation Matrix</h4>
            <p className="text-xs text-slate-400">
              Pairwise linear relationships across {columns.length} numeric features
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-indigo-600 inline-block" /> -1.0 (Inverse)
          </span>
          <span className="text-slate-600">|</span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-slate-800 inline-block" /> 0.0 (None)
          </span>
          <span className="text-slate-600">|</span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-emerald-500 inline-block" /> +1.0 (Direct)
          </span>
        </div>
      </div>

      {/* Heatmap Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left text-xs font-mono text-slate-500 border-b border-slate-800 sticky left-0 bg-slate-900 z-10 min-w-[120px]">
                Feature
              </th>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className="p-2 text-center text-xs font-mono text-slate-400 border-b border-slate-800 min-w-[80px]"
                  title={col}
                >
                  <span className="truncate max-w-[90px] block mx-auto">{col}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {columns.map((rowCol, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-slate-800/30 transition-colors">
                <td className="p-2 text-xs font-mono font-medium text-slate-300 border-r border-slate-800/80 sticky left-0 bg-slate-900 z-10 truncate max-w-[140px]" title={rowCol}>
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
                      className={`p-2.5 text-center text-xs font-mono transition-all duration-150 border border-slate-900/60 ${getColor(val)} ${
                        isDiagonal ? 'ring-1 ring-inset ring-slate-700/50' : 'cursor-pointer hover:scale-105 hover:z-20'
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
        <div className="mt-3 p-2.5 bg-slate-950/90 border border-slate-800 rounded-lg text-xs font-mono flex items-center justify-between text-slate-300 animate-fadeIn">
          <span>
            Correlation (<strong className="text-indigo-300">{hoveredCell.row}</strong> vs <strong className="text-emerald-300">{hoveredCell.col}</strong>):
          </span>
          <strong className="text-sm font-bold text-white">
            {hoveredCell.val !== null ? hoveredCell.val.toFixed(4) : 'N/A'}
          </strong>
        </div>
      )}
    </div>
  );
};
