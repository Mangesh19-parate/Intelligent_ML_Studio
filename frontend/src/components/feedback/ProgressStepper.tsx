import React from 'react';
import { Check, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface StepItem {
  id: string;
  label: string;
  description?: string;
  status: 'complete' | 'current' | 'upcoming' | 'error';
}

export interface ProgressStepperProps {
  steps: StepItem[];
  className?: string;
}

export const ProgressStepper: React.FC<ProgressStepperProps> = ({ steps, className }) => {
  return (
    <div className={cn('w-full py-3', className)}>
      <div className="flex items-center justify-between relative">
        {/* Connecting progress line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -translate-y-1/2 z-0" />

        {steps.map((step, idx) => {
          const isComplete = step.status === 'complete';
          const isCurrent = step.status === 'current';
          const isError = step.status === 'error';

          return (
            <div key={step.id} className="relative z-10 flex flex-col items-center group">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center font-semibold text-xs border-2 transition-all duration-200 shadow-md',
                  isComplete && 'bg-emerald-500 border-emerald-500 text-white',
                  isCurrent && 'bg-indigo-600 border-indigo-400 text-white ring-4 ring-indigo-500/20',
                  isError && 'bg-rose-600 border-rose-500 text-white',
                  step.status === 'upcoming' &&
                    'bg-slate-900 border-slate-700 text-slate-500'
                )}
              >
                {isComplete ? (
                  <Check className="w-4 h-4" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : isError ? (
                  <AlertCircle className="w-4 h-4" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  'mt-2 text-xs font-medium text-center max-w-[90px] truncate',
                  isCurrent && 'text-indigo-400 font-semibold',
                  isComplete && 'text-slate-300',
                  isError && 'text-rose-400',
                  step.status === 'upcoming' && 'text-slate-500'
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
