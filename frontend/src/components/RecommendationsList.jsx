import React from 'react';
import { Lightbulb, AlertCircle, ArrowRight, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const RecommendationsList = ({ recommendations = [] }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 text-center text-slate-500 text-sm">
        <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/80" />
        No critical data quality risks detected. Dataset satisfies baseline health checks.
      </div>
    );
  }

  const getConfidenceBadge = (confidence) => {
    switch (confidence) {
      case 'HIGH':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">HIGH CONFIDENCE</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">MEDIUM CONFIDENCE</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-slate-500/10 text-slate-400 border border-slate-500/20">LOW CONFIDENCE</span>;
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-400">
            <Lightbulb className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-white">Diagnostics & Transformation Recommendations</h4>
            <p className="text-xs text-slate-400">
              Traceable prescriptive actions generated from DQI diagnostics (SRS §2.16)
            </p>
          </div>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-300">
          {recommendations.length} Actionable Items
        </span>
      </div>

      <div className="space-y-4">
        {recommendations.map((rec, idx) => (
          <div
            key={rec.id || idx}
            className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 transition-all duration-200 hover:border-slate-700"
          >
            {/* Header: Finding & Confidence */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-800/60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                <h5 className="text-sm font-semibold text-white">{rec.finding}</h5>
              </div>
              <div>{getConfidenceBadge(rec.confidence)}</div>
            </div>

            {/* Grid for Evidence & Recommended Action */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-3 text-xs">
              <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800/80">
                <span className="text-slate-500 uppercase font-mono text-[10px] tracking-wider block mb-1">
                  Empirical Evidence
                </span>
                <p className="text-slate-300 leading-relaxed font-sans">{rec.evidence}</p>
              </div>

              <div className="bg-indigo-950/30 p-3 rounded-lg border border-indigo-900/40">
                <span className="text-indigo-400 uppercase font-mono text-[10px] tracking-wider block mb-1 flex items-center gap-1">
                  <ArrowRight className="w-3 h-3" /> Recommended Action (Day 4+)
                </span>
                <p className="text-indigo-200 leading-relaxed font-medium">{rec.recommended_action}</p>
              </div>
            </div>

            {/* Risk Note */}
            {rec.risk_note && (
              <div className="p-2.5 bg-rose-950/20 border border-rose-900/30 rounded-lg flex items-start gap-2 text-xs text-rose-300">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
                <span>
                  <strong className="text-rose-400">Risk / Tradeoff:</strong> {rec.risk_note}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
