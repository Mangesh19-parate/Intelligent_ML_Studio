import React, { useState } from 'react';
import { Table, Search, ChevronDown, ChevronUp, BarChart2 } from 'lucide-react';

export const ColumnStatsTable = ({ columnStats = {} }) => {
  const [search, setSearch] = useState('');
  const [selectedCol, setSelectedCol] = useState(null);

  const columnsList = Object.entries(columnStats).map(([name, stats]) => ({
    name,
    ...stats,
  }));

  const filteredColumns = columnsList.filter((col) =>
    col.name.toLowerCase().includes(search.toLowerCase()) ||
    col.type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/20 rounded-xl text-cyan-400">
            <Table className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-white">Feature Profiling & Column Diagnostics</h4>
            <p className="text-xs text-slate-400">
              Descriptive statistics computed strictly on Development rows
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter features..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-mono">
              <th className="py-2.5 px-3">Column</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Missing</th>
              <th className="py-2.5 px-3">Unique</th>
              <th className="py-2.5 px-3">Mean / Mode</th>
              <th className="py-2.5 px-3">Std / Granularity</th>
              <th className="py-2.5 px-3">Skew / IQR</th>
              <th className="py-2.5 px-3">Outliers</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {filteredColumns.map((col) => {
              const isSelected = selectedCol === col.name;
              return (
                <React.Fragment key={col.name}>
                  <tr
                    onClick={() => setSelectedCol(isSelected ? null : col.name)}
                    className="hover:bg-slate-800/30 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-3 font-mono font-medium text-white flex items-center gap-2">
                      {isSelected ? (
                        <ChevronUp className="w-3.5 h-3.5 text-cyan-400" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                      )}
                      {col.name}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-slate-800 text-slate-300">
                        {col.type}
                      </span>
                      {col.is_mixed_type && (
                        <span className="ml-1 px-1.5 py-0.5 rounded text-[9px] font-mono bg-rose-500/20 text-rose-300">
                          MIXED
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono">
                      <span className={col.missing_pct > 0 ? 'text-amber-400 font-medium' : 'text-slate-400'}>
                        {col.missing_pct}% ({col.missing_count})
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-300">{col.unique_count}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">
                      {col.type === 'numeric'
                        ? col.mean !== null ? col.mean.toFixed(2) : '-'
                        : col.mode || '-'}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {col.type === 'numeric'
                        ? col.std !== null ? col.std.toFixed(2) : '-'
                        : col.granularity || '-'}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {col.type === 'numeric'
                        ? col.skew !== null ? `skew: ${col.skew.toFixed(2)}` : '-'
                        : '-'}
                    </td>
                    <td className="py-3 px-3 font-mono">
                      {col.type === 'numeric' ? (
                        <span className={col.outlier_pct > 0 ? 'text-rose-400 font-medium' : 'text-slate-400'}>
                          {col.outlier_pct}% ({col.outlier_count})
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>

                  {/* Expanded detail row */}
                  {isSelected && (
                    <tr className="bg-slate-950/60">
                      <td colSpan={8} className="p-4 border-t border-b border-slate-800">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          {col.type === 'numeric' ? (
                            <div className="space-y-1.5 font-mono text-slate-300 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block mb-1 font-sans">
                                Five-Number Summary & Moments
                              </span>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>Min: <strong>{col.min}</strong></div>
                                <div>Max: <strong>{col.max}</strong></div>
                                <div>Q25: <strong>{col.q25}</strong></div>
                                <div>Q75: <strong>{col.q75}</strong></div>
                                <div>Median: <strong>{col.median}</strong></div>
                                <div>IQR: <strong>{col.iqr}</strong></div>
                              </div>
                            </div>
                          ) : col.frequency_table && col.frequency_table.length > 0 ? (
                            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block mb-2 font-sans flex items-center gap-1.5">
                                <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
                                Top-10 Frequency Distribution
                              </span>
                              <div className="space-y-1.5">
                                {col.frequency_table.map((freq, fIdx) => (
                                  <div key={fIdx} className="flex items-center justify-between text-xs">
                                    <span className="text-slate-300 font-mono truncate max-w-[150px]">{freq.value}</span>
                                    <div className="flex items-center gap-2">
                                      <div className="w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                        <div
                                          className="bg-cyan-500 h-full rounded-full"
                                          style={{ width: `${freq.percentage}%` }}
                                        />
                                      </div>
                                      <span className="font-mono text-slate-400 text-[11px] w-12 text-right">
                                        {freq.percentage}%
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="text-slate-500 font-mono">No frequency table available</div>
                          )}

                          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs text-slate-300">
                            <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block mb-1 font-sans">
                              Data Quality Observations
                            </span>
                            <ul className="space-y-1 text-slate-400">
                              <li>• Missing cell count: <strong className="text-slate-200">{col.missing_count}</strong> ({col.missing_pct}%)</li>
                              <li>• Distinct values count: <strong className="text-slate-200">{col.unique_count}</strong></li>
                              {col.type === 'numeric' && (
                                <li>• IQR Outlier cells: <strong className="text-slate-200">{col.outlier_count}</strong> ({col.outlier_pct}%)</li>
                              )}
                              {col.is_mixed_type && (
                                <li className="text-rose-400">• Mixed data types detected across string/numeric values.</li>
                              )}
                            </ul>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
