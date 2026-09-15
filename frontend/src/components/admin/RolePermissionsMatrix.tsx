import React from 'react';
import { Cpu, Activity, Sliders, Check } from 'lucide-react';

interface RolePermissionsMatrixProps {
  algorithms: any[];
  metrics: any[];
  features: any;
}

export const RolePermissionsMatrix: React.FC<RolePermissionsMatrixProps> = ({
  algorithms,
  metrics,
  features,
}) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Algorithms Catalog */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center space-x-2 border-b border-[var(--color-border)] pb-3">
            <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
            <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">
              Supported ML Algorithms ({algorithms.length})
            </h3>
          </div>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {algorithms.map((alg: any) => (
              <div
                key={alg.id || alg.name}
                className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-[var(--color-text)]">{alg.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-accent)]">
                    {alg.task_type || 'GENERAL'}
                  </span>
                </div>
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  {alg.description || 'Verified scikit-learn estimator engine.'}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Evaluation Metrics Catalog */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center space-x-2 border-b border-[var(--color-border)] pb-3">
            <Activity className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">
              Statistical Evaluation Metrics ({metrics.length})
            </h3>
          </div>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {metrics.map((m: any) => (
              <div
                key={m.id || m.key || m.name}
                className="p-3 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-[var(--color-text)]">{m.name || m.key}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {m.direction || 'OPTIMIZE'}
                  </span>
                </div>
                <p className="text-[11px] text-[var(--color-text-muted)]">
                  {m.description || 'Calculated strictly on out-of-fold and locked test data.'}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Transformations & Engineering */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center space-x-2 border-b border-[var(--color-border)] pb-3">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">
              Preprocessing & Transformations
            </h3>
          </div>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {features?.imputers?.map((imp: string) => (
              <div key={imp} className="p-2.5 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--color-text)]">{imp}</span>
                <span className="text-[10px] text-[var(--color-text-muted)] font-mono">Imputer</span>
              </div>
            ))}
            {features?.scalers?.map((sc: string) => (
              <div key={sc} className="p-2.5 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--color-text)]">{sc}</span>
                <span className="text-[10px] text-[var(--color-text-muted)] font-mono">Scaler</span>
              </div>
            ))}
            {features?.encoders?.map((enc: string) => (
              <div key={enc} className="p-2.5 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-border)] flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--color-text)]">{enc}</span>
                <span className="text-[10px] text-[var(--color-text-muted)] font-mono">Encoder</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
