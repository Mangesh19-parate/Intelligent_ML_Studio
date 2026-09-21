import React from 'react';
import { LegalLayout } from './LegalLayout';
import { AlertTriangle, ShieldCheck, Lock, FileCode, CheckCircle2 } from 'lucide-react';

export const TermsOfService: React.FC = () => {
  const tocItems = [
    { id: 'acceptance', number: '01', title: 'Acceptance of Terms' },
    { id: 'eligibility', number: '02', title: 'Eligibility & Account Registration' },
    { id: 'authorized-use', number: '03', title: 'Authorized Use & Workspaces' },
    { id: 'customer-data', number: '04', title: 'Customer Data & Partition Ownership' },
    { id: 'intellectual-property', number: '05', title: 'Intellectual Property Rights' },
    { id: 'models-outputs', number: '06', title: 'ML Models, Predictions & Passports' },
    { id: 'third-party', number: '07', title: 'Third-Party Services & Dependencies' },
    { id: 'security', number: '08', title: 'Security & Credential Integrity' },
    { id: 'prohibited-uses', number: '09', title: 'Prohibited Uses & System Protection' },
    { id: 'availability', number: '10', title: 'Service Availability & Modifications' },
    { id: 'disclaimers', number: '11', title: 'Disclaimers of Warranties' },
    { id: 'liability', number: '12', title: 'Limitation of Liability' },
    { id: 'indemnity', number: '13', title: 'Indemnification Obligations' },
    { id: 'termination', number: '14', title: 'Suspension & Termination' },
    { id: 'confidentiality', number: '15', title: 'Confidentiality & Cryptographic Audit' },
    { id: 'governing-law', number: '16', title: 'Governing Law & Dispute Resolution' },
    { id: 'amendments', number: '17', title: 'Amendments to These Terms' },
    { id: 'contact', number: '18', title: 'Contact & Legal Notices' },
  ];

  return (
    <LegalLayout
      title="Terms of Service"
      lastUpdated="September 15, 2026"
      subtitle="These Enterprise Service Terms govern your access to, use of, and workload execution across ML Studio."
      tocItems={tocItems}
      activeDoc="terms"
    >
      {/* Prominent Important Notice Box */}
      <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs space-y-2">
        <div className="flex items-center space-x-2 font-bold uppercase tracking-wider text-amber-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Important Notice Concerning Machine Learning Tooling</span>
        </div>
        <p className="leading-relaxed text-[var(--color-text-muted)] dark:text-amber-200/90">
          ML Studio provides automated machine-learning development, validation, profiling, and deployment tooling.
          You are solely responsible for evaluating whether model predictions, inferred features, explainability metrics,
          and production inferences are appropriate, lawful, and validated for your specific commercial, clinical, or regulated domain.
        </p>
      </div>

      {/* 01 Acceptance */}
      <section id="acceptance" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">01</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Acceptance of Terms</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          By registering an account, accessing the ML Studio web dashboard, calling our REST APIs, or uploading datasets into the platform, you (“Customer,” “User,” or “You”) agree to be bound by these Terms of Service (“Terms”). If you represent an entity, you represent and warrant that you possess full legal authority to bind that entity to these Terms.
        </p>
      </section>

      {/* 02 Eligibility */}
      <section id="eligibility" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">02</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Eligibility & Account Registration</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          You must provide accurate, current, and complete corporate registration details. You are responsible for maintaining the confidentiality of your authentication credentials, multi-factor authentication (MFA/TOTP) keys, and API tokens. You agree to notify ML Studio immediately upon becoming aware of any unauthorized account access.
        </p>
      </section>

      {/* 03 Authorized Use */}
      <section id="authorized-use" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">03</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Authorized Use & Workspaces</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Subject to compliance with these Terms and your enterprise service tier, ML Studio grants you a limited, non-exclusive, non-transferable right to access and use the platform to ingest tabular data, run leakage-guarded cross-validation experiments, compute explainability metrics, and deploy authorized model endpoints.
        </p>
      </section>

      {/* 04 Customer Data */}
      <section id="customer-data" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">04</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Customer Data & Partition Ownership</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          As between the parties, you retain all right, title, and interest (including all intellectual property rights) in and to all data files, schemas, and records uploaded by you into ML Studio (“Customer Data”).
        </p>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          You grant ML Studio a strictly limited license to host, copy, process, and transform Customer Data solely to the extent necessary to provide the platform features requested by you. <strong>ML Studio will not use Customer Data to train, fine-tune, or calibrate public foundational models or shared services without your prior express written consent.</strong>
        </p>
      </section>

      {/* 05 Intellectual Property */}
      <section id="intellectual-property" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">05</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Intellectual Property Rights</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          ML Studio and its licensors retain all intellectual property rights in and to the platform, including proprietary rank-aggregation algorithms, diagnostic rule engines, user interfaces, documentation, APIs, and software binaries.
        </p>
      </section>

      {/* 06 Models & Outputs */}
      <section id="models-outputs" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">06</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">ML Models, Predictions & Passports</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Models trained within your workspace (including fitted ColumnTransformers, serialized model weights, and Model Passports) are your work product. You are responsible for ensuring that all target labels, feature definitions, and inference predictions comply with applicable anti-discrimination, credit, healthcare, and algorithmic transparency laws.
        </p>
      </section>

      {/* 07 Third-Party */}
      <section id="third-party" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">07</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Third-Party Services & Dependencies</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          The platform may utilize open-source computational libraries (e.g., scikit-learn, LightGBM, SHAP) and cloud infrastructure hosting. Use of third-party compute services is subject to their respective open-source licenses and service agreements.
        </p>
      </section>

      {/* 08 Security */}
      <section id="security" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">08</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Security & Credential Integrity</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          ML Studio maintains administrative, physical, and technical safeguards designed to protect Customer Data from unauthorized disclosure. You agree not to disable, bypass, or tamper with security controls, including partition isolation guards, cryptographic hash verifiers, or dual-signoff promotion policies.
        </p>
      </section>

      {/* 09 Prohibited Uses */}
      <section id="prohibited-uses" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">09</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Prohibited Uses & System Protection</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          You agree not to: (a) reverse engineer, decompile, or disassemble the platform; (b) probe, scan, or test the vulnerability of the infrastructure without explicit written consent; (c) upload malware, malicious scripts, or unlawful data; or (d) train models designed to facilitate unlawful surveillance or weapons proliferation.
        </p>
      </section>

      {/* 10 Availability */}
      <section id="availability" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">10</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Service Availability & Modifications</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          While we strive for 99.9% platform availability, ML Studio may undergo scheduled maintenance or emergency security patching. We reserve the right to modify, upgrade, or deprecate specific features with reasonable advance notice.
        </p>
      </section>

      {/* 11 Disclaimers */}
      <section id="disclaimers" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">11</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Disclaimers of Warranties</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          EXCEPT AS EXPRESSLY PROVIDED IN A WRITTEN ENTERPRISE SLA, THE PLATFORM IS PROVIDED ON AN “AS IS” AND “AS AVAILABLE” BASIS. ML STUDIO DISCLAIMS ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. WE DO NOT GUARANTEE THAT TRAINED MODELS WILL ACHIEVE SPECIFIC COMMERCIAL REVENUE OR ACCURACY OUTCOMES.
        </p>
      </section>

      {/* 12 Liability */}
      <section id="liability" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">12</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Limitation of Liability</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, NEITHER PARTY SHALL BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR LOSS OF PROFITS, DATA, OR REVENUE. IN NO EVENT SHALL ML STUDIO'S AGGREGATE LIABILITY ARISING OUT OF THESE TERMS EXCEED THE AMOUNTS ACTUALLY PAID BY YOU FOR THE PLATFORM IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.
        </p>
      </section>

      {/* 13 Indemnity */}
      <section id="indemnity" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">13</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Indemnification Obligations</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          You agree to defend, indemnify, and hold harmless ML Studio against third-party claims, damages, or liabilities arising from: (a) your breach of these Terms; (b) unlawful Customer Data ingested by you; or (c) your commercial deployment and application of trained models in downstream decision-making.
        </p>
      </section>

      {/* 14 Termination */}
      <section id="termination" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">14</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Suspension & Account Termination</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We may suspend or terminate your workspace access immediately if you commit a material breach of these Terms, fail to remediate security risks, or violate applicable laws. Upon termination, you may request an export of Customer Data within thirty (30) days, after which data will be securely purged.
        </p>
      </section>

      {/* 15 Confidentiality */}
      <section id="confidentiality" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">15</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Confidentiality & Cryptographic Lineage</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Each party agrees to safeguard the other's proprietary technical information, schemas, and business configurations with the same standard of care used to protect its own confidential assets (not less than reasonable care).
        </p>
      </section>

      {/* 16 Governing Law */}
      <section id="governing-law" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">16</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Governing Law & Dispute Resolution</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          These Terms shall be governed by and construed in accordance with the laws of the agreed corporate jurisdiction, without giving effect to conflicts-of-law principles. Any unresolved controversy shall be resolved through binding commercial arbitration under established arbitration rules.
        </p>
      </section>

      {/* 17 Amendments */}
      <section id="amendments" className="space-y-4 pt-2">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">17</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Amendments to These Terms</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          We reserve the right to revise these Terms. Continued use of ML Studio following the effective date of updated Terms constitutes your binding agreement to the amendments.
        </p>
      </section>

      {/* 18 Contact */}
      <section id="contact" className="space-y-4 pt-2 border-t border-[var(--color-border)]">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-xs font-black text-[var(--color-accent)] px-2 py-0.5 rounded-md bg-[var(--color-accent-soft)]">18</span>
          <h2 className="text-xl font-black text-[var(--color-text)] tracking-tight">Contact & Legal Notices</h2>
        </div>
        <p className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-relaxed">
          Official legal notices or inquiries concerning these Terms of Service should be directed to:
        </p>
        <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-mono space-y-1 text-[var(--color-text)]">
          <div>ML Studio Legal Department & Enterprise Contracting</div>
          <div>Email: <a href="mailto:legal@mlstudio.io" className="text-[var(--color-accent)] hover:underline">legal@mlstudio.io</a></div>
        </div>
      </section>
    </LegalLayout>
  );
};

export default TermsOfService;
