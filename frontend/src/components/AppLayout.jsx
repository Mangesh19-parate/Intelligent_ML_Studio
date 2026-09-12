import React, { useState } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  LayoutDashboard,
  FolderKanban,
  Upload,
  Database,
  BarChart3,
  Sparkles,
  SlidersHorizontal,
  Workflow,
  Search,
  AlertCircle,
  Stethoscope,
  Lightbulb,
  BrainCircuit,
  Cpu,
  FlaskConical,
  Trophy,
  Boxes,
  ShieldCheck,
  Zap,
  Activity,
  ShieldAlert,
  Moon,
  Sun,
  LogOut,
  Menu,
  X,
  ChevronRight,
  ChevronDown,
  Sparkle,
  Radio,
} from 'lucide-react';

export const AppLayout = ({ children }) => {
  const { user, logout, darkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState({});

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleSection = (title) => {
    setCollapsedSections((prev) => ({
      ...prev,
      [title]: !prev[title],
    }));
  };

  const userPerms = new Set(
    user?.permissions ||
    (user?.role?.permissions ? user.role.permissions.map((p) => (typeof p === 'string' ? p : p.permission_key)) : [])
  );
  const roleName = user?.role?.role_name || (typeof user?.role === 'string' ? user?.role : 'VIEWER');
  const isAdmin = roleName === 'ADMIN';

  // Navigation Structure matching the 8-stage enterprise ML workflow
  const NAV_SECTIONS = [
    {
      title: 'Workspace',
      tag: '01',
      items: [
        { name: 'Project Overview', path: '/dashboard', icon: LayoutDashboard },
        { name: 'My Projects', path: '/workspace', icon: FolderKanban },
      ],
    },
    {
      title: 'Data Ingestion',
      tag: '02',
      items: [
        { name: 'Upload Data', path: '/data/upload', icon: Upload },
        { name: 'Dataset Catalog', path: '/data/datasets', icon: Database },
        { name: 'Data Profiling', path: '/data/profiling', icon: BarChart3 },
        { name: 'Cleaning & Prep', path: '/data/cleaning', icon: SlidersHorizontal },
      ],
    },
    {
      title: 'Analysis & Features',
      tag: '03',
      items: [
        { name: 'Feature Engineering', path: '/analysis/feature-engineering', icon: Workflow },
        { name: 'Exploratory EDA', path: '/analysis/eda', icon: Search },
        { name: 'Outlier Detection', path: '/analysis/outliers', icon: AlertCircle },
        { name: 'Missing Imputation', path: '/analysis/imputation', icon: Sparkles },
        { name: 'Feature Selection', path: '/analysis/feature-selection', icon: SlidersHorizontal },
      ],
    },
    {
      title: 'Intelligence & Diagnostics',
      tag: '04',
      items: [
        { name: 'System Diagnostics', path: '/intelligence/diagnostics', icon: Stethoscope },
        { name: 'Remediation Advice', path: '/intelligence/recommendations', icon: Lightbulb },
        { name: 'Model Explainability', path: '/intelligence/explainability', icon: BrainCircuit },
      ],
    },
    {
      title: 'Machine Learning',
      tag: '05',
      items: [
        { name: 'Model Training', path: '/ml/training', icon: Cpu },
        { name: 'Experiment Runs', path: '/ml/experiments', icon: FlaskConical },
        { name: 'Evaluation Matrix', path: '/ml/evaluation', icon: Trophy },
        { name: 'Model Registry', path: '/ml/registry', icon: Boxes },
      ],
    },
    {
      title: 'Production & Serving',
      tag: '06',
      items: [
        { name: 'Gate Validation', path: '/validation', icon: ShieldCheck },
        { name: 'Prediction Engine', path: '/production/predictions', icon: Zap },
        { name: 'Deployment Drift', path: '/production/monitoring', icon: Activity },
      ],
    },
  ];

  const getNavPath = (basePath) => {
    return location.search ? `${basePath}${location.search}` : basePath;
  };

  const isItemActive = (itemPath) => {
    const currentPath = location.pathname;
    if (itemPath === '/dashboard' && (currentPath === '/' || currentPath === '/dashboard')) return true;
    if (itemPath === '/workspace' && (currentPath === '/workspace' || currentPath === '/projects')) return true;
    if (itemPath === '/data/upload' && currentPath === '/data/upload') return true;
    if (itemPath === '/data/datasets' && (currentPath === '/data/datasets' || currentPath === '/data')) return true;
    if (itemPath === '/data/profiling' && (currentPath === '/data/profiling' || currentPath === '/data-analysis')) return true;
    if (itemPath === '/data/cleaning' && (currentPath === '/data/cleaning' || currentPath === '/transformations')) return true;
    if (itemPath === '/analysis/feature-engineering' && (currentPath === '/analysis/feature-engineering' || currentPath === '/feature-engineering')) return true;
    if (itemPath === '/analysis/eda' && currentPath === '/analysis/eda') return true;
    if (itemPath === '/analysis/outliers' && currentPath === '/analysis/outliers') return true;
    if (itemPath === '/analysis/imputation' && currentPath === '/analysis/imputation') return true;
    if (itemPath === '/analysis/feature-selection' && currentPath === '/analysis/feature-selection') return true;
    if (itemPath === '/intelligence/diagnostics' && (currentPath === '/intelligence/diagnostics' || currentPath === '/diagnostics')) return true;
    if (itemPath === '/intelligence/recommendations' && currentPath === '/intelligence/recommendations') return true;
    if (itemPath === '/intelligence/explainability' && currentPath === '/intelligence/explainability') return true;
    if (itemPath === '/ml/training' && (currentPath === '/ml/training' || currentPath === '/machine-learning')) return true;
    if (itemPath === '/ml/experiments' && currentPath === '/ml/experiments') return true;
    if (itemPath === '/ml/evaluation' && (currentPath === '/ml/evaluation' || currentPath === '/leaderboard')) return true;
    if (itemPath === '/ml/registry' && currentPath === '/ml/registry') return true;
    if (itemPath === '/validation' && (currentPath === '/validation' || currentPath === '/production')) return true;
    if (itemPath === '/production/predictions' && currentPath === '/production/predictions') return true;
    if (itemPath === '/production/monitoring' && (currentPath === '/production/monitoring' || currentPath === '/monitoring')) return true;
    return currentPath === itemPath;
  };

  const sidebarContent = (
    <div className="flex flex-col h-full select-none bg-[var(--color-surface)]">
      {/* Brand Header */}
      <div className="px-5 py-5 flex items-center justify-between shrink-0 border-b border-[var(--color-border)]/60">
        <Link 
          to={getNavPath('/dashboard')} 
          onClick={() => setMobileOpen(false)}
          className="flex items-center space-x-3 group focus:outline-hidden"
        >
          <div className="relative flex items-center justify-center">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[var(--color-accent)] via-amber-500 to-orange-400 flex items-center justify-center text-white shadow-md shadow-[var(--color-accent)]/20 group-hover:shadow-[var(--color-accent)]/30 group-hover:scale-105 transition-all duration-200 shrink-0">
              <Layers className="w-4.5 h-4.5" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 ring-2 ring-[var(--color-surface)]"></span>
            </span>
          </div>

          <div className="flex flex-col min-w-0">
            <div className="flex items-center space-x-1.5">
              <span className="text-[15px] font-extrabold tracking-tight text-[var(--color-text)] leading-none">
                ML Studio
              </span>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent)]/20">
                PRO
              </span>
            </div>
            <span className="text-[10px] font-medium text-[var(--color-text-muted)] tracking-wider uppercase mt-1">
              Modular Platform
            </span>
          </div>
        </Link>

        {mobileOpen && (
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        )}
      </div>

      {/* Navigation Scrollable Body */}
      <div className="flex-1 overflow-y-auto px-3 py-3.5 space-y-4 custom-scrollbar">
        {NAV_SECTIONS.map((section) => {
          const isCollapsed = collapsedSections[section.title];
          return (
            <div key={section.title} className="space-y-1">
              {/* Section Header */}
              <button
                type="button"
                onClick={() => toggleSection(section.title)}
                className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/80 hover:text-[var(--color-text)] transition-colors group cursor-pointer"
              >
                <div className="flex items-center space-x-1.5">
                  <span className="text-[9px] font-mono text-[var(--color-text-muted)]/50 group-hover:text-[var(--color-accent)] transition-colors">
                    {section.tag}
                  </span>
                  <span>{section.title}</span>
                </div>
                <ChevronDown
                  className={`w-3 h-3 text-[var(--color-text-muted)]/50 group-hover:text-[var(--color-text)] transition-transform duration-200 ${
                    isCollapsed ? '-rotate-90' : 'rotate-0'
                  }`}
                />
              </button>

              {/* Items List */}
              {!isCollapsed && (
                <nav className="space-y-0.5">
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    const active = isItemActive(item.path);
                    return (
                      <NavLink
                        key={item.name}
                        to={getNavPath(item.path)}
                        onClick={() => setMobileOpen(false)}
                        className={`group relative flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                          active
                            ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-semibold shadow-xs'
                            : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]'
                        }`}
                      >
                        {/* Active vertical pill indicator */}
                        {active && (
                          <div className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[var(--color-accent)]" />
                        )}

                        <div className="flex items-center space-x-2.5 min-w-0">
                          <Icon
                            className={`w-4 h-4 shrink-0 transition-transform duration-150 group-hover:scale-105 ${
                              active
                                ? 'text-[var(--color-accent)]'
                                : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text)]'
                            }`}
                          />
                          <span className="truncate">{item.name}</span>
                        </div>

                        {active && (
                          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] shadow-xs shrink-0" />
                        )}
                      </NavLink>
                    );
                  })}
                </nav>
              )}
            </div>
          );
        })}

        {/* Administration Section */}
        {isAdmin && (
          <div className="pt-2 border-t border-[var(--color-border)]/60">
            <div className="px-2.5 pb-1 text-[10px] font-bold uppercase tracking-wider text-rose-500/90 flex items-center justify-between">
              <span>Admin Center</span>
              <span className="text-[9px] font-mono text-rose-400 bg-rose-500/10 px-1 rounded">SECURE</span>
            </div>
            <NavLink
              to={getNavPath('/admin')}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-rose-500 text-white shadow-xs'
                    : 'text-rose-400 hover:text-rose-300 hover:bg-rose-500/10'
                }`
              }
            >
              <div className="flex items-center space-x-2.5">
                <ShieldAlert className="w-4 h-4" />
                <span>Console & Users</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 opacity-60" />
            </NavLink>
          </div>
        )}
      </div>

      {/* User & Settings Footer */}
      {user && (
        <div className="p-3 border-t border-[var(--color-border)]/60 bg-[var(--color-surface)] shrink-0">
          <div className="flex items-center justify-between p-2 rounded-xl bg-[var(--color-surface-hover)]/40 border border-[var(--color-border)]/50 mb-2 shadow-xs">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[var(--color-accent)] to-amber-500 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-xs">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold truncate text-[var(--color-text)]">
                  {user.full_name || 'Studio User'}
                </div>
                <div className="flex items-center space-x-1.5 text-[10px] text-[var(--color-text-muted)] font-mono truncate">
                  <span className="font-semibold text-[var(--color-accent)]">{roleName}</span>
                  <span>&bull;</span>
                  <span>{userPerms.size} perms</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-0.5 px-0.5">
            <button
              onClick={toggleDarkMode}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-all cursor-pointer"
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {darkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
              <span className="text-[11px] font-medium">{darkMode ? 'Light' : 'Dark'}</span>
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-rose-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="text-[11px]">Logout</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex transition-colors">
      {/* Desktop Left Sidebar */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 h-screen sticky top-0 border-r border-[var(--color-border)]/80 bg-[var(--color-surface)] shadow-xs z-30 transition-colors">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Sidebar */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex flex-col w-72 max-w-[85vw] h-full bg-[var(--color-surface)] border-r border-[var(--color-border)] z-10 shadow-2xl">
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Mobile Top Header */}
        <header className="md:hidden sticky top-0 z-20 h-14 border-b border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-md px-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]"
              aria-label="Open Navigation Menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-base tracking-tight text-[var(--color-text)]">
                ML Studio
              </span>
              <span className="text-[9px] font-bold text-[var(--color-accent)] px-1.5 py-0.5 rounded-full bg-[var(--color-accent-soft)]">
                PRO
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              onClick={handleLogout}
              className="p-2 rounded-full text-rose-500 hover:bg-rose-500/10"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Main Viewport */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>

        {/* Minimal Footer */}
        <footer className="border-t border-[var(--color-border)]/60 bg-[var(--color-surface)]/30 py-3 text-center text-xs text-[var(--color-text-muted)]">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-1">
            <span>ML Studio &bull; Intelligent Machine Learning Platform</span>
            <span className="font-mono text-[11px]">Role: {roleName} {isAdmin && '&bull; Admin'}</span>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default AppLayout;
