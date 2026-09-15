import React from 'react';
import { LegalLayout } from './LegalLayout';
import { ShieldCheck, Lock, Database, Cpu, Eye, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

export const PrivacyPolicy: React.FC = () => {
  const tocItems = [
    { id: 'overview', number: '01', title: 'Who We Are & Overview' },
    { id: 'scope', number: '02', title: 'Scope & Applicability' },
    { id: 'data-categories', number: '03', title: 'Categories of Information We Process' },
    { id: 'purposes', number: '04', title: 'Purposes & Legal Bases for Processing' },
    { id: 'automated-processing', number: '05', title: 'ML & Automated Recommendation Processing' },
    { id: 'cookies', number: '06', title: 'Cookies & Session Authentication' },
    { id: 'sharing', number: '07', title: 'Data Sharing & Sub-Processors' },
    { id: 'transfers', number: '08', title: 'Cross-Border Data Transfers' },
    { id: 'retention', number: '09', title: 'Data Retention & Isolation Lifecycles' },
    { id: 'security', number: '10', title: 'Technical & Organizational Security' },
    { id: 'rights', number: '11', title: 'Your Privacy & Data Subject Rights' },
    { id: 'children', number: '12', title: "Children's Privacy" },
    { id: 'changes', number: '13', title: 'Revisions to This Policy' },
    { id: 'contact', number: '14', title: 'Contact & Data Protection Officer' },
  ];

  return (
    <LegalLayout
      title="Privacy Policy"
      lastUpdated="September 15, 2026"
      subtitle="How ML Studio collects, uses, isolates, stores, and protects personal information and customer machine-learning assets."
      tocItems={tocItems}
      activeDoc="privacy"
    >
      {/* At A Glance Panel */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center space-x-2 text-xs font-mono font-bold text-[var(--color-accent)] uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" />
          <span>At A Glance Summary</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-1">
            <div className="font-bold text-[var(--color-text)] uppercase text-[10px] tracking-wider">What We Collect</div>
            <p className="text-[var(--color-text-muted)] leading-relaxed">
              Account identifiers, workspace configurations, platform telemetry, and customer datasets uploaded for model training.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-1">
            <div className="font-bold text-[var(--color-text)] uppercase text-[10px] tracking-wider">Why We Use It</div>
            <p className="text-[var(--color-text-muted)] leading-relaxed">
              To operate the platform, enforce role-based access controls, prevent data leakage, and generate verifiable model passports.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-1">
            <div className="font-bold text-[var(--color-text)] uppercase text-[10px] tracking-wider">Your Dataset Rights</div>
            <p className="text-[var(--color-text-muted)] leading-relaxed">
              We do not use customer datasets or trained model weights to train our own foundation models unless explicitly agreed in writing.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-[var(--color-surface-hover)] border border-[var(--color-border)] space-y-1">
            <div className="font-bold text-[var(--color-text)] uppercase text-[10px] tracking-wider">Data Retention</div>
            <p className="text-[var(--color-text-muted)] leading-relaxed">
              Customer data is retained strictly as required for active workspace lifecycles, model lineage, and statutory audit obligations.
            </p>
          </div>
        </div>
      </div>

      {/* 01 Overview */}
      <section id="overview" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">01</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Who We Are & Overview</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          ML Studio (“we,” “us,” or “our”) provides an enterprise tabular machine learning platform engineered around leakage prevention, deterministic reproducibility, model explainability, and governed deployment. This Privacy Policy sets out how personal data and enterprise assets are collected, processed, and protected when you interact with our platform, APIs, and associated web services.
        </p>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          For the purposes of applicable data protection legislation (including the EU/UK General Data Protection Regulation and relevant US state privacy statutes), ML Studio acts as a <strong>Data Controller</strong> with respect to user account and administrative registration data, and as a <strong>Data Processor</strong> (or Service Provider) with respect to customer datasets ingested into customer workspaces.
        </p>
      </section>

      {/* 02 Scope */}
      <section id="scope" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">02</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Scope & Applicability</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          This Policy applies to all authorized users, workspace collaborators, account administrators, and API consumers accessing the ML Studio platform. It covers data processed across all pipeline stages: Ingestion, Profiling, Transformation, Feature Engineering, Controlled Experimentation, SHAP Explainability, Model Governance, and Production REST Inference.
        </p>
      </section>

      {/* 03 Categories of Information We Process */}
      <section id="data-categories" className="space-y-5 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">03</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Categories of Information We Process</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Because ML Studio is an enterprise machine learning platform handling complex tabular workflows, we explicitly distinguish between four distinct data classifications:
        </p>

        <div className="space-y-3.5">
          {/* Category 1 */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-[var(--color-text)]">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span>1. User Account & Identity Data</span>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              Full name, corporate email address, hashed authentication credentials (via bcrypt with cryptographic salts), role-based permissions (ADMIN, USER, VIEWER), and TOTP two-factor authentication secrets.
            </p>
          </div>

          {/* Category 2 */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-[var(--color-text)]">
              <span className="w-2 h-2 rounded-full bg-[var(--color-accent)]" />
              <span>2. Customer Ingested Datasets & Partitions</span>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              Tabular files uploaded in CSV or Parquet format, column schema definitions, physical data types, derived development partitions, and cryptographically sealed locked test sets (accompanied by SHA-256 integrity hashes).
            </p>
          </div>

          {/* Category 3 */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-[var(--color-text)]">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>3. Model Artifacts, Weights & Explainability Passports</span>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              Fitted preprocessing ColumnTransformers, trained scikit-learn/LightGBM model binaries, hyperparameter configurations, cross-validation metrics, global & local TreeSHAP attribution matrices, and dual-signoff gate approvals.
            </p>
          </div>

          {/* Category 4 */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-[var(--color-text)]">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>4. Platform Telemetry, Audit Logs & Inference Traces</span>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              API request timestamps, decoupled REST endpoint latency profiles, input payload logging for data drift monitoring (PSI), client IP addresses, user agent strings, and audit log entries tracking model promotion events.
            </p>
          </div>
        </div>
      </section>

      {/* 04 Purposes */}
      <section id="purposes" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">04</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Purposes & Legal Bases for Processing</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We process personal data and customer assets under the following legal bases:
        </p>
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] text-xs">
          <table className="w-full text-left">
            <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase text-[10px] font-semibold">
              <tr>
                <th className="px-4 py-3">Processing Activity</th>
                <th className="px-4 py-3">Data Categories</th>
                <th className="px-4 py-3">Legal Basis (GDPR Art. 6)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)] text-[var(--color-text)]">
              <tr>
                <td className="px-4 py-3 font-medium">Platform Access & User Authentication</td>
                <td className="px-4 py-3 text-[var(--color-text-muted)]">User Account Data</td>
                <td className="px-4 py-3 font-mono">Performance of Contract</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Dataset Profiling, Transformation & Model Training</td>
                <td className="px-4 py-3 text-[var(--color-text-muted)]">Customer Datasets, Model Artifacts</td>
                <td className="px-4 py-3 font-mono">Performance of Contract (Processor Terms)</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Security Auditing, 2FA & Leakage Guard Enforcement</td>
                <td className="px-4 py-3 text-[var(--color-text-muted)]">User Account Data, Telemetry</td>
                <td className="px-4 py-3 font-mono">Legitimate Interests & Legal Obligation</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Real-Time Model Inference & Drift Monitoring</td>
                <td className="px-4 py-3 text-[var(--color-text-muted)]">Model Artifacts, Telemetry</td>
                <td className="px-4 py-3 font-mono">Performance of Contract</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 05 Automated Processing */}
      <section id="automated-processing" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">05</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">ML / Automated Processing & Recommendation Transparency</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Pursuant to transparency standards concerning automated decision-support technologies (including GDPR Articles 13–15 and 22), ML Studio provides full disclosures regarding its internal heuristic logic:
        </p>
        <div className="space-y-3 text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          <p>
            • <strong>Deterministic Rule Trees: </strong> Our Recommendation Engine evaluates data characteristics (e.g., target cardinality, class balance ratios, missing rate thresholds, and high multicollinearity) through transparent, deterministic heuristic trees rather than black-box automated systems.
          </p>
          <p>
            • <strong>Strict Human-in-the-Loop Oversight: </strong> ML Studio recommendations are advisory. Platform users retain complete discretion to accept, customize, override, or reject any suggested algorithm, hyperparameter configuration, metric, or preprocessing transform.
          </p>
          <p>
            • <strong>No Uncontrolled Legal Decisions: </strong> ML Studio does not produce automated legal or similarly significant determinations regarding data subjects without human authorization. The customer remains the sole controller of the downstream application of trained models.
          </p>
        </div>
      </section>

      {/* 06 Cookies */}
      <section id="cookies" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">06</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Cookies & Session Authentication</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We use strictly necessary session cookies and local storage tokens exclusively to maintain authentication state, secure API communication via HttpOnly refresh tokens, and preserve user UI preferences (such as dark/light mode). We do not deploy third-party advertising or cross-site tracking cookies.
        </p>
      </section>

      {/* 07 Data Sharing */}
      <section id="sharing" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">07</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Data Sharing, Processors & Sub-Processors</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We do not sell, rent, or monetize your personal data or customer datasets. We disclose information only to vetted infrastructure service providers (cloud storage, database hosting, compute clusters) under binding Data Processing Agreements containing strict confidentiality and security commitments.
        </p>
      </section>

      {/* 08 International Transfers */}
      <section id="transfers" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">08</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Cross-Border Data Transfers</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Where customer workloads necessitate cross-border data transfers, we implement appropriate safeguards in compliance with applicable law, including Standard Contractual Clauses (SCCs) approved by the European Commission and relevant UK adequacy mechanisms.
        </p>
      </section>

      {/* 09 Retention */}
      <section id="retention" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">09</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Data Retention & Partition Isolation Lifecycles</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          • <strong>Customer Datasets & Partitions: </strong> Retained for the duration of the active project workspace. Upon project deletion, datasets and associated partitions are securely purged from local storage and object stores.
        </p>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          • <strong>Audit Logs & Model Passports: </strong> Immutable governance audit records are retained for compliance verification purposes for up to seven (7) years or as required by customer contractual mandates.
        </p>
      </section>

      {/* 10 Security */}
      <section id="security" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">10</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Technical & Organizational Security Measures</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          ML Studio is designed with enterprise-grade security controls:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <strong className="text-[var(--color-text)]">✓ Encryption in Transit & Rest: </strong>
            <span className="text-[var(--color-text-muted)]"> TLS 1.3 enforced for all network calls; AES-256 for persistent database and object storage.</span>
          </div>
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <strong className="text-[var(--color-text)]">✓ Cryptographic Partition Seals: </strong>
            <span className="text-[var(--color-text-muted)]"> SHA-256 verification hashes preventing silent test partition contamination.</span>
          </div>
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <strong className="text-[var(--color-text)]">✓ Role-Based Access Control (RBAC): </strong>
            <span className="text-[var(--color-text-muted)]"> Granular permission matrices isolating dataset editing from model deployment.</span>
          </div>
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
            <strong className="text-[var(--color-text)]">✓ Dual-Key Deployment Governance: </strong>
            <span className="text-[var(--color-text-muted)]"> Mandatory peer review preventing single-user unverified production rollouts.</span>
          </div>
        </div>
      </section>

      {/* 11 Rights */}
      <section id="rights" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">11</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Your Privacy & Data Subject Rights</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Depending on your jurisdiction, you may exercise statutory privacy rights, including:
        </p>
        <ul className="list-disc list-inside text-xs sm:text-sm text-[var(--color-text-muted)] space-y-1.5 leading-relaxed pl-2">
          <li><strong>Right of Access: </strong> Request copies of your personal data held by ML Studio.</li>
          <li><strong>Right to Rectification: </strong> Correct inaccurate or incomplete account records.</li>
          <li><strong>Right to Erasure (“Right to be Forgotten”): </strong> Request deletion of your account and personal records.</li>
          <li><strong>Right to Restriction & Objection: </strong> Limit or object to specific processing activities.</li>
          <li><strong>Right to Data Portability: </strong> Receive your data in a structured, machine-readable format.</li>
        </ul>
      </section>

      {/* 12 Children */}
      <section id="children" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">12</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Children's Privacy</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          ML Studio is strictly an enterprise business-to-business application and is not intended for or directed toward individuals under the age of eighteen (18). We do not knowingly collect personal information from minors.
        </p>
      </section>

      {/* 13 Changes */}
      <section id="changes" className="space-y-4 pt-4">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">13</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Revisions to This Policy</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We may update this Privacy Policy from time to time to reflect technological enhancements, architectural changes, or evolving regulatory standards. Material modifications will be communicated via the platform notification interface or corporate email.
        </p>
      </section>

      {/* 14 Contact */}
      <section id="contact" className="space-y-4 pt-4 border-t border-[var(--color-border)]">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">14</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Contact & Data Protection Officer</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          If you have questions, inquiries, or wish to exercise data subject rights regarding this Policy, please contact our Data Governance & Privacy Office:
        </p>
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-mono space-y-1 text-[var(--color-text)]">
          <div>ML Studio Data Protection & Legal Compliance</div>
          <div>Email: <a href="mailto:privacy@mlstudio.io" className="text-[var(--color-accent)] hover:underline">privacy@mlstudio.io</a></div>
          <div>Address: Enterprise ML Governance Desk, Global Technology Center</div>
        </div>
      </section>
    </LegalLayout>
  );
};

export default PrivacyPolicy;
