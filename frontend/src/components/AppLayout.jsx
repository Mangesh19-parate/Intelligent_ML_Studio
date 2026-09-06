import React from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  LayoutDashboard,
  Database,
  BarChart3,
  SlidersHorizontal,
  Workflow,
  Stethoscope,
  Cpu,
  Rocket,
  ShieldAlert,
  ShieldCheck,
  Moon,
  Sun,
  LogOut,
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
  const roleName = user?.role?.role_name || (typeof user?.role === 'string' ? user?.role : 'VIEWER');
  const isAdmin = roleName === 'ADMIN';

  const STAGES = [
    { id: 'workspace', name: '1. Workspace', path: '/dashboard', icon: LayoutDashboard },
    { id: 'data', name: '2. Data', path: '/data', icon: Database },
    { id: 'analysis', name: '3. Data Analysis', path: '/data-analysis', icon: BarChart3 },
    { id: 'transformations', name: '4. Feature Transformation', path: '/transformations', icon: SlidersHorizontal },
    { id: 'features', name: '5. Feature Engineering', path: '/feature-engineering', icon: Workflow },
    { id: 'diagnostics', name: '6. Diagnostics', path: '/diagnostics', icon: Stethoscope },
    { id: 'ml', name: '7. Machine Learning', path: '/machine-learning', icon: Cpu },
    { id: 'production', name: '8. Production', path: '/production', icon: Rocket },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-text flex flex-col transition-colors">
      {/* Top Main Navbar */}
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
                  8-Stage Leakage-Safe Workbench
                </span>
              </div>
            </Link>
          </div>

          {/* User Controls & Role State */}
          {user && (
            <div className="flex items-center space-x-4">
              <div className={`hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-semibold ${
                isAdmin 
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-500' 
                  : 'bg-[var(--color-bg)] border-[var(--color-border)] text-text'
              }`}>
                {isAdmin ? <ShieldAlert className="w-3.5 h-3.5 text-rose-500" /> : <ShieldCheck className="w-3.5 h-3.5 text-[var(--color-accent)]" />}
                <span>{roleName}</span>
                <span className="text-[var(--color-text-muted)]">({userPerms.size} perms)</span>
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

        {/* 8-Stage Navigation Bar + Conditional Admin Section */}
        <div className="border-t border-[var(--color-border)]/60 bg-[var(--color-surface)]/50 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto flex items-center justify-between overflow-x-auto py-2">
            <div className="flex items-center space-x-1 sm:space-x-2 shrink-0">
              {STAGES.map((stage) => {
                const Icon = stage.icon;
                const isActive = location.pathname === stage.path || (stage.path === '/dashboard' && location.pathname === '/');
                return (
                  <NavLink
                    key={stage.id}
                    to={stage.path}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-[var(--color-accent)] text-white shadow-sm font-bold'
                        : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{stage.name}</span>
                  </NavLink>
                );
              })}
            </div>

            {/* Admin Section: STRICTLY VISIBLE ONLY TO ADMIN */}
            {isAdmin && (
              <div className="pl-4 border-l border-[var(--color-border)] shrink-0">
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                      isActive
                        ? 'bg-rose-600 text-white font-bold shadow-sm'
                        : 'text-rose-500 hover:bg-rose-500/10 font-bold'
                    }`
                  }
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Admin Console</span>
                </NavLink>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/50 py-4 text-center text-xs text-[var(--color-text-muted)]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>ML Studio &bull; 8-Stage Leakage-Controlled Tabular ML Workbench</span>
          <span className="font-mono text-[11px]">Role: {roleName} {isAdmin && '&bull; (Admin Privileges Active)'}</span>
        </div>
      </footer>
    </div>
  );
};
