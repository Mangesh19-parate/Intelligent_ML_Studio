import React, { useState, useEffect } from 'react';
import { transformationApi } from '../api/client';
import {
  Wand2,
  SlidersHorizontal,
  Eye,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  HelpCircle,
  Zap,
  Layers,
  ArrowRight,
  ShieldCheck,
  X,
  Database
} from 'lucide-react';

const NUMERIC_MISSING_OPTIONS = [
  { value: 'none', label: 'None (Passthrough)' },
  { value: 'mean', label: 'Mean Imputation' },
  { value: 'median', label: 'Median Imputation (Robust)' },
  { value: 'arbitrary', label: 'Arbitrary Constant (0.0)' },
  { value: 'knn', label: 'KNN Imputer (k=5)' },
  { value: 'iterative', label: 'Iterative (MICE)' },
];

const CATEGORICAL_MISSING_OPTIONS = [
  { value: 'none', label: 'None (Passthrough)' },
  { value: 'mode', label: 'Mode (Most Frequent)' },
  { value: 'missing_category', label: "Missing Category ('missing')" },
];

const ENCODING_OPTIONS = [
  { value: 'none', label: 'None (Raw String)' },
  { value: 'one_hot', label: 'One-Hot Encoding (OHE)' },
  { value: 'ordinal', label: 'Ordinal Encoding (Integer)' },
];

const SCALING_OPTIONS = [
  { value: 'none', label: 'None (Unscaled)' },
  { value: 'standard', label: 'Standard Scaler (Mean=0, Std=1)' },
  { value: 'minmax', label: 'Min-Max Scaler [0, 1]' },
  { value: 'robust', label: 'Robust Scaler (Median/IQR)' },
];

const OUTLIER_OPTIONS = [
  { value: 'none', label: 'None (Keep Outliers)' },
  { value: 'iqr', label: 'IQR Capping (1.5 × IQR)' },
  { value: 'zscore', label: 'Z-Score Capping (±3.0σ)' },
  { value: 'percentile', label: 'Percentile Capping (1% – 99%)' },
  { value: 'winsorize', label: 'Winsorization (5% – 95%)' },
];

export const TransformationsTable = ({ projectId, isTargetColumn, onTransformationChanged }) => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingColumn, setSavingColumn] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const loadConfigs = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const res = await transformationApi.getConfigs(projectId);
      setConfigs(res.data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load transformation configurations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadConfigs();
    }
  }, [projectId]);

  const handleStrategyChange = async (columnName, field, value) => {
    // Optimistic UI update
    setConfigs((prev) =>
      prev.map((c) => (c.column_name === columnName ? { ...c, [field]: value } : c))
    );

    setSavingColumn(columnName);
    setErrorMsg('');
    setStatusMsg('');

    try {
      const res = await transformationApi.updateColumn(projectId, columnName, {
        [field]: value,
      });
      // Sync with server response
      setConfigs((prev) =>
        prev.map((c) => (c.column_name === columnName ? { ...c, ...res.data } : c))
      );
      setStatusMsg(`Updated ${field.replace('_', ' ')} for column "${columnName}"`);
      if (onTransformationChanged) onTransformationChanged();
      setTimeout(() => setStatusMsg(''), 3000);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || `Failed to update ${field} for column ${columnName}`);
      loadConfigs(); // Revert on failure
    } finally {
      setSavingColumn(null);
    }
  };

  const handlePreview = async (columnName) => {
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewData(null);

    try {
      const res = await transformationApi.preview(projectId, columnName, 50);
      setPreviewData(res.data);
    } catch (err) {
      setPreviewError(err.response?.data?.detail || 'Failed to generate transformation preview.');
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
        <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading transformation configurations...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 text-indigo-400">
              <Wand2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>Configurable Feature Transformation Engine</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-full">
                  Template Mode
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Define column transformation strategies. Generates fresh, unfit <code className="text-indigo-300 font-mono text-[11px]">ColumnTransformer</code> templates for per-fold cross-validation.
              </p>
            </div>
          </div>

          <button
            onClick={loadConfigs}
            className="self-start sm:self-auto px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all flex items-center space-x-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {/* Architectural Guarantee Box */}
        <div className="p-3.5 rounded-xl bg-indigo-500/5 border border-indigo-500/15 flex items-start space-x-3 text-xs text-slate-300">
          <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-white">
              Leakage-Controlled Architectural Guarantee (SRS §2.6 / §4.2):
            </p>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              No transformer is fit on the entire Development partition. Strategies are stored as declared recipes in <code className="text-indigo-300 font-mono">transformation_configs</code>. The pipeline is instantiated and fit on each training CV fold independently during model training.
            </p>
          </div>
        </div>

        {/* Notification alerts */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {statusMsg && (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{statusMsg}</span>
          </div>
        )}

        {/* Table of Column Configurations */}
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold text-[10px]">
                <th className="py-3 px-4">Column & Type</th>
                <th className="py-3 px-4">Missing Values</th>
                <th className="py-3 px-4">Encoding (Categorical)</th>
                <th className="py-3 px-4">Scaling (Numeric)</th>
                <th className="py-3 px-4">Outliers (Numeric)</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {configs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 italic">
                    No columns found in dataset schema.
                  </td>
                </tr>
              ) : (
                configs.map((cfg) => {
                  const isNumeric = cfg.data_type === 'NUMERIC';
                  const isCategorical = cfg.data_type === 'CATEGORICAL' || cfg.data_type === 'MIXED';
                  const isSaving = savingColumn === cfg.column_name;
                  const isTarget = isTargetColumn && isTargetColumn(cfg.column_name);

                  return (
                    <tr
                      key={cfg.column_name}
                      className="hover:bg-slate-900/40 transition-colors"
                    >
                      {/* Column Name & Type Badge */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono font-semibold text-white">
                            {cfg.column_name}
                          </span>
                          {isTarget && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              TARGET
                            </span>
                          )}
                        </div>
                        <div className="mt-1">
                          {isNumeric && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              NUMERIC
                            </span>
                          )}
                          {isCategorical && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              CATEGORICAL
                            </span>
                          )}
                          {!isNumeric && !isCategorical && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400">
                              {cfg.data_type}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Missing Value Strategy */}
                      <td className="py-3.5 px-4 min-w-[160px]">
                        <select
                          value={cfg.missing_value_strategy || 'none'}
                          disabled={isSaving}
                          onChange={(e) =>
                            handleStrategyChange(
                              cfg.column_name,
                              'missing_value_strategy',
                              e.target.value
                            )
                          }
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                        >
                          {isNumeric &&
                            NUMERIC_MISSING_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          {isCategorical &&
                            CATEGORICAL_MISSING_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          {!isNumeric && !isCategorical && (
                            <option value="none">None (Passthrough)</option>
                          )}
                        </select>
                      </td>

                      {/* Encoding Strategy (Categorical only) */}
                      <td className="py-3.5 px-4 min-w-[160px]">
                        {isCategorical ? (
                          <select
                            value={cfg.encoding_strategy || 'none'}
                            disabled={isSaving}
                            onChange={(e) =>
                              handleStrategyChange(
                                cfg.column_name,
                                'encoding_strategy',
                                e.target.value
                              )
                            }
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                          >
                            {ENCODING_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-[11px] text-slate-600 italic">
                            N/A (Numeric)
                          </span>
                        )}
                      </td>

                      {/* Scaling Strategy (Numeric only) */}
                      <td className="py-3.5 px-4 min-w-[160px]">
                        {isNumeric ? (
                          <select
                            value={cfg.scaling_strategy || 'none'}
                            disabled={isSaving}
                            onChange={(e) =>
                              handleStrategyChange(
                                cfg.column_name,
                                'scaling_strategy',
                                e.target.value
                              )
                            }
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                          >
                            {SCALING_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-[11px] text-slate-600 italic">
                            N/A (Categorical)
                          </span>
                        )}
                      </td>

                      {/* Outlier Strategy (Numeric only) */}
                      <td className="py-3.5 px-4 min-w-[160px]">
                        {isNumeric ? (
                          <select
                            value={cfg.outlier_strategy || 'none'}
                            disabled={isSaving}
                            onChange={(e) =>
                              handleStrategyChange(
                                cfg.column_name,
                                'outlier_strategy',
                                e.target.value
                              )
                            }
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                          >
                            {OUTLIER_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-[11px] text-slate-600 italic">
                            N/A (Categorical)
                          </span>
                        )}
                      </td>

                      {/* Preview Impact Action */}
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handlePreview(cfg.column_name)}
                          disabled={previewLoading}
                          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/15 hover:bg-indigo-600/25 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold transition-all cursor-pointer disabled:opacity-50"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Preview Impact</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Preview Modal / Drawer */}
      {(previewLoading || previewData || previewError) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>Transformation Preview</span>
                    {previewData && (
                      <span className="font-mono text-indigo-300 text-xs">
                        "{previewData.column}"
                      </span>
                    )}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Temporary UI fit on Development partition sample. State discarded immediately.
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  setPreviewData(null);
                  setPreviewError(null);
                }}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {previewLoading && (
              <div className="py-12 text-center space-y-3">
                <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Computing preview transformation...</p>
              </div>
            )}

            {previewError && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{previewError}</span>
              </div>
            )}

            {previewData && !previewLoading && (
              <div className="space-y-4 overflow-y-auto flex-1 pr-1">
                {/* Applied recipe badges */}
                <div className="flex flex-wrap gap-2 text-[10px]">
                  <span className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-mono">
                    Missing: {previewData.applied_strategies.missing_value_strategy}
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-mono">
                    Encoding: {previewData.applied_strategies.encoding_strategy}
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-mono">
                    Scaling: {previewData.applied_strategies.scaling_strategy}
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-mono">
                    Outliers: {previewData.applied_strategies.outlier_strategy}
                  </span>
                </div>

                {/* Before / After Table */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/70 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                        <th className="py-2.5 px-3 w-12 text-center">#</th>
                        <th className="py-2.5 px-4 text-slate-300">Raw Input (Before)</th>
                        <th className="py-2.5 px-4 text-indigo-400">Transformed Output (After)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 font-mono text-[11px]">
                      {previewData.before_values.map((rawVal, idx) => {
                        const afterVal = previewData.after_values[idx];
                        const isChanged = JSON.stringify(rawVal) !== JSON.stringify(afterVal);

                        return (
                          <tr
                            key={idx}
                            className={isChanged ? 'bg-indigo-950/20' : 'hover:bg-slate-900/30'}
                          >
                            <td className="py-1.5 px-3 text-center text-slate-500 text-[10px]">
                              {idx + 1}
                            </td>
                            <td className="py-1.5 px-4 text-slate-300">
                              {rawVal === null || rawVal === undefined ? (
                                <span className="text-amber-400/80 italic font-sans text-[10px]">
                                  null (missing)
                                </span>
                              ) : (
                                String(rawVal)
                              )}
                            </td>
                            <td className="py-1.5 px-4 text-white">
                              {Array.isArray(afterVal) ? (
                                <span className="text-purple-300">[{afterVal.join(', ')}]</span>
                              ) : afterVal === null || afterVal === undefined ? (
                                <span className="text-slate-500 italic font-sans text-[10px]">
                                  null
                                </span>
                              ) : (
                                <span className={isChanged ? 'text-indigo-300 font-semibold' : 'text-slate-300'}>
                                  {typeof afterVal === 'number' ? afterVal.toFixed(4) : String(afterVal)}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  setPreviewData(null);
                  setPreviewError(null);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
