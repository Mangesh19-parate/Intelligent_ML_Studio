import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { StabilityRanker } from '../components/features/StabilityRanker';
import { FeatureConfigPanel } from '../components/features/FeatureConfigPanel';
import { FeatureImportanceTable } from '../components/features/FeatureImportanceTable';

describe('Feature Engineering Subcomponents', () => {
  describe('StabilityRanker', () => {
    it('renders feature counts and stability metrics', () => {
      const onOpenFoldModal = vi.fn();
      render(
        <StabilityRanker
          totalFeatures={20}
          selectedFeaturesCount={15}
          selectionMethod="RANK_AGGREGATION"
          foldCount={5}
          averageStabilityScore={0.925}
          onOpenFoldModal={onOpenFoldModal}
        />
      );

      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('/ 20')).toBeInTheDocument();
      expect(screen.getByText('0.925')).toBeInTheDocument();

      fireEvent.click(screen.getByText(/Inspect Fold Matrices/i));
      expect(onOpenFoldModal).toHaveBeenCalled();
    });
  });

  describe('FeatureConfigPanel', () => {
    it('handles method and split changes and run trigger', () => {
      const onNSplits = vi.fn();
      const onCv = vi.fn();
      const onSeed = vi.fn();
      const onMethod = vi.fn();
      const onRun = vi.fn();

      render(
        <FeatureConfigPanel
          nSplits={5}
          onNSplitsChange={onNSplits}
          cvStrategy="AUTO"
          onCvStrategyChange={onCv}
          seed={42}
          onSeedChange={onSeed}
          method="RANK_AGGREGATION"
          onMethodChange={onMethod}
          onRun={onRun}
          running={false}
        />
      );

      expect(screen.getByText(/Ensemble Feature Selection/i)).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: /Run Ensemble Selection/i }));
      expect(onRun).toHaveBeenCalled();
    });
  });

  describe('FeatureImportanceTable', () => {
    it('renders feature list and handles search and selection', () => {
      const onToggle = vi.fn();
      const onSelectAll = vi.fn();
      const onDeselectAll = vi.fn();
      const onThreshold = vi.fn();
      const onSearch = vi.fn();
      const onFilter = vi.fn();
      const onSort = vi.fn();
      const onSave = vi.fn();

      const features = [
        {
          column_name: 'age',
          avg_rank_score: 0.95,
        },
        {
          column_name: 'income',
          avg_rank_score: 0.82,
        },
      ];

      render(
        <FeatureImportanceTable
          features={features}
          selectedFeaturesMap={{ age: true, income: false }}
          onToggleFeature={onToggle}
          onSelectAll={onSelectAll}
          onDeselectAll={onDeselectAll}
          threshold={0.5}
          onThresholdChange={onThreshold}
          searchTerm=""
          onSearchTermChange={onSearch}
          filterMode="ALL"
          onFilterModeChange={onFilter}
          sortBy="SCORE_DESC"
          onSortByChange={onSort}
          onSaveSelection={onSave}
          saving={false}
        />
      );

      expect(screen.getByText('age')).toBeInTheDocument();
      expect(screen.getByText('income')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Select All'));
      expect(onSelectAll).toHaveBeenCalled();

      fireEvent.click(screen.getByRole('button', { name: /Save Selection/i }));
      expect(onSave).toHaveBeenCalled();
    });
  });
});
