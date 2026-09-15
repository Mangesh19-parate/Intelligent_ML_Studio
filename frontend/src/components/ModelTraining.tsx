import React, { useState, useEffect, useRef } from 'react';
import { experimentApi, modelApi } from '../api/client';
import { LineageViewer } from './LineageViewer';
import { ExplainabilityViewer } from './ExplainabilityViewer';
import DeploymentGateModal from './DeploymentGateModal';
import ModelPassportModal from './ModelPassportModal';
import ExperimentHealthModal from './ExperimentHealthModal';
import {
  TrainingConfigPanel,
  WinnerCalloutCard,
  LeaderboardTable,
  ModelMetricsModal,
  ExperimentHistoryList,
  REGRESSION_ALGORITHMS,
  CLASSIFICATION_ALGORITHMS,
} from './training';
import { EmptyState } from './feedback/EmptyState';
import { ErrorState } from './feedback/ErrorState';
import { ShieldCheck, CheckCircle2, Layers, AlertTriangle } from 'lucide-react';

interface ModelTrainingProps {
  projectId: string;
  taskType?: 'REGRESSION' | 'CLASSIFICATION' | string;
  targetColumn?: string | null;
  onExperimentCompleted?: () => void;
}

export const ModelTraining: React.FC<ModelTrainingProps> = ({
  projectId,
  taskType,
  targetColumn,
  onExperimentCompleted,
}) => {
  const isRegression = taskType === 'REGRESSION';
  const isClassification = taskType === 'CLASSIFICATION';
  const availableAlgs = isRegression
    ? REGRESSION_ALGORITHMS
    : isClassification
    ? CLASSIFICATION_ALGORITHMS
    : [];

  const [selectedAlgorithms, setSelectedAlgorithms] = useState<string[]>(
    availableAlgs.map((a) => a.id)
  );
  const [folds, setFolds] = useState<number>(5);
  const [seed, setSeed] = useState<string>('');
  const [selectionMetric, setSelectionMetric] = useState<string>(isRegression ? 'rmse' : 'f1_macro');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Active Experiment, Leaderboard & History State
  const [activeExperiment, setActiveExperiment] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [experimentsHistory, setExperimentsHistory] = useState<any[]>([]);
  const [pollingActive, setPollingActive] = useState<boolean>(false);
  const [selectedModelMetrics, setSelectedModelMetrics] = useState<any[] | null>(null);
  const [modelModalOpen, setModelModalOpen] = useState<boolean>(false);
  const [lineageModalOpen, setLineageModalOpen] = useState<boolean>(false);
  const [lineageExperimentId, setLineageExperimentId] = useState<string | null>(null);
  const [explainModalOpen, setExplainModalOpen] = useState<boolean>(false);
  const [selectedExplainModel, setSelectedExplainModel] = useState<any>(null);
  const [deploymentModalOpen, setDeploymentModalOpen] = useState<boolean>(false);
  const [selectedDeploymentModel, setSelectedDeploymentModel] = useState<any>(null);
  const [passportModalOpen, setPassportModalOpen] = useState<boolean>(false);
  const [selectedPassportModelId, setSelectedPassportModelId] = useState<string | null>(null);
  const [healthModalOpen, setHealthModalOpen] = useState<boolean>(false);
  const [healthExperimentId, setHealthExperimentId] = useState<string | null>(null);
  const [rerunningDiagnostic, setRerunningDiagnostic] = useState<boolean>(false);

  const pollingTimerRef = useRef<any>(null);

  useEffect(() => {
    setSelectedAlgorithms(availableAlgs.map((a) => a.id));
    setSelectionMetric(isRegression ? 'rmse' : 'f1_macro');
  }, [taskType]);

  const loadLeaderboardData = async (experimentId: string | null = null) => {
    try {
      const res = await modelApi.getLeaderboard(projectId, experimentId);
      setLeaderboard(res.data);
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await experimentApi.listByProject(projectId);
      const list = res.data || [];
      setExperimentsHistory(list);
      if (list.length > 0) {
        const latest = list[0];
        setActiveExperiment(latest);
        await loadLeaderboardData(latest.id);
        if (latest.status === 'RUNNING') {
          startPolling(latest.id);
        }
      }
    } catch (err) {
      console.error('Failed to load experiment history:', err);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadHistory();
    }
    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [projectId]);

  const startPolling = (experimentId: string) => {
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    setPollingActive(true);

    const poll = async () => {
      try {
        const res = await experimentApi.get(experimentId);
        setActiveExperiment(res.data);
        await loadLeaderboardData(experimentId);

        if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
          clearInterval(pollingTimerRef.current);
          setPollingActive(false);
          loadHistory();
          if (onExperimentCompleted) onExperimentCompleted();
        }
      } catch (err) {
        console.error('Polling error:', err);
        clearInterval(pollingTimerRef.current);
        setPollingActive(false);
      }
    };

    poll();
    pollingTimerRef.current = setInterval(poll, 1500);
  };

  const handleToggleAlgorithm = (algId: string) => {
    if (selectedAlgorithms.includes(algId)) {
      if (selectedAlgorithms.length === 1) return;
      setSelectedAlgorithms(selectedAlgorithms.filter((id) => id !== algId));
    } else {
      setSelectedAlgorithms([...selectedAlgorithms, algId]);
    }
  };

  const handleSelectAll = () => {
    setSelectedAlgorithms(availableAlgs.map((a) => a.id));
  };

  const handleRandomizeSeed = () => {
    setSeed(Math.floor(Math.random() * 1000000).toString());
  };

  const handleStartTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (selectedAlgorithms.length === 0) {
      setError('Please select at least one algorithm to train.');
      return;
    }

    try {
      setLoading(true);
      const payload = {
        algorithms: selectedAlgorithms,
        folds: Number(folds),
        seed: seed ? Number(seed) : null,
        selection_metric: selectionMetric,
      };

      const res = await experimentApi.create(projectId, payload);
      setSuccessMsg('Cross-validation training & evaluation launched.');
      startPolling(res.data.experiment_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to launch training experiment');
    } finally {
      setLoading(false);
    }
  };

  const handleDiagnosticRerun = async () => {
    if (!activeExperiment) return;
    setError('');
    setSuccessMsg('');
    try {
      setRerunningDiagnostic(true);
      const res = await experimentApi.diagnosticRerun(activeExperiment.id);
      setSuccessMsg(res.data.message || 'Diagnostic rerun completed. Stored as TEST_REUSED_DIAGNOSTIC.');
      await loadLeaderboardData(activeExperiment.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Diagnostic rerun failed');
    } finally {
      setRerunningDiagnostic(false);
    }
  };

  const handleOpenModelMetrics = async (modelId: string) => {
    try {
      const res = await modelApi.getMetrics(modelId);
      setSelectedModelMetrics(res.data);
      setModelModalOpen(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownloadModel = async (modelId: string, algorithmName: string) => {
    try {
      const resp = await modelApi.download(modelId, 'joblib');
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${algorithmName}_pipeline.joblib`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to download model artifact');
    }
  };

  if (!taskType || !['REGRESSION', 'CLASSIFICATION'].includes(taskType)) {
    return (
      <EmptyState
        title="Task Type Required"
        description="Please confirm the project task type (Regression or Classification) in the Data Profiling tab before running model training."
      />
    );
  }

  const winningModel = leaderboard?.models?.find((m: any) => m.is_winner);

  return (
    <div className="space-y-6">
      {/* Leakage Isolation & Locked Test Banner */}
      <div className="p-4 rounded-2xl bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-xs text-[var(--color-text)] flex items-start space-x-3 shadow-sm">
        <ShieldCheck className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
        <div>
          <strong className="font-bold text-[var(--color-text)]">Leakage-Safe Protocol & Locked Test Boundary: </strong>
          <span className="text-[var(--color-text-muted)]">
            Inner CV evaluation drives model ranking by primary metric. Upon finalization, the winning model is refit on full Development data and evaluated exactly ONCE against the Locked Test partition.
          </span>
        </div>
      </div>

      {error && (
        <ErrorState
          title="Training / Evaluation Error"
          message={error}
          onRetry={() => setError('')}
        />
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Training Configuration & History */}
        <div className="space-y-4">
          <TrainingConfigPanel
            taskType={taskType}
            selectedAlgorithms={selectedAlgorithms}
            onToggleAlgorithm={handleToggleAlgorithm}
            onSelectAllAlgorithms={handleSelectAll}
            selectionMetric={selectionMetric}
            onSelectionMetricChange={setSelectionMetric}
            folds={folds}
            onFoldsChange={setFolds}
            seed={seed}
            onSeedChange={setSeed}
            onRandomizeSeed={handleRandomizeSeed}
            onSubmit={handleStartTraining}
            loading={loading}
            pollingActive={pollingActive}
          />

          <ExperimentHistoryList
            experiments={experimentsHistory}
            activeExperimentId={activeExperiment?.id}
            onSelectExperiment={(exp) => {
              setActiveExperiment(exp);
              loadLeaderboardData(exp.id);
            }}
          />
        </div>

        {/* Right 2 Columns: Official Leaderboard & Winner Callout */}
        <div className="lg:col-span-2 space-y-5">
          {!leaderboard || !activeExperiment ? (
            <EmptyState
              title="No Model Leaderboard Available"
              description="Configure algorithms and folds on the left, then launch training to populate the authoritative primary-metric leaderboard."
            />
          ) : (
            <div className="space-y-5">
              {/* Winner Callout Card */}
              {winningModel && (
                <WinnerCalloutCard
                  winningModel={winningModel}
                  leaderboard={leaderboard}
                  onDiagnosticRerun={handleDiagnosticRerun}
                  rerunningDiagnostic={rerunningDiagnostic}
                />
              )}

              {/* Leaderboard Table Card */}
              <LeaderboardTable
                models={leaderboard.models || []}
                selectionMetric={leaderboard.selection_metric}
                selectionDirection={leaderboard.selection_direction}
                isRegression={isRegression}
                onOpenMetrics={handleOpenModelMetrics}
                onOpenExplain={(model) => {
                  setSelectedExplainModel(model);
                  setExplainModalOpen(true);
                }}
                onOpenPassport={(modelId) => {
                  setSelectedPassportModelId(modelId);
                  setPassportModalOpen(true);
                }}
                onDownloadArtifact={handleDownloadModel}
                onOpenDeploymentGate={(model) => {
                  setSelectedDeploymentModel(model);
                  setDeploymentModalOpen(true);
                }}
                onOpenHealthReport={() => {
                  setHealthExperimentId(activeExperiment.id);
                  setHealthModalOpen(true);
                }}
                onOpenLineage={() => {
                  setLineageExperimentId(activeExperiment.id);
                  setLineageModalOpen(true);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Model Metrics Modal */}
      <ModelMetricsModal
        isOpen={modelModalOpen}
        metrics={selectedModelMetrics}
        onClose={() => setModelModalOpen(false)}
      />

      {/* Lineage & Integrity Modal */}
      {lineageModalOpen && lineageExperimentId && (
        <LineageViewer
          experimentId={lineageExperimentId}
          onClose={() => setLineageModalOpen(false)}
        />
      )}

      {/* Model Explainability Modal */}
      {explainModalOpen && selectedExplainModel && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <ExplainabilityViewer
            modelId={selectedExplainModel.id}
            algorithmName={selectedExplainModel.algorithm_name}
            isWinner={selectedExplainModel.is_winner || activeExperiment?.selected_model_id === selectedExplainModel.id}
            hasArtifact={Boolean(selectedExplainModel.artifact_path)}
            onClose={() => {
              setExplainModalOpen(false);
              setSelectedExplainModel(null);
            }}
          />
        </div>
      )}

      {/* Model Deployment & Gate Modal */}
      {deploymentModalOpen && selectedDeploymentModel && (
        <DeploymentGateModal
          model={selectedDeploymentModel}
          isOpen={deploymentModalOpen}
          onClose={() => {
            setDeploymentModalOpen(false);
            setSelectedDeploymentModel(null);
          }}
          onDeploymentSuccess={(dep: any) => {
            setSuccessMsg(`Model successfully deployed into production at ${dep.endpoint_path}`);
          }}
        />
      )}

      {/* Model Passport Governance Modal */}
      {passportModalOpen && selectedPassportModelId && (
        <ModelPassportModal
          modelId={selectedPassportModelId}
          onClose={() => {
            setPassportModalOpen(false);
            setSelectedPassportModelId(null);
          }}
        />
      )}

      {/* Experiment Health Report Modal */}
      {healthModalOpen && healthExperimentId && (
        <ExperimentHealthModal
          experimentId={healthExperimentId}
          onClose={() => {
            setHealthModalOpen(false);
            setHealthExperimentId(null);
          }}
        />
      )}
    </div>
  );
};

export default ModelTraining;
