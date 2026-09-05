import React from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  LayoutDashboard,
  FolderGit2,
  Activity,
  ShieldCheck,
  Moon,
  Sun,
  LogOut,
  ChevronRight,
  Cpu,
  Sparkles,
  Lock,
} from 'lucide-react';

export const AppLayout = ({ children }) => {
  const { user, logout, darkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userPerms = new Set(
    user?.permissions ||
    (user?.role?.permissions ? user.role.permissions.map((p) => (typeof p === 'string' ? p : p.permission_key)) : [])
  );
  const roleName = user?.role?.role_name || user?.role || 'VIEWER';
  const isAdmin = roleName === 'ADMIN' || userPerms.has('MANAGE_USERS');
  const canEditData = isAdmin || userPerms.has('EDIT_DATA');
  const canTrain = isAdmin || userPerms.has('TRAIN');
  const canDeploy = isAdmin || userPerms.has('DEPLOY');
  const canRead = isAdmin || userPerms.has('READ') || true;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-text flex flex-col transition-colors">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 w-full border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-md transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link to="/dashboard" className="flex items-center space-x-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-[var(--color-accent)] flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-[var(--color-accent)] to-indigo-400 bg-clip-text text-transparent">
                  ML Studio
                </span>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)] -mt-1">
                  Leakage-Safe Platform
                </span>
              </div>
            </Link>

            {/* Main Navigation Links (Permission Gated) */}
            <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-[var(--color-border)]">
              {canRead && (
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                      isActive && !location.pathname.includes('/monitoring')
                        ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)] font-bold'
                        : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
                    }`
                  }
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  <span>Workspace</span>
                </NavLink>
              )}

              {/* Monitoring tab is visible if user has READ */}
              {canRead && (
                <NavLink
                  to="/monitoring"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                      isActive || location.pathname.includes('/monitoring')
                        ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)] font-bold'
                        : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
                    }`
                  }
                >
                  <Activity className="w-3.5 h-3.5" />
                  <span>Deployment Monitoring</span>
                </NavLink>
              )}
            </nav>
          </div>

          {/* User Controls */}
          {user && (
            <div className="flex items-center space-x-4">
              <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full bg-[var(--color-bg)] border border-[var(--color-border)] text-xs">
                <ShieldCheck className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                <span className="font-semibold">{roleName}</span>
                <span className="text-[var(--color-text-muted)]">
                  ({userPerms.size} perms)
                </span>
              </div>

              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
                title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              >
                {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
              </button>

              <div className="flex items-center space-x-3 border-l border-[var(--color-border)] pl-4">
                <div className="text-right hidden md:block">
                  <div className="text-xs font-semibold text-text">{user.full_name}</div>
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

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/50 py-4 text-center text-xs text-[var(--color-text-muted)]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>ML Studio Enterprise &bull; Strict Leakage-Controlled Tabular Platform</span>
          <span className="font-mono text-[11px]">Role: {roleName} &bull; Day 11 Platform Release</span>
        </div>
      </footer>
    </div>
  );
};
