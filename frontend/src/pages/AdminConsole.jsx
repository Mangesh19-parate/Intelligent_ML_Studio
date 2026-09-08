import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Users,
  Key,
  Database,
  Search,
  Plus,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Cpu,
  Layers,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Check,
  X,
  FileText,
  Clock,
  Filter,
  RefreshCw,
  Sparkles,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { adminApi } from '../api/client';

export const AdminConsole = () => {
  const [activeTab, setActiveTab] = useState('users'); // 'users' | 'catalog' | 'audits'

  // Users State
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [selectedUser, setSelectedUser] = useState(null);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserForm, setNewUserForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role_name: 'ML_ENGINEER',
  });
  const [userError, setUserError] = useState('');
  const [userSuccess, setUserSuccess] = useState('');

  // Catalog State
  const [algorithms, setAlgorithms] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [features, setFeatures] = useState(null);
  const [catalogTaskFilter, setCatalogTaskFilter] = useState('ALL');
  const [loadingCatalog, setLoadingCatalog] = useState(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditFilter, setAuditFilter] = useState('');
  const [auditSearch, setAuditSearch] = useState('');
  const [loadingAudits, setLoadingAudits] = useState(false);
  const [expandedLogId, setExpandedLogId] = useState(null);

  // Fetch Users
  const fetchUsers = async () => {
    setLoadingUsers(true);
    setUserError('');
    try {
      const res = await adminApi.getUsers();
      setUsers(res.data);
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to fetch users');
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
      setAlgorithms(algoRes.data);
      setMetrics(metricRes.data);
      setFeatures(featRes.data);
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
      setAuditLogs(res.data);
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

  useEffect(() => {
    if (activeTab === 'audits') {
      const timer = setTimeout(() => {
        fetchAuditLogs();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [auditFilter, auditSearch]);

  // User Actions
  const handleCreateUser = async (e) => {
    e.preventDefault();
    setUserError('');
    try {
      await adminApi.createUser(newUserForm);
      setUserSuccess(`User ${newUserForm.email} created successfully`);
      setShowAddUserModal(false);
      setNewUserForm({ full_name: '', email: '', password: '', role_name: 'ML_ENGINEER' });
      fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await adminApi.updateUser(userId, { role_name: newRole });
      fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to update user role');
    }
  };

  const handleStatusToggle = async (userId, currentStatus) => {
    try {
      await adminApi.updateUser(userId, { is_active: !currentStatus });
      fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to toggle status');
    }
  };

  const handleSetOverride = async (userId, permissionKey, isGranted) => {
    try {
      await adminApi.setPermissionOverride(userId, permissionKey, isGranted);
      fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to update override');
    }
  };

  const handleDeleteOverride = async (userId, permissionKey) => {
    try {
      await adminApi.deletePermissionOverride(userId, permissionKey);
      fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || 'Failed to reset override');
    }
  };

  const ROLES = ['ADMIN', 'ML_ENGINEER', 'DATA_STEWARD', 'DEPLOYMENT_MANAGER', 'VIEWER'];
  const PERMISSIONS = ['READ', 'EDIT_DATA', 'TRAIN', 'DEPLOY', 'MANAGE_USERS', 'EXPORT'];

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase());
    const matchesRole = roleFilter === 'ALL' || u.role_name === roleFilter;
    return matchesSearch && matchesRole;
  });

  const filteredAlgorithms = algorithms.filter((a) => {
    if (catalogTaskFilter === 'ALL') return true;
    return a.task_type === catalogTaskFilter;
  });

  const filteredMetrics = metrics.filter((m) => {
    if (catalogTaskFilter === 'ALL') return true;
    return m.task_type === catalogTaskFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-[var(--color-border)] gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold text-rose-500 uppercase tracking-wider mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Admin Restricted Area</span>
            <span>&bull;</span>
            <span>Governance & Security Control</span>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-text">System Administration Console</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Manage system users, assign role bundles, configure granular per-user DEPLOY overrides, inspect catalog metadata, and review unified governance audit trails.
          </p>
        </div>

        {/* Global Tab Navigation */}
        <div className="flex items-center bg-[var(--color-surface)] p-1.5 rounded-xl border border-[var(--color-border)] shadow-sm shrink-0">
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer ${
              activeTab === 'users'
                ? 'bg-rose-600 text-white shadow-md'
                : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>User Management</span>
          </button>
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer ${
              activeTab === 'catalog'
                ? 'bg-rose-600 text-white shadow-md'
                : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Algorithm & Metric Catalog</span>
          </button>
          <button
            onClick={() => setActiveTab('audits')}
            className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer ${
              activeTab === 'audits'
                ? 'bg-rose-600 text-white shadow-md'
                : 'text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)]'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Governance Audit Logs</span>
          </button>
        </div>
      </div>

      {userError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{userError}</span>
        </div>
      )}

      {userSuccess && (
        <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{userSuccess}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: USER MANAGEMENT & PER-USER DEPLOY OVERRIDES                         */}
      {/* ========================================================================= */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm">
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-72">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="text"
                  placeholder="Search by user name or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full pl-9.5 pr-4 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-text focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="px-3 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-medium text-text focus:outline-none"
              >
                <option value="ALL">All Roles</option>
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto justify-end">
              <button
                onClick={fetchUsers}
                className="p-2 rounded-xl border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
                title="Refresh Directory"
              >
                <RefreshCw className={`w-4 h-4 ${loadingUsers ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={() => setShowAddUserModal(true)}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center space-x-1.5 shadow-md transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Add New User</span>
              </button>
            </div>
          </div>

          {/* User Directory Table */}
          <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-surface-hover)]/30 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">Platform User Directory & Per-User DEPLOY Override</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Click on any user row to configure granular permission grants and revocations.
                </p>
              </div>
              <span className="text-xs font-bold text-[var(--color-text-muted)] bg-[var(--color-bg)] px-2.5 py-1 rounded-full border border-[var(--color-border)]">
                {filteredUsers.length} Users
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">
                    <th className="py-3 px-4">User Details</th>
                    <th className="py-3 px-4">Assigned Role</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4">DEPLOY Permission Status</th>
                    <th className="py-3 px-4 text-right">Overrides & Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {filteredUsers.map((u) => {
                    const deployOverride = u.permission_overrides?.find((o) => o.permission_key === 'DEPLOY');
                    const hasDeploy = u.effective_permissions?.includes('DEPLOY');

                    return (
                      <React.Fragment key={u.id}>
                        <tr className="hover:bg-[var(--color-surface-hover)]/40 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-rose-500 to-indigo-500 text-white font-black text-xs flex items-center justify-center shrink-0">
                                {u.full_name?.charAt(0)?.toUpperCase() || 'U'}
                              </div>
                              <div>
                                <div className="font-bold text-text">{u.full_name}</div>
                                <div className="text-[11px] text-[var(--color-text-muted)] font-mono">{u.email}</div>
                              </div>
                            </div>
                          </td>

                          <td className="py-3.5 px-4">
                            <select
                              value={u.role_name}
                              onChange={(e) => handleRoleChange(u.id, e.target.value)}
                              className="px-2.5 py-1 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-semibold text-text focus:outline-none cursor-pointer"
                            >
                              {ROLES.map((r) => (
                                <option key={r} value={r}>{r}</option>
                              ))}
                            </select>
                          </td>

                          <td className="py-3.5 px-4 text-center">
                            <button
                              onClick={() => handleStatusToggle(u.id, u.is_active)}
                              className={`px-2.5 py-1 rounded-full text-[11px] font-bold border transition-colors cursor-pointer ${
                                u.is_active
                                  ? 'bg-teal-500/10 border-teal-500/30 text-teal-400'
                                  : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                              }`}
                            >
                              {u.is_active ? 'ACTIVE' : 'INACTIVE'}
                            </button>
                          </td>

                          {/* DEPLOY Specific Override Column */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center space-x-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-bold flex items-center space-x-1 ${
                                  hasDeploy
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                                }`}
                              >
                                {hasDeploy ? <Check className="w-3 h-3 text-emerald-400" /> : <X className="w-3 h-3 text-slate-400" />}
                                <span>{hasDeploy ? 'CAN DEPLOY' : 'NO DEPLOY'}</span>
                              </span>

                              {deployOverride && (
                                <span
                                  className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                                    deployOverride.is_granted
                                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                  }`}
                                >
                                  {deployOverride.is_granted ? 'Override: Granted' : 'Override: Revoked'}
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end space-x-2">
                              {/* Quick DEPLOY override toggle */}
                              {!deployOverride ? (
                                <button
                                  onClick={() => handleSetOverride(u.id, 'DEPLOY', !hasDeploy)}
                                  className="px-2.5 py-1 rounded-lg bg-[var(--color-bg)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[11px] font-semibold text-text transition-colors cursor-pointer"
                                  title="Toggle DEPLOY override for this specific user"
                                >
                                  {hasDeploy ? 'Revoke DEPLOY' : 'Grant DEPLOY'}
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleDeleteOverride(u.id, 'DEPLOY')}
                                  className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-[11px] font-semibold text-amber-400 flex items-center space-x-1 transition-colors cursor-pointer"
                                  title="Reset DEPLOY permission back to Role Default"
                                >
                                  <RotateCcw className="w-3 h-3" />
                                  <span>Reset DEPLOY</span>
                                </button>
                              )}

                              <button
                                onClick={() => setSelectedUser(selectedUser?.id === u.id ? null : u)}
                                className="p-1.5 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] hover:text-text transition-colors cursor-pointer"
                                title="Manage all permissions"
                              >
                                <Sliders className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>

                        {/* Granular Permissions Drawer */}
                        {selectedUser?.id === u.id && (
                          <tr className="bg-[var(--color-bg)]/80">
                            <td colSpan="5" className="p-4 border-y border-[var(--color-border)]">
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-bold text-text">
                                    Granular Permission Overrides for {u.full_name} ({u.email})
                                  </span>
                                  <span className="text-[11px] text-[var(--color-text-muted)]">
                                    Overrides take precedence over the role baseline ({u.role_name})
                                  </span>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                                  {PERMISSIONS.map((perm) => {
                                    const override = u.permission_overrides?.find((o) => o.permission_key === perm);
                                    const isEffective = u.effective_permissions?.includes(perm);

                                    return (
                                      <div
                                        key={perm}
                                        className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2 flex flex-col justify-between"
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="font-mono text-xs font-bold text-text">{perm}</span>
                                          {isEffective ? (
                                            <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />
                                          ) : (
                                            <XCircle className="w-3.5 h-3.5 text-slate-500" />
                                          )}
                                        </div>

                                        <div className="text-[10px] text-[var(--color-text-muted)]">
                                          {override ? (
                                            <span className={override.is_granted ? 'text-teal-400 font-bold' : 'text-rose-400 font-bold'}>
                                              {override.is_granted ? 'Explicit GRANT' : 'Explicit REVOKE'}
                                            </span>
                                          ) : (
                                            <span>Role Default</span>
                                          )}
                                        </div>

                                        <div className="flex items-center space-x-1 pt-1 border-t border-[var(--color-border)]">
                                          <button
                                            onClick={() => handleSetOverride(u.id, perm, true)}
                                            className="flex-1 py-0.5 rounded bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 font-bold text-[10px] cursor-pointer"
                                            title="Grant permission"
                                          >
                                            +
                                          </button>
                                          <button
                                            onClick={() => handleSetOverride(u.id, perm, false)}
                                            className="flex-1 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 font-bold text-[10px] cursor-pointer"
                                            title="Revoke permission"
                                          >
                                            -
                                          </button>
                                          {override && (
                                            <button
                                              onClick={() => handleDeleteOverride(u.id, perm)}
                                              className="p-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-[10px] cursor-pointer"
                                              title="Reset to role default"
                                            >
                                              <RotateCcw className="w-2.5 h-2.5" />
                                            </button>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: ALGORITHM & METRIC CATALOG                                          */}
      {/* ========================================================================= */}
      {activeTab === 'catalog' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex items-center justify-between p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                Filter Task Suite:
              </span>
              {['ALL', 'REGRESSION', 'CLASSIFICATION'].map((task) => (
                <button
                  key={task}
                  onClick={() => setCatalogTaskFilter(task)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    catalogTaskFilter === task
                      ? 'bg-rose-600 text-white shadow-sm'
                      : 'bg-[var(--color-bg)] text-[var(--color-text-muted)] hover:text-text border border-[var(--color-border)]'
                  }`}
                >
                  {task}
                </button>
              ))}
            </div>

            <button
              onClick={fetchCatalog}
              className="p-2 rounded-xl border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
              title="Refresh Catalog"
            >
              <RefreshCw className={`w-4 h-4 ${loadingCatalog ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Algorithms Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-rose-500" />
              <h2 className="text-base font-bold text-text">Canonical Algorithm Suite (§2.8, §7)</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredAlgorithms.map((algo) => (
                <div
                  key={algo.id}
                  className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-extrabold text-text">{algo.display_name}</span>
                      <div className="flex items-center space-x-1.5">
                        {algo.is_baseline && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 uppercase">
                            Baseline
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 uppercase">
                          {algo.task_type}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {algo.description}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-[var(--color-border)] flex items-center justify-between text-[11px] font-mono text-[var(--color-text-muted)]">
                    <span className="truncate">{algo.sklearn_class}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics Section */}
          <div className="space-y-3 pt-4">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-rose-500" />
              <h2 className="text-base font-bold text-text">Canonical Metric Catalog & Optimization Rules (§2.9)</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {filteredMetrics.map((m) => (
                <div
                  key={m.id}
                  className="p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black text-text font-mono">{m.id.toUpperCase()}</span>
                    {m.is_default && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-500/10 text-teal-400 border border-teal-500/30">
                        Default
                      </span>
                    )}
                  </div>

                  <div className="text-xs font-semibold text-[var(--color-text)]">
                    {m.display_name}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)] text-[11px]">
                    <span className="text-[var(--color-text-muted)]">{m.task_type}</span>
                    {m.direction && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center space-x-1 ${
                          m.direction === 'MINIMIZE'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        }`}
                      >
                        {m.direction === 'MINIMIZE' ? <ArrowDownRight className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                        <span>{m.direction}</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Feature Selection Heuristics */}
          {features && (
            <div className="p-5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <h3 className="text-sm font-bold text-text">Feature Selection Defaults & Heuristics (§2.7, §8)</h3>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <div className="text-[var(--color-text-muted)] text-[10px] uppercase font-bold">Strategy</div>
                  <div className="text-text font-bold mt-1">{features.strategy}</div>
                </div>
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <div className="text-[var(--color-text-muted)] text-[10px] uppercase font-bold">Alpha (Top %)</div>
                  <div className="text-text font-bold mt-1">{(features.alpha * 100).toFixed(0)}%</div>
                </div>
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <div className="text-[var(--color-text-muted)] text-[10px] uppercase font-bold">Min Selectors Required</div>
                  <div className="text-text font-bold mt-1">{features.min_applied_methods} of {features.active_methods.length} methods</div>
                </div>
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <div className="text-[var(--color-text-muted)] text-[10px] uppercase font-bold">Feature Retention Limits</div>
                  <div className="text-text font-bold mt-1">{features.k_min} min - {features.k_max} max</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: SYSTEM AUDIT LOGS & GOVERNANCE                                      */}
      {/* ========================================================================= */}
      {activeTab === 'audits' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm">
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-80">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <input
                  type="text"
                  placeholder="Search audit trail by summary, ID, or status..."
                  value={auditSearch}
                  onChange={(e) => setAuditSearch(e.target.value)}
                  className="w-full pl-9.5 pr-4 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-text focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              <select
                value={auditFilter}
                onChange={(e) => setAuditFilter(e.target.value)}
                className="px-3 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-medium text-text focus:outline-none"
              >
                <option value="">All Event Types</option>
                <option value="GATE_EVALUATION">Deployment Gate Evaluations</option>
                <option value="INFERENCE_REQUEST">Inference Requests</option>
                <option value="VALIDATION_FAILURE">Validation Failures</option>
                <option value="PERMISSION_OVERRIDE">Permission Overrides</option>
              </select>
            </div>

            <button
              onClick={fetchAuditLogs}
              className="p-2 rounded-xl border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-text hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
              title="Refresh Audit Trail"
            >
              <RefreshCw className={`w-4 h-4 ${loadingAudits ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Audit Logs Stream */}
          <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-surface-hover)]/30 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">Multi-Entity Governance Audit Trail</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  Immutable audit records tracking deployment gates, real-time predictions, validation failures, and user RBAC overrides.
                </p>
              </div>
              <span className="text-xs font-bold text-[var(--color-text-muted)] bg-[var(--color-bg)] px-2.5 py-1 rounded-full border border-[var(--color-border)]">
                {auditLogs.length} Events
              </span>
            </div>

            {auditLogs.length === 0 ? (
              <div className="p-12 text-center text-xs text-[var(--color-text-muted)]">
                No audit events found matching the criteria.
              </div>
            ) : (
              <div className="divide-y divide-[var(--color-border)]">
                {auditLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;

                  return (
                    <div key={log.id} className="p-4 hover:bg-[var(--color-surface-hover)]/30 transition-colors space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center space-x-3">
                          <span
                            className={`px-2.5 py-1 rounded text-[10px] font-extrabold uppercase tracking-wider border ${
                              log.event_type === 'GATE_EVALUATION'
                                ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                                : log.event_type === 'INFERENCE_REQUEST'
                                ? 'bg-teal-500/10 text-teal-400 border-teal-500/30'
                                : log.event_type === 'VALIDATION_FAILURE'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            }`}
                          >
                            {log.event_type}
                          </span>

                          <span className="text-xs font-bold text-text">{log.summary}</span>
                        </div>

                        <div className="flex items-center space-x-3 text-[11px] text-[var(--color-text-muted)]">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                              log.status === 'PASSED' || log.status === 'SUCCESS' || log.status === 'GRANT'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            }`}
                          >
                            {log.status}
                          </span>
                          <span className="font-mono">{new Date(log.timestamp).toLocaleString()}</span>
                          <button
                            onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                            className="p-1 rounded hover:bg-[var(--color-surface-hover)] text-text cursor-pointer"
                            title="Inspect JSON details"
                          >
                            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </div>

                      {/* Expandable JSON details */}
                      {isExpanded && (
                        <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-mono text-text space-y-1">
                          <div className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase">Metadata Payload:</div>
                          <pre className="overflow-x-auto text-[11px]">{JSON.stringify(log.details, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--color-border)]">
              <h3 className="text-base font-bold text-text">Create Platform User</h3>
              <button
                onClick={() => setShowAddUserModal(false)}
                className="p-1 rounded-lg text-[var(--color-text-muted)] hover:text-text cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="font-semibold text-text">Full Name</label>
                <input
                  type="text"
                  required
                  value={newUserForm.full_name}
                  onChange={(e) => setNewUserForm({ ...newUserForm, full_name: e.target.value })}
                  placeholder="Jane Doe"
                  className="w-full px-3.5 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-text">Email Address</label>
                <input
                  type="email"
                  required
                  value={newUserForm.email}
                  onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
                  placeholder="jane.doe@company.com"
                  className="w-full px-3.5 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-text">Initial Password</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newUserForm.password}
                  onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })}
                  placeholder="Min 6 characters"
                  className="w-full px-3.5 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-text">Assigned Role</label>
                <select
                  value={newUserForm.role_name}
                  onChange={(e) => setNewUserForm({ ...newUserForm, role_name: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-text focus:outline-none"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[var(--color-border)]">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="px-4 py-2 rounded-xl border border-[var(--color-border)] text-text hover:bg-[var(--color-surface-hover)] font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-md cursor-pointer"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminConsole;
