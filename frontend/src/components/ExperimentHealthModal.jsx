import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Activity,
  Cpu,
  Layers,
  FileCheck,
  Lock,
  ExternalLink,
  X,
  RefreshCw,
  Sparkles,
  ArrowRight,
  Check
} from 'lucide-react';
import { experimentApi } from '../api/client';

export const ExperimentHealthModal = ({ experimentId, onClose }) => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchHealth = async () => {
    if (!experimentId) return;
    setLoading(true);
    setError('');
    try {
      const res = await experimentApi.getHealth(experimentId);
      setHealthData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load Experiment Health Report');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, [experimentId]);

  if (!experimentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-4xl bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-[var(--color-border)] bg-[var(--color-surface-hover)]/30 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-extrabold text-text">Experiment Health & Integrity Report</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text-muted)] font-bold">
                  SRS v9 §13
                </span>
              </div>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                Multi-dimensional validation of statistical fit, feature evidence, cryptographic lineage, and 6 structural guarantees.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchHealth}
              className="p-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
              title="Refresh Health Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <div className="text-[var(--color-text-muted)] font-semibold">
                Verifying partition isolation and computing diagnostic health signals...
              </div>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : healthData ? (
            <>
              {/* Prominent Risk Banner */}
              <div
                className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm ${
                  healthData.risks_flagged_count === 0
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : healthData.overall_health === 'WARNING'
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-black/20 flex items-center justify-center shrink-0">
                    {healthData.risks_flagged_count === 0 ? (
                      <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-6 h-6 text-amber-400" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-black tracking-tight">
                      {healthData.risks_flagged_count === 0
                        ? '0 Risks Flagged — Clean Health Profile'
                        : `${healthData.risks_flagged_count} Risk${healthData.risks_flagged_count > 1 ? 's' : ''} Flagged`}
                    </div>
                    <div className="text-xs opacity-90 mt-0.5">{healthData.risks_summary}</div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 self-start sm:self-center">
                  <span className="px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-black/20 border border-current">
                    {healthData.overall_health}
                  </span>
                </div>
              </div>

              {/* Dynamic Signals Grid */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text uppercase tracking-wider">
                    Per-Experiment Dynamic Signals
                  </span>
                  {healthData.champion_algorithm && (
                    <span className="text-[11px] text-[var(--color-text-muted)] font-mono">
                      Champion: <strong className="text-text">{healthData.champion_algorithm}</strong>
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {/* Signal 1: Fit Diagnosis */}
                  <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5">
                    <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>Fit Diagnosis (§2.10)</span>
                      <Cpu className="w-3 h-3 text-indigo-400" />
                    </div>
                    <div className="text-xs font-extrabold text-text flex items-center space-x-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          healthData.signals.fit_diagnosis === 'GOOD_FIT'
                            ? 'bg-emerald-400'
                            : 'bg-amber-400'
                        }`}
                      />
                      <span>{healthData.signals.fit_diagnosis}</span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">
                      Gap: {healthData.signals.generalization_gap !== null ? healthData.signals.generalization_gap : 'N/A'}
                    </div>
                  </div>

                  {/* Signal 2: Evidence Strength */}
                  <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5">
                    <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>Feature Evidence (§2.7)</span>
                      <Sparkles className="w-3 h-3 text-amber-400" />
                    </div>
                    <div className="text-xs font-extrabold text-text flex items-center space-x-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          healthData.signals.evidence_strength === 'STRONG'
                            ? 'bg-emerald-400'
                            : healthData.signals.evidence_strength === 'MODERATE'
                            ? 'bg-teal-400'
                            : 'bg-amber-400'
                        }`}
                      />
                      <span>{healthData.signals.evidence_strength}</span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">
                      {healthData.signals.selected_features_count} features retained
                    </div>
                  </div>

                  {/* Signal 3: Artifact Checksum */}
                  <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5">
                    <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>Disk Binary Checksum (§2.14)</span>
                      <FileCheck className="w-3 h-3 text-teal-400" />
                    </div>
                    <div className="text-xs font-extrabold text-text flex items-center space-x-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          healthData.signals.artifact_checksum_status === 'VERIFIED'
                            ? 'bg-emerald-400'
                            : 'bg-rose-400'
                        }`}
                      />
                      <span>{healthData.signals.artifact_checksum_status}</span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)] font-mono truncate">
                      SHA-256: {healthData.signals.artifact_checksum ? healthData.signals.artifact_checksum.slice(0, 10) + '...' : 'Pending'}
                    </div>
                  </div>

                  {/* Signal 4: Locked Test Single-Pass */}
                  <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5">
                    <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>Locked Test Split (§2.12)</span>
                      <Lock className="w-3 h-3 text-rose-400" />
                    </div>
                    <div className="text-xs font-extrabold text-text flex items-center space-x-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          healthData.signals.locked_test_status === 'CONSUMED' || healthData.signals.locked_test_status === 'EVALUATED'
                            ? 'bg-emerald-400'
                            : 'bg-amber-400'
                        }`}
                      />
                      <span>{healthData.signals.locked_test_status}</span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">
                      Score: {healthData.signals.locked_test_score !== null ? healthData.signals.locked_test_score : 'Unconsumed'}
                    </div>
                  </div>

                  {/* Signal 5: Deployment Gate */}
                  <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5 sm:col-span-2">
                    <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>Deployment Gate Verification (§2.13)</span>
                      <ShieldCheck className="w-3 h-3 text-indigo-400" />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-extrabold text-text">
                        Gate Status: <span className={healthData.signals.gate_status === 'PASSED' ? 'text-emerald-400' : 'text-amber-400'}>{healthData.signals.gate_status}</span>
                      </div>
                      <span className="text-[11px] font-bold text-[var(--color-text-muted)]">
                        {healthData.signals.gate_conditions_passed} of {healthData.signals.gate_conditions_total} conditions met
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-[var(--color-surface)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${(healthData.signals.gate_conditions_passed / 6) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Flagged Risks Section */}
              {healthData.risks && healthData.risks.length > 0 && (
                <div className="space-y-3">
                  <span className="text-xs font-bold text-text uppercase tracking-wider">
                    Identified Risk Items & Actionable Remediation
                  </span>

                  <div className="space-y-2.5">
                    {healthData.risks.map((risk, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-extrabold text-text">{risk.finding}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                              risk.severity === 'CRITICAL'
                                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                : risk.severity === 'HIGH'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                            }`}
                          >
                            {risk.severity} Severity
                          </span>
                        </div>

                        <p className="text-[11px] text-[var(--color-text-muted)] leading-relaxed">
                          {risk.description}
                        </p>

                        <div className="pt-2 border-t border-[var(--color-border)] flex items-start space-x-1.5 text-[11px] text-teal-400 font-semibold">
                          <ArrowRight className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>Remediation: {risk.remediation}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Structural Guarantees Section */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text uppercase tracking-wider">
                    Static Structural Guarantees (Architectural Proofs)
                  </span>
                  <span className="text-[11px] text-emerald-400 font-bold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>6/6 Active & Enforced</span>
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {healthData.structural_guarantees.map((item) => (
                    <div
                      key={item.id}
                      className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-1.5"
                    >
                      <div className="flex items-center space-x-2">
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="text-xs font-bold text-text">{item.title}</span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-muted)] leading-relaxed pl-5.5">
                        {item.description}
                      </p>
                      <div className="pl-5.5 pt-1 text-[10px] font-mono text-[var(--color-text-muted)] opacity-80">
                        {item.invariant_rule}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-surface-hover)]/30 flex items-center justify-between shrink-0">
          <span className="text-[11px] text-[var(--color-text-muted)]">
            Generated: {healthData ? new Date(healthData.generated_at).toLocaleString() : 'N/A'}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-text hover:bg-[var(--color-surface-hover)] font-bold text-xs cursor-pointer transition-colors"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExperimentHealthModal;
