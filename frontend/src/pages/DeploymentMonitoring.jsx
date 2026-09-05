import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { deploymentApi, predictApi, projectApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  Zap,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Pause,
  StopCircle,
  Play,
  RotateCw,
  ArrowLeft,
  ChevronRight,
  Database,
  BarChart3,
  Layers,
  Sparkles,
  FileCode,
  ShieldCheck,
  Search,
} from 'lucide-react';

export const DeploymentMonitoring = () => {
  const { id: routeDeploymentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [deploymentId, setDeploymentId] = useState(routeDeploymentId || '');
  const [monitoringData, setMonitoringData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [lookbackHours, setLookbackHours] = useState(24);

  // Try-It inference state
  const [inputJson, setInputJson] = useState('{\n  \n}');
  const [predictingFast, setPredictingFast] = useState(false);
  const [predictingExplain, setPredictingExplain] = useState(false);
  const [fastResult, setFastResult] = useState(null);
  const [explainResult, setExplainResult] = useState(null);

  const userPerms = new Set(
    user?.permissions ||
    (user?.role?.permissions ? user.role.permissions.map((p) => (typeof p === 'string' ? p : p.permission_key)) : [])
  );
  const canDeploy = user?.role === 'ADMIN' || userPerms.has('DEPLOY') || userPerms.has('MANAGE_USERS');

  const fetchMonitoring = async (depId) => {
    if (!depId) return;
    setLoading(true);
    setError('');
    try {
      const res = await deploymentApi.getMonitoring(depId, lookbackHours);
      setMonitoringData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load deployment monitoring data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (routeDeploymentId) {
      setDeploymentId(routeDeploymentId);
      fetchMonitoring(routeDeploymentId);
    }
  }, [routeDeploymentId, lookbackHours]);

  const handleUpdateStatus = async (newStatus) => {
    if (!deploymentId) return;
    setError('');
    setSuccessMsg('');
    try {
      await deploymentApi.updateStatus(deploymentId, newStatus);
      setSuccessMsg(`Deployment status updated to ${newStatus}`);
      fetchMonitoring(deploymentId);
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to transition deployment to ${newStatus}`);
    }
  };

  const handleRunPredict = async () => {
    if (!deploymentId) return;
    setPredictingFast(true);
    setError('');
    setFastResult(null);
    try {
      const payload = JSON.parse(inputJson);
      const res = await predictApi.predict(deploymentId, payload);
      setFastResult(res.data);
      fetchMonitoring(deploymentId);
    } catch (err) {
      setError(err.response?.data?.detail || 'Prediction failed');
    } finally {
      setPredictingFast(false);
    }
  };

  const handleRunPredictExplain = async () => {
    if (!deploymentId) return;
    setPredictingExplain(true);
    setError('');
    setExplainResult(null);
    try {
      const payload = JSON.parse(inputJson);
      const res = await predictApi.predictExplain(deploymentId, payload);
      setExplainResult(res.data);
      fetchMonitoring(deploymentId);
    } catch (err) {
      setError(err.response?.data?.detail || 'Explain prediction failed');
    } finally {
      setPredictingExplain(false);
    }
  };

  const baseStats = monitoringData?.latency_summary?.base_predictions || { avg_ms: 0, p50_ms: 0, p95_ms: 0, count: 0 };
  const explainStats = monitoringData?.latency_summary?.explained_predictions || { avg_ms: 0, p50_ms: 0, p95_ms: 0, count: 0 };
  const errorStats = monitoringData?.error_rate || { total_requests: 0, success_count: 0, validation_error_count: 0, server_error_count: 0, error_rate: 0, validation_error_rate: 0, server_error_rate: 0 };
  const volumeBuckets = monitoringData?.volume_over_time || [];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link
              to="/dashboard"
              className="text-xs font-semibold text-[var(--color-text-muted)] hover:text-text flex items-center space-x-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Workspace</span>
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
            <span className="text-xs font-semibold text-[var(--color-accent)]">Deployment Monitoring</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text mt-1 flex items-center space-x-2.5">
            <Activity className="w-6 h-6 text-[var(--color-accent)]" />
            <span>Inference & Telemetry Observability</span>
          </h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Real-time inference volume, decoupled latency profiles, and error decomposition
          </p>
        </div>

        {/* Lookback Filter & Refresh */}
        <div className="flex items-center space-x-3">
          <select
            value={lookbackHours}
            onChange={(e) => setLookbackHours(Number(e.target.value))}
            className="px-3 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-text font-semibold focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          >
            <option value={1}>Last 1 Hour</option>
            <option value={6}>Last 6 Hours</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
          </select>

          {deploymentId && (
            <button
              onClick={() => fetchMonitoring(deploymentId)}
              disabled={loading}
              className="p-2 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs font-semibold transition-all cursor-pointer"
              title="Refresh Monitoring Data"
            >
              <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Deployment ID Selector Bar if not in route */}
      {!routeDeploymentId && (
        <div className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center space-x-3">
          <Search className="w-4 h-4 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="Enter Deployment UUID to monitor..."
            value={deploymentId}
            onChange={(e) => setDeploymentId(e.target.value)}
            className="flex-1 bg-transparent text-sm text-text font-mono focus:outline-none"
          />
          <button
            onClick={() => fetchMonitoring(deploymentId)}
            className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-semibold cursor-pointer"
          >
            Load Telemetry
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {monitoringData && (
        <div className="space-y-6">
          {/* Status & Lifecycle Banner */}
          <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                  monitoringData.status === 'LIVE'
                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                    : monitoringData.status === 'PAUSED'
                    ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                    : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                }`}
              >
                {monitoringData.status}
              </span>
              <div>
                <div className="font-mono text-xs font-bold text-text">
                  Endpoint: <span className="text-[var(--color-accent)]">{monitoringData.endpoint_path}</span>
                </div>
                <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                  Deployment ID: <span className="font-mono">{monitoringData.deployment_id}</span>
                </div>
              </div>
            </div>

            {/* Lifecycle Controls (DEPLOY permission required) */}
            {canDeploy && (
              <div className="flex items-center space-x-2">
                {monitoringData.status === 'LIVE' && (
                  <button
                    onClick={() => handleUpdateStatus('PAUSED')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 text-xs font-semibold border border-amber-500/20 cursor-pointer"
                  >
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause Traffic</span>
                  </button>
                )}
                {monitoringData.status === 'PAUSED' && (
                  <button
                    onClick={() => handleUpdateStatus('LIVE')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 text-xs font-semibold border border-emerald-500/20 cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Resume LIVE</span>
                  </button>
                )}
                {monitoringData.status !== 'RETIRED' && (
                  <button
                    onClick={() => {
                      if (window.confirm('Are you sure you want to permanently RETIRE this deployment? Retired endpoints cannot be reactivated.')) {
                        handleUpdateStatus('RETIRED');
                      }
                    }}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 text-xs font-semibold border border-rose-500/20 cursor-pointer"
                  >
                    <StopCircle className="w-3.5 h-3.5" />
                    <span>Retire Endpoint</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total Requests */}
            <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2">
              <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">
                <span>Inference Requests</span>
                <BarChart3 className="w-4 h-4 text-[var(--color-accent)]" />
              </div>
              <div className="text-3xl font-black font-mono text-text">
                {errorStats.total_requests.toLocaleString()}
              </div>
              <div className="flex items-center space-x-3 text-xs text-[var(--color-text-muted)] pt-1">
                <span className="text-emerald-500 font-semibold">{errorStats.success_count} Success</span>
                <span>&bull;</span>
                <span className="text-rose-500 font-semibold">
                  {errorStats.validation_error_count + errorStats.server_error_count} Errors
                </span>
              </div>
            </div>

            {/* Error Rate Breakdown */}
            <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2">
              <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">
                <span>Error Rate</span>
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              </div>
              <div className="text-3xl font-black font-mono text-text">
                {(errorStats.error_rate * 100).toFixed(1)}%
              </div>
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-amber-500">
                  Validation: <strong>{(errorStats.validation_error_rate * 100).toFixed(1)}%</strong>
                </span>
                <span className="text-rose-500">
                  Server (500): <strong>{(errorStats.server_error_rate * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>

            {/* Base vs Explain Latency Comparison */}
            <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2">
              <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">
                <span>P95 Latency (Base vs SHAP)</span>
                <Clock className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-black font-mono text-emerald-500">
                  {baseStats.p95_ms}ms
                </span>
                <span className="text-xs text-[var(--color-text-muted)] font-semibold">vs</span>
                <span className="text-2xl font-black font-mono text-purple-500">
                  {explainStats.p95_ms}ms
                </span>
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)] pt-1">
                Base Avg: <strong className="text-text">{baseStats.avg_ms}ms</strong> &bull; Explain Avg: <strong className="text-text">{explainStats.avg_ms}ms</strong>
              </div>
            </div>
          </div>

          {/* Latency Comparison Profile Table */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>Decoupled Latency Profile Breakdown</span>
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Demonstrates the exact compute cost decoupling between low-latency inference and SHAP explainability
                </p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                  <tr>
                    <th className="px-5 py-3">Inference Path</th>
                    <th className="px-5 py-3">Requests Measured</th>
                    <th className="px-5 py-3 font-mono">Average</th>
                    <th className="px-5 py-3 font-mono">P50 (Median)</th>
                    <th className="px-5 py-3 font-mono">P95</th>
                    <th className="px-5 py-3 font-mono">Min / Max</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)] font-mono text-[11px]">
                  <tr className="hover:bg-[var(--color-surface)]/50 transition-colors">
                    <td className="px-5 py-3.5 font-sans font-bold text-emerald-500 flex items-center space-x-1.5">
                      <Zap className="w-3.5 h-3.5" />
                      <span>Base Fast Inference</span>
                    </td>
                    <td className="px-5 py-3.5 text-text">{baseStats.count}</td>
                    <td className="px-5 py-3.5 font-bold text-emerald-500">{baseStats.avg_ms} ms</td>
                    <td className="px-5 py-3.5 text-text">{baseStats.p50_ms} ms</td>
                    <td className="px-5 py-3.5 font-bold text-text">{baseStats.p95_ms} ms</td>
                    <td className="px-5 py-3.5 text-[var(--color-text-muted)]">{baseStats.min_ms} / {baseStats.max_ms} ms</td>
                  </tr>
                  <tr className="hover:bg-[var(--color-surface)]/50 transition-colors">
                    <td className="px-5 py-3.5 font-sans font-bold text-purple-400 flex items-center space-x-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Inference + SHAP Explanation</span>
                    </td>
                    <td className="px-5 py-3.5 text-text">{explainStats.count}</td>
                    <td className="px-5 py-3.5 font-bold text-purple-400">{explainStats.avg_ms} ms</td>
                    <td className="px-5 py-3.5 text-text">{explainStats.p50_ms} ms</td>
                    <td className="px-5 py-3.5 font-bold text-text">{explainStats.p95_ms} ms</td>
                    <td className="px-5 py-3.5 text-[var(--color-text-muted)]">{explainStats.min_ms} / {explainStats.max_ms} ms</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Volume Over Time Timeline */}
          {volumeBuckets.length > 0 && (
            <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
              <h3 className="text-sm font-bold text-text flex items-center space-x-2">
                <BarChart3 className="w-4 h-4 text-[var(--color-accent)]" />
                <span>Hourly Request Volume Over Time</span>
              </h3>
              <div className="space-y-2">
                {volumeBuckets.map((b, idx) => (
                  <div key={idx} className="flex items-center space-x-4 text-xs">
                    <span className="font-mono text-[11px] text-[var(--color-text-muted)] w-36 shrink-0">
                      {new Date(b.timestamp).toLocaleTimeString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <div className="flex-1 flex items-center h-5 rounded-lg bg-[var(--color-bg)] overflow-hidden border border-[var(--color-border)]">
                      {b.success_count > 0 && (
                        <div
                          style={{ width: `${(b.success_count / b.total_requests) * 100}%` }}
                          className="h-full bg-emerald-500/70"
                          title={`Success: ${b.success_count}`}
                        />
                      )}
                      {b.validation_error_count > 0 && (
                        <div
                          style={{ width: `${(b.validation_error_count / b.total_requests) * 100}%` }}
                          className="h-full bg-amber-500/70"
                          title={`Validation Error: ${b.validation_error_count}`}
                        />
                      )}
                      {b.server_error_count > 0 && (
                        <div
                          style={{ width: `${(b.server_error_count / b.total_requests) * 100}%` }}
                          className="h-full bg-rose-500/70"
                          title={`Server Error: ${b.server_error_count}`}
                        />
                      )}
                    </div>
                    <span className="font-mono text-[11px] font-bold text-text w-12 text-right">
                      {b.total_requests} req
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interactive Try-It Inference Form */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
              <h3 className="text-sm font-bold text-text flex items-center space-x-2">
                <FileCode className="w-4 h-4 text-[var(--color-accent)]" />
                <span>Test Inference Payload</span>
              </h3>
              <p className="text-xs text-[var(--color-text-muted)]">
                Execute live requests against the endpoint to test base latency and SHAP explanation paths
              </p>

              <textarea
                rows={6}
                value={inputJson}
                onChange={(e) => setInputJson(e.target.value)}
                placeholder='{"feature_1": 12.5, "feature_2": "category_a"}'
                className="w-full p-3 font-mono text-xs rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              />

              <div className="flex items-center space-x-3 pt-2">
                <button
                  onClick={handleRunPredict}
                  disabled={predictingFast || monitoringData.status !== 'LIVE'}
                  className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>{predictingFast ? 'Predicting...' : 'Fast Predict (Base)'}</span>
                </button>

                <button
                  onClick={handleRunPredictExplain}
                  disabled={predictingExplain || monitoringData.status !== 'LIVE'}
                  className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{predictingExplain ? 'Explaining...' : 'Predict + SHAP Explain'}</span>
                </button>
              </div>
            </div>

            {/* Inference Result Viewport */}
            <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
              <h3 className="text-sm font-bold text-text">Inference Response Output</h3>
              {fastResult && (
                <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-emerald-500/30 font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between text-emerald-500 font-bold">
                    <span>Base Predict Completed</span>
                    <span>{fastResult.latency_ms} ms</span>
                  </div>
                  <pre className="text-text text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(fastResult, null, 2)}
                  </pre>
                </div>
              )}

              {explainResult && (
                <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-purple-500/30 font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between text-purple-400 font-bold">
                    <span>Explain Predict Completed</span>
                    <span>Base: {explainResult.latency_ms}ms | SHAP: {explainResult.explanation_latency_ms}ms</span>
                  </div>
                  <pre className="text-text text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(explainResult, null, 2)}
                  </pre>
                </div>
              )}

              {!fastResult && !explainResult && (
                <div className="text-center py-12 text-xs text-[var(--color-text-muted)] italic">
                  Run a prediction on the left to inspect raw inference response and latency metrics.
                </div>
              )}
            </div>
          </div>

          {/* Audit Logs Table */}
          <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
            <h3 className="text-sm font-bold text-text">Recent Inference Audit Logs</h3>
            <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Base Latency</th>
                    <th className="px-4 py-3">SHAP Latency</th>
                    <th className="px-4 py-3">Payload Mode</th>
                    <th className="px-4 py-3">Schema Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)] font-mono text-[11px]">
                  {monitoringData.recent_logs?.map((l) => (
                    <tr key={l.id} className="hover:bg-[var(--color-surface)]/50 transition-colors">
                      <td className="px-4 py-2.5 text-[var(--color-text-muted)]">
                        {new Date(l.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            l.status === 'SUCCESS'
                              ? 'bg-emerald-500/10 text-emerald-500'
                              : l.status === 'VALIDATION_ERROR'
                              ? 'bg-amber-500/10 text-amber-500'
                              : 'bg-rose-500/10 text-rose-500'
                          }`}
                        >
                          {l.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-text font-bold">{l.latency_ms} ms</td>
                      <td className="px-4 py-2.5 text-purple-400">
                        {l.explanation_latency_ms ? `${l.explanation_latency_ms} ms` : '-'}
                      </td>
                      <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{l.payload_mode}</td>
                      <td className="px-4 py-2.5 text-[var(--color-text-muted)] truncate max-w-[120px]" title={l.schema_hash}>
                        {l.schema_hash.substring(0, 12)}...
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
