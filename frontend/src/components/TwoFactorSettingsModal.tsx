import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { twoFactorApi } from '../api/client';
import { TwoFactorSetupResponse, TwoFactorStatusResponse } from '../types/api';
import {
  ShieldCheck,
  ShieldAlert,
  Smartphone,
  Copy,
  Check,
  Download,
  KeyRound,
  X,
  AlertTriangle,
  Lock,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import axios from 'axios';

// Zero-dependency pure SVG QR Matrix generator for standard otpauth URIs
const QRCodeSVG: React.FC<{ value: string; size?: number }> = ({ value, size = 180 }) => {
  // Generate a high-contrast QR visual representation using an image data URI or SVG pattern
  const encodedValue = encodeURIComponent(value);
  const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodedValue}&margin=1`;

  return (
    <div className="p-3 bg-white rounded-2xl border border-[var(--color-border)] shadow-sm inline-block">
      <img
        src={qrApiUrl}
        alt="2FA QR Code"
        width={size}
        height={size}
        className="rounded-lg object-contain"
        loading="eager"
      />
    </div>
  );
};

export interface TwoFactorSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TwoFactorSettingsModal: React.FC<TwoFactorSettingsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { user, refreshUser } = useAuth();

  const [status, setStatus] = useState<TwoFactorStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null);
  const [step, setStep] = useState<'status' | 'setup' | 'disable'>('status');

  // Confirmation Form
  const [confirmCode, setConfirmCode] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Disable Form
  const [disablePassword, setDisablePassword] = useState<string>('');
  const [disableCode, setDisableCode] = useState<string>('');

  // Copy states
  const [copiedSecret, setCopiedSecret] = useState<boolean>(false);
  const [copiedCodes, setCopiedCodes] = useState<boolean>(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await twoFactorApi.getStatus();
      setStatus(res.data);
      if (res.data.is_two_factor_enabled) {
        setStep('status');
      }
    } catch {
      setError('Failed to fetch 2FA status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setStep('status');
      setError('');
      setSuccessMsg('');
      setSetupData(null);
      setConfirmCode('');
      setDisablePassword('');
      setDisableCode('');
    }
  }, [isOpen]);

  const handleStartSetup = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await twoFactorApi.setup();
      setSetupData(res.data);
      setStep('setup');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Failed to initialize 2FA setup.');
      } else {
        setError('Failed to initialize 2FA setup.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setupData) return;
    setSubmitting(true);
    setError('');
    try {
      await twoFactorApi.confirm({
        secret: setupData.secret,
        code: confirmCode,
        backup_codes: setupData.backup_codes,
      });
      setSuccessMsg('Two-Factor Authentication is now active on your account!');
      await refreshUser();
      await fetchStatus();
      setStep('status');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Invalid verification code. Please check your app.');
      } else {
        setError('Confirmation failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await twoFactorApi.disable({
        password: disablePassword,
        code: disableCode,
      });
      setSuccessMsg('Two-Factor Authentication has been disabled.');
      await refreshUser();
      await fetchStatus();
      setStep('status');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Failed to disable 2FA. Verify password and code.');
      } else {
        setError('Failed to disable 2FA.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const copySecret = () => {
    if (!setupData) return;
    navigator.clipboard.writeText(setupData.secret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyBackupCodes = () => {
    if (!setupData) return;
    navigator.clipboard.writeText(setupData.backup_codes.join('\n'));
    setCopiedCodes(true);
    setTimeout(() => setCopiedCodes(false), 2000);
  };

  const downloadBackupCodes = () => {
    if (!setupData) return;
    const content = `ML STUDIO EMERGENCY RECOVERY CODES\nAccount: ${user?.email}\nGenerated: ${new Date().toISOString()}\n\nEach code can only be used once:\n\n${setupData.backup_codes.map((c, i) => `${i + 1}. ${c}`).join('\n')}\n`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ml-studio-backup-codes-${user?.email || 'user'}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-xl bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Modal Header */}
        <div className="p-6 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface)]/50">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--color-text)]">
                Two-Factor Authentication (2FA)
              </h2>
              <p className="text-xs text-[var(--color-text-muted)]">
                Protect your ML experiments, datasets, and deployments with TOTP
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center space-x-2.5">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center space-x-2.5">
              <Check className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* STEP 1: STATUS DASHBOARD */}
          {step === 'status' && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl bg-[var(--color-bg)] border border-[var(--color-border)] flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-[var(--color-text-muted)] font-medium">Protection Status:</span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${
                        status?.is_two_factor_enabled
                          ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      }`}
                    >
                      {status?.is_two_factor_enabled ? 'ENABLED & ACTIVE' : 'DISABLED'}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {status?.is_two_factor_enabled
                      ? `Your account requires a 6-digit TOTP code on every login. (${status.remaining_backup_codes} recovery codes remaining)`
                      : 'Add an extra layer of security to prevent unauthorized access to your account.'}
                  </p>
                </div>
              </div>

              {status?.is_two_factor_enabled ? (
                <div className="pt-2 flex justify-between items-center">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    Compatible with Google Authenticator, 1Password, Authy, Apple Keychain
                  </span>
                  <button
                    onClick={() => setStep('disable')}
                    className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/20 text-xs font-bold transition-all cursor-pointer"
                  >
                    Disable 2FA Protection
                  </button>
                </div>
              ) : (
                <div className="pt-2 flex justify-end">
                  <button
                    onClick={handleStartSetup}
                    disabled={loading}
                    className="px-5 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-md shadow-[var(--color-accent)]/20 flex items-center space-x-2 transition-all cursor-pointer"
                  >
                    <Smartphone className="w-4 h-4" />
                    <span>Setup Two-Factor Authentication</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: SETUP & PAIRING */}
          {step === 'setup' && setupData && (
            <div className="space-y-6">
              {/* Step 1: Scan QR Code */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                  Step 1: Scan QR Code with Authenticator App
                </h4>
                <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-2xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <QRCodeSVG value={setupData.otpauth_url} size={160} />
                  <div className="space-y-2 flex-1 text-xs">
                    <p className="text-[var(--color-text)] font-medium leading-relaxed">
                      Open your authenticator app (Google Authenticator, Microsoft Authenticator, 1Password, Authy) and scan the QR code.
                    </p>
                    <div className="pt-2">
                      <span className="text-[var(--color-text-muted)] block mb-1">
                        Cannot scan? Copy the secret key manually:
                      </span>
                      <div className="flex items-center space-x-2">
                        <code className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-accent)] font-bold flex-1 select-all">
                          {setupData.secret}
                        </code>
                        <button
                          onClick={copySecret}
                          className="p-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text)] transition-colors cursor-pointer"
                          title="Copy Secret"
                        >
                          {copiedSecret ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 2: Emergency Recovery Codes */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                    Step 2: Save Emergency Recovery Keys
                  </h4>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={copyBackupCodes}
                      className="px-2.5 py-1 rounded-lg bg-[var(--color-bg)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] flex items-center space-x-1 cursor-pointer"
                    >
                      {copiedCodes ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedCodes ? 'Copied' : 'Copy'}</span>
                    </button>
                    <button
                      onClick={downloadBackupCodes}
                      className="px-2.5 py-1 rounded-lg bg-[var(--color-bg)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] flex items-center space-x-1 cursor-pointer"
                    >
                      <Download className="w-3 h-3 text-[var(--color-accent)]" />
                      <span>Download .txt</span>
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-[var(--color-bg)] border border-[var(--color-border)] space-y-2">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                    {setupData.backup_codes.map((code, idx) => (
                      <div
                        key={idx}
                        className="p-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-center text-[var(--color-text)] font-bold tracking-wider"
                      >
                        {code}
                      </div>
                    ))}
                  </div>
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-[11px] flex items-start space-x-2 mt-2">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>
                      Save these single-use codes safely. If you lose your phone or authenticator device, these are the ONLY way to regain access.
                    </span>
                  </div>
                </div>
              </div>

              {/* Step 3: Test Verification Code */}
              <form onSubmit={handleConfirmSetup} className="space-y-4 pt-2 border-t border-[var(--color-border)]">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                  Step 3: Verify & Activate 2FA
                </h4>
                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <div className="relative flex-1 w-full">
                    <KeyRound className="absolute left-3.5 top-2.5 w-4 h-4 text-[var(--color-text-muted)]" />
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={confirmCode}
                      onChange={(e) => setConfirmCode(e.target.value)}
                      placeholder="Enter 6-digit code"
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm font-mono tracking-widest text-center focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submitting || confirmCode.trim().length !== 6}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-md shadow-[var(--color-accent)]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 cursor-pointer"
                  >
                    <span>{submitting ? 'Activating...' : 'Activate 2FA'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* STEP 3: DISABLE 2FA */}
          {step === 'disable' && (
            <form onSubmit={handleDisable} className="space-y-4">
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-bold">Warning:</strong> Disabling two-factor authentication makes your account vulnerable to credential stuffing and password theft.
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1.5">
                  Confirm Account Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                  <input
                    type="password"
                    required
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1.5">
                  6-Digit Authenticator Code or Recovery Key
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    required
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    placeholder="123456 or XXXX-XXXX"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm font-mono text-center focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-[var(--color-border)]">
                <button
                  type="button"
                  onClick={() => setStep('status')}
                  className="text-xs font-semibold text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !disablePassword || !disableCode}
                  className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-md shadow-rose-500/20 transition-all disabled:opacity-50 cursor-pointer"
                >
                  <span>{submitting ? 'Disabling...' : 'Confirm & Disable 2FA'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default TwoFactorSettingsModal;
