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
        } else {
          setSelectedExperimentId('');
          setCurrentExperiment(null);
        }

        // Get leaderboard
        try {
          const lbRes = await modelApi.getLeaderboard(selectedProjectId);
          setLeaderboard(lbRes.data || []);
        } catch (lbErr) {
          console.warn('Could not load leaderboard', lbErr);
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
          <span className="px-2.5 py-1 rounded-full font-mono text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>GOOD_FIT</span>
          </span>
        );
      case 'POTENTIAL_OVERFIT':
        return (
          <span className="px-2.5 py-1 rounded-full font-mono text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center space-x-1">
            <Flame className="w-3 h-3 text-amber-400" />
            <span>POTENTIAL_OVERFIT</span>
          </span>
        );
      case 'POTENTIAL_UNDERFIT_WEAK_SIGNAL':
        return (
          <span className="px-2.5 py-1 rounded-full font-mono text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center space-x-1">
            <TrendingUp className="w-3 h-3 text-purple-400" />
            <span>UNDERFIT_WEAK_SIGNAL</span>
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return (
          <span className="px-2.5 py-1 rounded-full font-mono text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30 flex items-center space-x-1">
            <HelpCircle className="w-3 h-3 text-slate-400" />
            <span>INSUFFICIENT_DATA</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full font-mono text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
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
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-1">
            <span>Stage 6 of 8</span>
            <span>&bull;</span>
            <span>Diagnostics & Model Insights</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white flex items-center space-x-2">
            <span>Model Health & Decision Trace</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Direction-aware generalization gap analysis, traceable dataset recommendations, and why-not model selection comparison.
          </p>
        </div>

        {/* Action Controls & Navigation */}
        <div className="flex items-center space-x-3">
          <Link
            to={`/machine-learning?project_id=${selectedProjectId}`}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
          >
            <span>Next: Leaderboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Project & Experiment Selector Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-400">Project:</span>
            <select
              value={selectedProjectId}
              onChange={handleProjectChange}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-medium text-white focus:outline-none focus:border-cyan-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_name} ({p.task_type || 'Unset'})
                </option>
              ))}
            </select>
          </div>

          {experiments.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-slate-400">Experiment:</span>
              <select
                value={selectedExperimentId}
                onChange={(e) => setSelectedExperimentId(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
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
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono">
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
              Target: {currentProject.target_column || 'None'}
            </span>
            <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-bold">
              Metric: {primaryMetricName.toUpperCase()} ({selectionDirection})
            </span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveTab('fit_diagnosis')}
          className={`pb-3 px-4 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'fit_diagnosis'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Stethoscope className="w-4 h-4" />
          <span>Fit Diagnosis & Generalization Gaps</span>
          {trainedModels.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300">
              {trainedModels.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('why_not')}
          className={`pb-3 px-4 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'why_not'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Trophy className="w-4 h-4 text-amber-400" />
          <span>Why-Not Selection Comparison</span>
          {candidateModels.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-[10px] text-amber-300 font-mono">
              {candidateModels.length} Rejected
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('recommendations')}
          className={`pb-3 px-4 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'recommendations'
              ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>Traceable Recommendations</span>
          {recommendations.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-[10px] text-indigo-300">
              {recommendations.length}
            </span>
          )}
        </button>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="p-16 text-center text-slate-400 space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs">Loading diagnostics and candidate evaluations...</p>
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {trainedModels.length === 0 ? (
                  <div className="col-span-full p-8 text-center bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-400 space-y-2">
                    <Activity className="w-8 h-8 mx-auto text-slate-600" />
                    <p className="text-sm font-semibold text-slate-300">No trained models found for this experiment.</p>
                    <p className="text-xs text-slate-500">
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
                        className={`p-5 rounded-2xl border transition-all ${
                          isWinner
                            ? 'bg-slate-900/90 border-cyan-500/50 shadow-lg shadow-cyan-500/5'
                            : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
                        } space-y-4`}
                      >
                        {/* Card Header */}
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <h3 className="text-sm font-bold text-white">{model.algorithm_name}</h3>
                              {isWinner && (
                                <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center space-x-1">
                                  <Trophy className="w-2.5 h-2.5" />
                                  <span>Winner</span>
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">ID: {model.id.slice(0, 8)}</span>
                          </div>
                          {renderFitBadge(model.fit_diagnosis)}
                        </div>

                        {/* Scores Grid */}
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800">
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">CV Mean</span>
                            <div className="text-sm font-bold text-white mt-0.5">
                              {cvScore != null ? cvScore.toFixed(4) : 'N/A'}
                            </div>
                          </div>
                          <div className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800">
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">Train Mean</span>
                            <div className="text-sm font-bold text-slate-300 mt-0.5">
                              {trainScore != null ? trainScore.toFixed(4) : 'N/A'}
                            </div>
                          </div>
                        </div>

                        {/* Generalization Gap Meter */}
                        {gapPercent != null && (
                          <div className="space-y-1.5 pt-1">
                            <div className="flex justify-between text-[11px] font-mono">
                              <span className="text-slate-400">Generalization Gap:</span>
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
                            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
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
                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-2 border-t border-slate-800/80">
                          <div>
                            <span>Score: </span>
                            <span className="font-bold text-slate-200">
                              {model.model_selection_score != null ? Number(model.model_selection_score).toFixed(4) : 'N/A'}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedPassportModelId(model.id);
                              setPassportModalOpen(true);
                            }}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-semibold flex items-center space-x-1 cursor-pointer transition text-[10px]"
                            title="View Technical Model Passport"
                          >
                            <FileText className="w-3 h-3" />
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
                <div className="p-5 rounded-2xl bg-gradient-to-r from-cyan-950/40 via-slate-900 to-indigo-950/40 border border-cyan-500/40 shadow-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-cyan-500/20 text-cyan-300 rounded-xl border border-cyan-500/30 shadow-inner">
                        <Trophy className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h2 className="text-base font-bold text-white">
                            Authoritative Winner: {winningModel.algorithm_name}
                          </h2>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                            Selected
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 font-mono mt-0.5">
                          Artifact SHA-256: {winningModel.artifact_checksum ? winningModel.artifact_checksum.slice(0, 16) + '...' : 'Verified'}
                        </p>
                      </div>
                    </div>

                    <div className="text-right font-mono flex flex-col items-end">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Winning Metric</span>
                      <div className="text-lg font-black text-cyan-300">
                        {getPrimaryCvMetric(winningModel, primaryMetricName)?.toFixed(4) || 'N/A'}
                      </div>
                      <button
                        onClick={() => {
                          setSelectedPassportModelId(winningModel.id);
                          setPassportModalOpen(true);
                        }}
                        className="mt-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-500/30 text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer"
                        title="View Technical Governance Model Passport"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Model Passport</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Rejected Candidates Why-Not Comparison List */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                  <HelpCircle className="w-4 h-4 text-amber-400" />
                  <span>Why-Not Rationales for Rejected Candidates</span>
                </h3>

                {candidateModels.length === 0 ? (
                  <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-400 space-y-1">
                    <p className="text-xs">No competing candidates evaluated in this experiment.</p>
                  </div>
                ) : (
                  candidateModels.map((candidate) => {
                    const candCv = getPrimaryCvMetric(candidate, primaryMetricName);
                    const winCv = getPrimaryCvMetric(winningModel, primaryMetricName);

                    const whyNotReason = generateWhyNotReason(candidate, winningModel);

                    return (
                      <div
                        key={candidate.id}
                        className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 space-y-4 transition"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center space-x-3">
                            <span className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-bold">
                              Rejected
                            </span>
                            <div>
                              <h4 className="text-sm font-bold text-white">{candidate.algorithm_name}</h4>
                              <span className="text-[10px] font-mono text-slate-500">ID: {candidate.id.slice(0, 8)}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {renderFitBadge(candidate.fit_diagnosis)}
                            <button
                              onClick={() => {
                                setSelectedPassportModelId(candidate.id);
                                setPassportModalOpen(true);
                              }}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 font-semibold flex items-center space-x-1 cursor-pointer transition text-[10px]"
                              title="View Model Passport"
                            >
                              <FileText className="w-3 h-3" />
                              <span>Passport</span>
                            </button>
                          </div>
                        </div>

                        {/* Why Not Explanation Callout */}
                        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 flex items-start space-x-3 text-xs text-slate-300">
                          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-amber-300">Rejection Rationale: </span>
                            <span>{whyNotReason}</span>
                          </div>
                        </div>

                        {/* Head-to-Head Metric Comparison */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                          <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-400">Candidate CV</span>
                            <div className="font-bold text-white mt-0.5">{candCv != null ? candCv.toFixed(4) : 'N/A'}</div>
                          </div>
                          <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-400">Winner CV</span>
                            <div className="font-bold text-cyan-300 mt-0.5">{winCv != null ? winCv.toFixed(4) : 'N/A'}</div>
                          </div>
                          <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-400">Candidate Score</span>
                            <div className="font-bold text-slate-300 mt-0.5">{candidate.model_selection_score != null ? Number(candidate.model_selection_score).toFixed(3) : 'N/A'}</div>
                          </div>
                          <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-400">Winner Score</span>
                            <div className="font-bold text-cyan-300 mt-0.5">{winningModel?.model_selection_score != null ? Number(winningModel.model_selection_score).toFixed(3) : 'N/A'}</div>
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
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>Automated Dataset & Model Health Recommendations ({recommendations.length})</span>
                </h3>
              </div>

              {recommendations.length === 0 ? (
                <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl text-slate-400 space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-sm font-semibold text-slate-200">No active health warnings or recommendations</p>
                  <p className="text-xs text-slate-500">Dataset and model metrics adhere to all quality heuristics.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recommendations.map((rec, idx) => (
                    <div
                      key={rec.id || idx}
                      className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3 hover:border-slate-700 transition"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                            <span>{rec.finding}</span>
                          </h4>
                          {rec.evidence && (
                            <div className="text-xs font-mono text-cyan-300 bg-cyan-950/40 px-2.5 py-1 rounded border border-cyan-500/20 inline-block">
                              Evidence: {rec.evidence}
                            </div>
                          )}
                        </div>

                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                              rec.confidence_level === 'HIGH'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : rec.confidence_level === 'MEDIUM'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {rec.confidence_level || 'HIGH'} Confidence
                          </span>
                        </div>
                      </div>

                      {/* Prescriptive Action */}
                      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-300 flex items-start space-x-2">
                        <ArrowRight className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold text-cyan-300">Recommended Action: </span>
                          <span>{rec.recommended_action}</span>
                        </div>
                      </div>

                      {/* Risk Note */}
                      {rec.risk_note && (
                        <div className="text-[11px] text-slate-400 flex items-center space-x-2 font-mono">
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
