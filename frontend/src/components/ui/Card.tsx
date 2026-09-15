import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'interactive' | 'elevated' | 'bordered';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
  ...props
}) => {
  const baseStyles = 'rounded-xl transition-all duration-200';

  const variantStyles = {
    default: 'bg-slate-900/70 border border-slate-800 backdrop-blur-sm text-slate-100',
    interactive:
      'bg-slate-900/70 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-850 cursor-pointer text-slate-100 shadow-sm hover:shadow-md hover:shadow-indigo-500/5',
    elevated: 'bg-slate-900 border border-slate-750 shadow-xl shadow-black/40 text-slate-100',
    bordered: 'bg-transparent border border-slate-800 text-slate-100',
  };

  const paddingStyles = {
    none: 'p-0',
    sm: 'p-3.5',
    md: 'p-5',
    lg: 'p-7',
  };

  return (
    <div
      className={cn(baseStyles, variantStyles[variant], paddingStyles[padding], className)}
      {...props}
    >
      {children}
    </div>
  );
};
