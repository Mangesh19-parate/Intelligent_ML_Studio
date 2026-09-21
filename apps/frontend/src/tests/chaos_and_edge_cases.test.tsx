import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';

describe('Frontend Chaos & Edge Case Testing Suite', () => {
  it('prevents rapid double-clicks when button enters loading/disabled state', () => {
    const handleAction = vi.fn();
    const { rerender } = render(<Button onClick={handleAction}>Train Model</Button>);
    const button = screen.getByRole('button');

    // First click
    fireEvent.click(button);
    expect(handleAction).toHaveBeenCalledTimes(1);

    // Simulate button entering loading state
    rerender(<Button isLoading onClick={handleAction}>Train Model</Button>);
    expect(button).toBeDisabled();

    // Rapid spam clicks while in flight
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  it('safely renders special characters, XSS vectors, and Unicode strings in badges', () => {
    const xssPayload = '<script>alert("XSS")</script>';
    const unicodePayload = '🚀 測試データ / Déploiement €100%';

    const { rerender } = render(<Badge variant="neutral">{xssPayload}</Badge>);
    expect(screen.getByText(xssPayload)).toBeInTheDocument();

    rerender(<Badge variant="success">{unicodePayload}</Badge>);
    expect(screen.getByText(unicodePayload)).toBeInTheDocument();
  });

  it('handles extremely long text inputs without UI overflow breaking', () => {
    const oversizedTitle = 'A'.repeat(300);
    render(
      <Modal isOpen={true} onClose={() => {}} title={oversizedTitle}>
        <p>Modal body with normal content</p>
      </Modal>
    );

    expect(screen.getByText(oversizedTitle)).toBeInTheDocument();
  });

  it('handles rapid escape key presses on open modal without crashing', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Chaos Modal">
        <div>Content</div>
      </Modal>
    );

    for (let i = 0; i < 5; i++) {
      fireEvent.keyDown(window, { key: 'Escape' });
    }

    expect(handleClose).toHaveBeenCalledTimes(5);
  });
});
