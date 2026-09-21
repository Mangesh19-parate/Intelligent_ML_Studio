import React, { useState } from 'react';
import { ShieldAlert, Search, Filter, Clock, ChevronRight, ChevronDown } from 'lucide-react';

export interface AuditLogItem {
  id: string;
  action?: string;
  event_type?: string;
  user_email?: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any> | string;
  ip_address?: string;
  created_at: string;
}

interface AuditLogViewerProps {
  logs: AuditLogItem[];
  filter: string;
  onFilterChange: (filter: string) => void;
  search: string;
  onSearchChange: (search: string) => void;
}

export const AuditLogViewer: React.FC<AuditLogViewerProps> = ({
  logs,
  filter,
  onFilterChange,
  search,
  onSearchChange,
}) => {
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-5 h-5 text-[var(--color-accent)]" />
          <h3 className="text-sm font-bold text-[var(--color-text)]">
            Immutable Audit Trail & Governance Log
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          <select
            value={filter}
            onChange={(e) => onFilterChange(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="">All Event Types ({logs.length})</option>
            <option value="USER_AUTH">Authentication</option>
            <option value="MODEL_TRAIN">Model Training</option>
            <option value="GATE_EVALUATION">Gate Evaluation</option>
            <option value="DEPLOYMENT">Deployments</option>
          </select>
        </div>
      </div>

      <div className="space-y-2">
        {logs.length === 0 ? (
          <div className="p-8 text-center text-xs text-[var(--color-text-muted)]">
            No audit records matching your current filter.
          </div>
        ) : (
          logs.map((log) => {
            const isExpanded = expandedLogId === log.id;
            const eventName = log.event_type || log.action || 'SYSTEM_EVENT';

            return (
              <div
                key={log.id}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)] transition-colors overflow-hidden"
              >
                <div
                  onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                  className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-[var(--color-surface-hover)]"
                >
                  <div className="flex items-center space-x-3">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)]" />
                    )}
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
                      {eventName}
                    </span>
                    <span className="text-xs font-bold text-[var(--color-text)]">
                      {log.user_email || 'System Daemon'}
                    </span>
                    {log.resource_type && (
                      <span className="text-[11px] text-[var(--color-text-muted)]">
                        on {log.resource_type}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 text-xs text-[var(--color-text-muted)] font-mono">
                    {log.ip_address && <span>{log.ip_address}</span>}
                    <span>•</span>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(log.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-surface)] font-mono text-[11px] text-[var(--color-text)] overflow-x-auto">
                    <pre className="whitespace-pre-wrap">
                      {typeof log.details === 'object'
                        ? JSON.stringify(log.details, null, 2)
                        : log.details || 'No extended metadata payload.'}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
