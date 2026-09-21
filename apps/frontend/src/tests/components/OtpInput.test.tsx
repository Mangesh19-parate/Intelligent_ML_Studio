import React, { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OtpInput } from '../../components/auth/OtpInput';

const OtpInputWrapper: React.FC<{ initialValue?: string; length?: number; disabled?: boolean }> = ({
  initialValue = '',
  length = 6,
  disabled = false,
}) => {
  const [val, setVal] = useState(initialValue);
  return (
    <div>
      <OtpInput value={val} onChange={setVal} length={length} disabled={disabled} />
      <span data-testid="otp-output">{val}</span>
    </div>
  );
};

describe('OtpInput Component', () => {
  it('renders the configured number of input boxes (default 6)', () => {
    render(<OtpInputWrapper length={6} />);
    const inputs = screen.getAllByRole('textbox');
    expect(inputs).toHaveLength(6);
  });

  it('updates state when typing single digits sequentially', () => {
    render(<OtpInputWrapper length={6} />);
    const inputs = screen.getAllByRole('textbox');

    fireEvent.change(inputs[0], { target: { value: '4' } });
    expect(screen.getByTestId('otp-output')).toHaveTextContent('4');

    fireEvent.change(inputs[1], { target: { value: '8' } });
    expect(screen.getByTestId('otp-output')).toHaveTextContent('48');
  });

  it('ignores non-numeric characters', () => {
    render(<OtpInputWrapper length={6} />);
    const inputs = screen.getAllByRole('textbox');

    fireEvent.change(inputs[0], { target: { value: 'a' } });
    expect(screen.getByTestId('otp-output')).toHaveTextContent('');

    fireEvent.change(inputs[0], { target: { value: '$' } });
    expect(screen.getByTestId('otp-output')).toHaveTextContent('');
  });

  it('handles paste of full 6-digit OTP code', () => {
    render(<OtpInputWrapper length={6} />);
    const inputs = screen.getAllByRole('textbox');

    fireEvent.paste(inputs[0], {
      clipboardData: {
        getData: () => '951753',
      },
    });

    expect(screen.getByTestId('otp-output')).toHaveTextContent('951753');
  });

  it('handles paste with non-numeric characters stripped', () => {
    render(<OtpInputWrapper length={6} />);
    const inputs = screen.getAllByRole('textbox');

    fireEvent.paste(inputs[0], {
      clipboardData: {
        getData: () => '951-753',
      },
    });

    expect(screen.getByTestId('otp-output')).toHaveTextContent('951753');
  });

  it('handles backspace deletion', () => {
    render(<OtpInputWrapper initialValue="123456" length={6} />);
    const inputs = screen.getAllByRole('textbox');

    fireEvent.keyDown(inputs[5], { key: 'Backspace' });
    expect(screen.getByTestId('otp-output')).toHaveTextContent('12345');
  });

  it('disables all input boxes when disabled prop is true', () => {
    render(<OtpInputWrapper disabled={true} length={6} />);
    const inputs = screen.getAllByRole('textbox');
    inputs.forEach((input) => {
      expect(input).toBeDisabled();
    });
  });
});
