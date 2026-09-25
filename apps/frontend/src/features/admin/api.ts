import { httpClient } from '../../shared/api/httpClient';
import { User, AuditLogRecord } from '../../types/api';

export const adminApi = {
  getUsers: async (): Promise<User[]> => {
    const res = await httpClient.get<User[]>('/admin/users');
    return res.data;
  },

  createUser: async (payload: { email: string; full_name?: string; role_name: string; password?: string }): Promise<User> => {
    const res = await httpClient.post<User>('/admin/users', payload);
    return res.data;
  },

  updateUser: async (userId: string, payload: Partial<User>): Promise<User> => {
    const res = await httpClient.patch<User>(`/admin/users/${userId}`, payload);
    return res.data;
  },

  updateUserStatus: async (userId: string, isActive: boolean): Promise<User> => {
    const res = await httpClient.patch<User>(`/admin/users/${userId}`, { is_active: isActive });
    return res.data;
  },

  resetUserPassword: async (userId: string): Promise<{ message: string; temporary_password?: string; email?: string }> => {
    const res = await httpClient.post<{ message: string; temporary_password?: string; email?: string }>(`/admin/users/${userId}/reset-password`);
    return res.data;
  },

  setPermissionOverride: async (userId: string, permissionKey: string, isGranted: boolean): Promise<void> => {
    await httpClient.put(`/admin/users/${userId}/overrides`, {
      permission_key: permissionKey,
      is_granted: isGranted,
    });
  },

  deletePermissionOverride: async (userId: string, permissionKey: string): Promise<void> => {
    await httpClient.delete(`/admin/users/${userId}/overrides/${permissionKey}`);
  },

  getAuditLogs: async (eventType = '', search = '', limit = 100): Promise<AuditLogRecord[]> => {
    let url = `/admin/audit-logs?limit=${limit}`;
    if (eventType) url += `&event_type=${encodeURIComponent(eventType)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const res = await httpClient.get<AuditLogRecord[]>(url);
    return res.data;
  },
};
