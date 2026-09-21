import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  runId?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Operation Failed',
  message,
  runId,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-5 rounded-xl border border-rose-500/20 bg-rose-500/5 text-slate-100 flex flex-col gap-3',
        className
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 shrink-0">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold text-rose-300">{title}</h4>
            {runId && (
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono border border-slate-700">
                ID: {runId}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-300 leading-relaxed break-words">
            {message}
          </p>
        </div>
      </div>

      {onRetry && (
        <div className="flex justify-end pt-2 border-t border-rose-500/10">
          <Button
            variant="danger"
            size="sm"
            onClick={onRetry}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Retry Action
          </Button>
        </div>
      )}
    </div>
  );
};
