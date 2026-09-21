import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FitDiagnosisBadge } from '../components/training/FitDiagnosisBadge';
import { TrainingConfigPanel } from '../components/training/TrainingConfigPanel';
import { WinnerCalloutCard } from '../components/training/WinnerCalloutCard';
import { LeaderboardTable } from '../components/training/LeaderboardTable';

describe('Training Module Subcomponents', () => {
  describe('FitDiagnosisBadge', () => {
    it('renders Good Fit badge with checkmark', () => {
      render(<FitDiagnosisBadge diagnosis="GOOD_FIT" />);
      expect(screen.getByText(/Good Fit/i)).toBeInTheDocument();
    });

    it('renders Overfit Gap badge with warning', () => {
      render(<FitDiagnosisBadge diagnosis="POTENTIAL_OVERFIT" />);
      expect(screen.getByText(/Overfit Gap/i)).toBeInTheDocument();
    });

    it('renders Weak Signal badge', () => {
      render(<FitDiagnosisBadge diagnosis="POTENTIAL_UNDERFIT_WEAK_SIGNAL" />);
      expect(screen.getByText(/Weak Signal/i)).toBeInTheDocument();
    });

    it('renders Low Data badge', () => {
      render(<FitDiagnosisBadge diagnosis="LOW_DATA" />);
      expect(screen.getByText(/Low Data/i)).toBeInTheDocument();
    });

    it('renders N/A for null diagnosis', () => {
      render(<FitDiagnosisBadge diagnosis={null} />);
      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('TrainingConfigPanel', () => {
    it('renders regression algorithms and handles selection changes', () => {
      const onToggle = vi.fn();
      const onSelectAll = vi.fn();
      const onMetricChange = vi.fn();
      const onFoldsChange = vi.fn();
      const onSeedChange = vi.fn();
      const onRandomize = vi.fn();
      const onSubmit = vi.fn();

      render(
        <TrainingConfigPanel
          taskType="REGRESSION"
          selectedAlgorithms={['LinearRegression']}
          onToggleAlgorithm={onToggle}
          onSelectAllAlgorithms={onSelectAll}
          selectionMetric="rmse"
          onSelectionMetricChange={onMetricChange}
          folds={5}
          onFoldsChange={onFoldsChange}
          seed="42"
          onSeedChange={onSeedChange}
          onRandomizeSeed={onRandomize}
          onSubmit={onSubmit}
          loading={false}
          pollingActive={false}
        />
      );

      expect(screen.getByText(/Linear Regression/i)).toBeInTheDocument();
      expect(screen.getByText(/Random Forest Regressor/i)).toBeInTheDocument();

      // Test select all
      fireEvent.click(screen.getByText('Select All'));
      expect(onSelectAll).toHaveBeenCalled();

      // Test randomize seed
      fireEvent.click(screen.getByText('Rand'));
      expect(onRandomize).toHaveBeenCalled();
    });
  });

  describe('WinnerCalloutCard', () => {
    it('renders winning model information and locked test state', () => {
      const onRerun = vi.fn();
      const winningModel = {
        id: 'model-1',
        algorithm_name: 'RandomForestRegressor',
        is_winner: true,
        primary_metric_value: 0.12345,
        fit_diagnosis: 'GOOD_FIT',
        decision_threshold: null,
        locked_test_score: 0.12500,
      };

      const leaderboard = {
        selection_metric: 'rmse',
        selection_direction: 'MINIMIZE',
        locked_test_consumed: true,
        models: [winningModel],
      };

      render(
        <WinnerCalloutCard
          winningModel={winningModel}
          leaderboard={leaderboard}
          onDiagnosticRerun={onRerun}
          rerunningDiagnostic={false}
        />
      );

      expect(screen.getByText('RandomForestRegressor')).toBeInTheDocument();
      expect(screen.getByText(/0.12345/)).toBeInTheDocument();
      expect(screen.getByText(/0.12500/)).toBeInTheDocument();
      expect(screen.getByText(/Evaluated once, now consumed/i)).toBeInTheDocument();
    });
  });

  describe('LeaderboardTable', () => {
    it('renders models table with rank order and action buttons', () => {
      const onMetrics = vi.fn();
      const onExplain = vi.fn();
      const onPassport = vi.fn();
      const onDownload = vi.fn();
      const onDeploy = vi.fn();
      const onHealth = vi.fn();
      const onLineage = vi.fn();

      const models = [
        {
          id: 'model-1',
          algorithm_name: 'RandomForestRegressor',
          is_winner: true,
          primary_metric_value: 0.12345,
          secondary_metric_value: 0.89,
          fit_diagnosis: 'GOOD_FIT',
          model_selection_score: 95.5,
          artifact_path: 's3://artifacts/model-1.joblib',
        },
      ];

      render(
        <LeaderboardTable
          models={models}
          selectionMetric="rmse"
          selectionDirection="MINIMIZE"
          isRegression={true}
          onOpenMetrics={onMetrics}
          onOpenExplain={onExplain}
          onOpenPassport={onPassport}
          onDownloadArtifact={onDownload}
          onOpenDeploymentGate={onDeploy}
          onOpenHealthReport={onHealth}
          onOpenLineage={onLineage}
        />
      );

      expect(screen.getByText(/Authoritative Model Leaderboard/i)).toBeInTheDocument();
      expect(screen.getByText('RandomForestRegressor')).toBeInTheDocument();
      expect(screen.getByText('0.12345')).toBeInTheDocument();

      // Click Metrics action
      fireEvent.click(screen.getByRole('button', { name: /Metrics/i }));
      expect(onMetrics).toHaveBeenCalledWith('model-1');
    });
  });
});
