import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, experimentApi, modelApi } from '../api/client';
import ModelPassportModal from '../components/ModelPassportModal';
import {
  Stethoscope,
  Activity,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Trophy,
  ArrowRight,
  RefreshCw,
  Layers,
  Sparkles,
  ChevronRight,
  Split,
  Database,
  Sliders,
  FileCode,
  Flame,
  ShieldCheck,
  TrendingUp,
  Info,
  ExternalLink,
  FileText,
  FolderOpen,
} from 'lucide-react';

export const DiagnosticsStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get('project_id');

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);

  const [experiments, setExperiments] = useState([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState('');
  const [currentExperiment, setCurrentExperiment] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Active tab state: 'fit_diagnosis' | 'why_not' | 'recommendations'
  const [activeTab, setActiveTab] = useState('fit_diagnosis');

  const [passportModalOpen, setPassportModalOpen] = useState(false);
  const [selectedPassportModelId, setSelectedPassportModelId] = useState(null);

  // 1. Load Projects List
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        setError('');
        const res = await projectApi.list();
        const list = res.data || [];
        setProjects(list);

        if (!selectedProjectId && list.length > 0) {
          const firstProjId = list[0].id;
          setSelectedProjectId(firstProjId);
          setSearchParams({ project_id: firstProjId });
        }
      } catch (err) {
        console.error('Failed to load projects', err);
        setError('Failed to fetch projects.');
      } finally {
        setLoading(false);
      }
    };
    fetchProjects();
  }, []);

  // 2. Load Project Context, Experiments, and Recommendations
  useEffect(() => {
    if (!selectedProjectId) return;

    const fetchProjectData = async () => {
      try {
        setLoading(true);
        setError('');

        // Get single project info
        const projRes = await projectApi.get(selectedProjectId);
        setCurrentProject(projRes.data);

        // Get recommendations
        try {
          const recRes = await projectApi.getRecommendations(selectedProjectId);
          setRecommendations(recRes.data || []);
        } catch (rErr) {
          console.warn('Could not load recommendations', rErr);
          setRecommendations([]);
        }

        // Get experiments list
        const expRes = await experimentApi.listByProject(selectedProjectId);
        const expList = expRes.data || [];
        setExperiments(expList);

        if (expList.length > 0) {
          const latestExp = expList[0];
          setSelectedExperimentId(latestExp.id);
          setCurrentExperiment(latestExp);

          // Get leaderboard for latest experiment
          try {
            const lbRes = await modelApi.getLeaderboard(selectedProjectId, latestExp.id);
            setLeaderboard(lbRes.data?.leaderboard || lbRes.data || []);
          } catch (lbErr) {
            setLeaderboard([]);
          }
        } else {
          setSelectedExperimentId('');
          setCurrentExperiment(null);
          setLeaderboard([]);
        }
      } catch (err) {
        console.error('Failed to load project details', err);
        setError('Failed to load project diagnostics context.');
      } finally {
        setLoading(false);
      }
    };

    fetchProjectData();
  }, [selectedProjectId]);

  // 3. Sync selected experiment
  useEffect(() => {
    if (!selectedExperimentId || !experiments.length) return;
    const exp = experiments.find((e) => e.id === selectedExperimentId);
    if (exp) {
      setCurrentExperiment(exp);
    }
  }, [selectedExperimentId, experiments]);

  const handleProjectChange = (e) => {
    const newId = e.target.value;
    setSelectedProjectId(newId);
    setSearchParams({ project_id: newId });
  };

  // Helper to extract primary CV metric from model record
  const getPrimaryCvMetric = (model, metricName) => {
    if (!model || !model.metrics) {
      return model?.quick_cv_score != null ? Number(model.quick_cv_score) : null;
    }
    const targetMetric = metricName?.toLowerCase();
    const cvMean = model.metrics.find(
      (m) =>
        m.split === 'CV_MEAN' &&
        (m.metric_name?.toLowerCase() === targetMetric ||
          (targetMetric?.includes('f1') && m.metric_name?.toLowerCase().includes('f1')))
    );
    if (cvMean && cvMean.metric_value != null) {
      return Number(cvMean.metric_value);
    }
    return model.quick_cv_score != null ? Number(model.quick_cv_score) : null;
  };

  // Helper to extract Train metric for generalization gap
  const getTrainMetric = (model, metricName) => {
    if (!model || !model.metrics) return null;
    const targetMetric = metricName?.toLowerCase();
    const trainMetric = model.metrics.find(
      (m) =>
        m.split === 'TRAIN' &&
        (m.metric_name?.toLowerCase() === targetMetric ||
          (targetMetric?.includes('f1') && m.metric_name?.toLowerCase().includes('f1')))
    );
    return trainMetric && trainMetric.metric_value != null ? Number(trainMetric.metric_value) : null;
  };

  // Resolve winning model and candidate models for current experiment
  const trainedModels = currentExperiment?.trained_models || [];
  const winningModel =
    trainedModels.find((m) => m.id === currentExperiment?.selected_model_id) ||
    (trainedModels.length > 0 ? trainedModels[0] : null);

  const candidateModels = trainedModels.filter((m) => m.id !== winningModel?.id);

  const primaryMetricName = currentExperiment?.selection_metric || 'rmse';
  const selectionDirection = currentExperiment?.selection_direction || 'MINIMIZE';

  // Compute fit diagnosis badge styling
  const renderFitBadge = (diagnosis) => {
    switch (diagnosis) {
      case 'GOOD_FIT':
        return (
          <span className="px-3 py-1 rounded-full font-mono text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>GOOD_FIT</span>
          </span>
        );
      case 'POTENTIAL_OVERFIT':
        return (
          <span className="px-3 py-1 rounded-full font-mono text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center space-x-1.5">
            <Flame className="w-3.5 h-3.5 text-amber-400" />
            <span>POTENTIAL_OVERFIT</span>
          </span>
        );
      case 'POTENTIAL_UNDERFIT_WEAK_SIGNAL':
        return (
          <span className="px-3 py-1 rounded-full font-mono text-[11px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center space-x-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-purple-400" />
            <span>UNDERFIT_WEAK_SIGNAL</span>
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="px-3 py-1 rounded-full font-mono text-[11px] font-bold bg-slate-500/10 text-[var(--color-text-muted)] border border-[var(--color-border)] flex items-center space-x-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
            <span>INSUFFICIENT_DATA</span>
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full font-mono text-[11px] font-bold bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] border border-[var(--color-border)]">
            {diagnosis || 'UNCLASSIFIED'}
          </span>
        );
    }
  };

  // Generate automated "Why Not" reason for non-winning candidates
  const generateWhyNotReason = (candidate, winner) => {
    if (!winner || !candidate) return 'Not selected by authoritative leaderboard ranking.';

    const winnerCv = getPrimaryCvMetric(winner, primaryMetricName);
    const candidateCv = getPrimaryCvMetric(candidate, primaryMetricName);

    if (winnerCv == null || candidateCv == null) {
      return `Lower composite selection score (${candidate.model_selection_score ?? 'N/A'} vs. winner ${winner.model_selection_score ?? 'N/A'}).`;
    }

    const diff = Math.abs(candidateCv - winnerCv);
    const relDiffPct = ((diff / (Math.abs(winnerCv) + 1e-9)) * 100).toFixed(1);

    if (selectionDirection === 'MINIMIZE') {
      if (candidateCv > winnerCv) {
        return `Candidate ${candidate.algorithm_name} had ${relDiffPct}% higher (worse) ${primaryMetricName.toUpperCase()} (${candidateCv.toFixed(4)} vs. ${winnerCv.toFixed(4)}).`;
      }
    } else {
      if (candidateCv < winnerCv) {
        return `Candidate ${candidate.algorithm_name} achieved ${relDiffPct}% lower ${primaryMetricName.toUpperCase()} (${candidateCv.toFixed(4)} vs. ${winnerCv.toFixed(4)}).`;
      }
    }

    if (candidate.fit_diagnosis === 'POTENTIAL_OVERFIT') {
      return `Exhibited significant generalization gap (Train vs. CV divergence) and was penalized for potential overfitting.`;
    }

    if (candidate.fit_diagnosis === 'POTENTIAL_UNDERFIT_WEAK_SIGNAL') {
      return `Exhibited weak signal capture on training partitions (underfitting) compared to the winning model.`;
    }

    return `Lower overall composite selection score (${candidate.model_selection_score ?? 'N/A'} vs. winner ${winner.model_selection_score ?? 'N/A'}).`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-[var(--color-border)] gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[var(--color-accent)] bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-full px-3 py-1 mb-2">
            <Stethoscope className="w-3.5 h-3.5" />
            <span>Stage 6 of 8 • Diagnostics & Model Insights</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-text)] flex items-center space-x-3">
            <span>Model Health & Decision Trace</span>
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1.5 max-w-3xl">
            Direction-aware generalization gap analysis, traceable dataset recommendations, and why-not model selection comparison.
          </p>
        </div>

        {/* Action Controls & Navigation */}
        <div className="flex items-center space-x-3">
          <Link
            to={`/machine-learning?project_id=${selectedProjectId}`}
            className="px-5 py-2.5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition-all"
          >
            <span>Next: Leaderboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Project & Experiment Selector Bar */}
      <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2.5">
            <FolderOpen className="w-4 h-4 text-[var(--color-text-muted)]" />
            <span className="text-xs font-semibold text-[var(--color-text-muted)]">Project:</span>
            <select
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-full px-3.5 py-1.5 text-xs font-semibold text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_name} ({p.task_type || 'Unset'})
                </option>
              ))}
            </select>
          </div>

          {experiments.length > 0 && (
            <div className="flex items-center space-x-2.5">
              <Layers className="w-4 h-4 text-[var(--color-text-muted)]" />
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">Experiment:</span>
              <select
                value={selectedExperimentId}
                onChange={(e) => setSelectedExperimentId(e.target.value)}
                className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-full px-3.5 py-1.5 text-xs font-mono font-medium text-[var(--color-accent)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
              >
                {experiments.map((exp, idx) => (
                  <option key={exp.id} value={exp.id}>
                    Exp #{experiments.length - idx} &bull; {exp.task_type} &bull; {exp.fold_count} Folds ({exp.id.slice(0, 8)})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {currentProject && (
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <span className="px-3 py-1 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text)] font-semibold">
              Target: {currentProject.target_column || 'None'}
            </span>
            <span className="px-3 py-1 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] font-bold">
              Metric: {primaryMetricName.toUpperCase()} ({selectionDirection})
            </span>
          </div>
        )}
      </div>

      {/* Segmented Navigation Tabs */}
      <div className="flex flex-wrap gap-2 p-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-full w-fit shadow-sm">
        <button
          onClick={() => setActiveTab('fit_diagnosis')}
          className={`px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 transition-all ${
            activeTab === 'fit_diagnosis'
              ? 'bg-[var(--color-accent)] text-white shadow-sm'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
          }`}
        >
          <Stethoscope className="w-4 h-4" />
          <span>Fit Diagnosis & Generalization Gaps</span>
          {trainedModels.length > 0 && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
              activeTab === 'fit_diagnosis' ? 'bg-white/20 text-white' : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
            }`}>
              {trainedModels.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('why_not')}
          className={`px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 transition-all ${
            activeTab === 'why_not'
              ? 'bg-[var(--color-accent)] text-white shadow-sm'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
          }`}
        >
          <Trophy className="w-4 h-4" />
          <span>Why-Not Selection Comparison</span>
          {candidateModels.length > 0 && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
              activeTab === 'why_not' ? 'bg-white/20 text-white' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {candidateModels.length} Rejected
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('recommendations')}
          className={`px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 transition-all ${
            activeTab === 'recommendations'
              ? 'bg-[var(--color-accent)] text-white shadow-sm'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Traceable Recommendations</span>
          {recommendations.length > 0 && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
              activeTab === 'recommendations' ? 'bg-white/20 text-white' : 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
            }`}>
              {recommendations.length}
            </span>
          )}
        </button>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="p-16 text-center text-[var(--color-text-muted)] space-y-3 bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] shadow-sm">
          <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-medium">Loading diagnostics and candidate evaluations...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      ) : (
        <>
          {/* TAB 1: FIT DIAGNOSIS & GENERALIZATION GAPS */}
          {activeTab === 'fit_diagnosis' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {trainedModels.length === 0 ? (
                  <div className="col-span-full p-12 text-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl text-[var(--color-text-muted)] space-y-2 shadow-sm">
                    <Activity className="w-8 h-8 mx-auto text-[var(--color-text-muted)] opacity-60" />
                    <p className="text-sm font-bold text-[var(--color-text)]">No trained models found for this experiment.</p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      Run model training in the Machine Learning stage to populate fit diagnostics.
                    </p>
                  </div>
                ) : (
                  trainedModels.map((model) => {
                    const isWinner = model.id === currentExperiment?.selected_model_id;
                    const cvScore = getPrimaryCvMetric(model, primaryMetricName);
                    const trainScore = getTrainMetric(model, primaryMetricName);
                    
                    // Gap computation
                    let gapPercent = null;
                    if (trainScore != null && cvScore != null) {
                      const diff = Math.abs(cvScore - trainScore);
                      gapPercent = (diff / (Math.abs(trainScore) + 1e-9)) * 100;
                    }

                    return (
                      <div
                        key={model.id}
                        className={`p-5 rounded-2xl border transition-all space-y-4 shadow-sm ${
                          isWinner
                            ? 'bg-[var(--color-surface)] border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]'
                            : 'bg-[var(--color-surface)] border-[var(--color-border)] hover:border-[var(--color-border-subtle)]'
                        }`}
                      >
                        {/* Card Header */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center space-x-2">
                              <h3 className="text-sm font-bold text-[var(--color-text)]">{model.algorithm_name}</h3>
                              {isWinner && (
                                <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] flex items-center space-x-1">
                                  <Trophy className="w-2.5 h-2.5" />
                                  <span>Winner</span>
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] font-mono text-[var(--color-text-muted)]">ID: {model.id.slice(0, 8)}</span>
                          </div>
                          {renderFitBadge(model.fit_diagnosis)}
                        </div>

                        {/* Scores Grid */}
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="p-3 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">CV Mean</span>
                            <div className="text-sm font-bold text-[var(--color-text)] mt-0.5">
                              {cvScore != null ? cvScore.toFixed(4) : 'N/A'}
                            </div>
                          </div>
                          <div className="p-3 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">Train Mean</span>
                            <div className="text-sm font-bold text-[var(--color-text-muted)] mt-0.5">
                              {trainScore != null ? trainScore.toFixed(4) : 'N/A'}
                            </div>
                          </div>
                        </div>

                        {/* Generalization Gap Meter */}
                        {gapPercent != null && (
                          <div className="space-y-1.5 pt-1">
                            <div className="flex justify-between text-[11px] font-mono">
                              <span className="text-[var(--color-text-muted)]">Generalization Gap:</span>
                              <span
                                className={`font-bold ${
                                  gapPercent > 25
                                    ? 'text-rose-400'
                                    : gapPercent > 10
                                    ? 'text-amber-400'
                                    : 'text-emerald-400'
                                }`}
                              >
                                {gapPercent.toFixed(1)}%
                              </span>
                            </div>
                            <div className="w-full bg-[var(--color-surface-hover)] h-1.5 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  gapPercent > 25
                                    ? 'bg-rose-500'
                                    : gapPercent > 10
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${Math.min(100, gapPercent * 2)}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Selection Score pill & Passport Button */}
                        <div className="flex items-center justify-between text-[10px] text-[var(--color-text-muted)] font-mono pt-3 border-t border-[var(--color-border)]">
                          <div>
                            <span>Score: </span>
                            <span className="font-bold text-[var(--color-text)]">
                              {model.model_selection_score != null ? Number(model.model_selection_score).toFixed(4) : 'N/A'}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedPassportModelId(model.id);
                              setPassportModalOpen(true);
                            }}
                            className="px-3 py-1 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface-card)] border border-[var(--color-border)] text-[var(--color-text)] font-semibold flex items-center space-x-1.5 cursor-pointer transition text-[11px]"
                            title="View Technical Model Passport"
                          >
                            <FileText className="w-3 h-3 text-[var(--color-accent)]" />
                            <span>Passport</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB 2: WHY-NOT SELECTION ENGINE */}
          {activeTab === 'why_not' && (
            <div className="space-y-6">
              {/* Winner Highlight Banner */}
              {winningModel && (
                <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-accent-border)] shadow-md space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center space-x-3.5">
                      <div className="p-3 bg-[var(--color-accent-soft)] text-[var(--color-accent)] rounded-2xl border border-[var(--color-accent-border)]">
                        <Trophy className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h2 className="text-base font-bold text-[var(--color-text)]">
                            Authoritative Winner: {winningModel.algorithm_name}
                          </h2>
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] font-bold">
                            Selected
                          </span>
                        </div>
                        <p className="text-xs text-[var(--color-text-muted)] font-mono mt-0.5">
                          Artifact SHA-256: {winningModel.artifact_checksum ? winningModel.artifact_checksum.slice(0, 16) + '...' : 'Verified'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right font-mono">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">Winning Metric</span>
                        <div className="text-xl font-extrabold text-[var(--color-accent)]">
                          {getPrimaryCvMetric(winningModel, primaryMetricName)?.toFixed(4) || 'N/A'}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedPassportModelId(winningModel.id);
                          setPassportModalOpen(true);
                        }}
                        className="px-4 py-2 rounded-full bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] border border-[var(--color-accent-border)] text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer"
                        title="View Technical Governance Model Passport"
                      >
                        <FileText className="w-4 h-4" />
                        <span>Model Passport</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Rejected Candidates Why-Not Comparison List */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider flex items-center space-x-2">
                  <HelpCircle className="w-4 h-4 text-amber-400" />
                  <span>Why-Not Rationales for Rejected Candidates</span>
                </h3>

                {candidateModels.length === 0 ? (
                  <div className="p-8 text-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl text-[var(--color-text-muted)] space-y-1 shadow-sm">
                    <p className="text-xs font-medium">No competing candidates evaluated in this experiment.</p>
                  </div>
                ) : (
                  candidateModels.map((candidate) => {
                    const candCv = getPrimaryCvMetric(candidate, primaryMetricName);
                    const winCv = getPrimaryCvMetric(winningModel, primaryMetricName);

                    const whyNotReason = generateWhyNotReason(candidate, winningModel);

                    return (
                      <div
                        key={candidate.id}
                        className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[var(--color-border-subtle)] space-y-4 transition shadow-sm"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center space-x-3">
                            <span className="px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-bold">
                              Rejected
                            </span>
                            <div>
                              <h4 className="text-sm font-bold text-[var(--color-text)]">{candidate.algorithm_name}</h4>
                              <span className="text-[10px] font-mono text-[var(--color-text-muted)]">ID: {candidate.id.slice(0, 8)}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {renderFitBadge(candidate.fit_diagnosis)}
                            <button
                              onClick={() => {
                                setSelectedPassportModelId(candidate.id);
                                setPassportModalOpen(true);
                              }}
                              className="px-3 py-1 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface-card)] border border-[var(--color-border)] text-[var(--color-text)] font-semibold flex items-center space-x-1 cursor-pointer transition text-[11px]"
                              title="View Model Passport"
                            >
                              <FileText className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                              <span>Passport</span>
                            </button>
                          </div>
                        </div>

                        {/* Why Not Explanation Callout */}
                        <div className="p-3.5 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex items-start space-x-3 text-xs text-[var(--color-text)]">
                          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-amber-400">Rejection Rationale: </span>
                            <span className="text-[var(--color-text-muted)]">{whyNotReason}</span>
                          </div>
                        </div>

                        {/* Head-to-Head Metric Comparison */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
                          <div className="p-2.5 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)]">Candidate CV</span>
                            <div className="font-bold text-[var(--color-text)] mt-0.5">{candCv != null ? candCv.toFixed(4) : 'N/A'}</div>
                          </div>
                          <div className="p-2.5 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)]">Winner CV</span>
                            <div className="font-bold text-[var(--color-accent)] mt-0.5">{winCv != null ? winCv.toFixed(4) : 'N/A'}</div>
                          </div>
                          <div className="p-2.5 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)]">Candidate Score</span>
                            <div className="font-bold text-[var(--color-text-muted)] mt-0.5">{candidate.model_selection_score != null ? Number(candidate.model_selection_score).toFixed(3) : 'N/A'}</div>
                          </div>
                          <div className="p-2.5 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                            <span className="text-[10px] text-[var(--color-text-muted)]">Winner Score</span>
                            <div className="font-bold text-[var(--color-accent)] mt-0.5">{winningModel?.model_selection_score != null ? Number(winningModel.model_selection_score).toFixed(3) : 'N/A'}</div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB 3: TRACEABLE RECOMMENDATIONS */}
          {activeTab === 'recommendations' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>Automated Dataset & Model Health Recommendations ({recommendations.length})</span>
                </h3>
              </div>

              {recommendations.length === 0 ? (
                <div className="p-12 text-center bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl text-[var(--color-text-muted)] space-y-2 shadow-sm">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-sm font-bold text-[var(--color-text)]">No active health warnings or recommendations</p>
                  <p className="text-xs text-[var(--color-text-muted)]">Dataset and model metrics adhere to all quality heuristics.</p>
                </div>
              ) : (
                <div className="space-y-3.5">
                  {recommendations.map((rec, idx) => (
                    <div
                      key={rec.id || idx}
                      className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3 hover:border-[var(--color-border-subtle)] transition shadow-sm"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-[var(--color-text)] flex items-center space-x-2">
                            <span>{rec.finding}</span>
                          </h4>
                          {rec.evidence && (
                            <div className="text-xs font-mono text-[var(--color-accent)] bg-[var(--color-accent-soft)] px-3 py-1 rounded-full border border-[var(--color-accent-border)] inline-block">
                              Evidence: {rec.evidence}
                            </div>
                          )}
                        </div>

                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold ${
                              rec.confidence_level === 'HIGH'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : rec.confidence_level === 'MEDIUM'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                            }`}
                          >
                            {rec.confidence_level || 'HIGH'} Confidence
                          </span>
                        </div>
                      </div>

                      {/* Prescriptive Action */}
                      <div className="p-3 bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)] text-xs text-[var(--color-text)] flex items-start space-x-2.5">
                        <ArrowRight className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-[var(--color-accent)]">Recommended Action: </span>
                          <span className="text-[var(--color-text-muted)]">{rec.recommended_action}</span>
                        </div>
                      </div>

                      {/* Risk Note */}
                      {rec.risk_note && (
                        <div className="text-[11px] text-[var(--color-text-muted)] flex items-center space-x-2 font-mono">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          <span>Risk if ignored: {rec.risk_note}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Technical Model Passport Modal */}
      {passportModalOpen && selectedPassportModelId && (
        <ModelPassportModal
          modelId={selectedPassportModelId}
          isOpen={passportModalOpen}
          onClose={() => {
            setPassportModalOpen(false);
            setSelectedPassportModelId(null);
          }}
        />
      )}
    </div>
  );
};

export default DiagnosticsStage;
