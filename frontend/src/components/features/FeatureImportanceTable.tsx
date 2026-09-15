import React from 'react';
import { Search, Filter, CheckSquare, Square, Sliders, Check } from 'lucide-react';
import { Button } from '../ui/Button';

export interface FeatureScoreItem {
  column_name: string;
  avg_rank_score: number;
  mean_importance?: number;
  stability_std?: number;
  is_selected?: boolean;
}

interface FeatureImportanceTableProps {
  features: FeatureScoreItem[];
  selectedFeaturesMap: Record<string, boolean>;
  onToggleFeature: (columnName: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  threshold: number;
  onThresholdChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  searchTerm: string;
  onSearchTermChange: (val: string) => void;
  filterMode: 'ALL' | 'SELECTED' | 'EXCLUDED';
  onFilterModeChange: (mode: 'ALL' | 'SELECTED' | 'EXCLUDED') => void;
  sortBy: 'SCORE_DESC' | 'SCORE_ASC' | 'NAME_ASC';
  onSortByChange: (sort: 'SCORE_DESC' | 'SCORE_ASC' | 'NAME_ASC') => void;
  onSaveSelection: () => void;
  saving: boolean;
}

export const FeatureImportanceTable: React.FC<FeatureImportanceTableProps> = ({
  features,
  selectedFeaturesMap,
  onToggleFeature,
  onSelectAll,
  onDeselectAll,
  threshold,
  onThresholdChange,
  searchTerm,
  onSearchTermChange,
  filterMode,
  onFilterModeChange,
  sortBy,
  onSortByChange,
  onSaveSelection,
  saving,
}) => {
  const selectedCount = Object.values(selectedFeaturesMap).filter(Boolean).length;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
      {/* Top Filter and Threshold Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        {/* Threshold Slider */}
        <div className="space-y-1.5 min-w-[280px]">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-[var(--color-text)] flex items-center space-x-1.5">
              <Sliders className="w-3.5 h-3.5 text-[var(--color-accent)]" />
              <span>Selection Score Threshold</span>
            </span>
            <span className="font-mono font-bold text-[var(--color-accent)]">
              ≥ {Number(threshold).toFixed(3)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={threshold}
            onChange={onThresholdChange}
            className="w-full h-1.5 bg-[var(--color-surface-hover)] rounded-lg appearance-none cursor-pointer accent-[var(--color-accent)]"
          />
        </div>

        {/* Search, Filter Mode, Sorting, and Save Button */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative min-w-[180px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="Search features..."
              value={searchTerm}
              onChange={(e) => onSearchTermChange(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          {/* Filter Mode */}
          <select
            value={filterMode}
            onChange={(e) => onFilterModeChange(e.target.value as any)}
            className="px-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="ALL">Show All ({features.length})</option>
            <option value="SELECTED">Selected Only ({selectedCount})</option>
            <option value="EXCLUDED">Excluded Only ({features.length - selectedCount})</option>
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => onSortByChange(e.target.value as any)}
            className="px-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="SCORE_DESC">Rank Score (High → Low)</option>
            <option value="SCORE_ASC">Rank Score (Low → High)</option>
            <option value="NAME_ASC">Name (A → Z)</option>
          </select>

          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={onSaveSelection}
            disabled={saving}
            isLoading={saving}
            className="rounded-full font-bold shadow-sm"
          >
            <Check className="w-3.5 h-3.5 mr-1" />
            <span>Save Selection ({selectedCount})</span>
          </Button>
        </div>
      </div>

      {/* Select All / Deselect All Bar */}
      <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] px-1">
        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={onSelectAll}
            className="text-[var(--color-accent)] hover:underline flex items-center space-x-1 font-semibold cursor-pointer"
          >
            <CheckSquare className="w-3.5 h-3.5" />
            <span>Select All</span>
          </button>
          <span>•</span>
          <button
            type="button"
            onClick={onDeselectAll}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:underline flex items-center space-x-1 font-semibold cursor-pointer"
          >
            <Square className="w-3.5 h-3.5" />
            <span>Deselect All</span>
          </button>
        </div>
        <div className="text-[11px] font-mono">
          Showing {features.length} features
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-4 py-3 w-12 text-center">Status</th>
              <th className="px-4 py-3">Feature Name</th>
              <th className="px-4 py-3">Normalized Rank Score</th>
              <th className="px-4 py-3">Score Visual</th>
              <th className="px-4 py-3 text-right">Selection Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {features.map((feat) => {
              const isSelected = Boolean(selectedFeaturesMap[feat.column_name]);
              return (
                <tr
                  key={feat.column_name}
                  onClick={() => onToggleFeature(feat.column_name)}
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'bg-[var(--color-accent-soft)]/20' : 'hover:bg-[var(--color-surface-hover)]'
                  }`}
                >
                  <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleFeature(feat.column_name)}
                      className="rounded border-[var(--color-border)] text-[var(--color-accent)] focus:ring-[var(--color-accent)] cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-[var(--color-text)]">
                    {feat.column_name}
                  </td>
                  <td className="px-4 py-3 font-mono font-extrabold text-[var(--color-accent)] text-sm">
                    {Number(feat.avg_rank_score).toFixed(4)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-36 bg-[var(--color-surface-hover)] rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-[var(--color-accent)] h-2 rounded-full"
                        style={{ width: `${Math.min(100, Math.max(0, feat.avg_rank_score * 100))}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        isSelected
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
                      }`}
                    >
                      {isSelected ? '✓ Retained' : 'Excluded'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
