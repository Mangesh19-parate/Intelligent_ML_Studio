import React, { useState } from 'react';
import { Users, Search, Plus, CheckCircle2, XCircle, RotateCcw } from 'lucide-react';
import { Button } from '../ui/Button';

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role?: {
    role_name: string;
  };
  created_at?: string;
}

interface UserManagementTableProps {
  users: UserItem[];
  userSearch: string;
  onUserSearchChange: (search: string) => void;
  roleFilter: string;
  onRoleFilterChange: (role: string) => void;
  onToggleStatus: (userId: string, currentStatus: boolean) => void;
  onResetPassword: (userId: string) => void;
  onOpenAddUser: () => void;
}

export const UserManagementTable: React.FC<UserManagementTableProps> = ({
  users,
  userSearch,
  onUserSearchChange,
  roleFilter,
  onRoleFilterChange,
  onToggleStatus,
  onResetPassword,
  onOpenAddUser,
}) => {
  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email?.toLowerCase().includes(userSearch.toLowerCase());
    const matchesRole = roleFilter === 'ALL' || u.role?.role_name === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden space-y-4 p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div className="flex items-center space-x-2">
          <Users className="w-5 h-5 text-[var(--color-accent)]" />
          <h3 className="text-sm font-bold text-[var(--color-text)]">
            Platform User Management & Access Control
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={userSearch}
              onChange={(e) => onUserSearchChange(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => onRoleFilterChange(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
          >
            <option value="ALL">All Roles ({users.length})</option>
            <option value="ADMIN">Admins Only</option>
            <option value="USER">Users Only</option>
          </select>

          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={onOpenAddUser}
            className="rounded-full font-bold shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            <span>Create User</span>
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-card)]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Email Address</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {filteredUsers.map((u) => (
              <tr key={u.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                <td className="px-4 py-3 font-bold text-[var(--color-text)]">
                  {u.full_name}
                </td>
                <td className="px-4 py-3 font-mono text-[var(--color-text-muted)]">
                  {u.email}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      u.role?.role_name === 'ADMIN'
                        ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]'
                        : 'bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
                    }`}
                  >
                    {u.role?.role_name || 'USER'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      u.is_active
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {u.is_active ? (
                      <>
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span>Active</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3 h-3 text-rose-400" />
                        <span>Suspended</span>
                      </>
                    )}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      onClick={() => onToggleStatus(u.id, u.is_active)}
                      className="px-2.5 py-1 rounded-full text-[10px] font-semibold border border-[var(--color-border)] bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text)] cursor-pointer"
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => onResetPassword(u.id)}
                      className="p-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-hover)] hover:bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-accent)] cursor-pointer"
                      title="Reset Password"
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
