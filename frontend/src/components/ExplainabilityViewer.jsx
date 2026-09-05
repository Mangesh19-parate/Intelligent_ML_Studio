import React, { useState, useEffect } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { modelApi } from '../api/client';
import {
  BrainCircuit,
  Activity,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Zap,
  HelpCircle,
  Database,
  ArrowRight,
  Calculator,
  RefreshCw,
} from 'lucide-react';

const Plot = createPlotlyComponent(Plotly);

export const ExplainabilityViewer = ({
  modelId,
  algorithmName,
  isWinner,
  hasArtifact,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summaryData, setSummaryData] = useState(null);

  // Local explanation state
  const [localInput, setLocalInput] = useState('');
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState(null);
  const [localResult, setLocalResult] = useState(null);

  useEffect(() => {
    if (!hasArtifact && !isWinner) {
      setError(
        'This model has no persisted artifact — explainability is only available for the winning model of a completed experiment'
      );
      setLoading(false);
      return;
    }
    loadGlobalSummary();
  }, [modelId]);

  const loadGlobalSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await modelApi.getExplainability(modelId);
      setSummaryData(res.data);

      // Pre-fill local explanation test input template with feature names
      if (res.data && res.data.shap_values) {
        const template = {};
        Object.keys(res.data.shap_values).forEach((k) => {
          template[k] = 1.0;
        });
        setLocalInput(JSON.stringify(template, null, 2));
      }
    } catch (err) {
      console.error('Failed to load explainability summary:', err);
      const msg =
        err.response?.data?.detail ||
        'Failed to load explainability summary for this model.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRunLocalExplanation = async () => {
    try {
      setLocalLoading(true);
      setLocalError(null);
      setLocalResult(null);

      let parsedInput;
      try {
        parsedInput = JSON.parse(localInput);
      } catch (jsonErr) {
        setLocalError('Invalid JSON format for input instance.');
        setLocalLoading(false);
        return;
      }

      const res = await modelApi.getLocalExplainability(modelId, parsedInput);
      setLocalResult(res.data);
    } catch (err) {
      console.error('Failed to run local explanation:', err);
      setLocalError(
        err.response?.data?.detail || 'Failed to compute instance explanation.'
      );
    } finally {
      setLocalLoading(false);
    }
  };

  // Prepare plot data for Global Bar Chart
  const features = summaryData?.shap_values
    ? Object.keys(summaryData.shap_values).reverse()
    : [];
  const shapVals = summaryData?.shap_values
    ? Object.values(summaryData.shap_values).reverse()
    : [];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-slate-200">
      {/* Modal Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-bold text-white">Model Explainability</h3>
              {isWinner && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                  Winning Model
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              SHAP Attribution & Global/Local Feature Interpretability for{' '}
              <strong className="text-slate-200">{algorithmName}</strong>
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
        >
          Close
        </button>
      </div>

      {/* Modal Body */}
      <div className="p-6 overflow-y-auto space-y-6">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-400 font-mono">
              Computing SHAP explanations on development background sample...
            </p>
          </div>
        ) : error ? (
          <div className="p-5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
            <div className="space-y-1">
              <h4 className="font-bold text-rose-200">Explainability Unavailable</h4>
              <p className="text-xs text-rose-300/90 leading-relaxed">{error}</p>
            </div>
          </div>
        ) : summaryData ? (
          <>
            {/* Metadata Badges & Invariant Notice */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold flex items-center space-x-1">
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Explainer Architecture</span>
                </div>
                <div className="text-sm font-bold text-white font-mono flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  <span>{summaryData.explainer_type} Explainer</span>
                </div>
              </div>

              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold flex items-center space-x-1">
                  <Database className="w-3.5 h-3.5 text-blue-400" />
                  <span>Background Sample</span>
                </div>
                <div className="text-sm font-bold text-white font-mono">
                  {summaryData.background_sample_size} rows (Dev Split)
                </div>
              </div>

              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold flex items-center space-x-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                  <span>Cache Status</span>
                </div>
                <div className="text-sm font-bold text-white font-mono flex items-center space-x-1">
                  {summaryData.is_cached ? (
                    <span className="text-emerald-400">Schema DB Cache Hit</span>
                  ) : (
                    <span className="text-indigo-400">Computed & Cached</span>
                  )}
                </div>
              </div>

              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Generated At</span>
                </div>
                <div className="text-xs font-mono text-slate-300 truncate">
                  {new Date(summaryData.generated_at).toLocaleString()}
                </div>
              </div>
            </div>

            {/* Leakage Guard Invariant Banner */}
            <div className="p-3 rounded-xl bg-indigo-950/30 border border-indigo-500/20 text-indigo-300 text-xs flex items-center space-x-2.5 font-mono">
              <ShieldCheck className="w-4 h-4 text-indigo-400 flex-shrink-0" />
              <span>
                <strong>Leakage-Safe Partitioning:</strong> Explainer background reference is strictly drawn from the Development partition. Locked Test data is never sampled.
              </span>
            </div>

            {/* Global SHAP Summary Plotly Bar Chart */}
            <div className="p-5 bg-slate-950/80 border border-slate-800 rounded-2xl shadow-inner space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>Global Feature Importance (Mean Absolute SHAP)</span>
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Average magnitude of feature contributions across the reference sample.
                  </p>
                </div>
                <button
                  onClick={loadGlobalSummary}
                  title="Reload explainability summary"
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="w-full h-80">
                <Plot
                  data={[
                    {
                      type: 'bar',
                      orientation: 'h',
                      x: shapVals,
                      y: features,
                      marker: {
                        color: shapVals.map(
                          (v, i) =>
                            `rgba(99, 102, 241, ${0.45 + 0.55 * (i / (shapVals.length || 1))})`
                        ),
                        line: {
                          color: '#818cf8',
                          width: 1.5,
                        },
                      },
                      hoverinfo: 'x+y',
                    },
                  ]}
                  layout={{
                    autosize: true,
                    margin: { l: 150, r: 30, t: 20, b: 40 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                    xaxis: {
                      title: { text: 'Mean |SHAP value| (Average Impact)', font: { size: 11, color: '#94a3b8' } },
                      tickfont: { color: '#94a3b8', size: 10 },
                      gridcolor: '#1e293b',
                    },
                    yaxis: {
                      tickfont: { color: '#e2e8f0', size: 11 },
                      gridcolor: '#1e293b',
                    },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              </div>
            </div>

            {/* Interactive Local Explanation Playground (Day 9 Precursor to Day 10) */}
            <div className="p-5 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-4">
              <div className="flex items-center space-x-2 pb-2 border-b border-slate-800">
                <Calculator className="w-4 h-4 text-emerald-400" />
                <div>
                  <h4 className="text-sm font-bold text-white">Local Explanation & Additivity Inspector</h4>
                  <p className="text-[11px] text-slate-400">
                    Test instance-level feature contribution breakdown and verify exact SHAP additivity ($\sum contributions + base = prediction$).
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* JSON Input Area */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300 font-mono">
                    Input Instance Features (JSON)
                  </label>
                  <textarea
                    rows={6}
                    value={localInput}
                    onChange={(e) => setLocalInput(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs font-mono text-indigo-300 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                  <button
                    onClick={handleRunLocalExplanation}
                    disabled={localLoading}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold transition-colors flex items-center space-x-2 cursor-pointer"
                  >
                    {localLoading ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-amber-300" />
                    )}
                    <span>Compute Local Explanation</span>
                  </button>
                  {localError && (
                    <p className="text-xs text-rose-400 font-mono">{localError}</p>
                  )}
                </div>

                {/* Local Explanation Output & Additivity Breakdown */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                  <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Attribution Breakdown
                  </h5>

                  {localResult ? (
                    <div className="space-y-3 font-mono text-xs">
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                        <div className="flex justify-between text-slate-400">
                          <span>Base / Expected Value:</span>
                          <strong className="text-white">{localResult.base_value}</strong>
                        </div>
                        <div className="flex justify-between text-slate-400">
                          <span>Model Prediction:</span>
                          <strong className="text-indigo-400">{localResult.prediction ?? 'N/A'}</strong>
                        </div>
                        <div className="flex justify-between text-emerald-400 border-t border-slate-800 pt-1">
                          <span>Sum (Contribs + Base):</span>
                          <strong>{localResult.sum_contributions_plus_base}</strong>
                        </div>
                      </div>

                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {Object.entries(localResult.contributions).map(([feat, val]) => (
                          <div
                            key={feat}
                            className="flex items-center justify-between text-[11px] p-1.5 rounded bg-slate-950/60 border border-slate-800/60"
                          >
                            <span className="text-slate-300 truncate max-w-[140px]">{feat}</span>
                            <span
                              className={`font-bold ${
                                val > 0
                                  ? 'text-emerald-400'
                                  : val < 0
                                  ? 'text-rose-400'
                                  : 'text-slate-500'
                              }`}
                            >
                              {val > 0 ? `+${val}` : val}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic py-6 text-center">
                      Click "Compute Local Explanation" to view instance feature pushes and additivity check.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};
