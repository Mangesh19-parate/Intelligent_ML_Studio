import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  ChevronDown,
  Plus,
  Search,
  Target,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useProject } from '../../context/ProjectContext';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

export interface ProjectContextHeaderProps {
  onOpenCommandPalette: () => void;
  className?: string;
}

export const ProjectContextHeader: React.FC<ProjectContextHeaderProps> = ({
  onOpenCommandPalette,
  className,
}) => {
  const navigate = useNavigate();
  const { projects, activeProject, selectProject } = useProject();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const getStageVariant = (stage?: string): 'success' | 'warning' | 'info' | 'primary' | 'neutral' => {
    switch (stage) {
      case 'DEPLOYED':
        return 'success';
      case 'TRAINED':
      case 'EVALUATED':
      case 'GATE_PASSED':
        return 'info';
      case 'TRANSFORMED':
      case 'SPLIT':
      case 'PROFILED':
        return 'primary';
      case 'DATA':
        return 'warning';
      default:
        return 'neutral';
    }
  };

  return (
    <header
      className={cn(
        'w-full flex items-center justify-between px-4 sm:px-6 py-2.5 bg-slate-900/80 border-b border-slate-800 backdrop-blur-md sticky top-0 z-30 text-slate-100',
        className
      )}
    >
      {/* Left: Project Selector & Status */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-slate-600 transition-all text-left group"
          >
            <FolderKanban className="w-4 h-4 text-indigo-400 shrink-0" />
            <div className="flex flex-col min-w-0 max-w-[200px] sm:max-w-[280px]">
              <span className="text-xs font-semibold text-slate-200 truncate">
                {activeProject ? activeProject.project_name : 'Select Project'}
              </span>
              <span className="text-[10px] text-slate-400 truncate">
                {activeProject?.task_type || 'Workspace'}
              </span>
            </div>
            <ChevronDown
              className={cn(
                'w-3.5 h-3.5 text-slate-400 group-hover:text-slate-200 transition-transform duration-200 shrink-0 ml-1',
                dropdownOpen && 'rotate-180'
              )}
            />
          </button>

          {/* Project Switcher Dropdown */}
          {dropdownOpen && (
            <div className="absolute left-0 top-full mt-2 w-72 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-40 animate-fadeIn">
              <div className="p-2 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-2">
                  Projects ({projects.length})
                </span>
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    navigate('/dashboard');
                  }}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 px-1 py-0.5"
                >
                  <Plus className="w-3.5 h-3.5" /> New
                </button>
              </div>

              <div className="max-h-60 overflow-y-auto p-1 divide-y divide-slate-800/40">
                {projects.length === 0 ? (
                  <div className="p-3 text-xs text-slate-500 text-center">No projects available</div>
                ) : (
                  projects.map((p) => {
                    const isSelected = p.id === activeProject?.id;
                    return (
                      <div
                        key={p.id}
                        onClick={() => {
                          selectProject(String(p.id));
                          setDropdownOpen(false);
                        }}
                        className={cn(
                          'flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-colors',
                          isSelected
                            ? 'bg-indigo-600/15 text-indigo-200 font-semibold'
                            : 'text-slate-300 hover:bg-slate-800/60'
                        )}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <FolderKanban
                            className={cn('w-4 h-4 shrink-0', isSelected ? 'text-indigo-400' : 'text-slate-500')}
                          />
                          <div className="min-w-0">
                            <p className="text-xs truncate">{p.project_name}</p>
                            <p className="text-[10px] text-slate-500 truncate">{p.task_type}</p>
                          </div>
                        </div>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 shrink-0 font-mono">
                          {p.pipeline_stage}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Pipeline Stage Badge */}
        {activeProject && (
          <div className="hidden md:flex items-center gap-2">
            <Badge variant={getStageVariant(activeProject.pipeline_stage)} size="sm" hasDot>
              {activeProject.pipeline_stage}
            </Badge>

            {activeProject.target_column && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[11px] text-[var(--color-text-muted)]">
                <Target className="w-3 h-3 text-[var(--color-accent)]" />
                <span className="text-[var(--color-text-muted)] font-semibold">Target:</span>
                <span className="font-bold font-mono text-[var(--color-text)] truncate max-w-[120px]">
                  {activeProject.target_column}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: Global Command Palette Trigger & Shortcuts */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-all text-xs group cursor-pointer shadow-xs"
          aria-label="Open Command Palette"
        >
          <Search className="w-3.5 h-3.5 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] transition-colors" />
          <span className="hidden sm:inline">Search actions, stages, or projects...</span>
          <kbd className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-bg)] border border-[var(--color-border)] rounded shadow-xs">
            ⌘K
          </kbd>
        </button>
      </div>
    </header>
  );
};
