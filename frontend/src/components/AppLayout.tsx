import React, { useState, useEffect, ReactNode } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Breadcrumbs } from './navigation/Breadcrumbs';
import { CommandPalette } from './navigation/CommandPalette';
import {
  Layers,
  LayoutDashboard,
  Database,
  Sparkles,
  Search,
  Stethoscope,
  Cpu,
  Boxes,
  ShieldCheck,
  ShieldAlert,
  Moon,
  Sun,
  LogOut,
  LucideIcon,
  Shield,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
}

export interface AppLayoutProps {
  children: ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { user, logout, darkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);

  // Global keyboard shortcut for Command Palette (Ctrl+K / Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent): void => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = async (): Promise<void> => {
    await logout();
    navigate('/login');
  };

  const userPerms = new Set(
    user?.permissions ||
    (user?.role?.permissions ? user.role.permissions.map((p) => (typeof p === 'string' ? p : p.permission_key)) : [])
  );
  const roleName = user?.role?.role_name === 'ADMIN' ? 'ADMIN' : 'USER';
  const isAdmin = roleName === 'ADMIN' || userPerms.has('MANAGE_USERS');

  // Top Nav Items
  const TOP_NAV_ITEMS: NavItem[] = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Data', path: '/data', icon: Database },
    { name: 'Analysis', path: '/data-analysis', icon: Search },
    { name: 'Transform', path: '/transformations', icon: Sparkles },
    { name: 'Features', path: '/feature-engineering', icon: Boxes },
    { name: 'ML Training', path: '/ml/training', icon: Cpu },
    { name: 'Diagnostics', path: '/diagnostics', icon: Stethoscope },
    { name: 'Production', path: '/production', icon: ShieldCheck },
  ];

  if (isAdmin) {
    TOP_NAV_ITEMS.push({ name: 'Admin', path: '/admin', icon: ShieldAlert });
  }

  // Preserve project query param across transitions
  const currentProjectId = new URLSearchParams(location.search).get('project_id');
  const getNavPath = (basePath: string): string => {
    return currentProjectId ? `${basePath}?project_id=${currentProjectId}` : basePath;
  };

  const isItemActive = (itemPath: string): boolean => {
    const currentPath = location.pathname;
    if (itemPath === '/dashboard' && (currentPath === '/dashboard' || currentPath === '/')) return true;
    if (itemPath === '/data' && (currentPath.startsWith('/data') || currentPath === '/data')) return true;
    if (itemPath === '/data-analysis' && (currentPath.startsWith('/analysis') || currentPath === '/data-analysis')) return true;
    if (itemPath === '/transformations' && currentPath === '/transformations') return true;
    if (itemPath === '/feature-engineering' && currentPath.startsWith('/feature-engineering')) return true;
    if (itemPath === '/ml/training' && (currentPath.startsWith('/ml') || currentPath === '/machine-learning' || currentPath === '/leaderboard')) return true;
    if (itemPath === '/diagnostics' && (currentPath.startsWith('/intelligence') || currentPath === '/diagnostics')) return true;
    if (itemPath === '/production' && (currentPath.startsWith('/production') || currentPath === '/validation' || currentPath === '/monitoring')) return true;
    if (itemPath === '/admin' && currentPath.startsWith('/admin')) return true;
    return currentPath === itemPath;
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex flex-col transition-colors">
      {/* Sleek Top Navigation Header */}
      <header className="sticky top-0 z-40 w-full border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur-md transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <div className="flex items-center space-x-6 shrink-0">
            <Link 
              to={getNavPath('/dashboard')} 
              className="flex items-center space-x-3 group focus:outline-hidden"
            >
              <div className="relative flex items-center justify-center">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[var(--color-accent)] via-amber-500 to-orange-400 flex items-center justify-center text-white shadow-md shadow-[var(--color-accent)]/20 group-hover:scale-105 transition-all duration-200 shrink-0">
                  <Layers className="w-4 h-4" />
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 ring-2 ring-[var(--color-surface)]"></span>
                </span>
              </div>

              <div className="flex items-center">
                <span className="text-base font-extrabold tracking-tight text-[var(--color-text)] leading-none">
                  ML Studio
                </span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <nav className="hidden lg:flex items-center space-x-1.5 overflow-x-auto py-1">
              {TOP_NAV_ITEMS.map((item) => {
                const active = isItemActive(item.path);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={getNavPath(item.path)}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active
                        ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-semibold shadow-md shadow-[var(--color-accent)]/20 border border-[var(--color-accent)]/30 scale-[1.02]'
                        : 'text-[var(--color-text-muted)] bg-[var(--color-surface)]/80 hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)]/50 shadow-xs hover:shadow-sm'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Quick Actions & User Controls */}
          <div className="flex items-center space-x-2 shrink-0">
            {/* Quick Command Palette Button */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden sm:flex items-center space-x-2 px-2.5 py-1.5 rounded-lg bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
              title="Quick Search & Navigation (Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search...</span>
              <kbd className="text-[10px] font-mono bg-[var(--color-surface)] px-1.5 py-0.5 rounded-sm border border-[var(--color-border)]">
                ⌘K
              </kbd>
            </button>

            {/* Dark Mode Toggle */}
            <button
              type="button"
              onClick={toggleDarkMode}
              className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] min-h-[38px] min-w-[38px] flex items-center justify-center transition-colors"
              aria-label={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* User Profile / Logout */}
            {user && (
              <div className="flex items-center space-x-2 pl-2 border-l border-[var(--color-border)]">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-medium text-[var(--color-text)] leading-tight">
                    {user.full_name || user.email?.split('@')[0]}
                  </span>
                  <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
                    {roleName}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="p-2 rounded-xl text-rose-500 hover:text-rose-400 hover:bg-rose-500/10 min-h-[38px] min-w-[38px] flex items-center justify-center transition-colors cursor-pointer"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Sub-Navigation (Horizontal Scroll on smaller screens) */}
        <div className="lg:hidden flex items-center space-x-1.5 overflow-x-auto px-4 py-2 border-t border-[var(--color-border)]/60 bg-[var(--color-surface)]/80">
          {TOP_NAV_ITEMS.map((item) => {
            const active = isItemActive(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={getNavPath(item.path)}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  active
                    ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-semibold shadow-md shadow-[var(--color-accent)]/20 border border-[var(--color-accent)]/30'
                    : 'text-[var(--color-text-muted)] bg-[var(--color-surface)]/80 hover:text-[var(--color-text)] border border-[var(--color-border)]/50 shadow-xs'
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </header>

      {/* Dynamic Breadcrumb Trail */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-3 pb-1">
        <Breadcrumbs />
      </div>

      {/* Main Full-Width Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-3 sm:py-5 overflow-x-hidden">
        {children}
      </main>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {/* Launch-Ready Footer */}
      <footer className="border-t border-[var(--color-border)]/60 bg-[var(--color-surface)]/40 py-4 text-xs text-[var(--color-text-muted)] mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-3 text-center md:text-left">
          <div className="flex flex-wrap items-center justify-center md:justify-start gap-x-3 gap-y-1">
            <span className="font-medium text-[var(--color-text)]">
              &copy; {new Date().getFullYear()} ML Studio Inc.
            </span>
            <span className="hidden sm:inline">&bull;</span>
            <span className="text-[11px]">Intelligent Tabular ML Platform</span>
            <span className="hidden sm:inline">&bull;</span>
            <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Pipelines Operational</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[11px]">
            <a
              href="mailto:support@mlstudio.io"
              className="hover:text-[var(--color-accent)] transition-colors py-1 inline-flex items-center space-x-1"
              title="Email ML Studio Support"
            >
              <span>Support: support@mlstudio.io</span>
            </a>
            <span className="hidden sm:inline text-slate-600">&bull;</span>
            <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
              v1.0.0
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
