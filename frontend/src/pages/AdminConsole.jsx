import React from 'react';
import { ShieldAlert, Users, Key, Server, Lock } from 'lucide-react';

export const AdminConsole = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-5 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-rose-500 uppercase tracking-wider mb-1">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Admin Restricted Area</span>
            <span>&bull;</span>
            <span>ADMIN Role Required</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-text">System Administration & RBAC</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Manage system users, assign role bundles, configure granular permission overrides, and inspect audit activity logs.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center">
            <Users className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">User Directory</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            View all registered platform users, activate/deactivate accounts, and inspect assigned roles.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
            <Key className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">Permission Overrides</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Grant or revoke specific permission keys (READ, EDIT_DATA, TRAIN, DEPLOY, EXPORT) per user.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
            <Server className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-text">System Diagnostics</h3>
          <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
            Verify database health, git commit code version synchronization, and system resource limits.
          </p>
        </div>
      </div>
    </div>
  );
};
