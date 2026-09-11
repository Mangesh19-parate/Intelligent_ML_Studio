import React, { useState, useEffect } from 'react';
import { experimentApi } from '../api/client';
import {
  ShieldCheck,
  AlertTriangle,
  FileCode,
  Layers,
  Database,
  CheckCircle2,
  Clock,
  Hash,
  Cpu,
  Copy,
  Check,
  GitCommit,
  Sparkles,
  Lock,
  Boxes,
  Sliders,
  Split,
  RefreshCw,
  X,
} from 'lucide-react';

export const LineageViewer = ({ experimentId, onClose }) => {
  const [lineage, setLineage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedKey, setCopiedKey] = useState(null);

  // Reproducibility verification state
  const [reproducing, setReproducing] = useState(false);
  const [reproduceResult, setReproduceResult] = useState(null);
  const [reproduceError, setReproduceError] = useState('');

  useEffect(() => {
    if (!experimentId) return;
    const fetchLineage = async () => {
      try {
        setLoading(true);
        setError('');
        const res = await experimentApi.getLineage(experimentId);
        setLineage(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load lineage metadata.');
      } finally {
        setLoading(false);
      }
    };
    fetchLineage();
  }, [experimentId]);

  const handleReproduce = async () => {
    try {
      setReproducing(true);
      setReproduceError('');
      setReproduceResult(null);
      const res = await experimentApi.reproduce(experimentId);
      setReproduceResult(res.data);
    } catch (err) {
      setReproduceError(err.response?.data?.detail || 'Failed to reproduce experiment.');
    } finally {
      setReproducing(false);
    }
  };

  const copyToClipboard = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(String(text));
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (!experimentId) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface-card)]">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-[var(--color-accent)] rounded-xl shadow-inner">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[var(--color-text)] flex items-center space-x-2">
                <span>Experiment Lineage & Reproducibility Bundle</span>
              </h3>
              <p className="text-xs text-[var(--color-text-muted)] font-mono mt-0.5">
                Experiment ID: {experimentId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] transition-colors cursor-pointer"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {loading ? (
            <div className="p-12 text-center text-[var(--color-text-muted)] space-y-3">
              <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs">Loading lineage and reproducibility records...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          ) : lineage ? (
            <>
              {/* Backfill Warning or Live Capture Badge */}
              {lineage.environment_capture_method === 'BACKFILLED_APPROXIMATE' ? (
                <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start space-x-3 text-amber-200">
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div className="space-y-1 text-xs">
                    <div className="font-bold text-amber-300 flex items-center space-x-2">
                      <span>Environment Metadata Backfilled (Historical Experiment)</span>
                      <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-300 rounded-full text-[10px] font-mono">
                        BACKFILLED_APPROXIMATE
                      </span>
                    </div>
                    <p className="text-[var(--color-text-muted)]">
                      Environment metadata for this experiment was backfilled post-run to maintain complete records. Values reflect runtime environment at backfill time.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-emerald-300 shadow-sm">
                  <div className="flex items-center space-x-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="font-semibold">Captured Live at Experiment Creation (Zero Drift Lineage)</span>
                  </div>
                  <span className="px-3 py-1 bg-emerald-500/20 rounded-full font-mono text-[10px] font-bold text-emerald-300 border border-emerald-500/30 w-fit">
                    CAPTURED_LIVE
                  </span>
                </div>
              )}

              {/* Reproducibility Verification Action & Result Card */}
              <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center space-x-2">
                    <RefreshCw className={`w-4 h-4 text-[var(--color-accent)] ${reproducing ? 'animate-spin' : ''}`} />
                    <h4 className="text-xs font-bold text-[var(--color-text)]">
                      Automated Reproducibility Verification
                    </h4>
                  </div>
                  <button
                    onClick={handleReproduce}
                    disabled={reproducing}
                    className={`px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 transition-all shadow-sm cursor-pointer ${
                      reproducing
                        ? 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] cursor-not-allowed border border-[var(--color-border)]'
                        : 'bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white shadow-md'
                    }`}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${reproducing ? 'animate-spin' : ''}`} />
                    <span>{reproducing ? 'Re-running Experiment...' : 'Verify Reproducibility'}</span>
                  </button>
                </div>

                {reproduceError && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{reproduceError}</span>
                  </div>
                )}

                {reproduceResult && (
                  <div className={`p-4 rounded-xl border ${
                    reproduceResult.status === 'REPRODUCED'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                      : 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                  } space-y-3 animate-in fade-in duration-150`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {reproduceResult.status === 'REPRODUCED' ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-rose-400" />
                        )}
                        <span className="font-bold text-sm">
                          {reproduceResult.status === 'REPRODUCED' ? 'Reproducibility Verified' : 'Reproducibility Discrepancy Detected'}
                        </span>
                      </div>
                      <span className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold border ${
                        reproduceResult.status === 'REPRODUCED'
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                      }`}>
                        {reproduceResult.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                      <div className="p-2.5 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                        <div className="text-[var(--color-text-muted)] text-[10px]">Expected ({reproduceResult.metric_name})</div>
                        <div className="font-bold text-[var(--color-text)] mt-0.5">{reproduceResult.expected.toFixed(6)}</div>
                      </div>
                      <div className="p-2.5 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                        <div className="text-[var(--color-text-muted)] text-[10px]">Observed ({reproduceResult.metric_name})</div>
                        <div className="font-bold text-[var(--color-text)] mt-0.5">{reproduceResult.observed.toFixed(6)}</div>
                      </div>
                      <div className="p-2.5 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                        <div className="text-[var(--color-text-muted)] text-[10px]">Absolute Diff</div>
                        <div className="font-bold text-[var(--color-text)] mt-0.5">{reproduceResult.difference.toExponential(3)}</div>
                      </div>
                      <div className="p-2.5 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                        <div className="text-[var(--color-text-muted)] text-[10px]">Relative Diff</div>
                        <div className="font-bold text-[var(--color-text)] mt-0.5">{(reproduceResult.relative_difference * 100).toFixed(4)}%</div>
                      </div>
                    </div>

                    <div className="text-[11px] text-[var(--color-text-muted)] flex items-center justify-between pt-1 border-t border-[var(--color-border)] font-mono">
                      <span>Contract Tolerances: abs ≤ {reproduceResult.tolerance?.metric_absolute_tolerance} | rel ≤ {(reproduceResult.tolerance?.metric_relative_tolerance * 100)}%</span>
                      <span className="text-[10px]">Run ID: {reproduceResult.reproduced_experiment_id?.slice(0, 8)}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Deterministic Tuple */}
              <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-[var(--color-text)] flex items-center space-x-2">
                    <Split className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                    <span>Deterministic Partitioning & Seeds</span>
                  </h4>
                  <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                    Architecture Contract §9
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] space-y-1">
                    <div className="text-[var(--color-text-muted)] text-[10px] flex items-center justify-between">
                      <span>Split Seed (Outer)</span>
                      {lineage.split_seed !== undefined && lineage.split_seed !== null && (
                        <button
                          onClick={() => copyToClipboard(lineage.split_seed, 'split_seed')}
                          className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
                          title="Copy Seed"
                        >
                          {copiedKey === 'split_seed' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                    <div className="font-mono font-bold text-[var(--color-accent)] text-sm">
                      {lineage.split_seed !== undefined && lineage.split_seed !== null ? lineage.split_seed : '42'}
                    </div>
                  </div>

                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] space-y-1">
                    <div className="text-[var(--color-text-muted)] text-[10px] flex items-center justify-between">
                      <span>CV Seed (Inner)</span>
                      {lineage.cv_seed !== undefined && lineage.cv_seed !== null && (
                        <button
                          onClick={() => copyToClipboard(lineage.cv_seed, 'cv_seed')}
                          className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
                          title="Copy Seed"
                        >
                          {copiedKey === 'cv_seed' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                    <div className="font-mono font-bold text-[var(--color-accent)] text-sm">
                      {lineage.cv_seed !== undefined && lineage.cv_seed !== null ? lineage.cv_seed : '42'}
                    </div>
                  </div>

                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] space-y-1">
                    <div className="text-[var(--color-text-muted)] text-[10px]">CV Strategy</div>
                    <div className="font-mono font-bold text-[var(--color-text)] text-xs truncate mt-0.5">
                      {lineage.cv_strategy || (lineage.task_type === 'CLASSIFICATION' ? 'STRATIFIED_KFOLD' : 'KFOLD')}
                    </div>
                  </div>

                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] space-y-1">
                    <div className="text-[var(--color-text-muted)] text-[10px]">Folds / Partitions</div>
                    <div className="font-mono font-bold text-[var(--color-text)] text-sm mt-0.5">
                      {lineage.fold_count || 5} Folds
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic Hashes & Integrity Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
                    <span className="flex items-center space-x-2 font-bold text-[var(--color-text)]">
                      <Database className="w-4 h-4 text-[var(--color-accent)]" />
                      <span>Dataset Content Hash (SHA-256)</span>
                    </span>
                    {lineage.dataset_content_hash && (
                      <button
                        onClick={() => copyToClipboard(lineage.dataset_content_hash, 'data_hash')}
                        className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] p-1 rounded-full cursor-pointer transition-colors"
                        title="Copy Hash"
                      >
                        {copiedKey === 'data_hash' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                  <div className="font-mono text-xs text-[var(--color-text)] break-all bg-[var(--color-surface)] p-3 rounded-xl border border-[var(--color-border)]">
                    {lineage.dataset_content_hash || 'No hash recorded'}
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
                    <span className="flex items-center space-x-2 font-bold text-[var(--color-text)]">
                      <Lock className="w-4 h-4 text-amber-400" />
                      <span>Winning Model Checksum (SHA-256)</span>
                    </span>
                    {lineage.winning_model?.artifact_checksum && (
                      <button
                        onClick={() => copyToClipboard(lineage.winning_model.artifact_checksum, 'artifact_hash')}
                        className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] p-1 rounded-full cursor-pointer transition-colors"
                        title="Copy Checksum"
                      >
                        {copiedKey === 'artifact_hash' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                  <div className="font-mono text-xs text-emerald-400 break-all bg-[var(--color-surface)] p-3 rounded-xl border border-[var(--color-border)]">
                    {lineage.winning_model?.artifact_checksum || 'Pending finalization'}
                  </div>
                  {lineage.winning_model?.artifact_path && (
                    <div className="text-[10px] text-[var(--color-text-muted)] truncate font-mono">
                      File: {lineage.winning_model.artifact_path}
                    </div>
                  )}
                </div>
              </div>

              {/* Execution & Software Environment */}
              <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-3">
                <h4 className="text-xs font-bold text-[var(--color-text)] flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
                  <span>Software & Environment Versions</span>
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                    <div className="text-[var(--color-text-muted)] text-[10px]">Python</div>
                    <div className="font-mono font-bold text-[var(--color-text)] mt-0.5">{lineage.python_version || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                    <div className="text-[var(--color-text-muted)] text-[10px]">scikit-learn</div>
                    <div className="font-mono font-bold text-[var(--color-text)] mt-0.5">{lineage.sklearn_version || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                    <div className="text-[var(--color-text-muted)] text-[10px]">NumPy</div>
                    <div className="font-mono font-bold text-[var(--color-text)] mt-0.5">{lineage.numpy_version || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
                    <div className="text-[var(--color-text-muted)] text-[10px]">pandas</div>
                    <div className="font-mono font-bold text-[var(--color-text)] mt-0.5">{lineage.pandas_version || 'N/A'}</div>
                  </div>
                </div>

                <div className="p-3 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <GitCommit className="w-4 h-4 text-[var(--color-text-muted)]" />
                    <span className="text-[var(--color-text-muted)] text-[11px]">Git Commit Hash:</span>
                    <span className="font-mono font-bold text-[var(--color-text)] text-xs">{lineage.code_version || 'unknown'}</span>
                  </div>
                  {lineage.code_version && (
                    <button
                      onClick={() => copyToClipboard(lineage.code_version, 'commit')}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] p-1 rounded-full cursor-pointer transition-colors"
                      title="Copy Commit Hash"
                    >
                      {copiedKey === 'commit' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>

              {/* Snapshots & Frozen Config Section */}
              <div className="space-y-4">
                <div className="p-5 rounded-2xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-2.5">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-[var(--color-text)] flex items-center space-x-2">
                      <FileCode className="w-4 h-4 text-[var(--color-accent)]" />
                      <span>Frozen Experiment Configuration</span>
                    </h4>
                    {lineage.experiment_config && (
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(lineage.experiment_config, null, 2), 'cfg')}
                        className="px-3 py-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer text-xs flex items-center space-x-1"
                      >
                        {copiedKey === 'cfg' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span className="text-[10px] font-semibold">Copy JSON</span>
                      </button>
                    )}
                  </div>
                  <pre className="bg-[var(--color-surface)] p-3.5 rounded-xl border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-accent)] overflow-x-auto max-h-56">
                    {lineage.experiment_config ? JSON.stringify(lineage.experiment_config, null, 2) : 'No config recorded'}
                  </pre>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default LineageViewer;
