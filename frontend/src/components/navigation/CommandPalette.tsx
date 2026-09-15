import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Upload,
  Play,
  Layers,
  BarChart3,
  Server,
  ShieldCheck,
  Sliders,
  FolderKanban,
  Activity,
  FileSpreadsheet,
  CheckCircle2,
  Sparkles,
  Shield,
  FileText,
  Lock,
  Flame,
  ChevronRight,
  Database,
  ArrowRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useProject } from '../../context/ProjectContext';

export interface CommandItem {
  id: string;
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  category: 'Actions' | 'Navigation' | 'Projects' | 'Legal & Governance';
  shortcut?: string;
  onSelect: () => void;
}

export const CommandPalette: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { projects, currentProjectId, selectProject } = useProject();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global Escape key listener
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [isOpen, onClose]);

  const projectQueryParam = currentProjectId ? `?project_id=${currentProjectId}` : '';

  // Command items catalog
  const allItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = [
      // 1. Actions
      {
        id: 'action-upload',
        title: 'Upload Tabular Dataset',
        subtitle: 'Upload CSV, Excel, or Parquet and seal cryptographic test partition',
        icon: <Upload className="w-4 h-4 text-[var(--color-accent)]" />,
        category: 'Actions',
        shortcut: 'U',
        onSelect: () => {
          navigate(`/data${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'action-eda',
        title: 'Run Exploratory Data Analysis',
        subtitle: 'Inspect distributions, missingness matrices, and correlation heatmaps',
        icon: <BarChart3 className="w-4 h-4 text-emerald-400" />,
        category: 'Actions',
        shortcut: 'E',
        onSelect: () => {
          navigate(`/data-analysis${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'action-feature-selection',
        title: 'Run Feature Selection',
        subtitle: 'Calculate stability ranking across candidates with rank aggregation',
        icon: <Sliders className="w-4 h-4 text-amber-400" />,
        category: 'Actions',
        shortcut: 'F',
        onSelect: () => {
          navigate(`/features${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'action-train',
        title: 'Launch Model Training',
        subtitle: 'Configure algorithms and execute inner CV folds with zero leakage',
        icon: <Play className="w-4 h-4 text-orange-400" />,
        category: 'Actions',
        shortcut: 'T',
        onSelect: () => {
          navigate(`/ml${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'action-gates',
        title: 'Evaluate Deployment Gates',
        subtitle: 'Verify 6-condition pre-deployment checklist with dual-signoff',
        icon: <ShieldCheck className="w-4 h-4 text-indigo-400" />,
        category: 'Actions',
        shortcut: 'G',
        onSelect: () => {
          navigate(`/production${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'action-2fa',
        title: 'Two-Factor Authentication (2FA / OTP)',
        subtitle: 'Configure secure TOTP authenticator pairing and emergency recovery keys',
        icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
        category: 'Actions',
        shortcut: '2FA',
        onSelect: () => {
          window.dispatchEvent(new CustomEvent('open-2fa-modal'));
          onClose();
        },
      },

      // 2. Navigation
      {
        id: 'nav-workspace',
        title: 'Workspace Dashboard',
        subtitle: 'Project portfolio overview, active pipelines, and platform metrics',
        icon: <FolderKanban className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/dashboard');
          onClose();
        },
      },
      {
        id: 'nav-data',
        title: '1. Ingest & Profile Stage',
        subtitle: 'Dataset schema, preview rows, data quality score, and locked test split',
        icon: <Database className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/data${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-analysis',
        title: '2. Exploratory Analysis Stage',
        subtitle: 'Interactive bivariate scatterplots, distributions, and IQR outlier boundaries',
        icon: <BarChart3 className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/data-analysis${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-transformations',
        title: '3. Preprocessing Transformations',
        subtitle: 'Strict train-fitted scalers, categorical encoders, and KNN imputers',
        icon: <Layers className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/transformations${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-features',
        title: '4. Feature Engineering & Selection',
        subtitle: 'Stability index, multicollinearity pruning, and rank aggregation',
        icon: <Sliders className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/features${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-ml',
        title: '5. Model Training & Leaderboard',
        subtitle: 'Algorithm comparisons, ROC/PR curves, confusion matrices, and SHAP trees',
        icon: <Sparkles className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/ml${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-production',
        title: '6. Production Serving & Gating',
        subtitle: 'Dual-key approval, locked test score evaluation, and live REST inference',
        icon: <Server className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate(`/production${projectQueryParam}`);
          onClose();
        },
      },
      {
        id: 'nav-monitoring',
        title: '7. Telemetry & Observability',
        subtitle: 'Real-time worker task queue, P99 inference latencies, and PSI drift tracking',
        icon: <Activity className="w-4 h-4 text-[var(--color-text-muted)]" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/monitoring');
          onClose();
        },
      },

      // 3. Legal & Governance
      {
        id: 'legal-center',
        title: 'Legal & Governance Center',
        subtitle: 'Enterprise documentation hub, security safeguards, and compliance terms',
        icon: <Shield className="w-4 h-4 text-[var(--color-accent)]" />,
        category: 'Legal & Governance',
        onSelect: () => {
          navigate('/legal');
          onClose();
        },
      },
      {
        id: 'legal-privacy',
        title: 'Privacy Policy & Data Transparency',
        subtitle: '14-section disclosure on customer dataset isolation and retention',
        icon: <Lock className="w-4 h-4 text-emerald-400" />,
        category: 'Legal & Governance',
        onSelect: () => {
          navigate('/privacy');
          onClose();
        },
      },
      {
        id: 'legal-terms',
        title: 'Enterprise Terms of Service',
        subtitle: '18-clause SaaS agreement with customer IP and model ownership protections',
        icon: <FileText className="w-4 h-4 text-indigo-400" />,
        category: 'Legal & Governance',
        onSelect: () => {
          navigate('/terms');
          onClose();
        },
      },
    ];

    // 4. Projects
    projects.forEach((p) => {
      const isCurrent = String(p.id) === String(currentProjectId);
      items.push({
        id: `project-${p.id}`,
        title: p.project_name || p.name || `Project #${p.id}`,
        subtitle: `Stage: ${p.pipeline_stage || 'NEW'} • Task: ${p.task_type || 'Unassigned'}${
          p.target_column ? ` • Target: ${p.target_column}` : ''
        }${isCurrent ? ' (Active)' : ''}`,
        icon: <FolderKanban className={cn('w-4 h-4', isCurrent ? 'text-[var(--color-accent)]' : 'text-slate-400')} />,
        category: 'Projects',
        onSelect: () => {
          selectProject(String(p.id));
          navigate(`/dashboard?tab=overview&project_id=${p.id}`);
          onClose();
        },
      });
    });

    return items;
  }, [projects, currentProjectId, projectQueryParam, navigate, onClose, selectProject]);

  // Filter items by query
  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems;
    const lower = query.toLowerCase();
    return allItems.filter(
      (item) =>
        item.title.toLowerCase().includes(lower) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(lower)) ||
        item.category.toLowerCase().includes(lower)
    );
  }, [allItems, query]);

  // Reset index on filter change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredItems]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredItems.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredItems.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].onSelect();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col text-[var(--color-text)] animate-scaleUp transition-colors"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
          <Search className="w-4 h-4 text-[var(--color-accent)] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, action, or search projects..."
            className="w-full bg-transparent text-[var(--color-text)] placeholder-[var(--color-text-muted)] text-xs sm:text-sm font-medium focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded shadow-xs">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-[60vh] overflow-y-auto p-2 divide-y divide-[var(--color-border)]/50">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-[var(--color-text-muted)] text-xs space-y-1">
              <div>No matching actions, navigation items, or projects found for:</div>
              <div className="font-mono font-bold text-[var(--color-text)]">"{query}"</div>
            </div>
          ) : (
            (['Actions', 'Navigation', 'Projects', 'Legal & Governance'] as const).map((category) => {
              const categoryItems = filteredItems.filter((i) => i.category === category);
              if (categoryItems.length === 0) return null;

              return (
                <div key={category} className="py-2 first:pt-1 last:pb-1 space-y-1">
                  <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                    {category}
                  </div>
                  {categoryItems.map((item) => {
                    const globalIdx = filteredItems.indexOf(item);
                    const isSelected = globalIdx === selectedIndex;

                    return (
                      <div
                        key={item.id}
                        onClick={item.onSelect}
                        onMouseEnter={() => setSelectedIndex(globalIdx)}
                        className={cn(
                          'flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer transition-all',
                          isSelected
                            ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent)]/30 font-medium'
                            : 'text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] border border-transparent'
                        )}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={cn(
                              'p-1.5 rounded-lg shrink-0 transition-colors',
                              isSelected
                                ? 'bg-[var(--color-accent)]/20 text-[var(--color-accent)]'
                                : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)]'
                            )}
                          >
                            {item.icon}
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-bold truncate text-[var(--color-text)]">
                              {item.title}
                            </p>
                            {item.subtitle && (
                              <p className="text-[11px] text-[var(--color-text-muted)] truncate">
                                {item.subtitle}
                              </p>
                            )}
                          </div>
                        </div>

                        {item.shortcut && (
                          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded shadow-xs">
                            {item.shortcut}
                          </kbd>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-[var(--color-border)] bg-[var(--color-surface-hover)]/40 text-[11px] text-[var(--color-text-muted)]">
          <div className="flex items-center gap-3">
            <span>
              <strong className="text-[var(--color-text)]">↑↓</strong> Navigate
            </span>
            <span>
              <strong className="text-[var(--color-text)]">↵</strong> Select
            </span>
            <span>
              <strong className="text-[var(--color-text)]">ESC</strong> Close
            </span>
          </div>
          <span className="font-medium">ML Studio Universal Command Palette</span>
        </div>
      </div>
    </div>
  );
};
export default CommandPalette;
