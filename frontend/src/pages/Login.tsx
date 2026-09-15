import React, { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { OtpInput } from '../components/auth/OtpInput';
import {
  Layers,
  Lock,
  Mail,
  User,
  ShieldAlert,
  ArrowRight,
  ShieldCheck,
  KeyRound,
  ArrowLeft,
  Smartphone,
} from 'lucide-react';
import axios from 'axios';

export const Login: React.FC = () => {
  const [isRegister, setIsRegister] = useState<boolean>(false);
  const [fullName, setFullName] = useState<string>('');
  const [email, setEmail] = useState<string>('dev@mlstudio.io');
  const [password, setPassword] = useState<string>('password123');
  const [error, setError] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);

  // 2FA Challenge State
  const [is2FAPrompt, setIs2FAPrompt] = useState<boolean>(false);
  const [twoFactorToken, setTwoFactorToken] = useState<string>('');
  const [twoFactorCode, setTwoFactorCode] = useState<string>('');
  const [isBackupCodeMode, setIsBackupCodeMode] = useState<boolean>(false);

  const { login, register, verify2FA } = useAuth();
  const navigate = useNavigate();

  const handleInitialSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isRegister) {
        await register(fullName, email, password);
        navigate('/dashboard');
      } else {
        const res = await login(email, password);
        if (res.requires_2fa && res.two_factor_token) {
          setTwoFactorToken(res.two_factor_token);
          setIs2FAPrompt(true);
          setTwoFactorCode('');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail || 'Authentication failed. Please check your credentials.'
        );
      } else {
        setError('An unexpected error occurred during authentication.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handle2FASubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await verify2FA(twoFactorToken, twoFactorCode);
      navigate('/dashboard');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail || 'Invalid two-factor authentication code. Please try again.'
        );
      } else {
        setError('Verification failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const resetToLogin = () => {
    setIs2FAPrompt(false);
    setTwoFactorToken('');
    setTwoFactorCode('');
    setError('');
    setIsBackupCodeMode(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--color-bg)] transition-colors">
      <div className="w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-xl p-8 backdrop-blur-sm">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[var(--color-accent)] text-white shadow-lg shadow-indigo-500/20 mb-4">
            {is2FAPrompt ? <ShieldCheck className="w-6 h-6" /> : <Layers className="w-6 h-6" />}
          </div>
          <h1 className="text-2xl font-black tracking-tight text-[var(--color-text)]">
            {is2FAPrompt ? 'Two-Factor Verification' : 'ML Studio'}
          </h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            {is2FAPrompt
              ? isBackupCodeMode
                ? 'Enter your 8-character single-use emergency backup key'
                : 'Enter the 6-digit code from your authenticator app'
              : 'Leakage-Controlled No-Code Tabular ML Platform'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center space-x-2.5">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 2FA Challenge Form */}
        {is2FAPrompt ? (
          <form onSubmit={handle2FASubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-2 text-center">
                {isBackupCodeMode ? 'Enter 8-Character Emergency Recovery Key' : 'Enter 6-Digit Authenticator Code'}
              </label>

              {isBackupCodeMode ? (
                <div className="relative">
                  <KeyRound className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    required
                    autoFocus
                    maxLength={10}
                    value={twoFactorCode}
                    onChange={(e) => setTwoFactorCode(e.target.value)}
                    placeholder="XXXX-XXXX"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition-all text-center"
                  />
                </div>
              ) : (
                <div className="py-2">
                  <OtpInput
                    value={twoFactorCode}
                    onChange={setTwoFactorCode}
                    disabled={submitting}
                  />
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={submitting || (isBackupCodeMode ? !twoFactorCode.trim() : twoFactorCode.length !== 6)}
              className="w-full py-3 px-4 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white font-semibold text-sm shadow-md shadow-[var(--color-accent)]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{submitting ? 'Verifying Code...' : 'Verify & Enter Dashboard'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Toggle Backup Mode & Back to Login */}
            <div className="flex flex-col items-center space-y-2.5 pt-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  setIsBackupCodeMode(!isBackupCodeMode);
                  setTwoFactorCode('');
                  setError('');
                }}
                className="text-[var(--color-accent)] hover:underline font-semibold cursor-pointer"
              >
                {isBackupCodeMode
                  ? 'Use 6-digit Authenticator app code instead'
                  : 'Lost access? Use emergency backup recovery key'}
              </button>

              <button
                type="button"
                onClick={resetToLogin}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] flex items-center space-x-1 font-medium cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to sign in</span>
              </button>
            </div>
          </form>
        ) : (
          /* Standard Sign In / Register Form */
          <form onSubmit={handleInitialSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition-all"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3 w-4 h-4 text-[var(--color-text-muted)]" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white font-semibold text-sm shadow-md shadow-[var(--color-accent)]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{submitting ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {!is2FAPrompt && (
          <div className="mt-6 text-center border-t border-[var(--color-border)] pt-5">
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
              className="text-xs font-semibold text-[var(--color-accent)] hover:underline min-h-[44px] inline-flex items-center justify-center px-2 cursor-pointer"
            >
              {isRegister
                ? 'Already have an account? Sign In'
                : "Don't have an account? Create one"}
            </button>
          </div>
        )}

        {/* Dynamic Launch Footer */}
        <div className="mt-6 pt-4 border-t border-[var(--color-border)]/60 text-center text-[11px] text-[var(--color-text-muted)] space-y-1">
          <div>&copy; {new Date().getFullYear()} ML Studio Inc. All rights reserved.</div>
          <div>
            Need access? Contact{' '}
            <a href="mailto:support@mlstudio.io" className="text-[var(--color-accent)] hover:underline">
              support@mlstudio.io
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
