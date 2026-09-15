import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Moon, Sun, LogOut, Layers, ShieldCheck, KeyRound, ShieldAlert } from 'lucide-react';
import { TwoFactorSettingsModal } from './TwoFactorSettingsModal';

export const Navbar: React.FC = () => {
  const { user, logout, darkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();
  const [show2FAModal, setShow2FAModal] = useState<boolean>(false);

  const handleLogout = async (): Promise<void> => {
    await logout();
    navigate('/login');
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-md transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link to="/dashboard" className="flex items-center space-x-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-[var(--color-accent)] flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-accent)] to-indigo-400 bg-clip-text text-transparent">
                  ML Studio
                </span>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)] -mt-1">
                  Enterprise Tabular Platform
                </span>
              </div>
            </Link>
          </div>

          {user && (
            <div className="flex items-center space-x-3">
              {/* Role Badge */}
              <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full bg-[var(--color-bg)] border border-[var(--color-border)] text-xs">
                <ShieldCheck className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                <span className="font-semibold">{user.role?.role_name || 'USER'}</span>
                <span className="text-[var(--color-text-muted)]">({user.permissions?.length || 0} perms)</span>
              </div>

              {/* 2FA Security Button */}
              <button
                onClick={() => setShow2FAModal(true)}
                className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer shadow-sm ${
                  user.is_two_factor_enabled
                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/20'
                    : 'bg-[var(--color-bg)] text-[var(--color-text-muted)] border-[var(--color-border)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)]'
                }`}
                title="Configure Two-Factor Authentication"
              >
                {user.is_two_factor_enabled ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span>2FA Active</span>
                  </>
                ) : (
                  <>
                    <KeyRound className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                    <span>2FA Setup</span>
                  </>
                )}
              </button>

              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
                title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
              >
                {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
              </button>

              <div className="flex items-center space-x-3 border-l border-[var(--color-border)] pl-4">
                <div className="text-right hidden md:block">
                  <div className="text-xs font-semibold text-[var(--color-text)]">{user.full_name}</div>
                  <div className="text-[11px] text-[var(--color-text-muted)]">{user.email}</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* 2FA Settings Modal */}
      <TwoFactorSettingsModal
        isOpen={show2FAModal}
        onClose={() => setShow2FAModal(false)}
      />
    </>
  );
};
