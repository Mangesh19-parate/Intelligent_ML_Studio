import React, { useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Database,
  BarChart3,
  Layers,
  Sparkles,
  Cpu,
  Eye,
  ShieldCheck,
  Send,
  ArrowRight,
  CheckCircle2,
  Lock,
  RotateCcw,
  Users,
  Code2,
  FileText,
  Sliders,
  ChevronRight,
  Sun,
  Moon,
  Info,
  Check,
  AlertTriangle,
  Terminal,
  X,
  Mail,
  KeyRound,
  ShieldAlert,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { OtpInput } from '../components/auth/OtpInput';
import axios from 'axios';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, register, verify2FA, darkMode, toggleDarkMode } = useAuth();

  // Navigation & Interactive Stage States
  const [activeStage, setActiveStage] = useState<number>(0);
  const [selectedTaskType, setSelectedTaskType] = useState<'CLASSIFICATION' | 'REGRESSION'>('CLASSIFICATION');
  const [showRuleTrace, setShowRuleTrace] = useState<boolean>(false);

  // Sign In Modal State
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [isRegister, setIsRegister] = useState<boolean>(false);
  const [authFullName, setAuthFullName] = useState<string>('');
  const [authEmail, setAuthEmail] = useState<string>('dev@mlstudio.io');
  const [authPassword, setAuthPassword] = useState<string>('password123');
  const [authError, setAuthError] = useState<string>('');
  const [authSubmitting, setAuthSubmitting] = useState<boolean>(false);

  // 2FA Challenge State inside Modal
  const [is2FAPrompt, setIs2FAPrompt] = useState<boolean>(false);
  const [twoFactorToken, setTwoFactorToken] = useState<string>('');
  const [twoFactorCode, setTwoFactorCode] = useState<string>('');
  const [isBackupCodeMode, setIsBackupCodeMode] = useState<boolean>(false);

  const openSignInModal = (registerMode = false) => {
    setIsRegister(registerMode);
    setAuthError('');
    setIs2FAPrompt(false);
    setIsBackupCodeMode(false);
    setShowAuthModal(true);
  };

  const handleAuthSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setAuthError('');
    setAuthSubmitting(true);
    try {
      if (is2FAPrompt) {
        await verify2FA(twoFactorToken, twoFactorCode);
        setShowAuthModal(false);
        navigate('/dashboard');
        return;
      }

      if (isRegister) {
        await register(authFullName, authEmail, authPassword);
        setShowAuthModal(false);
        navigate('/dashboard');
      } else {
        const res = await login(authEmail, authPassword);
        if (res.requires_2fa && res.two_factor_token) {
          setTwoFactorToken(res.two_factor_token);
          setIs2FAPrompt(true);
          setTwoFactorCode('');
        } else {
          setShowAuthModal(false);
          navigate('/dashboard');
        }
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setAuthError(
          err.response?.data?.detail || 'Authentication failed. Please check your credentials.'
        );
      } else {
        setAuthError('An unexpected error occurred during authentication.');
      }
    } finally {
      setAuthSubmitting(false);
    }
  };

  const lifecycleStages = [
    {
      id: 'dataset',
      title: 'Dataset',
      subtitle: 'Ingestion & Partition Seal',
      icon: Database,
      explanation: 'Ingest tabular CSV/Parquet and cryptographically seal the locked test partition before profiling runs.',
      metric: 'SHA-256 Cryptographic Hash',
      detail: 'The test partition is isolated into a sealed storage container with read-only access. Zero test rows are ever loaded during EDA or feature tuning.',
      code: `split_summary = dataset_split_service.create_split(
    dataset_id=dataset.id,
    locked_test_pct=20,
    seed=42
)
# Sealed Hash: 8f3a9e22... (Strictly Locked)`,
    },
    {
      id: 'profile',
      title: 'Profile',
      subtitle: 'DQI & Task-Type Detection',
      icon: BarChart3,
      explanation: 'Multi-factor Data Quality Index, Pearson correlation matrices, and automated task-type inference.',
      metric: 'DQI: 94.8 / 100 Score',
      detail: 'Assesses completeness, uniqueness, stability, and target association exclusively on the development partition.',
      code: `profile = data_profiling_service.generate_report(dataset_id)
# Detected Task: Classification (Binary)
# Target Balance: 72% Class 0 / 28% Class 1`,
    },
    {
      id: 'prepare',
      title: 'Prepare',
      subtitle: 'Leakage-Free Transformations',
      icon: Layers,
      explanation: 'Imputation, scaling, and categorical encoding fitted strictly inside CV training folds.',
      metric: 'Zero-Contamination Pipelines',
      detail: 'Imputers and scalers compute parameters only on training slices and apply them to validation slices to eliminate distribution leakage.',
      code: `transformer = ColumnTransformer([
    ('num', StandardScaler(), numeric_cols),
    ('cat', OneHotEncoder(drop='first'), cat_cols)
])
# Fitted fresh on each CV training fold slice`,
    },
    {
      id: 'features',
      title: 'Features',
      subtitle: 'Cross-Fold Rank Aggregation',
      icon: Sparkles,
      explanation: 'Select predictors via 4-technique ensemble without contaminating evaluation.',
      metric: '4-Selector Ensemble',
      detail: 'Ensemble of Absolute Correlation, Lasso L1, Random Forest Importance, and Permutation Importance aggregated across K folds.',
      code: `scores = feature_selection_service.run_cv_feature_selection(
    project_id=project.id,
    n_splits=5,
    method="RANK_AGGREGATION"
)
# Retained 12 of 18 features (Stability Index: 0.96)`,
    },
    {
      id: 'experiment',
      title: 'Experiment',
      subtitle: 'Controlled Algorithm Benchmarking',
      icon: Cpu,
      explanation: 'Compare standardized tabular models using controlled cross-validation.',
      metric: 'Standardized Leaderboard',
      detail: 'Automated hyperparameter exploration for Logistic Regression, Ridge, Random Forest, and LightGBM with identical fold splits.',
      code: `experiment = experiment_service.train_model(
    project_id=project.id,
    algorithm="LIGHTGBM",
    cv_strategy="STRATIFIED_K_FOLD"
)
# F1 Macro: 0.942 | ROC AUC: 0.978`,
    },
    {
      id: 'explain',
      title: 'Explain',
      subtitle: 'Global & Local SHAP Reasoning',
      icon: Eye,
      explanation: 'Understand model behavior with feature-level SHAP explanations.',
      metric: 'Exact TreeSHAP Attribution',
      detail: 'Decompose any single prediction into positive and negative feature contributions with mathematical consistency.',
      code: `shap_values = explainability_service.get_local_shap(
    model_id=model.id,
    input_row=sample_record
)
# +0.34 debt_ratio | -0.18 credit_score`,
    },
    {
      id: 'govern',
      title: 'Govern',
      subtitle: 'Dual-Signoff Quality Gates',
      icon: ShieldCheck,
      explanation: 'Apply eligibility criteria, threshold policies, and deployment controls.',
      metric: 'Dual-Key Approval Gate',
      detail: 'Production promotion requires independent verification by Data Scientist and Risk/Compliance Officer with immutable audit trail.',
      code: `gate_decision = governance_service.evaluate_gates(
    model_id=model.id,
    test_performance=test_metrics
)
# Passed: Accuracy >= 0.90, Fairness Delta < 0.05`,
    },
    {
      id: 'deploy',
      title: 'Deploy',
      subtitle: 'Live REST Endpoint & Drift Tracker',
      icon: Send,
      explanation: 'Serve real-time inference with decoupled latency profiles and drift alerts.',
      metric: '< 12ms P99 Latency',
      detail: 'Low-latency REST inference with background input payload logging, PSI data drift monitoring, and automatic fallback.',
      code: `POST /api/v1/deployments/{id}/predict
{ "account_age": 42, "credit_score": 750 }
# Response: { "prediction": 0, "latency_ms": 6.8 }`,
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] transition-colors duration-300 flex flex-col selection:bg-[var(--color-accent)] selection:text-white">
      {/* 1. Restrained Top Navigation Bar */}
      <header className="sticky top-0 z-40 backdrop-blur-md bg-[var(--color-bg)]/90 border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          {/* Brand Mark */}
          <Link to="/" className="flex items-center space-x-3 group">
            <span className="w-4 h-4 rounded-full bg-[var(--color-accent)] shadow-sm group-hover:scale-110 transition-transform" />
            <span className="text-lg font-black tracking-tight text-[var(--color-text)]">
              ML Studio
            </span>
          </Link>

          {/* Restrained Navigation Links */}
          <nav className="hidden md:flex items-center space-x-8 text-xs font-semibold text-[var(--color-text-muted)]">
            <a href="#platform" className="hover:text-[var(--color-text)] transition-colors">
              Platform
            </a>
            <a href="#lifecycle" className="hover:text-[var(--color-text)] transition-colors">
              Capabilities
            </a>
            <a href="#recommendations" className="hover:text-[var(--color-text)] transition-colors">
              Recommendations
            </a>
            <a href="#architecture" className="hover:text-[var(--color-text)] transition-colors">
              Architecture
            </a>
            <a href="#research" className="hover:text-[var(--color-text)] transition-colors">
              Research
            </a>
            <a href="#platform" className="hover:text-[var(--color-text)] transition-colors">
              Docs
            </a>
          </nav>

          {/* Auth & Mode Actions */}
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={toggleDarkMode}
              className="p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-all cursor-pointer"
              title="Toggle theme"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button
              type="button"
              onClick={() => openSignInModal(false)}
              className="px-4 py-2 text-xs font-bold text-[var(--color-text)] hover:text-[var(--color-accent)] transition-colors cursor-pointer"
            >
              Sign In
            </button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => openSignInModal(false)}
              className="rounded-full text-xs font-bold shadow-sm"
            >
              <span>Launch Studio</span>
            </Button>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section id="platform" className="pt-16 pb-20 md:pt-24 md:pb-28 px-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Narrative */}
          <div className="lg:col-span-7 space-y-6">
            {/* Pill Eyebrow */}
            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center px-3.5 py-1 rounded-full bg-[#F5C7B8]/40 dark:bg-[#F37338]/20 text-[#CF4500] dark:text-[#F37338] text-xs font-bold tracking-tight">
                no, really — exactly once
              </span>
              <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">
                Explainable AutoML Platform
              </span>
            </div>

            {/* Headline */}
            <div className="space-y-2">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-[var(--color-text)] leading-[1.08]">
                Stop grading your <br className="hidden sm:inline" />
                own homework.
              </h1>
              <p className="text-2xl sm:text-3xl font-bold text-[var(--color-text-muted)] tracking-tight">
                Build, validate, explain, and deploy ML models — with evidence.
              </p>
            </div>

            {/* Supporting Text */}
            <p className="text-sm sm:text-base text-[var(--color-text-muted)] max-w-xl leading-relaxed">
              We hide the test set before you ever see the data, and we only let you look at it one time.
              A tabular machine learning platform designed around leakage prevention, mathematical reproducibility,
              inspectable explanations, and governed dual-signoff deployment.
            </p>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Button
                variant="primary"
                size="lg"
                onClick={() => openSignInModal(false)}
                className="rounded-full text-xs font-bold shadow-md hover:shadow-lg transition-all"
              >
                <span>Upload a dataset</span>
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>

              <Button
                variant="secondary"
                size="lg"
                onClick={() => openSignInModal(false)}
                className="rounded-full text-xs font-bold"
              >
                <span>Explore Platform Demo</span>
              </Button>
            </div>

            {/* Trust Footer line */}
            <div className="pt-4 border-t border-[var(--color-border)]">
              <p className="text-[11px] font-mono tracking-widest uppercase text-[var(--color-text-muted)]">
                Tabular Regression and Classification • Six Algorithms • No Zoo
              </p>
            </div>
          </div>

          {/* Right Column: Evidence Inspection Cards & Product Preview */}
          {/* Right Column: 3 Invariant Stadium Cards & Model Passport */}
          <div className="lg:col-span-5 space-y-4">
            {/* 3 Core Invariant Cards matching reference screenshot */}
            <div className="space-y-4">
              <div className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-3xl p-6 flex items-center space-x-5 shadow-sm hover:shadow-md transition-all">
                <span className="w-11 h-11 rounded-2xl border-2 border-[var(--color-accent)] text-[var(--color-accent)] flex items-center justify-center shrink-0 bg-[var(--color-accent-soft)]">
                  <Lock className="w-5 h-5" strokeWidth={2} />
                </span>
                <div className="space-y-0.5 min-w-0">
                  <h4 className="text-base font-black text-[var(--color-text)] tracking-tight">
                    Test set sealed
                  </h4>
                  <p className="text-sm text-[var(--color-text-muted)] font-medium truncate sm:whitespace-normal">
                    before profiling runs
                  </p>
                </div>
              </div>

              <div className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-3xl p-6 flex items-center space-x-5 shadow-sm hover:shadow-md transition-all">
                <span className="w-11 h-11 rounded-2xl border-2 border-emerald-500 text-emerald-500 flex items-center justify-center shrink-0 bg-emerald-500/10">
                  <RotateCcw className="w-5 h-5" strokeWidth={2} />
                </span>
                <div className="space-y-0.5 min-w-0">
                  <h4 className="text-base font-black text-[var(--color-text)] tracking-tight">
                    Replay any run
                  </h4>
                  <p className="text-sm text-[var(--color-text-muted)] font-medium truncate sm:whitespace-normal">
                    same seeds, same answer
                  </p>
                </div>
              </div>

              <div className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-3xl p-6 flex items-center space-x-5 shadow-sm hover:shadow-md transition-all">
                <span className="w-11 h-11 rounded-2xl border-2 border-indigo-500 text-indigo-500 flex items-center justify-center shrink-0 bg-indigo-500/10">
                  <Users className="w-5 h-5" strokeWidth={2} />
                </span>
                <div className="space-y-0.5 min-w-0">
                  <h4 className="text-base font-black text-[var(--color-text)] tracking-tight">
                    Two people to ship
                  </h4>
                  <p className="text-sm text-[var(--color-text-muted)] font-medium truncate sm:whitespace-normal">
                    you can't approve yourself
                  </p>
                </div>
              </div>
            </div>

            {/* Live Model Passport Widget Mockup */}
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-3xl p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between text-xs pb-2.5 border-b border-[var(--color-border)]">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-bold font-mono text-[var(--color-text)]">
                    Model Passport: LightGBM-v3
                  </span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  PASSED ALL GATES
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
                <div className="p-2.5 rounded-2xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                  <div className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">F1 Macro</div>
                  <div className="font-mono font-black text-sm text-[var(--color-accent)] mt-0.5">0.9420</div>
                </div>
                <div className="p-2.5 rounded-2xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                  <div className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">Test Leakage</div>
                  <div className="font-mono font-black text-sm text-emerald-400 mt-0.5">0.00%</div>
                </div>
                <div className="p-2.5 rounded-2xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                  <div className="text-[10px] text-[var(--color-text-muted)] uppercase font-semibold">P99 Latency</div>
                  <div className="font-mono font-black text-sm text-[var(--color-text)] mt-0.5">8.4 ms</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. ML Lifecycle Section */}
      <section id="lifecycle" className="py-20 px-6 border-y border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div>
              <div className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider mb-2">
                End-to-End Workflow
              </div>
              <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--color-text)]">
                The Governed ML Lifecycle
              </h2>
              <p className="text-xs sm:text-sm text-[var(--color-text-muted)] mt-1.5 max-w-xl">
                Every stage enforces cryptographic partition boundaries, cross-validation isolation, and verifiable evidence.
              </p>
            </div>

            <div className="text-xs text-[var(--color-text-muted)] font-mono">
              8 Stages • 0% Outer Test Leakage Guarantee
            </div>
          </div>

          {/* Lifecycle Stepper Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            {lifecycleStages.map((stage, idx) => {
              const Icon = stage.icon;
              const isActive = activeStage === idx;
              return (
                <button
                  key={stage.id}
                  type="button"
                  onClick={() => setActiveStage(idx)}
                  className={`p-3.5 rounded-2xl text-left transition-all border cursor-pointer ${
                    isActive
                      ? 'bg-[var(--color-surface-card)] border-[var(--color-accent)] shadow-md translate-y-[-2px]'
                      : 'bg-[var(--color-bg)] border-[var(--color-border)] hover:border-[var(--color-text-muted)] text-[var(--color-text-muted)]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`p-2 rounded-xl text-xs ${
                        isActive
                          ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold'
                          : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </span>
                    <span className="text-[10px] font-mono font-bold">0{idx + 1}</span>
                  </div>
                  <div className={`text-xs font-bold ${isActive ? 'text-[var(--color-text)]' : 'text-[var(--color-text-muted)]'}`}>
                    {stage.title}
                  </div>
                  <div className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">
                    {stage.subtitle}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Active Stage Deep-Dive Card */}
          {(() => {
            const current = lifecycleStages[activeStage];
            const CurrentIcon = current.icon;
            return (
              <div className="bg-[var(--color-surface-card)] border border-[var(--color-border)] rounded-3xl p-6 lg:p-8 shadow-sm grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                <div className="lg:col-span-6 space-y-4">
                  <div className="flex items-center space-x-3">
                    <span className="p-3 rounded-2xl bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                      <CurrentIcon className="w-6 h-6" />
                    </span>
                    <div>
                      <div className="text-[10px] font-mono font-bold text-[var(--color-accent)] uppercase">
                        Stage {activeStage + 1} of 8
                      </div>
                      <h3 className="text-xl font-black text-[var(--color-text)]">
                        {current.title} — {current.subtitle}
                      </h3>
                    </div>
                  </div>

                  <p className="text-sm font-semibold text-[var(--color-text)]">
                    {current.explanation}
                  </p>

                  <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                    {current.detail}
                  </p>

                  <div className="flex items-center space-x-3 pt-2">
                    <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text)] font-mono">
                      {current.metric}
                    </span>
                  </div>
                </div>

                <div className="lg:col-span-6 min-w-0 w-full overflow-hidden">
                  <div className="bg-[#141413] text-[#F3F0EE] rounded-3xl p-5 border border-[#333230] font-mono text-xs space-y-3 shadow-inner w-full overflow-hidden">
                    <div className="flex flex-wrap items-center justify-between pb-3 border-b border-[#333230] text-[11px] text-[#A8A4A0] gap-2">
                      <div className="flex items-center space-x-2 shrink-0">
                        <Terminal className="w-4 h-4 text-[#F37338]" />
                        <span className="font-bold text-[#F3F0EE]">Execution Trace</span>
                      </div>
                      <span className="text-[10px] text-[#A8A4A0] bg-[#222220] px-2.5 py-0.5 rounded-full border border-[#333230]">
                        Python 3.13 / FastAPI Engine
                      </span>
                    </div>
                    <pre className="text-[11px] text-[#E3DFDC] leading-relaxed whitespace-pre-wrap break-words font-mono overflow-hidden">
                      <code>{current.code}</code>
                    </pre>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </section>

      {/* 4. Recommendation Engine (The Differentiator) */}
      <section id="recommendations" className="py-20 px-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column */}
          <div className="lg:col-span-6 space-y-6">
            <div>
              <div className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider mb-2">
                Inspectable Intelligence
              </div>
              <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--color-text)] leading-tight">
                Recommendations you can inspect.
              </h2>
            </div>

            <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
              Recommendations are generated from <strong className="text-[var(--color-text)]">explicit, deterministic, inspectable rules</strong> rather than black-box hidden model behavior.
            </p>

            <div className="space-y-3.5">
              <div className="flex items-start space-x-3">
                <span className="p-1 rounded-full bg-emerald-500/10 text-emerald-400 mt-0.5 shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </span>
                <p className="text-xs text-[var(--color-text-muted)]">
                  <strong className="text-[var(--color-text)]">Deterministic Rules: </strong>
                  Thresholds, missing rate criteria, and class balance ratios are codified in open rule trees.
                </p>
              </div>

              <div className="flex items-start space-x-3">
                <span className="p-1 rounded-full bg-emerald-500/10 text-emerald-400 mt-0.5 shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </span>
                <p className="text-xs text-[var(--color-text-muted)]">
                  <strong className="text-[var(--color-text)]">Target-Leakage Heuristics: </strong>
                  Detects suspicious $R^2 \ge 0.99$ or perfect single-feature separation before model training begins.
                </p>
              </div>

              <div className="flex items-start space-x-3">
                <span className="p-1 rounded-full bg-emerald-500/10 text-emerald-400 mt-0.5 shrink-0">
                  <Check className="w-3.5 h-3.5" />
                </span>
                <p className="text-xs text-[var(--color-text-muted)]">
                  <strong className="text-[var(--color-text)]">Human Override: </strong>
                  Accept, reject, or customize any metric, algorithm, or preprocessing suggestion at any step.
                </p>
              </div>
            </div>

            <div className="pt-2">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setShowRuleTrace(!showRuleTrace)}
                className="rounded-full text-xs font-bold"
              >
                <Code2 className="w-4 h-4 mr-2 text-[var(--color-accent)]" />
                <span>{showRuleTrace ? 'Hide Rule Trace Tree' : 'View Rule Trace Engine'}</span>
              </Button>
            </div>
          </div>

          {/* Right Column: Actual Recommendation Engine Card */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-3xl p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
                <div className="flex items-center space-x-2.5">
                  <span className="p-2 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                    <Sparkles className="w-4 h-4" />
                  </span>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-muted)]">
                      Recommendation Engine
                    </h4>
                    <span className="text-sm font-black text-[var(--color-text)]">
                      Active Dataset Diagnostic
                    </span>
                  </div>
                </div>

                {/* Task Type Switcher */}
                <div className="flex items-center bg-[var(--color-surface-hover)] p-1 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setSelectedTaskType('CLASSIFICATION')}
                    className={`px-3 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedTaskType === 'CLASSIFICATION'
                        ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                        : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    Classification
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedTaskType('REGRESSION')}
                    className={`px-3 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                      selectedTaskType === 'REGRESSION'
                        ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                        : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    Regression
                  </button>
                </div>
              </div>

              {/* Detected Facts */}
              <div className="space-y-2">
                <div className="text-[11px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                  Detected Data Characteristics
                </div>
                <div className="space-y-2 text-xs">
                  {selectedTaskType === 'CLASSIFICATION' ? (
                    <>
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>✓ Missing values: 3.4% in numeric columns (Iterative Imputation suggested)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>✓ Class imbalance: 72% Class 0 / 28% Class 1 (Stratified K-Fold applied)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                        <span>⚠ Potential target leakage: Column 'account_id' excluded from feature candidates</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>✓ Target distribution: Continuous float with positive skewness (+1.42)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>✓ Missing values: 2.8% in continuous features (KNN Imputation suggested)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                        <span>⚠ Outlier detection: 14 high-leverage outliers flagged (&gt; 3.0 IQR boundary)</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Recommended Metric & Models */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-3.5 rounded-2xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                  <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">
                    Recommended Metric
                  </div>
                  <div className="text-sm font-black text-[var(--color-accent)] mt-1">
                    {selectedTaskType === 'CLASSIFICATION' ? 'F1 Macro' : 'RMSE & MAE'}
                  </div>
                  <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
                    {selectedTaskType === 'CLASSIFICATION'
                      ? 'Balanced precision/recall on imbalanced target'
                      : 'Robust against high-value outliers'}
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-[var(--color-surface-hover)] border border-[var(--color-border)]">
                  <div className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">
                    Recommended Models
                  </div>
                  <div className="text-xs font-bold text-[var(--color-text)] mt-1 space-y-0.5 font-mono">
                    {selectedTaskType === 'CLASSIFICATION' ? (
                      <>
                        <div>1. Logistic Regression (Baseline)</div>
                        <div>2. Random Forest Classifier</div>
                        <div>3. LightGBM GBDT Classifier</div>
                      </>
                    ) : (
                      <>
                        <div>1. Ridge / Lasso Regression (Baseline)</div>
                        <div>2. Random Forest Regressor</div>
                        <div>3. LightGBM GBDT Regressor</div>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Rule Trace Expanded */}
              {showRuleTrace && (
                <div className="p-4 rounded-2xl bg-[#141413] text-[#F3F0EE] border border-[#333230] font-mono text-[11px] space-y-1.5 animate-fadeIn min-w-0 overflow-hidden break-words whitespace-pre-wrap">
                  <div className="text-[#F37338] font-bold text-xs pb-1.5 border-b border-[#333230] flex items-center justify-between">
                    <span>Rule Execution Trace</span>
                    <span className="text-[10px] text-[#A8A4A0]">
                      {selectedTaskType === 'CLASSIFICATION' ? 'RuleID: REC-CLF-042' : 'RuleID: REC-REG-019'}
                    </span>
                  </div>
                  {selectedTaskType === 'CLASSIFICATION' ? (
                    <>
                      <div className="text-[#E3DFDC] pt-1">→ Condition: target_cardinality == 2 & class_ratio &lt; 0.30</div>
                      <div className="text-[#E3DFDC]">→ Action: Set primary_metric = "F1_MACRO", cv = "STRATIFIED_K_FOLD"</div>
                      <div className="text-[#E3DFDC]">→ Heuristic: High multicollinearity detected (corr &gt; 0.85). Applied L1 Lasso selector.</div>
                      <div className="text-emerald-400 font-semibold pt-1">✓ Rule fired deterministically with zero black-box bias.</div>
                    </>
                  ) : (
                    <>
                      <div className="text-[#E3DFDC] pt-1">→ Condition: target_dtype == "float64" & target_skewness &gt; 1.0</div>
                      <div className="text-[#E3DFDC]">→ Action: Set primary_metric = "RMSE_MAE", cv = "K_FOLD", loss = "HUBER"</div>
                      <div className="text-[#E3DFDC]">→ Heuristic: Non-linear continuous interactions detected. Prioritized tree-based regressors.</div>
                      <div className="text-emerald-400 font-semibold pt-1">✓ Rule fired deterministically with zero black-box bias.</div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 5. Core Architectural Pillars */}
      <section id="architecture" className="py-20 px-6 border-t border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <div className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider">
              Architecture & Guarantees
            </div>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--color-text)]">
              Reliable ML is harder. We built the controls.
            </h2>
            <p className="text-xs sm:text-sm text-[var(--color-text-muted)]">
              ML is easy to train. ML Studio provides mathematical controls around the workflow that make the resulting evidence trustworthy.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="mc-card p-6 space-y-3">
              <span className="p-3 rounded-2xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] inline-block">
                <Lock className="w-6 h-6" />
              </span>
              <h3 className="text-base font-bold text-[var(--color-text)]">Zero Leakage Boundary</h3>
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                The locked test partition is sealed before any EDA, imputation, scaling, or feature selection runs. You can only evaluate the test set once at final gating.
              </p>
            </div>

            <div className="mc-card p-6 space-y-3">
              <span className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 inline-block">
                <RotateCcw className="w-6 h-6" />
              </span>
              <h3 className="text-base font-bold text-[var(--color-text)]">Deterministic Reproducibility</h3>
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                Every split seed, hyperparameter configuration, data version, and software package is stamped into a cryptographic Model Passport for 100% replayability.
              </p>
            </div>

            <div className="mc-card p-6 space-y-3">
              <span className="p-3 rounded-2xl bg-indigo-500/10 text-indigo-400 inline-block">
                <Users className="w-6 h-6" />
              </span>
              <h3 className="text-base font-bold text-[var(--color-text)]">Dual-Signoff Governance</h3>
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                You cannot deploy a model without an independent review. Both the author and an independent compliance officer must sign off on gate thresholds.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Call To Action Footer */}
      <section className="py-20 px-6 max-w-7xl mx-auto text-center space-y-6">
        <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--color-text)]">
          Ready to train machine learning models with real evidence?
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] max-w-xl mx-auto">
          Start ingesting tabular datasets, evaluating leak-free models, and producing cryptographic passports in minutes.
        </p>
        <div className="flex items-center justify-center space-x-4 pt-2">
          <Button
            variant="primary"
            size="lg"
            onClick={() => openSignInModal(false)}
            className="rounded-full text-xs font-bold shadow-lg"
          >
            <span>Launch ML Studio</span>
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </section>

      {/* 7. Restrained Footer */}
      <footer className="mt-auto border-t border-[var(--color-border)] py-8 px-6 bg-[var(--color-surface)]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[var(--color-text-muted)]">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-[var(--color-accent)]" />
            <span className="font-bold text-[var(--color-text)]">ML Studio</span>
            <span>• Enterprise Tabular Machine Learning Platform</span>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <a href="#platform" className="hover:text-[var(--color-text)] transition-colors">Platform</a>
            <a href="#lifecycle" className="hover:text-[var(--color-text)] transition-colors">Lifecycle</a>
            <a href="#recommendations" className="hover:text-[var(--color-text)] transition-colors">Recommendations</a>
            <Link to="/legal" className="hover:text-[var(--color-text)] transition-colors">Legal Center</Link>
            <Link to="/privacy" className="hover:text-[var(--color-text)] transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-[var(--color-text)] transition-colors">Terms of Service</Link>
            <button
              type="button"
              onClick={() => openSignInModal(false)}
              className="hover:text-[var(--color-text)] transition-colors cursor-pointer"
            >
              Sign In
            </button>
          </div>
        </div>
      </footer>

      {/* 8. Interactive Sign In & Authentication Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-3xl shadow-2xl p-7 space-y-6 relative animate-fadeIn">
            {/* Close Button */}
            <button
              type="button"
              onClick={() => setShowAuthModal(false)}
              className="absolute top-5 right-5 p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Header */}
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-[var(--color-accent)]" />
                <span className="text-xs font-mono font-bold text-[var(--color-accent)] uppercase tracking-wider">
                  ML Studio Access
                </span>
              </div>
              <h3 className="text-xl font-black text-[var(--color-text)] tracking-tight">
                {is2FAPrompt
                  ? 'Two-Factor Verification'
                  : isRegister
                  ? 'Create ML Studio Account'
                  : 'Sign in to ML Studio'}
              </h3>
              <p className="text-xs text-[var(--color-text-muted)]">
                {is2FAPrompt
                  ? 'Enter the 6-digit TOTP token generated by your authenticator app.'
                  : isRegister
                  ? 'Register your account to access leakage-free tabular ML pipelines.'
                  : 'Sign in to access your projects, models, and real-time inference deployments.'}
              </p>
            </div>

            {/* Error Message */}
            {authError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleAuthSubmit} className="space-y-4">
              {is2FAPrompt ? (
                <div className="space-y-3">
                  <label className="block text-xs font-semibold text-[var(--color-text-muted)] text-center">
                    {isBackupCodeMode ? 'Enter 8-Character Emergency Recovery Key' : 'Enter 6-Digit Authenticator Code'}
                  </label>

                  {isBackupCodeMode ? (
                    <div className="relative">
                      <KeyRound className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                      <input
                        type="text"
                        required
                        autoFocus
                        maxLength={10}
                        placeholder="XXXX-XXXX"
                        value={twoFactorCode}
                        onChange={(e) => setTwoFactorCode(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 text-xs font-mono font-bold tracking-widest rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] text-center"
                      />
                    </div>
                  ) : (
                    <div className="py-2">
                      <OtpInput
                        value={twoFactorCode}
                        onChange={setTwoFactorCode}
                        disabled={authSubmitting}
                      />
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setIsBackupCodeMode(!isBackupCodeMode);
                        setTwoFactorCode('');
                        setAuthError('');
                      }}
                      className="text-xs text-[var(--color-accent)] hover:underline font-medium cursor-pointer"
                    >
                      {isBackupCodeMode ? 'Use Authenticator Code Instead' : 'Lost device? Use Recovery Key'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIs2FAPrompt(false);
                        setTwoFactorToken('');
                        setTwoFactorCode('');
                        setAuthError('');
                      }}
                      className="text-xs text-[var(--color-text-muted)] hover:underline cursor-pointer"
                    >
                      Back to Sign In
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {isRegister && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-[var(--color-text)]">Full Name</label>
                      <input
                        type="text"
                        required
                        placeholder="Dr. Jane Doe"
                        value={authFullName}
                        onChange={(e) => setAuthFullName(e.target.value)}
                        className="w-full px-4 py-2.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                      />
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-[var(--color-text)]">Email Address</label>
                    <div className="relative">
                      <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                      <input
                        type="email"
                        required
                        placeholder="you@company.com"
                        value={authEmail}
                        onChange={(e) => setAuthEmail(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-[var(--color-text)]">Password</label>
                    <div className="relative">
                      <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                      <input
                        type="password"
                        required
                        placeholder="••••••••••••"
                        value={authPassword}
                        onChange={(e) => setAuthPassword(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                disabled={authSubmitting}
                isLoading={authSubmitting}
                className="w-full rounded-full font-bold shadow-md text-xs py-2.5 mt-2"
              >
                <span>{is2FAPrompt ? 'Verify and Enter Dashboard' : isRegister ? 'Create Account & Enter' : 'Sign In to Dashboard'}</span>
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </form>

            {/* Dev Account Quick Fill Helper */}
            {!is2FAPrompt && (
              <div className="pt-2 border-t border-[var(--color-border)] flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setAuthEmail('dev@mlstudio.io');
                    setAuthPassword('password123');
                    setIsRegister(false);
                  }}
                  className="text-[11px] font-mono font-semibold text-[var(--color-accent)] hover:underline cursor-pointer"
                >
                  ⚡ Auto-fill Dev Account
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(!isRegister);
                    setAuthError('');
                  }}
                  className="text-xs font-bold text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors cursor-pointer"
                >
                  {isRegister ? 'Already have an account? Sign In' : 'Need an account? Register'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
