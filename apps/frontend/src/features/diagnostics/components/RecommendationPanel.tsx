import React from 'react';
import { Sparkles, ArrowRight, Lightbulb } from 'lucide-react';
import { RecommendationItem } from '../../../types/api';

interface RecommendationPanelProps {
  recommendations: RecommendationItem[];
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({ recommendations }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-400">
        <Lightbulb className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-sm">No actionable recommendations generated yet.</p>
        <p className="text-xs text-slate-500 mt-1">Run an experiment or ingest fresh dataset features to trigger suggestions.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-white">Automated Pipeline Recommendations</h3>
          <p className="text-xs text-slate-400">Prescriptive interventions based on data distribution & fit diagnostics</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {recommendations.map((rec, idx) => (
          <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">{rec.category || 'MODELING'}</span>
                <span className="text-xs text-slate-400">Impact: {rec.impact || 'MEDIUM'}</span>
              </div>
              <h4 className="text-sm font-medium text-white mb-1">{rec.title}</h4>
              <p className="text-xs text-slate-400 leading-relaxed">{rec.description}</p>
            </div>
            {rec.action_label && (
              <div className="mt-4 pt-3 border-t border-slate-700/40 flex items-center justify-between text-xs text-indigo-400 font-medium cursor-pointer hover:text-indigo-300">
                <span>{rec.action_label}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
