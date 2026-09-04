import React from 'react';
import { ShieldCheck, AlertCircle, Info, Scale, CheckCircle2, AlertTriangle } from 'lucide-react';

export const DataQualityCard = ({ dqiData }) => {
  if (!dqiData) return null;

  const { sub_scores, effective_weights, overall_index } = dqiData;
  const isRenormalized = effective_weights?.outlier_prevalence === null;

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return 'text-slate-400';
    if (score >= 90) return 'text-emerald-400';
    if (score >= 75) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getProgressColor = (score) => {
    if (score === null || score === undefined) return 'bg-slate-700';
    if (score >= 90) return 'bg-gradient-to-r from-emerald-500 to-teal-400';
    if (score >= 75) return 'bg-gradient-to-r from-amber-500 to-yellow-400';
    return 'bg-gradient-to-r from-rose-500 to-red-400';
  };

  const getScoreBadge = (score) => {
    if (score >= 90) return { label: 'EXCELLENT', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
    if (score >= 75) return { label: 'ACCEPTABLE', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' };
    return { label: 'REQUIRES ACTION', color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' };
  };

  const badge = getScoreBadge(overall_index);

  const subScoreItems = [
    {
      key: 'missingness',
      name: 'Missingness Score',
      score: sub_scores?.missingness,
      weight: effective_weights?.missingness,
      defaultWeight: 0.35,
      desc: '100 - (missing cells / total cells) * 100',
    },
    {
      key: 'duplicate_rate',
      name: 'Duplicate Rate Score',
      score: sub_scores?.duplicate_rate,
      weight: effective_weights?.duplicate_rate,
      defaultWeight: 0.25,
      desc: '100 - (duplicate rows / total rows) * 100',
    },
    {
      key: 'outlier_prevalence',
      name: 'Outlier Prevalence Score',
      score: sub_scores?.outlier_prevalence,
      weight: effective_weights?.outlier_prevalence,
      defaultWeight: 0.20,
      desc: '100 - (IQR-flagged cells / numeric cells) * 100',
      isNA: sub_scores?.outlier_prevalence === null,
    },
    {
      key: 'type_consistency',
      name: 'Type Consistency Score',
      score: sub_scores?.type_consistency,
      weight: effective_weights?.type_consistency,
      defaultWeight: 0.20,
      desc: '100 - (mixed-dtype cols / total cols) * 100',
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-sm">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
                Data Quality Index (DQI)
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${badge.color}`}>
                  {badge.label}
                </span>
              </h3>
              <p className="text-sm text-slate-400 mt-0.5">
                Evaluated exclusively on the isolated Development partition
              </p>
            </div>
          </div>
        </div>

        {/* Big Score Display */}
        <div className="flex items-center gap-4 bg-slate-950/60 border border-slate-800 px-6 py-4 rounded-xl">
          <div className="text-right">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-500 block">Overall DQI</span>
            <span className={`text-4xl font-black tracking-tight ${getScoreColor(overall_index)}`}>
              {overall_index?.toFixed(1)}
            </span>
            <span className="text-slate-500 text-sm font-semibold"> / 100</span>
          </div>
        </div>
      </div>

      {/* Sub-scores grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-6">
        {subScoreItems.map((item) => {
          const formattedWeight = item.weight !== null && item.weight !== undefined
            ? `${(item.weight * 100).toFixed(1)}%`
            : 'N/A';

          return (
            <div
              key={item.key}
              className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-4 transition-all duration-200 hover:border-slate-700/80"
            >
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-sm font-medium text-slate-200">{item.name}</span>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{item.desc}</p>
                </div>
                <div className="text-right">
                  {item.isNA ? (
                    <span className="text-xs font-semibold px-2 py-1 bg-slate-800 text-slate-400 rounded-md">
                      N/A (No Numeric)
                    </span>
                  ) : (
                    <span className={`text-lg font-bold ${getScoreColor(item.score)}`}>
                      {item.score?.toFixed(1)}
                    </span>
                  )}
                  <span className="text-xs text-slate-500 block">
                    Weight: <strong className="text-slate-400">{formattedWeight}</strong>
                  </span>
                </div>
              </div>

              {/* Bar */}
              {!item.isNA ? (
                <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden mt-3">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${getProgressColor(item.score)}`}
                    style={{ width: `${Math.min(Math.max(item.score || 0, 0), 100)}%` }}
                  />
                </div>
              ) : (
                <div className="w-full bg-slate-800/40 rounded-full h-2 overflow-hidden mt-3">
                  <div className="h-full bg-slate-700/40 rounded-full w-full" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Weight Renormalization Notice */}
      {isRenormalized && (
        <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center gap-3 text-xs text-amber-300">
          <Scale className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            <strong>Adaptive Weight Renormalization:</strong> Since no numeric columns were present, Outlier Prevalence was excluded and remaining weights were renormalized (Missingness: 43.75%, Duplicate: 31.25%, Type Consistency: 25.0%) to preserve 100% total weight distribution.
          </span>
        </div>
      )}

      {/* Mandatory SRS §2.3 Disclaimer Caption */}
      <div className="p-3.5 bg-slate-950/80 border border-slate-800/80 rounded-xl flex items-start gap-3">
        <Info className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-slate-400 leading-relaxed">
          <strong className="text-slate-300">Interpretation Guard:</strong> This summarizes data condition, not fitness for a specific modeling task — e.g. high outlier prevalence is not inherently bad for problems like fraud detection.
        </p>
      </div>
    </div>
  );
};
