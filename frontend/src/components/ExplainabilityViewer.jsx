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
  X,
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
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-[var(--color-text)]">
      {/* Modal Header */}
      <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface-card)]">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-xl text-[var(--color-accent)]">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-bold text-[var(--color-text)]">Model Explainability</h3>
              {isWinner && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] uppercase">
                  Winning Model
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              SHAP Attribution & Global/Local Feature Interpretability for{' '}
              <strong className="text-[var(--color-text)]">{algorithmName}</strong>
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Modal Body */}
      <div className="p-6 overflow-y-auto space-y-6">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-3 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-[var(--color-text-muted)] font-mono">
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
              <div className="p-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold flex items-center space-x-1.5">
                  <Activity className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                  <span>Explainer Architecture</span>
                </div>
                <div className="text-sm font-bold text-[var(--color-text)] font-mono flex items-center space-x-1.5 mt-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  <span>{summaryData.explainer_type} Explainer</span>
                </div>
              </div>

              <div className="p-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold flex items-center space-x-1.5">
                  <Database className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                  <span>Background Sample</span>
                </div>
                <div className="text-sm font-bold text-[var(--color-text)] font-mono mt-1">
                  {summaryData.background_sample_size} rows (Dev Split)
                </div>
              </div>

              <div className="p-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                  <span>Cache Status</span>
                </div>
                <div className="text-sm font-bold text-[var(--color-text)] font-mono flex items-center space-x-1 mt-1">
                  {summaryData.is_cached ? (
                    <span className="text-emerald-400">Schema DB Cache Hit</span>
                  ) : (
                    <span className="text-[var(--color-accent)]">Computed & Cached</span>
                  )}
                </div>
              </div>

              <div className="p-4 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl space-y-1">
                <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold flex items-center space-x-1.5">
                  <Clock className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
                  <span>Generated At</span>
                </div>
                <div className="text-xs font-mono text-[var(--color-text-muted)] truncate mt-1">
                  {new Date(summaryData.generated_at).toLocaleString()}
                </div>
              </div>
            </div>

            {/* Leakage Guard Invariant Banner */}
            <div className="p-4 rounded-2xl bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] text-[var(--color-text)] text-xs flex items-center space-x-2.5 font-mono">
              <ShieldCheck className="w-4 h-4 text-[var(--color-accent)] flex-shrink-0" />
              <span>
                <strong>Leakage-Safe Partitioning:</strong> Explainer background reference is strictly drawn from the Development partition. Locked Test data is never sampled.
              </span>
            </div>

            {/* Global SHAP Summary Plotly Bar Chart */}
            <div className="p-5 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[var(--color-border)]">
                <div>
                  <h4 className="text-sm font-bold text-[var(--color-text)] flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>Global Feature Importance (Mean Absolute SHAP)</span>
                  </h4>
                  <p className="text-[11px] text-[var(--color-text-muted)]">
                    Average magnitude of feature contributions across the reference sample.
                  </p>
                </div>
                <button
                  onClick={loadGlobalSummary}
                  title="Reload explainability summary"
                  className="p-2 rounded-full bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] border border-[var(--color-border)] transition-colors cursor-pointer"
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
                            `rgba(255, 94, 0, ${0.45 + 0.55 * (i / (shapVals.length || 1))})`
                        ),
                        line: {
                          color: '#ff5e00',
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
                      gridcolor: 'rgba(255,255,255,0.06)',
                    },
                    yaxis: {
                      tickfont: { color: '#e2e8f0', size: 11 },
                      gridcolor: 'rgba(255,255,255,0.06)',
                    },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              </div>
            </div>

            {/* Interactive Local Explanation Playground */}
            <div className="p-5 bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-2xl space-y-4">
              <div className="flex items-center space-x-2 pb-2 border-b border-[var(--color-border)]">
                <Calculator className="w-4 h-4 text-emerald-400" />
                <div>
                  <h4 className="text-sm font-bold text-[var(--color-text)]">Local Explanation & Additivity Inspector</h4>
                  <p className="text-[11px] text-[var(--color-text-muted)]">
                    Test instance-level feature contribution breakdown and verify exact SHAP additivity.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* JSON Input Area */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-[var(--color-text)] font-mono">
                    Input Instance Features (JSON)
                  </label>
                  <textarea
                    rows={6}
                    value={localInput}
                    onChange={(e) => setLocalInput(e.target.value)}
                    className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 text-xs font-mono text-[var(--color-accent)] focus:outline-none focus:border-[var(--color-accent)] transition-colors"
                  />
                  <button
                    onClick={handleRunLocalExplanation}
                    disabled={localLoading}
                    className="px-5 py-2.5 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-50 text-white text-xs font-bold transition-all flex items-center space-x-2 cursor-pointer shadow-sm"
                  >
                    {localLoading ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5" />
                    )}
                    <span>Compute Local Explanation</span>
                  </button>
                  {localError && (
                    <p className="text-xs text-rose-400 font-mono">{localError}</p>
                  )}
                </div>

                {/* Local Explanation Output & Additivity Breakdown */}
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 space-y-3">
                  <h5 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">
                    Attribution Breakdown
                  </h5>

                  {localResult ? (
                    <div className="space-y-3 font-mono text-xs">
                      <div className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1">
                        <div className="flex justify-between text-[var(--color-text-muted)]">
                          <span>Base / Expected Value:</span>
                          <strong className="text-[var(--color-text)]">{localResult.base_value}</strong>
                        </div>
                        <div className="flex justify-between text-[var(--color-text-muted)]">
                          <span>Model Prediction:</span>
                          <strong className="text-[var(--color-accent)]">{localResult.prediction ?? 'N/A'}</strong>
                        </div>
                        <div className="flex justify-between text-emerald-400 border-t border-[var(--color-border)] pt-1">
                          <span>Sum (Contribs + Base):</span>
                          <strong>{localResult.sum_contributions_plus_base}</strong>
                        </div>
                      </div>

                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {Object.entries(localResult.contributions).map(([feat, val]) => (
                          <div
                            key={feat}
                            className="flex items-center justify-between text-[11px] p-2 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-border)]"
                          >
                            <span className="text-[var(--color-text)] truncate max-w-[140px]">{feat}</span>
                            <span
                              className={`font-bold ${
                                val > 0
                                  ? 'text-emerald-400'
                                  : val < 0
                                  ? 'text-rose-400'
                                  : 'text-[var(--color-text-muted)]'
                              }`}
                            >
                              {val > 0 ? `+${val}` : val}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-[var(--color-text-muted)] italic py-6 text-center">
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

export default ExplainabilityViewer;
