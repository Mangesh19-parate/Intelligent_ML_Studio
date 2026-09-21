import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { UserManagementTable } from '../components/admin/UserManagementTable';
import { RolePermissionsMatrix } from '../components/admin/RolePermissionsMatrix';
import { AuditLogViewer } from '../components/admin/AuditLogViewer';

describe('Admin Console Subcomponents', () => {
  describe('UserManagementTable', () => {
    it('renders users list and handles status toggle', () => {
      const onSearch = vi.fn();
      const onRole = vi.fn();
      const onToggle = vi.fn();
      const onReset = vi.fn();
      const onOpenAdd = vi.fn();

      const users = [
        {
          id: 'u1',
          full_name: 'Alice Smith',
          email: 'alice@example.com',
          is_active: true,
          role: { role_name: 'ADMIN' },
        },
      ];

      render(
        <UserManagementTable
          users={users}
          userSearch=""
          onUserSearchChange={onSearch}
          roleFilter="ALL"
          onRoleFilterChange={onRole}
          onToggleStatus={onToggle}
          onResetPassword={onReset}
          onOpenAddUser={onOpenAdd}
        />
      );

      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
      expect(screen.getByText('Active')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Deactivate'));
      expect(onToggle).toHaveBeenCalledWith('u1', true);
    });
  });

  describe('RolePermissionsMatrix', () => {
    it('renders capability catalogs for algorithms and metrics', () => {
      const algorithms = [
        { id: '1', name: 'RandomForestRegressor', task_type: 'REGRESSION', description: 'Ensemble model' },
      ];
      const metrics = [
        { id: '1', name: 'RMSE', key: 'rmse', direction: 'MINIMIZE', description: 'Root mean squared error' },
      ];

      render(
        <RolePermissionsMatrix
          algorithms={algorithms}
          metrics={metrics}
          features={{ imputers: ['SimpleImputer'], scalers: ['StandardScaler'], encoders: [] }}
        />
      );

      expect(screen.getByText('RandomForestRegressor')).toBeInTheDocument();
      expect(screen.getByText('RMSE')).toBeInTheDocument();
      expect(screen.getByText('SimpleImputer')).toBeInTheDocument();
      expect(screen.getByText('StandardScaler')).toBeInTheDocument();
    });
  });

  describe('AuditLogViewer', () => {
    it('renders audit events and toggles details accordion', () => {
      const onFilter = vi.fn();
      const onSearch = vi.fn();

      const logs = [
        {
          id: 'log-1',
          event_type: 'MODEL_TRAIN',
          user_email: 'user@example.com',
          resource_type: 'Experiment',
          created_at: new Date().toISOString(),
          details: { folds: 5, seed: 42 },
        },
      ];

      render(
        <AuditLogViewer
          logs={logs}
          filter=""
          onFilterChange={onFilter}
          search=""
          onSearchChange={onSearch}
        />
      );

      expect(screen.getByText('MODEL_TRAIN')).toBeInTheDocument();
      expect(screen.getByText('user@example.com')).toBeInTheDocument();

      // Expand details
      fireEvent.click(screen.getByText('MODEL_TRAIN'));
      expect(screen.getByText(/"folds": 5/i)).toBeInTheDocument();
    });
  });
});
