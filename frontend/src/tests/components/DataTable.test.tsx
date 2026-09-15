import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DataTable } from '../../components/ui/DataTable';

interface MockItem {
  id: string;
  name: string;
  role: string;
  score: number;
}

describe('DataTable Component', () => {
  const sampleColumns = [
    { key: 'name', header: 'User Name', sortable: true },
    { key: 'role', header: 'Role' },
    { key: 'score', header: 'CV Score', sortable: true },
  ];

  const sampleData: MockItem[] = [
    { id: '1', name: 'Alice Smith', role: 'ADMIN', score: 0.92 },
    { id: '2', name: 'Bob Jones', role: 'USER', score: 0.85 },
    { id: '3', name: 'Charlie Brown', role: 'USER', score: 0.78 },
  ];

  it('renders table headers and rows correctly', () => {
    render(<DataTable columns={sampleColumns} data={sampleData} />);
    expect(screen.getByText('User Name')).toBeInTheDocument();
    expect(screen.getByText('Role')).toBeInTheDocument();
    expect(screen.getByText('CV Score')).toBeInTheDocument();

    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('Bob Jones')).toBeInTheDocument();
    expect(screen.getByText('Charlie Brown')).toBeInTheDocument();
  });

  it('filters data via search input', () => {
    render(<DataTable columns={sampleColumns} data={sampleData} />);
    const searchInput = screen.getByPlaceholderText('Search table...');

    fireEvent.change(searchInput, { target: { value: 'Alice' } });
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.queryByText('Bob Jones')).not.toBeInTheDocument();
    expect(screen.queryByText('Charlie Brown')).not.toBeInTheDocument();
  });

  it('renders empty state when search matches nothing', () => {
    render(<DataTable columns={sampleColumns} data={sampleData} />);
    const searchInput = screen.getByPlaceholderText('Search table...');

    fireEvent.change(searchInput, { target: { value: 'NonExistent' } });
    expect(screen.getByText('No records found')).toBeInTheDocument();
  });
});
