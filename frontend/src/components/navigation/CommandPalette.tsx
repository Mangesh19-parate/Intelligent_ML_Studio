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
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useProject } from '../../context/ProjectContext';

export interface CommandItem {
  id: string;
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  category: 'Actions' | 'Navigation' | 'Projects';
  shortcut?: string;
  onSelect: () => void;
}

export const CommandPalette: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { projects, selectProject } = useProject();
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

  // Command items catalog
  const allItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = [
      // Actions
      {
        id: 'action-upload',
        title: 'Upload Tabular Dataset',
        subtitle: 'Upload CSV, Excel, or JSON file to active project',
        icon: <Upload className="w-4 h-4 text-indigo-400" />,
        category: 'Actions',
        shortcut: 'U',
        onSelect: () => {
          navigate('/data/upload');
          onClose();
        },
      },
      {
        id: 'action-train',
        title: 'Launch Model Training',
        subtitle: 'Configure algorithms and execute inner CV folds',
        icon: <Play className="w-4 h-4 text-emerald-400" />,
        category: 'Actions',
        shortcut: 'T',
        onSelect: () => {
          navigate('/ml/training');
          onClose();
        },
      },
      {
        id: 'action-feature-selection',
        title: 'Run Feature Selection',
        subtitle: 'Calculate stability ranking across candidates',
        icon: <Sliders className="w-4 h-4 text-amber-400" />,
        category: 'Actions',
        shortcut: 'F',
        onSelect: () => {
          navigate('/features/selection');
          onClose();
        },
      },
      {
        id: 'action-gates',
        title: 'Evaluate Deployment Gates',
        subtitle: 'Verify 6-condition pre-deployment checklist',
        icon: <ShieldCheck className="w-4 h-4 text-purple-400" />,
        category: 'Actions',
        shortcut: 'G',
        onSelect: () => {
          navigate('/production/gates');
          onClose();
        },
      },

      // Navigation
      {
        id: 'nav-workspace',
        title: 'Workspace Overview',
        subtitle: 'View all projects and platform health',
        icon: <FolderKanban className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/dashboard');
          onClose();
        },
      },
      {
        id: 'nav-data',
        title: 'Data & Schema Inspection',
        subtitle: 'Column statistics, dtypes, and null counts',
        icon: <FileSpreadsheet className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/data');
          onClose();
        },
      },
      {
        id: 'nav-analysis',
        title: 'Exploratory Data Analysis (EDA)',
        subtitle: 'Interactive distributions and correlation matrix',
        icon: <BarChart3 className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/data-analysis');
          onClose();
        },
      },
      {
        id: 'nav-transformations',
        title: 'Feature Transformations',
        subtitle: 'Scaling, encoding, and imputation pipeline',
        icon: <Layers className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/transformations');
          onClose();
        },
      },
      {
        id: 'nav-ml',
        title: 'Model Leaderboard & Evaluation',
        subtitle: 'Compare candidate models and locked test metrics',
        icon: <Sparkles className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/ml/leaderboard');
          onClose();
        },
      },
      {
        id: 'nav-production',
        title: 'Production & Serving',
        subtitle: 'Real-time REST inference and prediction logs',
        icon: <Server className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/production');
          onClose();
        },
      },
      {
        id: 'nav-monitoring',
        title: 'Telemetry & Observability',
        subtitle: 'Task queue depth, worker state, and latencies',
        icon: <Activity className="w-4 h-4 text-slate-400" />,
        category: 'Navigation',
        onSelect: () => {
          navigate('/monitoring');
          onClose();
        },
      },
    ];

    // Add projects
    projects.forEach((p) => {
      items.push({
        id: `project-${p.id}`,
        title: p.project_name,
        subtitle: `Stage: ${p.pipeline_stage} • Task: ${p.task_type}`,
        icon: <FolderKanban className="w-4 h-4 text-indigo-400" />,
        category: 'Projects',
        onSelect: () => {
          selectProject(String(p.id));
          navigate(`/projects/${p.id}`);
          onClose();
        },
      });
    });

    return items;
  }, [projects, navigate, onClose, selectProject]);

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
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col text-slate-100 animate-scaleUp"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800 bg-slate-900/90">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, action, or search projects..."
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-[10px] font-semibold text-slate-400 bg-slate-800 border border-slate-700 rounded">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-[60vh] overflow-y-auto p-2 divide-y divide-slate-800/40">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No matching commands or projects found for "{query}"
            </div>
          ) : (
            ['Actions', 'Navigation', 'Projects'].map((category) => {
              const categoryItems = filteredItems.filter((i) => i.category === category);
              if (categoryItems.length === 0) return null;

              return (
                <div key={category} className="py-1.5 first:pt-0 last:pb-0">
                  <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
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
                          'flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-colors',
                          isSelected
                            ? 'bg-indigo-600/15 text-indigo-200 border border-indigo-500/20'
                            : 'text-slate-300 hover:bg-slate-800/50 border border-transparent'
                        )}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={cn(
                              'p-1.5 rounded-lg shrink-0',
                              isSelected ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-400'
                            )}
                          >
                            {item.icon}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{item.title}</p>
                            {item.subtitle && (
                              <p className="text-xs text-slate-400 truncate">{item.subtitle}</p>
                            )}
                          </div>
                        </div>

                        {item.shortcut && (
                          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700 rounded">
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
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-800 bg-slate-900/50 text-[11px] text-slate-500">
          <div className="flex items-center gap-3">
            <span>
              <strong className="text-slate-400">↑↓</strong> Navigate
            </span>
            <span>
              <strong className="text-slate-400">↵</strong> Select
            </span>
            <span>
              <strong className="text-slate-400">ESC</strong> Close
            </span>
          </div>
          <span>ML Studio Command Palette</span>
        </div>
      </div>
    </div>
  );
};
