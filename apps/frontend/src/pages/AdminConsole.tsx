import React, { useState, useEffect } from 'react';
import { adminApi } from '../api/client';
import {
  UserManagementTable,
  RolePermissionsMatrix,
  AuditLogViewer,
  UserItem,
  AuditLogItem,
} from '../components/admin';
import { EmptyState } from '../components/feedback/EmptyState';
import { ErrorState } from '../components/feedback/ErrorState';
import { Skeleton } from '../components/feedback/Skeleton';
import { Button } from '../components/ui/Button';
import { ShieldAlert, Users, Database, FileText, CheckCircle2, X } from 'lucide-react';

export const AdminConsole: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'catalog' | 'audits'>('users');

  // Users State
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loadingUsers, setLoadingUsers] = useState<boolean>(false);
  const [userSearch, setUserSearch] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [showAddUserModal, setShowAddUserModal] = useState<boolean>(false);
  const [newUserForm, setNewUserForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role_name: 'USER',
  });
  const [userError, setUserError] = useState<string>('');
  const [userSuccess, setUserSuccess] = useState<string>('');

  // Catalog State
  const [algorithms, setAlgorithms] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [features, setFeatures] = useState<any>(null);
  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditFilter, setAuditFilter] = useState<string>('');
  const [auditSearch, setAuditSearch] = useState<string>('');
  const [loadingAudits, setLoadingAudits] = useState<boolean>(false);

  // Fetch Users
  const fetchUsers = async () => {
    setLoadingUsers(true);
    setUserError('');
    try {
      const res = await adminApi.getUsers();
      setUsers(res.data || []);
    } catch (err: any) {
      setUserError(err.response?.data?.detail || 'Failed to fetch platform users');
    } finally {
      setLoadingUsers(false);
    }
  };

  // Fetch Catalog
  const fetchCatalog = async () => {
    setLoadingCatalog(true);
    try {
      const [algoRes, metricRes, featRes] = await Promise.all([
        adminApi.getAlgorithms(),
        adminApi.getMetrics(),
        adminApi.getFeatures(),
      ]);
      setAlgorithms(algoRes.data || []);
      setMetrics(metricRes.data || []);
      setFeatures(featRes.data || null);
    } catch (err) {
      console.error('Failed to load catalog data', err);
    } finally {
      setLoadingCatalog(false);
    }
  };

  // Fetch Audit Logs
  const fetchAuditLogs = async () => {
    setLoadingAudits(true);
    try {
      const res = await adminApi.getAuditLogs(auditFilter, auditSearch);
      setAuditLogs(res.data || []);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoadingAudits(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'catalog') fetchCatalog();
    if (activeTab === 'audits') fetchAuditLogs();
  }, [activeTab]);

  const handleToggleUserStatus = async (userId: string, currentStatus: boolean) => {
    try {
      setUserError('');
      await adminApi.updateUserStatus(userId, !currentStatus);
      setUserSuccess(`User status updated to ${!currentStatus ? 'Active' : 'Suspended'}`);
      fetchUsers();
    } catch (err: any) {
      setUserError(err.response?.data?.detail || 'Failed to update user status');
    }
  };

  const handleResetPassword = async (userId: string) => {
    try {
      setUserError('');
      const res = await adminApi.resetUserPassword(userId);
      const tempPass = res.data?.temporary_password;
      setUserSuccess(
        tempPass
          ? `Password reset successfully. Temporary password: ${tempPass}`
          : 'Password reset successfully.'
      );
    } catch (err: any) {
      setUserError(err.response?.data?.detail || 'Failed to reset password');
    }
  };


  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setUserError('');
      await adminApi.createUser(newUserForm);
      setUserSuccess(`User "${newUserForm.email}" successfully created!`);
      setShowAddUserModal(false);
      setNewUserForm({ full_name: '', email: '', password: '', role_name: 'USER' });
      fetchUsers();
    } catch (err: any) {
      setUserError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Header Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <span className="p-2 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
            <ShieldAlert className="w-5 h-5" />
          </span>
          <div>
            <h1 className="text-xl font-black text-[var(--color-text)]">
              Administration & Governance Console
            </h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Manage platform users, algorithms catalog, evaluation metrics, and immutable audit trails.
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center space-x-2 bg-[var(--color-surface-hover)] p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
              activeTab === 'users'
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Users</span>
          </button>
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
              activeTab === 'catalog'
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Capability Catalog</span>
          </button>
          <button
            onClick={() => setActiveTab('audits')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
              activeTab === 'audits'
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Audit Trail</span>
          </button>
        </div>
      </div>

      {userError && (
        <ErrorState
          title="Admin Error"
          message={userError}
          onRetry={() => setUserError('')}
        />
      )}

      {userSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{userSuccess}</span>
        </div>
      )}

      {/* Tab Panels */}
      {activeTab === 'users' && (
        loadingUsers ? (
          <Skeleton variant="rectangular" height="300px" className="rounded-2xl" />
        ) : (
          <UserManagementTable
            users={users}
            userSearch={userSearch}
            onUserSearchChange={setUserSearch}
            roleFilter={roleFilter}
            onRoleFilterChange={setRoleFilter}
            onToggleStatus={handleToggleUserStatus}
            onResetPassword={handleResetPassword}
            onOpenAddUser={() => setShowAddUserModal(true)}
          />
        )
      )}

      {activeTab === 'catalog' && (
        loadingCatalog ? (
          <Skeleton variant="rectangular" height="300px" className="rounded-2xl" />
        ) : (
          <RolePermissionsMatrix
            algorithms={algorithms}
            metrics={metrics}
            features={features}
          />
        )
      )}

      {activeTab === 'audits' && (
        loadingAudits ? (
          <Skeleton variant="rectangular" height="300px" className="rounded-2xl" />
        ) : (
          <AuditLogViewer
            logs={auditLogs}
            filter={auditFilter}
            onFilterChange={setAuditFilter}
            search={auditSearch}
            onSearchChange={setAuditSearch}
          />
        )
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <h3 className="text-base font-bold text-[var(--color-text)]">Create Platform User</h3>
              <button
                onClick={() => setShowAddUserModal(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text)] rounded-full cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Jane Doe"
                  value={newUserForm.full_name}
                  onChange={(e) => setNewUserForm({ ...newUserForm, full_name: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. jane@company.com"
                  value={newUserForm.email}
                  onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Temporary Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={newUserForm.password}
                  onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Role</label>
                <select
                  value={newUserForm.role_name}
                  onChange={(e) => setNewUserForm({ ...newUserForm, role_name: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
                >
                  <option value="USER">Standard User (Project Scoped)</option>
                  <option value="ADMIN">Platform Administrator (Global Access)</option>
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAddUserModal(false)}
                  className="rounded-full"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  className="rounded-full font-bold shadow-sm"
                >
                  Create User
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminConsole;
