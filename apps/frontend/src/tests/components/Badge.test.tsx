import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../../components/ui/Badge';

describe('Badge Component', () => {
  it('renders badge with correct text content', () => {
    render(<Badge>LIVE</Badge>);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('renders status variants with correct classes', () => {
    const { rerender } = render(<Badge variant="success">PASSED</Badge>);
    expect(screen.getByText('PASSED')).toHaveClass('text-emerald-400');

    rerender(<Badge variant="danger">FAILED</Badge>);
    expect(screen.getByText('FAILED')).toHaveClass('text-rose-400');

    rerender(<Badge variant="warning">PENDING</Badge>);
    expect(screen.getByText('PENDING')).toHaveClass('text-amber-400');
  });

  it('renders dot indicator when hasDot is true', () => {
    const { container } = render(<Badge variant="success" hasDot>ONLINE</Badge>);
    const dot = container.querySelector('.rounded-full.bg-emerald-400');
    expect(dot).toBeInTheDocument();
  });
});
