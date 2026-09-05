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
    let icon = <XCircle className="w-5 h-5 text-red-400" />;
    let badge = <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-red-500/10 text-red-400 border border-red-500/20">FAIL</span>;

    if (isTriState) {
      if (statusVal === 'PASS') {
        icon = <CheckCircle className="w-5 h-5 text-emerald-400" />;
        badge = <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PASS</span>;
      } else if (statusVal === 'UNVERIFIABLE') {
        icon = <AlertTriangle className="w-5 h-5 text-amber-400" />;
        badge = (
          <div className="relative group">
            <span className="cursor-help px-2.5 py-1 text-xs font-semibold rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
              UNVERIFIABLE
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-72 p-2.5 bg-slate-900 border border-slate-700 text-xs text-slate-300 rounded-lg shadow-xl z-50">
              No frozen threshold was configured at experiment creation, or min_value was left null. A real evaluation threshold must be set before fold execution to guarantee verifiable deployment.
            </div>
          </div>
        );
      }
    } else {
      if (statusVal === true) {
        icon = <CheckCircle className="w-5 h-5 text-emerald-400" />;
        badge = <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PASS</span>;
      }
    }

    return (
      <div className="flex items-center justify-between p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/50 hover:border-slate-600 transition-colors">
        <div className="flex items-start gap-3">
          <div className="mt-0.5">{icon}</div>
          <div>
            <div className="text-sm font-semibold text-slate-200">{title}</div>
            <div className="text-xs text-slate-400">{description}</div>
          </div>
        </div>
        <div className="ml-4 flex-shrink-0">{badge}</div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Production Deployment Gate
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                  {model?.algorithm_name}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                SRS §2.14 / §2.16 Strict Multi-Condition Gatekeeper & Gated Model Serving
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2">
          <button
            onClick={() => setActiveTab('gate')}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'gate'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Gate Checklist
          </button>

          {deployment && (
            <>
              <button
                onClick={() => setActiveTab('try_it')}
                className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
                  activeTab === 'try_it'
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap className="w-4 h-4" />
                Live Inference ("Try It")
              </button>
              <button
                onClick={() => {
                  setActiveTab('logs');
                  loadLogs();
                }}
                className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
                  activeTab === 'logs'
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Clock className="w-4 h-4" />
                Inference Audit Logs
              </button>
            </>
          )}
        </div>

        {/* Alerts */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-red-300 hover:text-white">✕</button>
          </div>
        )}
        {successMsg && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center justify-between">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-300 hover:text-white">✕</button>
          </div>
        )}

        {/* Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* TAB 1: GATE CHECKLIST */}
          {activeTab === 'gate' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Mandatory Verification Checklist (All 6 Required)
                </span>
                <button
                  onClick={loadGateStatus}
                  disabled={loadingGate}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingGate ? 'animate-spin' : ''}`} />
                  Re-evaluate Gate
                </button>
              </div>

              {loadingGate && !gate ? (
                <div className="p-12 text-center text-slate-400 text-sm">Evaluating gate conditions...</div>
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
              <div className="mt-6 pt-6 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  {canExport && (
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleDownload('joblib')}
                        className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download (.joblib)
                      </button>
                      <button
                        onClick={() => handleDownload('pkl')}
                        className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download (.pkl)
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {!gate?.user_approved && canDeploy && (
                    <button
                      onClick={handleApprove}
                      disabled={approving || loadingGate}
                      className="px-4 py-2 text-xs font-semibold rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 transition-colors"
                    >
                      <Check className="w-4 h-4" />
                      {approving ? 'Approving...' : 'Approve Gate'}
                    </button>
                  )}

                  <button
                    onClick={handleDeploy}
                    disabled={!gate?.gate_passed || deploying || loadingGate}
                    className={`px-5 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
                      gate?.gate_passed
                        ? 'bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 text-white shadow-lg shadow-indigo-500/20'
                        : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                    }`}
                  >
                    <Play className="w-4 h-4 fill-current" />
                    {deploying ? 'Deploying...' : 'Deploy to Production'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LIVE INFERENCE ("TRY IT") */}
          {activeTab === 'try_it' && (
            <div className="space-y-6">
              
              {/* Deployment Info Banner */}
              <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-300">Endpoint:</span>
                    <code className="text-xs px-2 py-0.5 rounded bg-slate-900 text-indigo-400 font-mono">
                      {deployment?.endpoint_path}
                    </code>
                    <button
                      onClick={copyEndpoint}
                      className="p-1 hover:text-indigo-300 text-slate-400 transition-colors"
                      title="Copy Endpoint"
                    >
                      {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                    <span>Status: <strong className={`font-semibold ${deployment?.status === 'LIVE' ? 'text-emerald-400' : 'text-amber-400'}`}>{deployment?.status}</strong></span>
                    <span>Retention: {deployment?.log_retention_days} Days</span>
                  </div>
                </div>

                {/* Status controls */}
                {canDeploy && (
                  <div className="flex items-center gap-2">
                    {deployment?.status === 'LIVE' && (
                      <button
                        onClick={() => handleUpdateStatus('PAUSED')}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1"
                      >
                        <Pause className="w-3.5 h-3.5" /> Pause
                      </button>
                    )}
                    {deployment?.status === 'PAUSED' && (
                      <button
                        onClick={() => handleUpdateStatus('LIVE')}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1"
                      >
                        <Play className="w-3.5 h-3.5" /> Resume
                      </button>
                    )}
                    {deployment?.status !== 'RETIRED' && (
                      <button
                        onClick={() => handleUpdateStatus('RETIRED')}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1"
                      >
                        <StopCircle className="w-3.5 h-3.5" /> Retire
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Inference Input */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-300">Input Payload (JSON format)</label>
                  <button
                    onClick={() => {
                      setRawJsonInput('{\n  "feature_1": 10,\n  "feature_2": 2.5\n}');
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    Insert Sample
                  </button>
                </div>
                <textarea
                  value={rawJsonInput}
                  onChange={(e) => setRawJsonInput(e.target.value)}
                  rows={4}
                  className="w-full p-3 font-mono text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                  placeholder='{\n  "sqft": 1500,\n  "bedrooms": 3\n}'
                />
              </div>

              {/* Trigger Buttons */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleFastPredict}
                  disabled={predictingFast || predictingExplain || deployment?.status !== 'LIVE'}
                  className="flex-1 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  <Zap className="w-4 h-4" />
                  {predictingFast ? 'Running...' : 'Fast Predict (/predict)'}
                </button>
                <button
                  onClick={handleExplainPredict}
                  disabled={predictingFast || predictingExplain || deployment?.status !== 'LIVE'}
                  className="flex-1 py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 font-semibold text-xs flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  {predictingExplain ? 'Explaining...' : 'Predict + Explain (/predict/.../explain)'}
                </button>
              </div>

              {/* Fast Prediction Output Card */}
              {predictResult && (
                <div className="p-4 rounded-xl bg-slate-950 border border-indigo-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5" /> Fast Inference Result
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                      {predictResult.latency_ms} ms Latency
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-white font-mono">
                    {String(predictResult.prediction)}
                  </div>
                  {predictResult.probabilities && (
                    <div className="text-xs text-slate-400 font-mono">
                      Probabilities: {JSON.stringify(predictResult.probabilities)}
                    </div>
                  )}
                </div>
              )}

              {/* Explainable Prediction Output Card */}
              {explainResult && (
                <div className="p-4 rounded-xl bg-slate-950 border border-cyan-500/30 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" /> Explainable Inference Breakdown
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono">
                        Base Latency: {explainResult.latency_ms} ms
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono">
                        SHAP Latency: {explainResult.explanation_latency_ms} ms
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                        Total: {explainResult.total_latency_ms} ms
                      </span>
                    </div>
                  </div>

                  <div className="text-2xl font-bold text-white font-mono">
                    Prediction: {String(explainResult.prediction)}
                  </div>

                  <div className="space-y-2 border-t border-slate-800 pt-3">
                    <span className="text-xs font-semibold text-slate-300">Feature Contributions (SHAP)</span>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {Object.entries(explainResult.explanation?.contributions || {}).map(([feat, val]) => (
                        <div key={feat} className="flex items-center justify-between text-xs font-mono p-1.5 bg-slate-900/60 rounded">
                          <span className="text-slate-300">{feat}</span>
                          <span className={val >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                            {val >= 0 ? `+${val}` : val}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-slate-400 flex justify-between font-mono pt-1">
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
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Live Prediction Audit Stream (SRS §2.15)
                </span>
                <button
                  onClick={loadLogs}
                  disabled={loadingLogs}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingLogs ? 'animate-spin' : ''}`} />
                  Refresh Logs
                </button>
              </div>

              {loadingLogs && logs.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">Loading logs...</div>
              ) : logs.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">No prediction requests logged yet.</div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-3">Time</th>
                        <th className="p-3">Request ID</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Base Latency</th>
                        <th className="p-3">SHAP Latency</th>
                        <th className="p-3">Payload Mode</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-800/30">
                          <td className="p-3 text-slate-400">
                            {new Date(log.requested_at).toLocaleTimeString()}
                          </td>
                          <td className="p-3 text-slate-300">{log.request_id.slice(0, 8)}...</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              log.status === 'SUCCESS'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-red-500/10 text-red-400 border border-red-500/20'
                            }`}>
                              {log.status}
                            </span>
                          </td>
                          <td className="p-3 text-indigo-400">{log.latency_ms} ms</td>
                          <td className="p-3 text-cyan-400">
                            {log.explanation_latency_ms != null ? `${log.explanation_latency_ms} ms` : '—'}
                          </td>
                          <td className="p-3 text-slate-400">{log.payload_mode}</td>
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
