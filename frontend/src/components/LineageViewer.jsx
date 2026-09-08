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
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60 backdrop-blur">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl shadow-inner">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Experiment Lineage & Reproducibility Bundle</span>
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Experiment ID: {experimentId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar">
          {loading ? (
            <div className="p-12 text-center text-slate-400 space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
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
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start space-x-3 text-amber-200">
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div className="space-y-1 text-xs">
                    <div className="font-bold text-amber-300 flex items-center space-x-2">
                      <span>Environment Metadata Backfilled (Historical Experiment)</span>
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded text-[10px] font-mono">
                        BACKFILLED_APPROXIMATE
                      </span>
                    </div>
                    <p className="text-slate-300">
                      Environment metadata for this experiment was backfilled post-run to maintain complete records. Values reflect runtime environment at backfill time.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between text-xs text-emerald-300">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-semibold">Captured Live at Experiment Creation (Zero Drift Lineage)</span>
                  </div>
                  <span className="px-2.5 py-0.5 bg-emerald-500/20 rounded-full font-mono text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                    CAPTURED_LIVE
                  </span>
                </div>
              )}

              {/* Reproducibility Verification Action & Result Card (Day 4 P0) */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <RefreshCw className={`w-4 h-4 text-cyan-400 ${reproducing ? 'animate-spin' : ''}`} />
                    <h4 className="text-xs font-bold text-white">
                      Automated Reproducibility Verification
                    </h4>
                  </div>
                  <button
                    onClick={handleReproduce}
                    disabled={reproducing}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
                      reproducing
                        ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700'
                        : 'bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white border border-cyan-400/30 shadow-cyan-500/10'
                    }`}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${reproducing ? 'animate-spin' : ''}`} />
                    <span>{reproducing ? 'Re-running Experiment...' : 'Verify Reproducibility'}</span>
                  </button>
                </div>

                {reproduceError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{reproduceError}</span>
                  </div>
                )}

                {reproduceResult && (
                  <div className={`p-4 rounded-xl border ${
                    reproduceResult.status === 'REPRODUCED'
                      ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200'
                      : 'bg-rose-950/30 border-rose-500/30 text-rose-200'
                  } space-y-3 animate-in fade-in zoom-in-95 duration-150`}>
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
                      <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Expected ({reproduceResult.metric_name})</div>
                        <div className="font-bold text-slate-100 mt-0.5">{reproduceResult.expected.toFixed(6)}</div>
                      </div>
                      <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Observed ({reproduceResult.metric_name})</div>
                        <div className="font-bold text-slate-100 mt-0.5">{reproduceResult.observed.toFixed(6)}</div>
                      </div>
                      <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Absolute Diff</div>
                        <div className="font-bold text-slate-100 mt-0.5">{reproduceResult.difference.toExponential(3)}</div>
                      </div>
                      <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Relative Diff</div>
                        <div className="font-bold text-slate-100 mt-0.5">{(reproduceResult.relative_difference * 100).toFixed(4)}%</div>
                      </div>
                    </div>

                    <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800/60 font-mono">
                      <span>Contract Tolerances: abs ≤ {reproduceResult.tolerance?.metric_absolute_tolerance} | rel ≤ {(reproduceResult.tolerance?.metric_relative_tolerance * 100)}%</span>
                      <span className="text-[10px] text-slate-500">Run ID: {reproduceResult.reproduced_experiment_id?.slice(0, 8)}</span>
                    </div>
                  </div>
                )}
              </div>


              {/* Deterministic Tuple (Seeds, Strategy, Task) */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                    <Split className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Deterministic Partitioning & Seeds</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-400">
                    Architecture Contract §9
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  {/* Split Seed */}
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                    <div className="text-slate-400 text-[10px] flex items-center justify-between">
                      <span>Split Seed (Outer)</span>
                      {lineage.split_seed !== undefined && lineage.split_seed !== null && (
                        <button
                          onClick={() => copyToClipboard(lineage.split_seed, 'split_seed')}
                          className="text-slate-400 hover:text-white"
                          title="Copy Seed"
                        >
                          {copiedKey === 'split_seed' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                    <div className="font-mono font-bold text-indigo-300 text-sm">
                      {lineage.split_seed !== undefined && lineage.split_seed !== null ? lineage.split_seed : '42'}
                    </div>
                  </div>

                  {/* CV Seed */}
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                    <div className="text-slate-400 text-[10px] flex items-center justify-between">
                      <span>CV Seed (Inner)</span>
                      {lineage.cv_seed !== undefined && lineage.cv_seed !== null && (
                        <button
                          onClick={() => copyToClipboard(lineage.cv_seed, 'cv_seed')}
                          className="text-slate-400 hover:text-white"
                          title="Copy Seed"
                        >
                          {copiedKey === 'cv_seed' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                    <div className="font-mono font-bold text-indigo-300 text-sm">
                      {lineage.cv_seed !== undefined && lineage.cv_seed !== null ? lineage.cv_seed : '42'}
                    </div>
                  </div>

                  {/* CV Strategy */}
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                    <div className="text-slate-400 text-[10px]">CV Strategy</div>
                    <div className="font-mono font-bold text-slate-200 text-xs truncate">
                      {lineage.cv_strategy || (lineage.task_type === 'CLASSIFICATION' ? 'STRATIFIED_KFOLD' : 'KFOLD')}
                    </div>
                  </div>

                  {/* Fold Count */}
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                    <div className="text-slate-400 text-[10px]">Folds / Partitions</div>
                    <div className="font-mono font-bold text-slate-200 text-sm">
                      {lineage.fold_count || 5} Folds
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic Hashes & Integrity Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Dataset Content Hash */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center space-x-1.5 font-medium">
                      <Database className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Dataset Content Hash (SHA-256)</span>
                    </span>
                    {lineage.dataset_content_hash && (
                      <button
                        onClick={() => copyToClipboard(lineage.dataset_content_hash, 'data_hash')}
                        className="text-slate-400 hover:text-white p-1 rounded transition-colors"
                        title="Copy Hash"
                      >
                        {copiedKey === 'data_hash' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                  <div className="font-mono text-xs text-slate-200 break-all bg-slate-900 p-2.5 rounded-lg border border-slate-800/80">
                    {lineage.dataset_content_hash || 'No hash recorded'}
                  </div>
                </div>

                {/* Model Artifact Checksum */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center space-x-1.5 font-medium">
                      <Lock className="w-3.5 h-3.5 text-amber-400" />
                      <span>Winning Model Artifact Checksum (SHA-256)</span>
                    </span>
                    {lineage.winning_model?.artifact_checksum && (
                      <button
                        onClick={() => copyToClipboard(lineage.winning_model.artifact_checksum, 'artifact_hash')}
                        className="text-slate-400 hover:text-white p-1 rounded transition-colors"
                        title="Copy Checksum"
                      >
                        {copiedKey === 'artifact_hash' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                  <div className="font-mono text-xs text-slate-200 break-all bg-slate-900 p-2.5 rounded-lg border border-slate-800/80">
                    {lineage.winning_model?.artifact_checksum || 'Pending finalization'}
                  </div>
                  {lineage.winning_model?.artifact_path && (
                    <div className="text-[10px] text-slate-400 truncate font-mono">
                      File: {lineage.winning_model.artifact_path}
                    </div>
                  )}
                </div>
              </div>

              {/* Execution & Software Environment */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Software & Environment Versions</span>
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">Python</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{lineage.python_version || 'N/A'}</div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">scikit-learn</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{lineage.sklearn_version || 'N/A'}</div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">NumPy</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{lineage.numpy_version || 'N/A'}</div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">pandas</div>
                    <div className="font-mono font-bold text-slate-200 mt-0.5">{lineage.pandas_version || 'N/A'}</div>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <GitCommit className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-slate-400 text-[11px]">Git Commit Hash:</span>
                    <span className="font-mono font-bold text-slate-200 text-xs">{lineage.code_version || 'unknown'}</span>
                  </div>
                  {lineage.code_version && (
                    <button
                      onClick={() => copyToClipboard(lineage.code_version, 'commit')}
                      className="text-slate-400 hover:text-white p-1 rounded transition-colors"
                      title="Copy Commit Hash"
                    >
                      {copiedKey === 'commit' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  )}
                </div>

                {lineage.model_library_versions && Object.keys(lineage.model_library_versions).length > 0 && (
                  <div className="text-[11px] text-slate-400 space-y-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-500">Supporting Libraries:</span>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(lineage.model_library_versions).map(([k, v]) => (
                        <span key={k} className="px-2 py-0.5 bg-slate-900 text-slate-300 font-mono text-[10px] rounded border border-slate-800">
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Snapshots & Frozen Config Section */}
              <div className="space-y-4">
                {/* Frozen Experiment Config */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                      <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Frozen Experiment Configuration (experiment_config)</span>
                    </h4>
                    {lineage.experiment_config && (
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(lineage.experiment_config, null, 2), 'cfg')}
                        className="text-slate-400 hover:text-white p-1 rounded transition-colors text-xs flex items-center space-x-1"
                      >
                        {copiedKey === 'cfg' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span className="text-[10px]">Copy JSON</span>
                      </button>
                    )}
                  </div>
                  <pre className="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-indigo-300 overflow-x-auto max-h-56">
                    {lineage.experiment_config ? JSON.stringify(lineage.experiment_config, null, 2) : 'No config recorded'}
                  </pre>
                </div>

                {/* Feature Selection Snapshot */}
                {lineage.feature_selection_snapshot && (
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <h4 className="font-bold text-white flex items-center space-x-2">
                        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                        <span>Feature Selection Snapshot (Full Dev Refit)</span>
                      </h4>
                      <span className="text-[10px] font-mono text-slate-400">
                        Method: {lineage.feature_selection_snapshot.final_selection_method}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {lineage.feature_selection_snapshot.final_selected_features.map((feat) => (
                        <span key={feat} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[10px]">
                          {feat}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Transformation Snapshot */}
                {lineage.transformation_snapshot && (
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <h4 className="font-bold text-white flex items-center space-x-2">
                        <Layers className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Transformation Snapshot (Frozen Copy)</span>
                      </h4>
                      <span className="text-[10px] font-mono text-slate-400">
                        Snapshot ID: {lineage.transformation_snapshot.id}
                      </span>
                    </div>
                    <pre className="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-[10px] text-slate-400 overflow-x-auto max-h-40">
                      {JSON.stringify(lineage.transformation_snapshot.config_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
