import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { CommandPalette } from '../../components/navigation/CommandPalette';

// Mock ProjectContext
vi.mock('../../context/ProjectContext', () => ({
  useProject: () => ({
    projects: [
      {
        id: '11111111-1111-1111-1111-111111111111',
        project_name: 'Credit Risk Model',
        task_type: 'CLASSIFICATION',
        pipeline_stage: 'TRAINED',
      },
    ],
    selectProject: vi.fn(),
  }),
}));

describe('CommandPalette Component', () => {
  it('does not render when isOpen is false', () => {
    render(
      <BrowserRouter>
        <CommandPalette isOpen={false} onClose={() => {}} />
      </BrowserRouter>
    );
    expect(screen.queryByPlaceholderText(/type a command/i)).not.toBeInTheDocument();
  });

  it('renders search input and commands when isOpen is true', () => {
    render(
      <BrowserRouter>
        <CommandPalette isOpen={true} onClose={() => {}} />
      </BrowserRouter>
    );
    expect(screen.getByPlaceholderText(/type a command/i)).toBeInTheDocument();
    expect(screen.getByText('Upload Tabular Dataset')).toBeInTheDocument();
    expect(screen.getByText('Launch Model Training')).toBeInTheDocument();
    expect(screen.getByText('Credit Risk Model')).toBeInTheDocument();
  });

  it('filters actions by search query', () => {
    render(
      <BrowserRouter>
        <CommandPalette isOpen={true} onClose={() => {}} />
      </BrowserRouter>
    );
    const input = screen.getByPlaceholderText(/type a command/i);

    fireEvent.change(input, { target: { value: 'Training' } });
    expect(screen.getByText('Launch Model Training')).toBeInTheDocument();
    expect(screen.queryByText('Upload Tabular Dataset')).not.toBeInTheDocument();
  });

  it('calls onClose when close or escape is triggered', () => {
    const handleClose = vi.fn();
    render(
      <BrowserRouter>
        <CommandPalette isOpen={true} onClose={handleClose} />
      </BrowserRouter>
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    // Or clicking backdrop
    const backdrop = screen.getByPlaceholderText(/type a command/i).closest('.fixed');
    if (backdrop) fireEvent.click(backdrop);

    expect(handleClose).toHaveBeenCalled();
  });
});
