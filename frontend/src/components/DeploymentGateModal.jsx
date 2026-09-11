import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Play,
  Zap,
  Cpu,
  Clock,
  Download,
  Copy,
  Check,
  Pause,
  StopCircle,
  RefreshCw,
  Sliders,
  ChevronRight,
  Database,
  Lock,
  Layers,
  X,
} from 'lucide-react';
import { modelApi, deploymentApi, predictApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function DeploymentGateModal({ model, isOpen, onClose, onDeploymentSuccess }) {
  const { user } = useAuth();
  const [gate, setGate] = useState(null);
  const [loadingGate, setLoadingGate] = useState(false);
  const [approving, setApproving] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployment, setDeployment] = useState(null);
  const [activeTab, setActiveTab] = useState('gate'); // 'gate' | 'try_it' | 'logs'
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Try-It Form State
  const [inputFeatures, setInputFeatures] = useState({});
  const [rawJsonInput, setRawJsonInput] = useState('{\n  \n}');
  const [isJsonMode, setIsJsonMode] = useState(false);
  const [predictingFast, setPredictingFast] = useState(false);
  const [predictingExplain, setPredictingExplain] = useState(false);
  const [predictResult, setPredictResult] = useState(null);
  const [explainResult, setExplainResult] = useState(null);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [logs, setLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const canDeploy = user?.role === 'ADMIN' || user?.role === 'DEPLOYMENT_MANAGER' || user?.permissions?.includes('DEPLOY');
  const canExport = user?.role === 'ADMIN' || user?.role === 'DEPLOYMENT_MANAGER' || user?.permissions?.includes('EXPORT');

  useEffect(() => {
    if (isOpen && model?.id) {
      loadGateStatus();
      setErrorMsg(null);
      setSuccessMsg(null);
      setPredictResult(null);
      setExplainResult(null);
    }
  }, [isOpen, model?.id]);

  const loadGateStatus = async () => {
    setLoadingGate(true);
    try {
      const res = await modelApi.getDeploymentGate(model.id);
      setGate(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to evaluate deployment gate.');
    } finally {
      setLoadingGate(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    setErrorMsg(null);
    try {
      const res = await modelApi.approveDeploymentGate(model.id);
      setGate(res.data.gate);
      setSuccessMsg('Deployment gate approved successfully.');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Approval failed.');
    } finally {
      setApproving(false);
    }
  };

  const handleDeploy = async () => {
    setDeploying(true);
    setErrorMsg(null);
    try {
      const res = await modelApi.deploy(model.id);
      setDeployment(res.data);
      setSuccessMsg('Model successfully deployed into production LIVE status!');
      setActiveTab('try_it');
      if (onDeploymentSuccess) onDeploymentSuccess(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Deployment failed.');
    } finally {
      setDeploying(false);
    }
  };

  const handleDownload = async (format = 'joblib') => {
    try {
      const res = await modelApi.download(model.id, format);
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `model_${model.algorithm_name}_${model.id.slice(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Download failed.');
    }
  };

  const handleUpdateStatus = async (targetStatus) => {
    if (!deployment?.id) return;
    try {
      const res = await deploymentApi.updateStatus(deployment.id, targetStatus);
      setDeployment(res.data);
      setSuccessMsg(`Deployment status updated to ${targetStatus}.`);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update deployment status.');
    }
  };

  const handleFastPredict = async () => {
    if (!deployment?.id) return;
    setPredictingFast(true);
    setErrorMsg(null);
    setPredictResult(null);
    try {
      const payload = isJsonMode ? JSON.parse(rawJsonInput) : inputFeatures;
      const res = await predictApi.predict(deployment.id, payload);
      setPredictResult(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Prediction failed.');
    } finally {
      setPredictingFast(false);
    }
  };

  const handleExplainPredict = async () => {
    if (!deployment?.id) return;
    setPredictingExplain(true);
    setErrorMsg(null);
    setExplainResult(null);
    try {
      const payload = isJsonMode ? JSON.parse(rawJsonInput) : inputFeatures;
      const res = await predictApi.predictExplain(deployment.id, payload);
      setExplainResult(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Explainable prediction failed.');
    } finally {
      setPredictingExplain(false);
    }
  };

  const loadLogs = async () => {
    if (!deployment?.id) return;
    setLoadingLogs(true);
    try {
      const res = await deploymentApi.getLogs(deployment.id, 50);
      setLogs(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load logs.');
    } finally {
      setLoadingLogs(false);
    }
  };

  const copyEndpoint = () => {
    if (!deployment?.endpoint_path) return;
    navigator.clipboard.writeText(`${window.location.origin}${deployment.endpoint_path}`);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  if (!isOpen) return null;

  const renderGateRow = (title, description, statusVal, isTriState = false) => {
    let icon = <XCircle className="w-5 h-5 text-rose-400" />;
    let badge = <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">FAIL</span>;

    if (isTriState) {
      if (statusVal === 'PASS') {
        icon = <CheckCircle className="w-5 h-5 text-emerald-400" />;
        badge = <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PASS</span>;
      } else if (statusVal === 'UNVERIFIABLE') {
        icon = <AlertTriangle className="w-5 h-5 text-amber-400" />;
        badge = (
          <div className="relative group">
            <span className="cursor-help px-2.5 py-1 text-xs font-bold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
              UNVERIFIABLE
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-72 p-3 bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text)] rounded-xl shadow-xl z-50">
              No frozen threshold was configured at experiment creation, or min_value was left null. A real evaluation threshold must be set before fold execution to guarantee verifiable deployment.
            </div>
          </div>
        );
      }
    } else {
      if (statusVal === true) {
        icon = <CheckCircle className="w-5 h-5 text-emerald-400" />;
        badge = <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PASS</span>;
      }
    }

    return (
      <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] hover:border-[var(--color-border-subtle)] transition-colors">
        <div className="flex items-start gap-3.5">
          <div className="mt-0.5">{icon}</div>
          <div>
            <div className="text-sm font-bold text-[var(--color-text)]">{title}</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>
          </div>
        </div>
        <div className="ml-4 flex-shrink-0">{badge}</div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface-card)]">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--color-text)] flex flex-wrap items-center gap-2">
                Production Deployment Gate
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-accent)] font-mono font-bold">
                  {model?.algorithm_name}
                </span>
              </h2>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                SRS §2.14 / §2.16 Strict Multi-Condition Gatekeeper & Gated Model Serving
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer border border-transparent hover:border-[var(--color-border)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-2.5 gap-2">
          <button
            onClick={() => setActiveTab('gate')}
            className={`py-1.5 px-4 rounded-full text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === 'gate'
                ? 'bg-[var(--color-accent)] text-white shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Gate Checklist</span>
          </button>

          {deployment && (
            <>
              <button
                onClick={() => setActiveTab('try_it')}
                className={`py-1.5 px-4 rounded-full text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
                  activeTab === 'try_it'
                    ? 'bg-[var(--color-accent)] text-white shadow-sm'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
                }`}
              >
                <Zap className="w-4 h-4" />
                <span>Live Inference ("Try It")</span>
              </button>
              <button
                onClick={() => {
                  setActiveTab('logs');
                  loadLogs();
                }}
                className={`py-1.5 px-4 rounded-full text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
                  activeTab === 'logs'
                    ? 'bg-[var(--color-accent)] text-white shadow-sm'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>Inference Audit Logs</span>
              </button>
            </>
          )}
        </div>

        {/* Alerts */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-rose-300 hover:text-white cursor-pointer">✕</button>
          </div>
        )}
        {successMsg && (
          <div className="mx-6 mt-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-300 hover:text-white cursor-pointer">✕</button>
          </div>
        )}

        {/* Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* TAB 1: GATE CHECKLIST */}
          {activeTab === 'gate' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                  Mandatory Verification Checklist (All 6 Required)
                </span>
                <button
                  onClick={loadGateStatus}
                  disabled={loadingGate}
                  className="text-xs text-[var(--color-accent)] hover:underline flex items-center gap-1 cursor-pointer font-semibold"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingGate ? 'animate-spin' : ''}`} />
                  <span>Re-evaluate Gate</span>
                </button>
              </div>

              {loadingGate && !gate ? (
                <div className="p-12 text-center text-[var(--color-text-muted)] text-sm">Evaluating gate conditions...</div>
              ) : (
                <div className="space-y-2.5">
                  {renderGateRow(
                    '1. Locked Test Evaluated',
                    'Model evaluated on authoritative locked test partition (single consumption, never reused diagnostic split).',
                    gate?.locked_test_evaluated
                  )}
                  {renderGateRow(
                    '2. Feature Schema Locked',
                    'Input feature schema derived from feature selection snapshot cross-referenced with dataset columns.',
                    gate?.schema_locked
                  )}
                  {renderGateRow(
                    '3. Artifact Cryptographically Verified',
                    'Disk artifact integrity verified via SHA-256 checksum recheck right now.',
                    gate?.artifact_verified
                  )}
                  {renderGateRow(
                    '4. Lineage Capture Complete',
                    'Experiment config, transformation snapshot, feature selection snapshot, and all 6 environment fields are non-null.',
                    gate?.lineage_complete
                  )}
                  {renderGateRow(
                    '5. Performance Threshold Passed',
                    'Frozen creation threshold evaluated against Locked Test metric in required direction.',
                    gate?.performance_threshold_passed,
                    true
                  )}
                  {renderGateRow(
                    '6. User Approved',
                    'Explicit manual sign-off by an authorized user holding DEPLOY permission.',
                    gate?.user_approved
                  )}
                </div>
              )}

              {/* Gate Actions */}
              <div className="mt-6 pt-6 border-t border-[var(--color-border)] flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  {canExport && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDownload('joblib')}
                        className="px-4 py-2 text-xs font-semibold rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] flex items-center gap-1.5 transition-colors cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                        <span>Download (.joblib)</span>
                      </button>
                      <button
                        onClick={() => handleDownload('pkl')}
                        className="px-4 py-2 text-xs font-semibold rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] flex items-center gap-1.5 transition-colors cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                        <span>Download (.pkl)</span>
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {!gate?.user_approved && canDeploy && (
                    <button
                      onClick={handleApprove}
                      disabled={approving || loadingGate}
                      className="px-5 py-2 text-xs font-bold rounded-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Check className="w-4 h-4" />
                      <span>{approving ? 'Approving...' : 'Approve Gate'}</span>
                    </button>
                  )}

                  <button
                    onClick={handleDeploy}
                    disabled={!gate?.gate_passed || deploying || loadingGate}
                    className={`px-6 py-2.5 text-xs font-bold rounded-full flex items-center gap-2 transition-all cursor-pointer ${
                      gate?.gate_passed
                        ? 'bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white shadow-lg shadow-[var(--color-accent-soft)]'
                        : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] cursor-not-allowed border border-[var(--color-border)]'
                    }`}
                  >
                    <Play className="w-4 h-4 fill-current" />
                    <span>{deploying ? 'Deploying...' : 'Deploy to Production'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LIVE INFERENCE ("TRY IT") */}
          {activeTab === 'try_it' && (
            <div className="space-y-6">
              
              {/* Deployment Info Banner */}
              <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--color-text)]">Endpoint:</span>
                    <code className="text-xs px-2.5 py-1 rounded-full bg-[var(--color-surface)] text-[var(--color-accent)] font-mono border border-[var(--color-border)]">
                      {deployment?.endpoint_path}
                    </code>
                    <button
                      onClick={copyEndpoint}
                      className="p-1.5 hover:text-[var(--color-text)] text-[var(--color-text-muted)] transition-colors cursor-pointer"
                      title="Copy Endpoint"
                    >
                      {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-1.5 flex items-center gap-3">
                    <span>Status: <strong className={`font-semibold ${deployment?.status === 'LIVE' ? 'text-emerald-400' : 'text-amber-400'}`}>{deployment?.status}</strong></span>
                    <span>•</span>
                    <span>Retention: {deployment?.log_retention_days} Days</span>
                  </div>
                </div>

                {/* Status controls */}
                {canDeploy && (
                  <div className="flex items-center gap-2">
                    {deployment?.status === 'LIVE' && (
                      <button
                        onClick={() => handleUpdateStatus('PAUSED')}
                        className="px-4 py-1.5 text-xs font-bold rounded-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 cursor-pointer"
                      >
                        <Pause className="w-3.5 h-3.5" /> <span>Pause</span>
                      </button>
                    )}
                    {deployment?.status === 'PAUSED' && (
                      <button
                        onClick={() => handleUpdateStatus('LIVE')}
                        className="px-4 py-1.5 text-xs font-bold rounded-full bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 cursor-pointer"
                      >
                        <Play className="w-3.5 h-3.5" /> <span>Resume</span>
                      </button>
                    )}
                    {deployment?.status !== 'RETIRED' && (
                      <button
                        onClick={() => handleUpdateStatus('RETIRED')}
                        className="px-4 py-1.5 text-xs font-bold rounded-full bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1.5 cursor-pointer"
                      >
                        <StopCircle className="w-3.5 h-3.5" /> <span>Retire</span>
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Inference Input */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-[var(--color-text)]">Input Payload (JSON format)</label>
                  <button
                    onClick={() => {
                      setRawJsonInput('{\n  "feature_1": 10,\n  "feature_2": 2.5\n}');
                    }}
                    className="text-xs text-[var(--color-accent)] hover:underline cursor-pointer font-semibold"
                  >
                    Insert Sample
                  </button>
                </div>
                <textarea
                  value={rawJsonInput}
                  onChange={(e) => setRawJsonInput(e.target.value)}
                  rows={4}
                  className="w-full p-3 font-mono text-xs bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                  placeholder='{\n  "sqft": 1500,\n  "bedrooms": 3\n}'
                />
              </div>

              {/* Trigger Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <button
                  onClick={handleFastPredict}
                  disabled={predictingFast || predictingExplain || deployment?.status !== 'LIVE'}
                  className="w-full sm:flex-1 py-3 px-5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-[var(--color-accent-soft)] disabled:opacity-50 cursor-pointer"
                >
                  <Zap className="w-4 h-4" />
                  <span>{predictingFast ? 'Running...' : 'Fast Predict (/predict)'}</span>
                </button>
                <button
                  onClick={handleExplainPredict}
                  disabled={predictingFast || predictingExplain || deployment?.status !== 'LIVE'}
                  className="w-full sm:flex-1 py-3 px-5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] font-bold text-xs flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>{predictingExplain ? 'Explaining...' : 'Predict + Explain (/predict/.../explain)'}</span>
                </button>
              </div>

              {/* Fast Prediction Output Card */}
              {predictResult && (
                <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-accent-border)] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--color-accent)] flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5" /> Fast Inference Result
                    </span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                      {predictResult.latency_ms} ms Latency
                    </span>
                  </div>
                  <div className="text-2xl font-black text-[var(--color-text)] font-mono">
                    {String(predictResult.prediction)}
                  </div>
                  {predictResult.probabilities && (
                    <div className="text-xs text-[var(--color-text-muted)] font-mono">
                      Probabilities: {JSON.stringify(predictResult.probabilities)}
                    </div>
                  )}
                </div>
              )}

              {/* Explainable Prediction Output Card */}
              {explainResult && (
                <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--color-accent)] flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" /> Explainable Inference Breakdown
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-surface)] text-[var(--color-text-muted)] font-mono border border-[var(--color-border)]">
                        Base: {explainResult.latency_ms} ms
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-mono border border-[var(--color-accent-border)]">
                        SHAP: {explainResult.explanation_latency_ms} ms
                      </span>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                        Total: {explainResult.total_latency_ms} ms
                      </span>
                    </div>
                  </div>

                  <div className="text-2xl font-black text-[var(--color-text)] font-mono">
                    Prediction: {String(explainResult.prediction)}
                  </div>

                  <div className="space-y-2 border-t border-[var(--color-border)] pt-3">
                    <span className="text-xs font-bold text-[var(--color-text)]">Feature Contributions (SHAP)</span>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {Object.entries(explainResult.explanation?.contributions || {}).map(([feat, val]) => (
                        <div key={feat} className="flex items-center justify-between text-xs font-mono p-2 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                          <span className="text-[var(--color-text)]">{feat}</span>
                          <span className={val >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                            {val >= 0 ? `+${val}` : val}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] flex justify-between font-mono pt-1">
                      <span>Base Value: {explainResult.explanation?.base_value}</span>
                      <span>Sum: {explainResult.explanation?.sum_contributions_plus_base}</span>
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 3: AUDIT LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                  Live Prediction Audit Stream (SRS §2.15)
                </span>
                <button
                  onClick={loadLogs}
                  disabled={loadingLogs}
                  className="text-xs text-[var(--color-accent)] hover:underline flex items-center gap-1 cursor-pointer font-semibold"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingLogs ? 'animate-spin' : ''}`} />
                  <span>Refresh Logs</span>
                </button>
              </div>

              {loadingLogs && logs.length === 0 ? (
                <div className="p-8 text-center text-[var(--color-text-muted)] text-xs">Loading logs...</div>
              ) : logs.length === 0 ? (
                <div className="p-8 text-center text-[var(--color-text-muted)] text-xs">No prediction requests logged yet.</div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--color-surface)] text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                      <tr>
                        <th className="p-3">Time</th>
                        <th className="p-3">Request ID</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Base Latency</th>
                        <th className="p-3">SHAP Latency</th>
                        <th className="p-3">Payload Mode</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)] font-mono">
                      {logs.map((log) => (
                        <tr key={log.id} className="hover:bg-[var(--color-surface-hover)]">
                          <td className="p-3 text-[var(--color-text-muted)]">
                            {new Date(log.requested_at).toLocaleTimeString()}
                          </td>
                          <td className="p-3 text-[var(--color-text)]">{log.request_id.slice(0, 8)}...</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              log.status === 'SUCCESS'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {log.status}
                            </span>
                          </td>
                          <td className="p-3 text-[var(--color-accent)]">{log.latency_ms} ms</td>
                          <td className="p-3 text-cyan-400">
                            {log.explanation_latency_ms != null ? `${log.explanation_latency_ms} ms` : '—'}
                          </td>
                          <td className="p-3 text-[var(--color-text-muted)]">{log.payload_mode}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
