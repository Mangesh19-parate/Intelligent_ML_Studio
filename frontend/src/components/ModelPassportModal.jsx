import React, { useState, useEffect } from 'react';
import { modelApi } from '../api/client';
import {
  FileText,
  ShieldCheck,
  Trophy,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Copy,
  Download,
  Check,
  Cpu,
  Layers,
  Sparkles,
  Database,
  Sliders,
  Code2,
  Activity,
  ArrowRight,
  ExternalLink,
  Lock,
  X,
  Clock,
  Terminal,
} from 'lucide-react';

export const ModelPassportModal = ({ modelId, onClose }) => {
  const [passport, setPassport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!modelId) return;

    const fetchPassport = async () => {
      setLoading(true);
      setError('');
      try {
        const resp = await modelApi.getPassport(modelId);
        setPassport(resp.data);
      } catch (err) {
        console.error('Failed to fetch model passport', err);
        setError(err.response?.data?.detail || 'Failed to retrieve Model Technical Passport.');
      } finally {
        setLoading(false);
      }
    };

    fetchPassport();
  }, [modelId]);

  const handleCopyJson = () => {
    if (!passport) return;
    navigator.clipboard.writeText(JSON.stringify(passport, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    if (!passport) return;
    const blob = new Blob([JSON.stringify(passport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `model_passport_${passport.model_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!modelId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-[var(--color-surface-card)] border-b border-[var(--color-border)]">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-[var(--color-accent)] flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider">
                  Technical Governance Passport (SRS v9 §13)
                </span>
                {passport?.is_selected_champion && (
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-[10px] font-bold border border-amber-500/20 flex items-center space-x-1">
                    <Trophy className="w-3 h-3 text-amber-400" />
                    <span>Champion</span>
                  </span>
                )}
                {passport?.governance?.is_deployed && (
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20">
                    LIVE_DEPLOYMENT
                  </span>
                )}
              </div>
              <h2 className="text-lg font-bold text-[var(--color-text)] flex items-center space-x-2 mt-0.5">
                <span>{passport?.algorithm_name || 'Model Passport'}</span>
                <span className="text-xs font-mono text-[var(--color-text-muted)] font-normal">({modelId})</span>
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopyJson}
              disabled={loading || !passport}
              className="px-3.5 py-1.5 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-semibold flex items-center space-x-1.5 border border-[var(--color-border)] transition cursor-pointer"
              title="Copy Complete Passport JSON"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>
            <button
              onClick={handleDownloadJson}
              disabled={loading || !passport}
              className="px-3.5 py-1.5 rounded-full bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] text-xs font-semibold flex items-center space-x-1.5 border border-[var(--color-accent-border)] transition cursor-pointer"
              title="Download Passport JSON"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition border border-transparent hover:border-[var(--color-border)] cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap items-center gap-1.5 px-6 py-2.5 bg-[var(--color-surface)] border-b border-[var(--color-border)] text-xs">
          {[
            { id: 'overview', label: 'Overview & Lineage', icon: ShieldCheck },
            { id: 'data_pipeline', label: 'Data & Pipeline', icon: Layers },
            { id: 'metrics', label: 'Performance Matrix', icon: Activity },
            { id: 'explainability', label: 'Explainability & SHAP', icon: Sparkles },
            { id: 'governance', label: 'Governance & Gate', icon: Lock },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-1.5 px-3.5 rounded-full font-bold flex items-center space-x-2 transition cursor-pointer ${
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

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-3 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-[var(--color-text-muted)]">Loading immutable technical passport from database...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
          ) : passport ? (
            <>
              {/* Tab 1: Overview & Cryptographic Lineage */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Summary Metric Strip */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1">
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Model Status</span>
                      <div className="text-sm font-bold text-[var(--color-text)] flex items-center space-x-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>{passport.status}</span>
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1">
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Fit Diagnosis</span>
                      <div className="text-sm font-bold text-[var(--color-text)]">
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold ${
                          passport.fit_diagnosis === 'GOOD_FIT'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : passport.fit_diagnosis?.includes('OVERFIT')
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                        }`}>
                          {passport.fit_diagnosis || 'EVALUATED'}
                        </span>
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1">
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Generalization Gap</span>
                      <div className="text-sm font-bold text-[var(--color-text)] font-mono">
                        {passport.generalization_gap !== null ? (
                          <span className={passport.generalization_gap <= 0.05 ? 'text-emerald-400' : 'text-amber-400'}>
                            {passport.generalization_gap > 0 ? `+${passport.generalization_gap}` : passport.generalization_gap}
                          </span>
                        ) : 'N/A'}
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1">
                      <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Selection Score</span>
                      <div className="text-sm font-bold text-[var(--color-accent)] font-mono">
                        {passport.model_selection_score !== null ? `${passport.model_selection_score} / 100` : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Cryptographic Lineage & Integrity */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                    <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                      <ShieldCheck className="w-4 h-4 text-[var(--color-accent)]" />
                      <span>Cryptographic Provenance & Lineage Audit</span>
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div className="space-y-1.5">
                        <span className="text-[var(--color-text-muted)]">Dataset Content Hash (SHA-256):</span>
                        <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-accent)] break-all">
                          {passport.dataset?.content_hash || passport.experiment?.dataset_content_hash || 'Unverified'}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <span className="text-[var(--color-text-muted)]">Model Artifact Checksum (SHA-256):</span>
                        <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[11px] text-emerald-400 break-all">
                          {passport.artifact_checksum || 'Not Serialized'}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <span className="text-[var(--color-text-muted)]">Code Commit Version:</span>
                        <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-text)]">
                          {passport.experiment?.code_version || 'HEAD'}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <span className="text-[var(--color-text-muted)]">Environment Capture Method:</span>
                        <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-accent)]">
                          {passport.experiment?.environment_capture_method || 'CAPTURED_LIVE'}
                        </div>
                      </div>
                    </div>

                    {/* Runtime Environment Matrix */}
                    <div className="pt-3 border-t border-[var(--color-border)]">
                      <span className="text-[11px] text-[var(--color-text-muted)] font-bold block mb-2">Runtime Dependency Matrix:</span>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                        <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)]">Python: </span>
                          <span className="text-[var(--color-text)] font-semibold">{passport.experiment?.python_version || '3.11+'}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)]">scikit-learn: </span>
                          <span className="text-[var(--color-text)] font-semibold">{passport.experiment?.sklearn_version || '1.4+'}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)]">NumPy: </span>
                          <span className="text-[var(--color-text)] font-semibold">{passport.experiment?.numpy_version || '1.26+'}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                          <span className="text-[var(--color-text-muted)]">pandas: </span>
                          <span className="text-[var(--color-text)] font-semibold">{passport.experiment?.pandas_version || '2.2+'}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Hyperparameters */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-3">
                    <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                      <Sliders className="w-4 h-4 text-[var(--color-accent)]" />
                      <span>Hyperparameter Configuration</span>
                    </h3>
                    <pre className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-mono text-[var(--color-accent)] overflow-x-auto">
                      {JSON.stringify(passport.hyperparameters, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Tab 2: Data & Pipeline */}
              {activeTab === 'data_pipeline' && (
                <div className="space-y-6">
                  {/* Dataset Overview */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                    <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                      <Database className="w-4 h-4 text-[var(--color-accent)]" />
                      <span>Dataset Ingestion & Structural Geometry</span>
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[var(--color-text-muted)]">Total Rows</span>
                        <div className="text-sm font-bold text-[var(--color-text)] font-mono mt-0.5">{passport.dataset?.row_count?.toLocaleString()}</div>
                      </div>
                      <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[var(--color-text-muted)]">Total Columns</span>
                        <div className="text-sm font-bold text-[var(--color-text)] font-mono mt-0.5">{passport.dataset?.column_count}</div>
                      </div>
                      <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[var(--color-text-muted)]">Dataset Version</span>
                        <div className="text-sm font-bold text-[var(--color-accent)] font-mono mt-0.5">v{passport.dataset?.version_number}</div>
                      </div>
                      <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)]">
                        <span className="text-[var(--color-text-muted)]">Target Column</span>
                        <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">{passport.project?.target_column || 'interest_rate'}</div>
                      </div>
                    </div>
                  </div>

                  {/* Feature Selection Snapshot */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                        <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
                        <span>Feature Selection Snapshot</span>
                      </h3>
                      <span className="px-2.5 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)] text-[10px] font-mono font-bold">
                        {passport.feature_selection?.final_selection_method || 'rank_aggregation_ensemble'}
                      </span>
                    </div>

                    <div className="space-y-2 text-xs">
                      <span className="text-[var(--color-text-muted)]">Selected Features ({passport.feature_selection?.feature_count || passport.feature_selection?.final_selected_features?.length || 0}):</span>
                      <div className="flex flex-wrap gap-2">
                        {(passport.feature_selection?.final_selected_features || []).map((feat, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[var(--color-text)] text-xs font-medium"
                          >
                            {feat}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Preprocessing Snapshot */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-3">
                    <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                      <Layers className="w-4 h-4 text-emerald-400" />
                      <span>Leakage-Safe Preprocessing Pipeline Config</span>
                    </h3>
                    <pre className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-mono text-[var(--color-text)] overflow-x-auto">
                      {JSON.stringify(passport.preprocessing?.config_json, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Tab 3: Performance Matrix */}
              {activeTab === 'metrics' && (
                <div className="space-y-6">
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                        <Activity className="w-4 h-4 text-emerald-400" />
                        <span>Multi-Split Evaluation Matrix</span>
                      </h3>
                      <span className="text-xs text-[var(--color-text-muted)]">Direct Read from <code className="text-[var(--color-accent)]">model_metrics</code></span>
                    </div>

                    {/* Table of metrics by split */}
                    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-[var(--color-surface-card)] text-[var(--color-text-muted)] uppercase tracking-wider text-[10px] border-b border-[var(--color-border)]">
                          <tr>
                            <th className="px-4 py-3">Metric Name</th>
                            <th className="px-4 py-3">TRAIN</th>
                            <th className="px-4 py-3">CV_MEAN</th>
                            <th className="px-4 py-3">LOCKED_TEST</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--color-border)] font-mono">
                          {Object.keys({
                            ...(passport.metrics_summary_by_split?.TRAIN || {}),
                            ...(passport.metrics_summary_by_split?.CV_MEAN || {}),
                            ...(passport.metrics_summary_by_split?.LOCKED_TEST || {}),
                          }).map((metricName) => {
                            const trainVal = passport.metrics_summary_by_split?.TRAIN?.[metricName];
                            const cvVal = passport.metrics_summary_by_split?.CV_MEAN?.[metricName];
                            const testVal = passport.metrics_summary_by_split?.LOCKED_TEST?.[metricName];

                            return (
                              <tr key={metricName} className="hover:bg-[var(--color-surface-hover)]">
                                <td className="px-4 py-2.5 font-bold text-[var(--color-text)]">{metricName}</td>
                                <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{trainVal !== undefined ? trainVal.toFixed(4) : '—'}</td>
                                <td className="px-4 py-2.5 text-[var(--color-accent)] font-bold">{cvVal !== undefined ? cvVal.toFixed(4) : '—'}</td>
                                <td className="px-4 py-2.5 text-emerald-400 font-bold">{testVal !== undefined ? testVal.toFixed(4) : '—'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Explainability & SHAP */}
              {activeTab === 'explainability' && (
                <div className="space-y-6">
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                        <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
                        <span>Global Feature Attribution (Mean |SHAP|)</span>
                      </h3>
                      {passport.explainability?.has_summary ? (
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold border border-emerald-500/30">
                          SCHEMA_CACHED
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--color-text-muted)]">No SHAP summary cached</span>
                      )}
                    </div>

                    {passport.explainability?.top_features && passport.explainability.top_features.length > 0 ? (
                      <div className="space-y-3">
                        {passport.explainability.top_features.map((item, idx) => {
                          const featName = item.feature || item.name || `Feature ${idx + 1}`;
                          const shapVal = typeof item.mean_abs_shap === 'number' ? item.mean_abs_shap : typeof item.importance === 'number' ? item.importance : 0;
                          return (
                            <div key={idx} className="space-y-1 text-xs">
                              <div className="flex items-center justify-between font-mono">
                                <span className="text-[var(--color-text)] font-semibold">{featName}</span>
                                <span className="text-[var(--color-accent)] font-bold">{shapVal.toFixed(5)}</span>
                              </div>
                              <div className="w-full bg-[var(--color-surface-hover)] rounded-full h-1.5 overflow-hidden">
                                <div
                                  className="bg-[var(--color-accent)] h-full rounded-full"
                                  style={{ width: `${Math.min(100, Math.max(10, shapVal * 200))}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs text-[var(--color-text-muted)] italic">No global SHAP explanation registered for this candidate model.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 5: Governance & Gate */}
              {activeTab === 'governance' && (
                <div className="space-y-6">
                  {/* Deployment Gate Certification */}
                  <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider flex items-center space-x-2">
                        <Lock className="w-4 h-4 text-[var(--color-accent)]" />
                        <span>Pre-Deployment Verification Gate (6 Conditions)</span>
                      </h3>
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                        passport.governance?.gate_is_passing
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}>
                        {passport.governance?.gate_is_passing ? 'GATE_PASSED' : 'GATE_PENDING'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {(passport.governance?.gate_checks || []).map((chk, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-between"
                        >
                          <span className="font-mono text-[var(--color-text)] font-semibold">{chk.check || chk.condition_name}</span>
                          {chk.passed ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Production Endpoint Details */}
                  {passport.governance?.is_deployed && (
                    <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-emerald-500/30 space-y-3">
                      <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>Active Production Deployment</span>
                      </h3>
                      <div className="p-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-between text-xs font-mono">
                        <span className="text-[var(--color-accent)]">{passport.governance.endpoint_url}</span>
                        <span className="text-[var(--color-text-muted)]">{new Date(passport.governance.deployed_at).toLocaleString()}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-[var(--color-surface-card)] border-t border-[var(--color-border)] flex items-center justify-between text-xs text-[var(--color-text-muted)]">
          <span className="font-mono text-[11px]">Strict SELECT + Render Only • Zero Recomputations</span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] font-semibold border border-[var(--color-border)] transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelPassportModal;
