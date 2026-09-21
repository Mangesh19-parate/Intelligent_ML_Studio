import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ToastProvider, useToast } from '../../context/ToastContext';

const TestComponent = () => {
  const { toast } = useToast();
  return (
    <div>
      <button onClick={() => toast.success('Model Deployed', 'Endpoint is LIVE')}>
        Trigger Success Toast
      </button>
      <button onClick={() => toast.error('Training Failed', 'Worker timeout')}>
        Trigger Error Toast
      </button>
    </div>
  );
};

describe('Toast Notification System', () => {
  it('renders success toast when triggered', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Success Toast'));

    expect(screen.getByText('Model Deployed')).toBeInTheDocument();
    expect(screen.getByText('Endpoint is LIVE')).toBeInTheDocument();
  });

  it('renders error toast when triggered and allows dismiss', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Error Toast'));

    expect(screen.getByText('Training Failed')).toBeInTheDocument();
    expect(screen.getByText('Worker timeout')).toBeInTheDocument();

    const dismissBtn = screen.getByRole('button', { name: /dismiss toast/i });
    fireEvent.click(dismissBtn);

    expect(screen.queryByText('Training Failed')).not.toBeInTheDocument();
  });
});
