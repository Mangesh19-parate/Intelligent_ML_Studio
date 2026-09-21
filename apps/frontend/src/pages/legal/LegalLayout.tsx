import React, { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Sun,
  Moon,
  ArrowLeft,
  ShieldCheck,
  FileText,
  Lock,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';

interface TocItem {
  id: string;
  number: string;
  title: string;
}

interface LegalLayoutProps {
  title: string;
  lastUpdated: string;
  subtitle: string;
  tocItems: TocItem[];
  activeSection?: string;
  children: ReactNode;
  activeDoc: 'privacy' | 'terms' | 'legal' | 'security';
}

export const LegalLayout: React.FC<LegalLayoutProps> = ({
  title,
  lastUpdated,
  subtitle,
  tocItems,
  activeSection,
  children,
  activeDoc,
}) => {
  const { darkMode, toggleDarkMode } = useAuth();

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const yOffset = -80;
      const y = el.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] transition-colors selection:bg-[var(--color-accent)] selection:text-white flex flex-col font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-40 backdrop-blur-md bg-[var(--color-bg)]/95 border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link
              to="/"
              className="flex items-center space-x-2.5 text-xs font-bold text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors group"
            >
              <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to ML Studio</span>
            </Link>

            <span className="text-[var(--color-border)]">/</span>

            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-[var(--color-accent)] shrink-0" />
              <Link to="/legal" className="text-xs font-bold text-[var(--color-text)] hover:text-[var(--color-accent)] transition-colors">
                Legal & Governance Center
              </Link>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <nav className="hidden sm:flex items-center space-x-4 text-xs font-semibold text-[var(--color-text-muted)]">
              <Link
                to="/privacy"
                className={`hover:text-[var(--color-text)] transition-colors ${
                  activeDoc === 'privacy' ? 'text-[var(--color-accent)] font-bold' : ''
                }`}
              >
                Privacy Policy
              </Link>
              <Link
                to="/terms"
                className={`hover:text-[var(--color-text)] transition-colors ${
                  activeDoc === 'terms' ? 'text-[var(--color-accent)] font-bold' : ''
                }`}
              >
                Terms of Service
              </Link>
            </nav>

            <button
              type="button"
              onClick={toggleDarkMode}
              className="p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-all cursor-pointer"
              title="Toggle theme"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 py-12 flex-1 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* Sticky Table of Contents (Left Column) */}
          <aside className="lg:col-span-3 hidden lg:block">
            <div className="sticky top-24 space-y-6">
              <div className="space-y-1">
                <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-[var(--color-accent)]">
                  On this page
                </div>
                <h4 className="text-xs font-bold text-[var(--color-text)]">
                  Table of Contents
                </h4>
              </div>

              <nav className="space-y-1 text-xs max-h-[calc(100vh-200px)] overflow-y-auto pr-2">
                {tocItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => scrollToSection(item.id)}
                    className="w-full text-left py-1.5 px-2.5 rounded-lg text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)] transition-all flex items-baseline space-x-2 group cursor-pointer"
                  >
                    <span className="font-mono text-[10px] text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] shrink-0">
                      {item.number}
                    </span>
                    <span className="truncate">{item.title}</span>
                  </button>
                ))}
              </nav>

              <div className="pt-4 border-t border-[var(--color-border)] space-y-2 text-[11px] text-[var(--color-text-muted)]">
                <div className="font-bold text-[var(--color-text)]">Other Legal Resources</div>
                <div>
                  <Link to="/privacy" className="hover:underline flex items-center justify-between">
                    <span>Privacy Policy</span>
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
                <div>
                  <Link to="/terms" className="hover:underline flex items-center justify-between">
                    <span>Terms of Service</span>
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
                <div>
                  <Link to="/legal" className="hover:underline flex items-center justify-between">
                    <span>Legal & Security Hub</span>
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          </aside>

          {/* Document Content (Right Column - 900-1000px max reading width) */}
          <article className="lg:col-span-9 max-w-4xl space-y-10">
            {/* Document Header */}
            <div className="border-b border-[var(--color-border)] pb-8 space-y-3">
              <div className="flex items-center space-x-3 text-xs text-[var(--color-text-muted)] font-mono">
                <span>Official Policy Document</span>
                <span>•</span>
                <span>Last updated: {lastUpdated}</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--color-text)]">
                {title}
              </h1>
              <p className="text-sm text-[var(--color-text-muted)] max-w-2xl leading-relaxed">
                {subtitle}
              </p>
            </div>

            {/* Document Body */}
            {children}
          </article>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] py-8 px-6 bg-[var(--color-surface)] text-xs text-[var(--color-text-muted)] mt-16">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)]" />
            <span className="font-bold text-[var(--color-text)]">ML Studio</span>
            <span>• Enterprise Governance & Regulatory Documentation</span>
          </div>

          <div className="flex items-center space-x-6">
            <Link to="/privacy" className="hover:text-[var(--color-text)]">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-[var(--color-text)]">Terms of Service</Link>
            <Link to="/legal" className="hover:text-[var(--color-text)]">Legal Center</Link>
            <Link to="/" className="hover:text-[var(--color-text)]">Platform Home</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
