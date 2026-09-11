import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { projectApi, modelApi, deploymentApi, predictApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Rocket,
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Copy,
  Check,
  Pause,
  StopCircle,
  RefreshCw,
  FolderOpen,
  Layers,
  Cpu,
  Lock,
  ArrowRight,
  ArrowLeft,
  Sliders,
  Code2,
  Clock,
  ExternalLink,
} from 'lucide-react';

export const ProductionStage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProjectId = searchParams.get('project_id');
  const initialTab = searchParams.get('tab') || 'gate'; // 'gate' | 'predict' | 'monitoring'

  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState(null);
  const [winningModel, setWinningModel] = useState(null);
  const [gate, setGate] = useState(null);
  const [deployment, setDeployment] = useState(null);

  const [activeTab, setActiveTab] = useState(initialTab);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Live Inference Test State
  const [inputPayload, setInputPayload] = useState('{\n  \n}');
  const [predicting, setPredicting] = useState(false);
  const [predictResult, setPredictResult] = useState(null);
  const [explainResult, setExplainResult] = useState(null);
  const [copiedUrl, setCopiedUrl] = useState(false);

  // Monitoring logs
  const [logs, setLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const { user } = useAuth();
  const canDeploy = user?.role === 'ADMIN' || user?.role === 'DEPLOYMENT_MANAGER' || user?.permissions?.includes('DEPLOY');

  // Load Projects
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const res = await projectApi.list();
        const list = res.data || [];
        setProjects(list);
        if (!selectedProjectId && list.length > 0) {
          const firstId = list[0].id;
          setSelectedProjectId(firstId);
          setSearchParams({ project_id: firstId });
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

  // Load Project, Winning Model & Deployment Gate
  useEffect(() => {
    if (!selectedProjectId) return;

    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const projRes = await projectApi.get(selectedProjectId);
        setCurrentProject(projRes.data);

        // Find winning model
        const expRes = await modelApi.getLeaderboard(selectedProjectId);
        const lb = expRes.data;
        const winner = lb?.models?.find((m) => m.is_winner) || (lb?.models?.length ? lb.models[0] : null);
        setWinningModel(winner);

        if (winner) {
          try {
            const gateRes = await modelApi.getDeploymentGate(winner.id);
            setGate(gateRes.data);
          } catch {}
        } else {
          setGate(null);
        }

        // Check active deployment
        if (projRes.data?.active_deployment) {
          setDeployment(projRes.data.active_deployment);
        } else {
          setDeployment(null);
        }
      } catch (err) {
        console.error('Failed to load production data', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedProjectId]);

  const handleApproveGate = async () => {
    if (!winningModel) return;
    setApproving(true);
    setError('');
    try {
      const res = await modelApi.approveDeploymentGate(winningModel.id);
      setGate(res.data.gate);
      setSuccessMsg('Deployment gate approved successfully.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Approval failed.');
    } finally {
      setApproving(false);
    }
  };

  const handleDeploy = async () => {
    if (!winningModel) return;
    setDeploying(true);
    setError('');
    try {
      const res = await modelApi.deploy(winningModel.id);
      setDeployment(res.data);
      setSuccessMsg('Model successfully deployed to production endpoint!');
      setActiveTab('predict');
    } catch (err) {
      setError(err.response?.data?.detail || 'Deployment failed.');
    } finally {
      setDeploying(false);
    }
  };

  const handleFastPredict = async () => {
    if (!deployment?.id) return;
    setPredicting(true);
    setError('');
    setPredictResult(null);
    try {
      const payload = JSON.parse(inputPayload);
      const res = await predictApi.predict(deployment.id, payload);
      setPredictResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Prediction failed. Check input JSON.');
    } finally {
      setPredicting(false);
    }
  };

  const handleExplainPredict = async () => {
    if (!deployment?.id) return;
    setPredicting(true);
    setError('');
    setExplainResult(null);
    try {
      const payload = JSON.parse(inputPayload);
      const res = await predictApi.predictExplain(deployment.id, payload);
      setExplainResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Explainable prediction failed.');
    } finally {
      setPredicting(false);
    }
  };

  const loadAuditLogs = async () => {
    if (!deployment?.id) return;
    setLoadingLogs(true);
    try {
      const res = await deploymentApi.getLogs(deployment.id, 50);
      setLogs(res.data || []);
    } catch (err) {
      console.error('Failed to load logs', err);
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

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-[var(--color-border)] gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[var(--color-accent)] bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-full px-3 py-1 mb-2">
            <Rocket className="w-3.5 h-3.5" />
            <span>Stage 8 of 8 • Production Deployment & Monitoring</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-text)] flex items-center space-x-3">
            <span>Production Serving & Observability</span>
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1.5 max-w-3xl">
            Strict 6-condition pre-deployment verification gatekeeper, high-performance REST inference API, and real-time latency & drift monitoring.
          </p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center space-x-3">
          <div className="relative min-w-[220px]">
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                setSearchParams({ project_id: e.target.value });
              }}
              className="w-full pl-9 pr-8 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-full text-xs font-bold text-[var(--color-text)] shadow-sm focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_name || p.name} ({p.task_type || 'Unset'})
                </option>
              ))}
            </select>
            <FolderOpen className="w-4 h-4 text-[var(--color-text-muted)] absolute left-3.5 top-2.5 pointer-events-none" />
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Segmented Navigation Tabs */}
      <div className="flex flex-wrap gap-2 p-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-full w-fit shadow-sm">
        {[
          { id: 'gate', label: '1. Pre-Deployment Gate (6 Rules)', icon: ShieldCheck },
          { id: 'predict', label: '2. Live Prediction API ("Try It")', icon: Zap },
          { id: 'monitoring', label: '3. Audit Logs & Latency', icon: Activity },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id === 'monitoring') loadAuditLogs();
              }}
              className={`px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer ${
                isActive
                  ? 'bg-[var(--color-accent)] text-white shadow-sm'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm space-y-6">
        {/* TAB 1: PRE-DEPLOYMENT GATE */}
        {activeTab === 'gate' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-[var(--color-text)]">Mandatory Verification Checklist (6 Rules)</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  All 6 automated criteria must evaluate to PASS before a model artifact can be served in production.
                </p>
              </div>

              {gate?.gate_passed && (
                <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-xs font-bold flex items-center space-x-1.5 w-fit">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>ALL GATES VERIFIED</span>
                </span>
              )}
            </div>

            <div className="space-y-3">
              {[
                { title: '1. Locked Test Evaluated', desc: 'Evaluated once on locked holdout data (never reused diagnostic split).', passed: gate?.locked_test_evaluated },
                { title: '2. Feature Schema Locked', desc: 'Input feature schema matches dataset columns and transformation pipeline.', passed: gate?.schema_locked },
                { title: '3. Artifact Cryptographically Verified', desc: 'Disk artifact SHA-256 checksum matches database hash record.', passed: gate?.artifact_verified },
                { title: '4. Lineage Capture Complete', desc: 'Software environment (Python, scikit-learn, numpy) & git commit SHA recorded.', passed: gate?.lineage_complete },
                { title: '5. Performance Threshold Met', desc: 'Performance metric satisfies baseline business criteria on test split.', passed: gate?.performance_threshold_passed },
                { title: '6. User Approved Sign-Off', desc: 'Explicit approval by authorized DEPLOYMENT_MANAGER or ADMIN.', passed: gate?.user_approved },
              ].map((rule, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex items-center justify-between"
                >
                  <div className="flex items-start space-x-3">
                    {rule.passed ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="text-sm font-bold text-[var(--color-text)]">{rule.title}</div>
                      <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{rule.desc}</div>
                    </div>
                  </div>

                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                    rule.passed
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {rule.passed ? 'PASS' : 'FAIL'}
                  </span>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-[var(--color-border)] flex flex-wrap items-center justify-between gap-4">
              <div>
                {!gate?.user_approved && canDeploy && (
                  <button
                    onClick={handleApproveGate}
                    disabled={approving}
                    className="px-5 py-2 rounded-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all cursor-pointer"
                  >
                    {approving ? 'Approving...' : 'Sign Off & Approve Gate'}
                  </button>
                )}
              </div>

              <button
                onClick={handleDeploy}
                disabled={!gate?.gate_passed || deploying}
                className={`px-6 py-2.5 rounded-full text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer ${
                  gate?.gate_passed
                    ? 'bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white shadow-md shadow-[var(--color-accent-soft)]'
                    : 'bg-[var(--color-surface-card)] text-[var(--color-text-muted)] border border-[var(--color-border)] cursor-not-allowed opacity-60'
                }`}
              >
                <Play className="w-4 h-4 fill-current" />
                <span>{deploying ? 'Deploying...' : 'Deploy to Production LIVE'}</span>
              </button>
            </div>
          </div>
        )}

        {/* TAB 2: LIVE INFERENCE API */}
        {activeTab === 'predict' && (
          <div className="space-y-6">
            {deployment ? (
              <div className="p-4 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-[var(--color-text)]">Endpoint:</span>
                    <code className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[var(--color-surface)] text-[var(--color-accent)] border border-[var(--color-border)]">
                      {deployment.endpoint_path}
                    </code>
                    <button
                      onClick={copyEndpoint}
                      className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
                    >
                      {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)]">
                    Status: <strong className="text-emerald-400 font-bold">{deployment.status}</strong> &bull; Latency: ~12ms
                  </div>
                </div>

                <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold">
                  LIVE SERVING
                </span>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                No active deployment found. Please verify the 6 pre-deployment gates on Tab 1 and click Deploy.
              </div>
            )}

            <div className="space-y-3">
              <label className="text-xs font-bold text-[var(--color-text)]">Test Payload (JSON)</label>
              <textarea
                rows={5}
                value={inputPayload}
                onChange={(e) => setInputPayload(e.target.value)}
                placeholder='{\n  "feature_1": 25,\n  "feature_2": 1.4\n}'
                className="w-full p-3 font-mono text-xs bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-xl text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              />

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={handleFastPredict}
                  disabled={predicting || !deployment}
                  className="px-5 py-2.5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold flex items-center space-x-2 shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <Zap className="w-4 h-4" />
                  <span>Fast Predict (/predict)</span>
                </button>
                <button
                  onClick={handleExplainPredict}
                  disabled={predicting || !deployment}
                  className="px-5 py-2.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] text-xs font-bold flex items-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>Predict + Explain (/predict/.../explain)</span>
                </button>
              </div>
            </div>

            {predictResult && (
              <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-accent-border)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[var(--color-accent)]">Prediction Result</span>
                  <span className="text-xs font-mono text-emerald-400 font-bold">{predictResult.latency_ms} ms</span>
                </div>
                <div className="text-2xl font-black text-[var(--color-text)] font-mono">
                  {String(predictResult.prediction)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AUDIT LOGS & MONITORING */}
        {activeTab === 'monitoring' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[var(--color-text)]">Live Inference Audit Stream</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Immutable request logs with latency metrics and payload hashes.
                </p>
              </div>
              <button
                onClick={loadAuditLogs}
                disabled={loadingLogs}
                className="p-2 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingLogs ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {logs.length === 0 ? (
              <div className="p-8 text-center text-[var(--color-text-muted)] text-xs bg-[var(--color-surface-card)] rounded-xl border border-[var(--color-border)]">
                No inference audit records logged yet. Run predictions from Tab 2 to populate stream.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase text-[10px]">
                    <tr>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3">Request ID</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {logs.map((l) => (
                      <tr key={l.id} className="hover:bg-[var(--color-surface-hover)]">
                        <td className="p-3 text-[var(--color-text-muted)]">{new Date(l.requested_at).toLocaleTimeString()}</td>
                        <td className="p-3 text-[var(--color-text)]">{l.request_id?.slice(0, 8)}...</td>
                        <td className="p-3 text-emerald-400 font-bold">{l.status}</td>
                        <td className="p-3 text-[var(--color-accent)]">{l.latency_ms} ms</td>
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
  );
};

export default ProductionStage;
