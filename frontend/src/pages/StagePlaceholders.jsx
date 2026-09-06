import React from 'react';
import { Link } from 'react-router-dom';
import {
  Database,
  BarChart3,
  SlidersHorizontal,
  Workflow,
  Stethoscope,
  Cpu,
  Rocket,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Lock,
} from 'lucide-react';

export const DataStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 2 of 8</span>
            <span>&bull;</span>
            <span>Structural Ingestion</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Data Ingestion & Schema</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Upload raw tabular files (CSV, XLSX, JSON) with strict structural schema validation and pre-split isolation.
          </p>
        </div>
        <Link
          to="/data-analysis"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Data Analysis</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Raw Dataset Upload</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Multi-format stream upload with SHA-256 content hashing for reproducible deduplication.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Structural Validation</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Pre-split inference of column dtypes (numeric, categorical, datetime) and null percentages.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
            <Lock className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Outer Split Lock</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Deterministic partitioning into Development and isolated Locked Test sets.
          </p>
        </div>
      </div>
    </div>
  );
};

export const AnalysisStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 3 of 8</span>
            <span>&bull;</span>
            <span>Development Profiling</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Data Analysis & DQI</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Explore distributions, correlations, and compute the multi-factor Data Quality Index (DQI).
          </p>
        </div>
        <Link
          to="/transformations"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Feature Transformation</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center">
            <BarChart3 className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Development Partition Profiling</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Distribution histograms, missingness heatmaps, and Pearson/Spearman correlation matrices.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Data Quality Index (DQI)</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Composite 0-100 score across missingness, duplicate rate, outlier prevalence, and type consistency.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-500 flex items-center justify-center">
            <Workflow className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Task-Type Confidence</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Automated detection for Classification vs. Regression with confidence level boundaries.
          </p>
        </div>
      </div>
    </div>
  );
};

export const TransformationStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 4 of 8</span>
            <span>&bull;</span>
            <span>Leakage-Safe Preprocessing</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Feature Transformation</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Configure imputation, categorical encoding, scaling, and outlier handling fit strictly per CV fold.
          </p>
        </div>
        <Link
          to="/feature-engineering"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Feature Engineering</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <h3 className="text-base font-bold text-text flex items-center space-x-2">
          <SlidersHorizontal className="w-5 h-5 text-[var(--color-accent)]" />
          <span>Transformation Strategy Pipeline</span>
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Transformations are compiled into a ColumnTransformer wrapped directly in each training fold.
        </p>
      </div>
    </div>
  );
};

export const FeatureEngineeringStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 5 of 8</span>
            <span>&bull;</span>
            <span>Rank-Aggregation Ensemble</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Feature Engineering</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Multi-method rank aggregation combining Correlation, Lasso, Random Forest, and Permutation importance.
          </p>
        </div>
        <Link
          to="/diagnostics"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Diagnostics</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <h3 className="text-base font-bold text-text flex items-center space-x-2">
          <Workflow className="w-5 h-5 text-indigo-400" />
          <span>Ensemble Feature Selection</span>
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Default selection parameters: TOP_K_PERCENT, alpha=0.25, k_min=5, k_max=50, min_applied_methods=2.
        </p>
      </div>
    </div>
  );
};

export const DiagnosticsStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 6 of 8</span>
            <span>&bull;</span>
            <span>Model Health & Recommendations</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Diagnostics & Insights</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Overfitting/underfitting gap analysis and automated dataset health recommendations.
          </p>
        </div>
        <Link
          to="/machine-learning"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Machine Learning</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <h3 className="text-base font-bold text-text flex items-center space-x-2">
          <Stethoscope className="w-5 h-5 text-rose-400" />
          <span>Overfit / Underfit Diagnostics</span>
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Direction-aware generalization gap calculations comparing Training vs. CV-mean performance.
        </p>
      </div>
    </div>
  );
};

export const MLStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 7 of 8</span>
            <span>&bull;</span>
            <span>6-Algorithm Model Training</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Machine Learning Training</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            5-fold cross-validation across the canonical algorithm catalog with primary-metric leaderboard ranking.
          </p>
        </div>
        <Link
          to="/production"
          className="px-4 py-2 rounded-xl bg-[var(--color-accent)] hover:opacity-90 text-white text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Next: Production & Deployment</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <h3 className="text-base font-bold text-text flex items-center space-x-2">
          <Cpu className="w-5 h-5 text-amber-400" />
          <span>Algorithm Catalog & Leaderboard</span>
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Regression: Linear Regression, Ridge, Random Forest, Gradient Boosting.<br />
          Classification: Logistic Regression, Random Forest, Gradient Boosting.
        </p>
      </div>
    </div>
  );
};

export const ProductionStage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-1">
            <span>Stage 8 of 8</span>
            <span>&bull;</span>
            <span>Deployment Gates & Serving</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">Production Deployment</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Enforce multi-condition deployment gates, serve real-time predictions, and monitor traffic logs.
          </p>
        </div>
        <Link
          to="/dashboard"
          className="px-4 py-2 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-text text-xs font-bold flex items-center space-x-2 shadow-sm transition"
        >
          <span>Return to Workspace</span>
        </Link>
      </div>

      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
        <h3 className="text-base font-bold text-text flex items-center space-x-2">
          <Rocket className="w-5 h-5 text-emerald-400" />
          <span>Deployment Gate & Serving Pipeline</span>
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Locked test verification, schema lock, artifact checksum match, performance threshold check, and sign-off.
        </p>
      </div>
    </div>
  );
};
