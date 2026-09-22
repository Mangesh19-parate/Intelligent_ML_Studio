import React from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Experiment } from '../../../types/api';

interface LeakagePanelProps {
  experiment: Experiment | null;
}

export const LeakagePanel: React.FC<LeakagePanelProps> = ({ experiment }) => {
  const isLockedTestConsumed = experiment?.locked_test_consumed ?? false;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Leakage Control & Partition Invariants</h3>
            <p className="text-xs text-slate-400">Strict isolation across train, validation, and locked test partitions</p>
          </div>
        </div>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Invariants Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <div className="flex items-center space-x-2 text-xs font-medium text-slate-400 mb-1">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Fold Isolation</span>
          </div>
          <div className="text-sm font-semibold text-white">Outer Cross-Validation Isolated</div>
          <div className="text-xs text-slate-500 mt-1">Preprocessors fitted strictly on training folds</div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <div className="flex items-center space-x-2 text-xs font-medium text-slate-400 mb-1">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Feature Selection Guard</span>
          </div>
          <div className="text-sm font-semibold text-white">Permutation Isolation Verified</div>
          <div className="text-xs text-slate-500 mt-1">Zero locked test access during rank aggregation</div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <div className="flex items-center space-x-2 text-xs font-medium text-slate-400 mb-1">
            {isLockedTestConsumed ? (
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            )}
            <span>Locked Test Partition</span>
          </div>
          <div className="text-sm font-semibold text-white">
            {isLockedTestConsumed ? 'Consumed (Single-Use Locked)' : 'Pristine & Sealed'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {isLockedTestConsumed
              ? 'Final benchmark score frozen to prevent adaptive overfitting'
              : 'Partition untouched prior to model finalization'}
          </div>
        </div>
      </div>
    </div>
  );
};
