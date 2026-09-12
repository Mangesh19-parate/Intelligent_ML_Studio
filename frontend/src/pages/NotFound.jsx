import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Compass,
  ArrowLeft,
  LayoutDashboard,
  Database,
  Cpu,
  Mail,
  Phone,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';

export const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex flex-col justify-between p-4 sm:p-6 lg:p-8 transition-colors">
      {/* Header */}
      <header className="max-w-6xl w-full mx-auto flex items-center justify-between py-4">
        <Link to="/dashboard" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[var(--color-accent)] via-amber-500 to-orange-400 flex items-center justify-center text-white shadow-md shadow-[var(--color-accent)]/20 group-hover:scale-105 transition-transform">
            <Compass className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-extrabold tracking-tight text-[var(--color-text)]">
              ML Studio
            </span>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-text-muted)] -mt-0.5">
              Pipeline Routing Core
            </span>
          </div>
        </Link>

        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-xs font-semibold hover:bg-[var(--color-surface-hover)] transition-all min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4 text-[var(--color-accent)]" />
          <span>Go Back</span>
        </button>
      </header>

      {/* Main 404 Hero */}
      <main className="max-w-2xl w-full mx-auto my-auto text-center py-12 px-4">
        {/* Status Badge */}
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs font-mono font-bold mb-6">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>HTTP 404 &bull; RESOURCE_NOT_FOUND</span>
        </div>

        {/* 404 Number with Signal Accent Glow */}
        <h1 className="text-7xl sm:text-9xl font-black tracking-tighter text-[var(--color-text)] relative">
          <span className="bg-gradient-to-b from-[var(--color-text)] via-[var(--color-text)] to-[var(--color-text-muted)] bg-clip-text text-transparent">
            404
          </span>
        </h1>

        <h2 className="text-xl sm:text-2xl font-bold mt-4 tracking-tight text-[var(--color-text)]">
          Stage Not Found in ML Studio Pipeline
        </h2>

        <p className="text-sm text-[var(--color-text-muted)] mt-2 max-w-lg mx-auto leading-relaxed">
          The pipeline stage, experiment artifact, or dataset endpoint you requested does not exist or has been archived. Check the URL or return to an active workspace stage.
        </p>

        {/* Quick Navigation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-8 text-left">
          <Link
            to="/dashboard"
            className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-accent)]/50 hover:bg-[var(--color-surface-hover)] transition-all group min-h-[44px] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <LayoutDashboard className="w-4 h-4 text-[var(--color-accent)]" />
              <span className="text-[10px] font-mono text-[var(--color-text-muted)]">STAGE 01</span>
            </div>
            <div>
              <div className="text-xs font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors">
                Workspace Dashboard
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                Overview & project metrics
              </div>
            </div>
          </Link>

          <Link
            to="/data"
            className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-accent)]/50 hover:bg-[var(--color-surface-hover)] transition-all group min-h-[44px] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <Database className="w-4 h-4 text-indigo-400" />
              <span className="text-[10px] font-mono text-[var(--color-text-muted)]">STAGE 02</span>
            </div>
            <div>
              <div className="text-xs font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors">
                Data Ingestion
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                Upload & dataset catalog
              </div>
            </div>
          </Link>

          <Link
            to="/machine-learning"
            className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-accent)]/50 hover:bg-[var(--color-surface-hover)] transition-all group min-h-[44px] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span className="text-[10px] font-mono text-[var(--color-text-muted)]">STAGE 05</span>
            </div>
            <div>
              <div className="text-xs font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors">
                ML Training Studio
              </div>
              <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                Algorithms & leaderboard
              </div>
            </div>
          </Link>
        </div>

        {/* Primary CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            to="/dashboard"
            className="w-full sm:w-auto px-6 py-3 rounded-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-md shadow-[var(--color-accent)]/20 transition-all flex items-center justify-center space-x-2 min-h-[44px]"
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Return to Workspace</span>
          </Link>
          <a
            href="mailto:support@mlstudio.io?subject=404%20Error%20Report"
            className="w-full sm:w-auto px-6 py-3 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text)] text-xs font-semibold transition-all flex items-center justify-center space-x-2 min-h-[44px]"
          >
            <Mail className="w-4 h-4 text-[var(--color-text-muted)]" />
            <span>Report Broken Route</span>
          </a>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl w-full mx-auto pt-6 border-t border-[var(--color-border)]/60 text-xs text-[var(--color-text-muted)] flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center space-x-4">
          <span>&copy; {new Date().getFullYear()} ML Studio Inc. All rights reserved.</span>
        </div>
        <div className="flex items-center space-x-4">
          <a
            href="mailto:support@mlstudio.io"
            className="flex items-center space-x-1.5 hover:text-[var(--color-accent)] transition-colors min-h-[44px] py-2"
          >
            <Mail className="w-3.5 h-3.5" />
            <span>support@mlstudio.io</span>
          </a>
          <span>&bull;</span>
          <a
            href="tel:+18005550199"
            className="flex items-center space-x-1.5 hover:text-[var(--color-accent)] transition-colors min-h-[44px] py-2"
          >
            <Phone className="w-3.5 h-3.5" />
            <span>+1 (800) 555-0199</span>
          </a>
        </div>
      </footer>
    </div>
  );
};

export default NotFound;
