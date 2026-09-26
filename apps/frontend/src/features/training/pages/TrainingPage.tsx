import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { experimentApi, datasetApi, datasetSplitApi } from '../../../api/client';
import { useProject } from '../../../context/ProjectContext';
import { ModelTraining } from '../../../components/ModelTraining';
import { EmptyState } from '../../../components/feedback/EmptyState';
import {
  Cpu,
  Trophy,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Layers,
  RefreshCw,
  Lock,
} from 'lucide-react';

export const TrainingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { currentProject, currentProjectId } = useProject();

  const [experimentsCount, setExperimentsCount] = useState<number>(0);
  const [splitInfo, setSplitInfo] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const loadStageData = async (projId: string) => {
    try {
      setLoading(true);
      setError('');

      try {
        const expResp = await experimentApi.listByProject(projId);
        setExperimentsCount(expResp.data?.length || 0);
      } catch {
        setExperimentsCount(0);
      }

      try {
        const dsResp = await datasetApi.listVersions(projId);
        if (dsResp.data && dsResp.data.length > 0) {
          const splitResp = await datasetSplitApi.getSplit(dsResp.data[0].id);
          setSplitInfo(splitResp.data);
        } else {
          setSplitInfo(null);
        }
      } catch {
        setSplitInfo(null);
      }
    } catch (err: any) {
      console.error('Failed to load stage data', err);
      setError('Failed to load experiment stage data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentProjectId) {
      loadStageData(currentProjectId);
    } else {
      setLoading(false);
    }
  }, [currentProjectId]);

  const handleRefresh = () => {
    if (currentProjectId) {
      loadStageData(currentProjectId);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--color-border)] pb-6">
        <div>
          <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[var(--color-accent)] bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-full px-3 py-1 mb-2">
            <Cpu className="w-3.5 h-3.5" />
            <span>Stage 7 of 8 • Machine Learning Studio</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--color-text)] tracking-tight flex flex-wrap items-center gap-3">
            <span>Model Training & Leaderboard</span>
            <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
              Zero Leakage Protocol
            </span>
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1.5 max-w-3xl">
            Train baseline and non-linear ensemble models with strict out-of-fold cross-validation. Rank models strictly by primary metric and evaluate the winning model against the Locked Test partition.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          className="p-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[var(--color-border-subtle)] rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors cursor-pointer shadow-sm self-start md:self-auto"
          title="Refresh Stage Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* KPI Stats Bar */}
      {currentProjectId && currentProject && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center space-x-3.5 shadow-sm">
            <div className="p-2.5 bg-[var(--color-accent-soft)] rounded-xl border border-[var(--color-accent-border)] text-[var(--color-accent)]">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Task & Target
              </div>
              <div className="text-sm font-bold text-[var(--color-text)] flex items-center gap-1.5 mt-0.5">
                <span>{currentProject.task_type || 'Unassigned'}</span>
                {currentProject.target_column && (
                  <span className="text-xs text-[var(--color-accent)] font-mono">
                    ({currentProject.target_column})
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center space-x-3.5 shadow-sm">
            <div className="p-2.5 bg-amber-500/10 rounded-xl border border-amber-500/20 text-amber-400">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Experiment Runs
              </div>
              <div className="text-sm font-bold text-[var(--color-text)] font-mono mt-0.5">
                {experimentsCount} Completed
              </div>
            </div>
          </div>

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center space-x-3.5 shadow-sm">
            <div className="p-2.5 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Leakage Guard
              </div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                Strict CV Isolation
              </div>
            </div>
          </div>

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center space-x-3.5 shadow-sm">
            <div className="p-2.5 bg-rose-500/10 rounded-xl border border-rose-500/20 text-rose-400">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Locked Test Partition
              </div>
              <div className="text-sm font-bold text-[var(--color-text)] mt-0.5">
                {splitInfo ? `${Math.round((splitInfo.test_rows / (splitInfo.train_rows + splitInfo.test_rows)) * 100)}% Holdout` : 'Configured'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {!currentProjectId ? (
        <EmptyState
          title="Select a Project to View Leaderboard"
          description="Choose a workspace project to configure training algorithms, launch cross-validation experiments, and view the authoritative model leaderboard."
        />
      ) : (
        <ModelTraining
          projectId={currentProjectId}
          taskType={currentProject?.task_type}
          targetColumn={currentProject?.target_column}
          onExperimentCompleted={handleRefresh}
        />
      )}

      {/* Stage Navigation Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-[var(--color-border)]">
        <Link
          to={currentProjectId ? `/diagnostics?project_id=${currentProjectId}` : '/diagnostics'}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Stage 6: Diagnostics & Pre-Flight</span>
        </Link>

        <Link
          to={currentProjectId ? `/production?project_id=${currentProjectId}` : '/production'}
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-sm transition-all"
        >
          <span>Proceed to Stage 8: Production</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
};

export default TrainingPage;
