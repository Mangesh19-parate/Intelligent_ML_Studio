import React, { useState } from 'react';
import { Target, HelpCircle, CheckCircle2, AlertTriangle, ArrowRight, Check } from 'lucide-react';

export const TaskTypeSelector = ({
  projectId,
  currentTaskType,
  taskTypeConfidence,
  taskTypeSuggestion,
  onTaskTypeConfirmed
}) => {
  const isAmbiguous = taskTypeSuggestion?.is_ambiguous || taskTypeConfidence === 'AMBIGUOUS' || currentTaskType === 'UNDETERMINED';
  const initialChoice = isAmbiguous
    ? ''
    : (currentTaskType && currentTaskType !== 'UNDETERMINED' ? currentTaskType : (taskTypeSuggestion?.suggested_task_type || ''));

  const [selectedType, setSelectedType] = useState(initialChoice);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleConfirm = async () => {
    if (!selectedType) {
      setError('Please select either Classification or Regression before proceeding.');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess(false);
    try {
      if (onTaskTypeConfirmed) {
        await onTaskTypeConfirmed(selectedType);
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update task type');
    } finally {
      setSaving(false);
    }
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence === 'HIGH') {
      return <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">HIGH CONFIDENCE</span>;
    }
    if (confidence === 'MEDIUM') {
      return <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">MEDIUM CONFIDENCE</span>;
    }
    return <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">AMBIGUOUS - MANUAL CHOICE REQUIRED</span>;
  };

  return (
    <div className={`border rounded-2xl p-6 shadow-sm relative overflow-hidden transition-all duration-300 ${
      isAmbiguous && !currentTaskType?.replace('UNDETERMINED', '')
        ? 'bg-amber-500/5 border-amber-500/40 ring-1 ring-amber-500/20'
        : 'bg-[var(--color-surface)] border-[var(--color-border)]'
    }`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[var(--color-accent-soft)] border border-[var(--color-accent)]/20 rounded-xl text-[var(--color-accent)]">
            <Target className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-bold text-[var(--color-text)] flex items-center gap-2.5">
              Task-Type Detection (Stage B)
              {getConfidenceBadge(taskTypeSuggestion?.confidence || taskTypeConfidence)}
            </h4>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Distributional inference on target column: <code className="text-[var(--color-accent)] bg-[var(--color-surface-hover)] px-1.5 py-0.5 rounded font-mono font-bold">{taskTypeSuggestion?.target_column || 'Target'}</code>
            </p>
          </div>
        </div>

        {currentTaskType && currentTaskType !== 'UNDETERMINED' && (
          <div className="flex items-center gap-2 bg-[var(--color-surface-hover)] px-3 py-1.5 rounded-full border border-[var(--color-border)] text-xs">
            <span className="text-[var(--color-text-muted)] font-medium">Active Task Type:</span>
            <strong className="text-[var(--color-accent)] font-bold">{currentTaskType}</strong>
          </div>
        )}
      </div>

      {/* Ambiguity Callout & Supporting Numbers */}
      {isAmbiguous && (
        <div className="my-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-bold text-amber-800 dark:text-amber-200">
                Distribution is Ambiguous — Explicit User Choice Required
              </h5>
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-1 leading-relaxed">
                The target column has an intermediate cardinality and ratio that sits between standard continuous and discrete thresholds. To prevent silent assumption leakage, the platform requires you to explicitly choose the modeling task.
              </p>

              {/* Supporting Numbers */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-amber-500/20 font-mono text-xs">
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-amber-500/20">
                  <span className="text-[var(--color-text-muted)] block text-[11px]">Unique Target Count:</span>
                  <strong className="text-amber-600 dark:text-amber-400 text-sm">{taskTypeSuggestion?.unique_count ?? 'N/A'}</strong>
                </div>
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-amber-500/20">
                  <span className="text-[var(--color-text-muted)] block text-[11px]">Unique / Total Ratio:</span>
                  <strong className="text-amber-600 dark:text-amber-400 text-sm">
                    {taskTypeSuggestion?.unique_ratio !== undefined ? `${(taskTypeSuggestion.unique_ratio * 100).toFixed(2)}%` : 'N/A'}
                  </strong>
                </div>
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-amber-500/20">
                  <span className="text-[var(--color-text-muted)] block text-[11px]">Sample Target Values:</span>
                  <span className="text-[var(--color-accent)] text-xs truncate block font-bold">
                    {taskTypeSuggestion?.sample_values?.slice(0, 4).join(', ') || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Radio Selection Options */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-5">
        <label
          className={`relative flex items-start gap-4 p-4 rounded-2xl border cursor-pointer transition-all duration-200 ${
            selectedType === 'CLASSIFICATION'
              ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/30'
              : 'bg-[var(--color-surface-card)] border-[var(--color-border)] hover:border-[var(--color-border-subtle)]'
          }`}
        >
          <input
            type="radio"
            name="taskType"
            value="CLASSIFICATION"
            checked={selectedType === 'CLASSIFICATION'}
            onChange={(e) => {
              setSelectedType(e.target.value);
              setError('');
            }}
            className="mt-1 text-[var(--color-accent)] focus:ring-[var(--color-accent)] h-4 w-4"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-[var(--color-text)] text-sm">Classification</span>
              {taskTypeSuggestion?.suggested_task_type === 'CLASSIFICATION' && (
                <span className="text-[10px] px-2 py-0.5 bg-[var(--color-accent)]/10 text-[var(--color-accent)] rounded-full font-bold font-mono">
                  Suggested
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-1 leading-relaxed">
              Predicts discrete category labels or binary outcomes (e.g. churn, risk level, class).
            </p>
          </div>
        </label>

        <label
          className={`relative flex items-start gap-4 p-4 rounded-2xl border cursor-pointer transition-all duration-200 ${
            selectedType === 'REGRESSION'
              ? 'bg-[var(--color-accent-soft)] border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/30'
              : 'bg-[var(--color-surface-card)] border-[var(--color-border)] hover:border-[var(--color-border-subtle)]'
          }`}
        >
          <input
            type="radio"
            name="taskType"
            value="REGRESSION"
            checked={selectedType === 'REGRESSION'}
            onChange={(e) => {
              setSelectedType(e.target.value);
              setError('');
            }}
            className="mt-1 text-[var(--color-accent)] focus:ring-[var(--color-accent)] h-4 w-4"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-[var(--color-text)] text-sm">Regression</span>
              {taskTypeSuggestion?.suggested_task_type === 'REGRESSION' && (
                <span className="text-[10px] px-2 py-0.5 bg-[var(--color-accent)]/10 text-[var(--color-accent)] rounded-full font-bold font-mono">
                  Suggested
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mt-1 leading-relaxed">
              Predicts continuous numerical quantities (e.g. price, duration, temperature, sales).
            </p>
          </div>
        </label>
      </div>

      {error && (
        <p className="text-xs text-rose-500 mb-3 font-medium flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <span className="text-xs text-[var(--color-text-muted)]">
          Task type dictates downstream feature encoding, evaluation metrics, and model search spaces.
        </span>

        <button
          onClick={handleConfirm}
          disabled={saving || !selectedType}
          className="px-5 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-full shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0"
        >
          {saving ? (
            'Saving...'
          ) : success ? (
            <>
              <Check className="w-4 h-4 text-emerald-300" />
              Confirmed
            </>
          ) : (
            <>
              Confirm Task Type
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
