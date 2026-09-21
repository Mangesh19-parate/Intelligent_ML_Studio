import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home, FolderKanban } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useProject } from '../../context/ProjectContext';

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Workspace',
  projects: 'Projects',
  data: 'Data & Schema',
  upload: 'Upload',
  datasets: 'Datasets',
  schema: 'Schema Inspection',
  quality: 'Data Quality',
  'data-analysis': 'Exploratory Analysis',
  analysis: 'Analysis',
  eda: 'Interactive EDA',
  profiling: 'Profiling Report',
  correlations: 'Correlations',
  distributions: 'Distributions',
  'feature-engineering': 'Feature Engineering',
  features: 'Features',
  transformations: 'Transformations',
  selection: 'Feature Selection',
  snapshots: 'Snapshots',
  ml: 'Machine Learning',
  training: 'Model Training',
  leaderboard: 'Model Leaderboard',
  experiments: 'Experiments',
  explainability: 'Explainability & SHAP',
  diagnostics: 'Diagnostics',
  production: 'Production & Serving',
  gates: 'Deployment Gates',
  serving: 'Live Serving',
  monitoring: 'Telemetry Monitoring',
  audit: 'Audit Logs',
  admin: 'Admin Console',
};

export interface BreadcrumbsProps {
  className?: string;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ className }) => {
  const location = useLocation();
  const { activeProject } = useProject();

  const pathSegments = location.pathname.split('/').filter(Boolean);

  if (pathSegments.length === 0 || (pathSegments.length === 1 && pathSegments[0] === 'dashboard')) {
    return null;
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center text-xs text-slate-400 py-1.5 overflow-x-auto', className)}
    >
      <ol className="flex items-center gap-1.5 flex-nowrap shrink-0">
        <li>
          <Link
            to="/dashboard"
            className="flex items-center gap-1 hover:text-slate-200 transition-colors"
          >
            <Home className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-medium">Workspace</span>
          </Link>
        </li>

        {activeProject && (
          <li className="flex items-center gap-1.5">
            <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
            <Link
              to={`/projects/${activeProject.id}`}
              className="flex items-center gap-1 text-slate-300 hover:text-indigo-400 font-medium transition-colors max-w-[150px] truncate"
            >
              <FolderKanban className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="truncate">{activeProject.project_name}</span>
            </Link>
          </li>
        )}

        {pathSegments.map((segment, idx) => {
          // If segment is a UUID (project id), skip duplicate display
          if (segment.length >= 32 && segment.includes('-')) {
            return null;
          }

          const label = ROUTE_LABELS[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);
          const isLast = idx === pathSegments.length - 1;
          const routePath = `/${pathSegments.slice(0, idx + 1).join('/')}`;

          return (
            <li key={segment + idx} className="flex items-center gap-1.5">
              <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
              {isLast ? (
                <span className="font-semibold text-slate-200 truncate max-w-[180px]">
                  {label}
                </span>
              ) : (
                <Link
                  to={routePath}
                  className="hover:text-slate-200 transition-colors truncate max-w-[140px]"
                >
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
