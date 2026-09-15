import React, { useRef, useEffect } from 'react';
import { cn } from '../../lib/utils';

export interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  disabled?: boolean;
  autoFocus?: boolean;
  className?: string;
}

export const OtpInput: React.FC<OtpInputProps> = ({
  value,
  onChange,
  length = 6,
  disabled = false,
  autoFocus = true,
  className,
}) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Pad or slice string to array of characters
  const digits = Array.from({ length }, (_, i) => value[i] || '');

  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [autoFocus]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const rawVal = e.target.value.replace(/[^0-9]/g, '');
    if (!rawVal) {
      // Clear current digit
      const newDigits = [...digits];
      newDigits[index] = '';
      onChange(newDigits.join(''));
      return;
    }

    if (rawVal.length > 1) {
      // User typed or pasted multiple digits directly in one box
      const pastedDigits = rawVal.slice(0, length).split('');
      const newDigits = [...digits];
      for (let i = 0; i < length; i++) {
        if (pastedDigits[i]) {
          newDigits[i] = pastedDigits[i];
        }
      }
      onChange(newDigits.join(''));
      const nextFocus = Math.min(pastedDigits.length, length - 1);
      inputRefs.current[nextFocus]?.focus();
      return;
    }

    const char = rawVal[rawVal.length - 1];
    const newDigits = [...digits];
    newDigits[index] = char;
    onChange(newDigits.join(''));

    // Move to next input box if available
    if (index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0) {
        // Move back and clear previous box
        const newDigits = [...digits];
        newDigits[index - 1] = '';
        onChange(newDigits.join(''));
        inputRefs.current[index - 1]?.focus();
      } else {
        const newDigits = [...digits];
        newDigits[index] = '';
        onChange(newDigits.join(''));
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      e.preventDefault();
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < length - 1) {
      e.preventDefault();
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, length);
    if (!pastedData) return;

    const newDigits = [...digits];
    for (let i = 0; i < length; i++) {
      newDigits[i] = pastedData[i] || '';
    }
    onChange(newDigits.join(''));

    const nextFocusIndex = Math.min(pastedData.length, length - 1);
    inputRefs.current[nextFocusIndex]?.focus();
  };

  return (
    <div className={cn('flex items-center justify-center gap-2 sm:gap-3', className)}>
      {Array.from({ length }).map((_, index) => {
        const digit = digits[index];
        const isFilled = Boolean(digit);

        return (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={digit}
            disabled={disabled}
            onChange={(e) => handleInputChange(e, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onPaste={handlePaste}
            className={cn(
              'w-10 h-12 sm:w-12 sm:h-14 text-center text-lg sm:text-xl font-mono font-bold rounded-xl border transition-all select-all focus:outline-none',
              isFilled
                ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-text)] shadow-xs'
                : 'border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:border-[var(--color-text-muted)]',
              'focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          />
        );
      })}
    </div>
  );
};
export default OtpInput;
