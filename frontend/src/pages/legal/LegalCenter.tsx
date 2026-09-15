import React from 'react';
import { Link } from 'react-router-dom';
import { LegalLayout } from './LegalLayout';
import {
  ShieldCheck,
  FileText,
  Lock,
  Cookie,
  ArrowRight,
  CheckCircle2,
  Server,
  FileCode,
  Users,
  Eye,
} from 'lucide-react';

export const LegalCenter: React.FC = () => {
  const tocItems = [
    { id: 'hub', number: '01', title: 'Legal & Governance Overview' },
    { id: 'documents', number: '02', title: 'Document Directory' },
    { id: 'safeguards', number: '03', title: 'Architectural Safeguards' },
    { id: 'inquiries', number: '04', title: 'Legal Inquiries' },
  ];

  return (
    <LegalLayout
      title="Legal & Governance Center"
      lastUpdated="September 15, 2026"
      subtitle="The central enterprise repository for ML Studio terms, data transparency disclosures, security architecture, and regulatory commitments."
      tocItems={tocItems}
      activeDoc="legal"
    >
      {/* 01 Overview */}
      <section id="hub" className="space-y-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">01</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Legal & Governance Overview</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Welcome to the ML Studio Legal & Governance Center. This resource provides transparent, binding, and verifiable documentation regarding our data handling policies, customer partition ownership, intellectual property boundaries, and cryptographic security controls.
        </p>
      </section>

      {/* 02 Document Directory */}
      <section id="documents" className="space-y-5 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">02</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Enterprise Document Directory</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Privacy Policy Card */}
          <Link
            to="/privacy"
            className="p-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-accent)] hover:shadow-md transition-all group flex flex-col justify-between space-y-4"
          >
            <div className="space-y-3">
              <span className="w-10 h-10 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </span>
              <h3 className="text-base font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors flex items-center justify-between">
                <span>Privacy Policy</span>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                Comprehensive data transparency framework detailing how personal data, customer datasets, model artifacts, and telemetry logs are processed, isolated, and protected.
              </p>
            </div>
            <div className="text-[10px] font-mono text-[var(--color-accent)] font-bold">
              View Privacy Policy →
            </div>
          </Link>

          {/* Terms of Service Card */}
          <Link
            to="/terms"
            className="p-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-accent)] hover:shadow-md transition-all group flex flex-col justify-between space-y-4"
          >
            <div className="space-y-3">
              <span className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </span>
              <h3 className="text-base font-bold text-[var(--color-text)] group-hover:text-[var(--color-accent)] transition-colors flex items-center justify-between">
                <span>Terms of Service</span>
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                Enterprise service agreement governing customer workspace access, dataset ownership guarantees, model output disclaimers, and liability allocations.
              </p>
            </div>
            <div className="text-[10px] font-mono text-[var(--color-accent)] font-bold">
              View Terms of Service →
            </div>
          </Link>

          {/* Security Safeguards Card */}
          <div className="p-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
            <span className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <Lock className="w-5 h-5" />
            </span>
            <h3 className="text-base font-bold text-[var(--color-text)]">
              Security Safeguards Overview
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              Technical, physical, and architectural safeguards including TLS 1.3 transit encryption, AES-256 at-rest storage, SHA-256 partition seals, and RBAC access matrices.
            </p>
            <div className="text-[10px] font-mono text-emerald-500 font-bold">
              Built into Platform Core
            </div>
          </div>

          {/* Cookie & Tracking Card */}
          <div className="p-6 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] space-y-3">
            <span className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center">
              <Cookie className="w-5 h-5" />
            </span>
            <h3 className="text-base font-bold text-[var(--color-text)]">
              Session & Cookie Notice
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              We exclusively use strictly necessary session cookies and HttpOnly JWT refresh mechanisms. No third-party behavioral analytics or advertising trackers are installed.
            </p>
            <div className="text-[10px] font-mono text-purple-500 font-bold">
              Zero Third-Party Trackers
            </div>
          </div>
        </div>
      </section>

      {/* 03 Architectural Safeguards */}
      <section id="safeguards" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">03</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Architectural & Privacy Safeguards</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          The ML Studio infrastructure is intentionally designed with core principles of technical privacy and rigorous verification:
        </p>

        <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Data Minimization</span>
          </div>
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Purpose Limitation</span>
          </div>
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Role-Based Access (RBAC)</span>
          </div>
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>End-to-End Encryption</span>
          </div>
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Audit Trail Verification</span>
          </div>
          <div className="flex items-center space-x-2 text-[var(--color-text)]">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Partition Isolation</span>
          </div>
        </div>
      </section>

      {/* 04 Contact */}
      <section id="inquiries" className="space-y-4 pt-4 border-t border-[var(--color-border)]">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">04</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Legal & Compliance Inquiries</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          For custom enterprise Data Processing Addenda (DPA), security questionnaires, or regulatory documentation, please contact our Legal Counsel at <a href="mailto:legal@mlstudio.io" className="text-[var(--color-accent)] hover:underline font-mono">legal@mlstudio.io</a>.
        </p>
      </section>
    </LegalLayout>
  );
};

export default LegalCenter;
