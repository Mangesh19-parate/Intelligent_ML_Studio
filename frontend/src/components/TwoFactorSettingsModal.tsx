import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { twoFactorApi } from '../api/client';
import { TwoFactorSetupResponse, TwoFactorStatusResponse } from '../types/api';
import { OtpInput } from './auth/OtpInput';
import {
  ShieldCheck,
  ShieldAlert,
  X,
  Lock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  KeyRound,
} from 'lucide-react';
import axios from 'axios';

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
              <CheckCircle2 className="w-4 h-4 shrink-0" />
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
                      {status?.is_two_factor_enabled ? 'EMAIL 2FA ACTIVE' : 'DISABLED'}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {status?.is_two_factor_enabled
                      ? `Your account requires a secure 6-digit OTP sent to ${user?.email || 'your email'} on every sign in.`
                      : 'Add an extra layer of security to require email verification on sign in.'}
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[var(--color-bg)]/60 border border-[var(--color-border)] text-xs space-y-2 text-[var(--color-text-muted)]">
                <div className="font-semibold text-[var(--color-text)] flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span>How Email Two-Factor Authentication Works</span>
                </div>
                <p>
                  Whenever you sign in (or log out and log back in), a temporary 6-digit verification code is immediately dispatched to <strong>{user?.email}</strong>.
                </p>
                <p className="text-[11px]">
                  ✓ No authenticator app or QR code scan is required.<br />
                  ✓ Protects against credential theft and unauthorized access attempts.
                </p>
              </div>

              {status?.is_two_factor_enabled ? (
                <div className="pt-2 flex justify-between items-center">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    Protected via registered email delivery
                  </span>
                  <button
                    onClick={() => setStep('disable')}
                    className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/20 text-xs font-bold transition-all cursor-pointer"
                  >
                    Disable Email 2FA
                  </button>
                </div>
              ) : (
                <div className="pt-2 flex justify-end">
                  <button
                    onClick={handleStartSetup}
                    disabled={loading}
                    className="px-5 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-md shadow-[var(--color-accent)]/20 flex items-center space-x-2 transition-all cursor-pointer"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Activate Email 2FA</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: SETUP & CONFIRMATION */}
          {step === 'setup' && setupData && (
            <div className="space-y-6">
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                  Verify Email Delivery
                </h4>
                <div className="p-4 rounded-2xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs space-y-2">
                  <p className="text-[var(--color-text)] font-medium">
                    A verification code has been dispatched to <strong>{user?.email}</strong>.
                  </p>
                  <p className="text-[var(--color-text-muted)]">
                    Please enter the 6-digit code received in your email to activate two-factor protection.
                  </p>
                </div>
              </div>

              {/* Confirmation Form */}
              <form onSubmit={handleConfirmSetup} className="space-y-4 pt-2 border-t border-[var(--color-border)]">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-accent)]">
                    Enter 6-Digit Email Code
                  </h4>
                  <span className="text-[11px] text-[var(--color-text-muted)] font-medium">
                    Auto-advancing input
                  </span>
                </div>

                <div className="py-2">
                  <OtpInput
                    value={confirmCode}
                    onChange={setConfirmCode}
                    disabled={submitting}
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={submitting || confirmCode.trim().length !== 6}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-bold shadow-md shadow-[var(--color-accent)]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 cursor-pointer"
                  >
                    <span>{submitting ? 'Activating Email 2FA...' : 'Verify & Activate Email 2FA'}</span>
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
