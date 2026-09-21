import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Breadcrumbs } from '../../components/navigation/Breadcrumbs';

// Mock ProjectContext
vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    activeProject: {
      id: '11111111-1111-1111-1111-111111111111',
      project_name: 'Churn Prediction Model',
    },
  }),
}));

describe('Breadcrumbs Component', () => {
  it('renders breadcrumb trail matching route path and project', () => {
    render(
      <MemoryRouter initialEntries={['/ml/training']}>
        <Breadcrumbs />
      </MemoryRouter>
    );

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByText('Churn Prediction Model')).toBeInTheDocument();
    expect(screen.getByText('Machine Learning')).toBeInTheDocument();
    expect(screen.getByText('Model Training')).toBeInTheDocument();
  });

  it('renders breadcrumbs for nested feature selection route', () => {
    render(
      <MemoryRouter initialEntries={['/features/selection']}>
        <Breadcrumbs />
      </MemoryRouter>
    );

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByText('Churn Prediction Model')).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
    expect(screen.getByText('Feature Selection')).toBeInTheDocument();
  });
});
