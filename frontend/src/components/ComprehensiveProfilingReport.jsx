import React, { useState } from 'react';
import {
  FileText,
  AlertTriangle,
  Info,
  Layers,
  Database,
  Search,
  ChevronDown,
  ChevronUp,
  Percent,
  TrendingUp,
  CheckCircle2,
} from 'lucide-react';

export const ComprehensiveProfilingReport = ({ edaReport }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [expandedVar, setExpandedVar] = useState(null);

  if (!edaReport || !edaReport.overview) {
    return null;
  }

  const { overview, variables, warnings } = edaReport;
  const variableList = Object.values(variables || {});

  const filteredVariables = variableList.filter((v) => {
    const matchesSearch = v.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'ALL' || v.type.toUpperCase() === filterType.toUpperCase();
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* 1. DATASET OVERVIEW SUMMARY (pandas-profiling style) */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border)] mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-[var(--color-accent-soft)] text-[var(--color-accent)] rounded-xl">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--color-text)]">Dataset Overview Summary</h2>
              <p className="text-xs text-[var(--color-text-muted)]">
                Exhaustive structural statistics on the Development partition (The Sixth Invariant)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-xs rounded-full border border-emerald-500/20 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>DQI Score: {overview.dqi_score ?? 100}/100</span>
            </span>
          </div>
        </div>

        {/* 6 Key High-level Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Observations
            </span>
            <span className="text-xl font-black text-[var(--color-text)]">
              {overview.row_count?.toLocaleString()}
            </span>
          </div>

          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Variables
            </span>
            <span className="text-xl font-black text-[var(--color-text)]">
              {overview.column_count}
            </span>
          </div>

          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Missing Cells
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-black text-[var(--color-text)]">
                {overview.missing_cells?.toLocaleString()}
              </span>
              <span className="text-xs font-bold text-amber-500">
                ({overview.missing_percentage}%)
              </span>
            </div>
          </div>

          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Duplicate Rows
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-black text-[var(--color-text)]">
                {overview.duplicate_rows?.toLocaleString()}
              </span>
              <span className="text-xs font-bold text-indigo-500">
                ({overview.duplicate_percentage}%)
              </span>
            </div>
          </div>

          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Memory Footprint
            </span>
            <span className="text-xl font-black text-[var(--color-text)]">
              {overview.memory_size_kb ? `${overview.memory_size_kb} KB` : 'N/A'}
            </span>
          </div>

          <div className="p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
              Variable Types
            </span>
            <div className="text-xs font-bold space-y-0.5 text-[var(--color-text)]">
              <div className="flex justify-between">
                <span>Num: {overview.variable_types?.Numeric || 0}</span>
                <span>Cat: {overview.variable_types?.Categorical || 0}</span>
              </div>
              <div className="flex justify-between text-[10px] text-[var(--color-text-muted)]">
                <span>Date: {overview.variable_types?.Datetime || 0}</span>
                <span>Bool: {overview.variable_types?.Boolean || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. AUTOMATED DATASET WARNINGS (YData/Pandas-profiling style) */}
      {warnings && warnings.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-[var(--color-border)] mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="text-sm font-bold text-[var(--color-text)]">
              Quality Warnings & Diagnostic Alerts ({warnings.length})
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {warnings.map((w, idx) => (
              <div
                key={idx}
                className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl flex items-start gap-3"
              >
                <span className="px-2 py-0.5 bg-amber-500/20 text-amber-600 dark:text-amber-400 font-bold text-[10px] rounded-md shrink-0">
                  {w.type}
                </span>
                <p className="text-xs font-medium text-[var(--color-text)]">{w.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. DETAILED VARIABLES PROFILING TABLE */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--color-border)]">
          <div>
            <h3 className="text-base font-bold text-[var(--color-text)]">Detailed Variable Statistics</h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              Per-feature distributions, missingness, zero frequencies, and quantiles
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <input
                type="text"
                placeholder="Search variables..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] w-40 sm:w-48"
              />
            </div>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-1.5 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs font-semibold text-[var(--color-text)] focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Types</option>
              <option value="NUMERIC">Numeric Only</option>
              <option value="CATEGORICAL">Categorical Only</option>
              <option value="DATETIME">Datetime Only</option>
            </select>
          </div>
        </div>

        {/* Variable Cards List */}
        <div className="space-y-4">
          {filteredVariables.map((v) => {
            const isExpanded = expandedVar === v.name;
            return (
              <div
                key={v.name}
                className="border border-[var(--color-border)] rounded-xl overflow-hidden bg-[var(--color-surface-hover)] transition-all"
              >
                {/* Header Row */}
                <div
                  onClick={() => setExpandedVar(isExpanded ? null : v.name)}
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface)]"
                >
                  <div className="flex items-center space-x-3">
                    <span
                      className={`px-2.5 py-1 text-[10px] font-extrabold rounded-md uppercase tracking-wider ${
                        v.type === 'Numeric'
                          ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
                          : v.type === 'Categorical'
                          ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20'
                          : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                      }`}
                    >
                      {v.type}
                    </span>
                    <span className="font-bold text-xs sm:text-sm text-[var(--color-text)]">{v.name}</span>
                    {v.is_mixed && (
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-600 text-[10px] font-bold rounded">
                        MIXED
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-6">
                    <div className="hidden sm:flex items-center space-x-4 text-xs text-[var(--color-text-muted)]">
                      <span>Distinct: <strong className="text-[var(--color-text)]">{v.distinct_count} ({v.distinct_percentage}%)</strong></span>
                      <span>Missing: <strong className={v.missing_count > 0 ? 'text-rose-500 font-bold' : 'text-[var(--color-text)]'}>{v.missing_count} ({v.missing_percentage}%)</strong></span>
                      {v.type === 'Numeric' && (
                        <span>Mean: <strong className="text-[var(--color-text)]">{v.mean ?? 'N/A'}</strong></span>
                      )}
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-[var(--color-text-muted)]" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
                    )}
                  </div>
                </div>

                {/* Expanded Details Body */}
                {isExpanded && (
                  <div className="p-4 bg-[var(--color-surface)] border-t border-[var(--color-border)] space-y-4">
                    {v.type === 'Numeric' && (
                      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 text-xs">
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Min</span>
                          <span className="font-bold text-[var(--color-text)]">{v.min}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Q25</span>
                          <span className="font-bold text-[var(--color-text)]">{v.q25}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Median</span>
                          <span className="font-bold text-[var(--color-text)]">{v.median}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Q75</span>
                          <span className="font-bold text-[var(--color-text)]">{v.q75}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Max</span>
                          <span className="font-bold text-[var(--color-text)]">{v.max}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Std Dev</span>
                          <span className="font-bold text-[var(--color-text)]">{v.std}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">IQR</span>
                          <span className="font-bold text-[var(--color-text)]">{v.iqr}</span>
                        </div>
                        <div className="p-2.5 bg-[var(--color-surface-hover)] rounded-lg">
                          <span className="text-[10px] text-[var(--color-text-muted)] block">Skewness</span>
                          <span className="font-bold text-[var(--color-text)]">{v.skewness}</span>
                        </div>
                      </div>
                    )}

                    {v.type === 'Categorical' && v.top_categories && (
                      <div>
                        <span className="text-xs font-bold text-[var(--color-text)] block mb-2">
                          Top Distinct Category Frequencies
                        </span>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                          {v.top_categories.map((cat, i) => (
                            <div
                              key={i}
                              className="p-2 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-lg text-xs"
                            >
                              <div className="font-semibold text-[var(--color-text)] truncate">{cat.value || '(Empty)'}</div>
                              <div className="text-[10px] text-[var(--color-text-muted)] flex justify-between mt-1">
                                <span>{cat.count} rows</span>
                                <span className="font-bold">{cat.percentage}%</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ComprehensiveProfilingReport;
