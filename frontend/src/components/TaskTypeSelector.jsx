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
      return <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">HIGH CONFIDENCE</span>;
    }
    if (confidence === 'MEDIUM') {
      return <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">MEDIUM CONFIDENCE</span>;
    }
    return <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">AMBIGUOUS - MANUAL CHOICE REQUIRED</span>;
  };

  return (
    <div className={`border rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 ${
      isAmbiguous && !currentTaskType?.replace('UNDETERMINED', '')
        ? 'bg-amber-950/20 border-amber-500/40 ring-1 ring-amber-500/20'
        : 'bg-slate-900/90 border-slate-800'
    }`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-400">
            <Target className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-white flex items-center gap-2.5">
              Task-Type Detection (Stage B)
              {getConfidenceBadge(taskTypeSuggestion?.confidence || taskTypeConfidence)}
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Distributional inference on target column: <code className="text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded font-mono">{taskTypeSuggestion?.target_column || 'Target'}</code>
            </p>
          </div>
        </div>

        {currentTaskType && currentTaskType !== 'UNDETERMINED' && (
          <div className="flex items-center gap-2 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
            <span className="text-slate-400">Active Task Type:</span>
            <strong className="text-indigo-400 font-semibold">{currentTaskType}</strong>
          </div>
        )}
      </div>

      {/* Ambiguity Callout & Supporting Numbers */}
      {isAmbiguous && (
        <div className="my-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold text-amber-200">
                Distribution is Ambiguous — Explicit User Choice Required
              </h5>
              <p className="text-xs text-amber-300/90 mt-1 leading-relaxed">
                The target column has an intermediate cardinality and ratio that sits between standard continuous and discrete thresholds. To prevent silent assumption leakage, the platform requires you to explicitly choose the modeling task.
              </p>

              {/* Supporting Numbers */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-amber-500/20 font-mono text-xs">
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-amber-500/20">
                  <span className="text-slate-400 block text-[11px]">Unique Target Count:</span>
                  <strong className="text-amber-300 text-sm">{taskTypeSuggestion?.unique_count ?? 'N/A'}</strong>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-amber-500/20">
                  <span className="text-slate-400 block text-[11px]">Unique / Total Ratio:</span>
                  <strong className="text-amber-300 text-sm">
                    {taskTypeSuggestion?.unique_ratio !== undefined ? `${(taskTypeSuggestion.unique_ratio * 100).toFixed(2)}%` : 'N/A'}
                  </strong>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-amber-500/20">
                  <span className="text-slate-400 block text-[11px]">Sample Target Values:</span>
                  <span className="text-indigo-300 text-xs truncate block">
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
          className={`relative flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
            selectedType === 'CLASSIFICATION'
              ? 'bg-blue-600/10 border-blue-500 ring-1 ring-blue-500/30'
              : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
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
            className="mt-1 text-blue-500 focus:ring-blue-500 h-4 w-4 bg-slate-900 border-slate-700"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white text-sm">Classification</span>
              {taskTypeSuggestion?.suggested_task_type === 'CLASSIFICATION' && (
                <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded font-mono">
                  Suggested
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Predicts discrete category labels or binary outcomes (e.g. churn, risk level, class).
            </p>
          </div>
        </label>

        <label
          className={`relative flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
            selectedType === 'REGRESSION'
              ? 'bg-indigo-600/10 border-indigo-500 ring-1 ring-indigo-500/30'
              : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
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
            className="mt-1 text-indigo-500 focus:ring-indigo-500 h-4 w-4 bg-slate-900 border-slate-700"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white text-sm">Regression</span>
              {taskTypeSuggestion?.suggested_task_type === 'REGRESSION' && (
                <span className="text-[10px] px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded font-mono">
                  Suggested
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Predicts continuous numerical quantities (e.g. price, duration, temperature, sales).
            </p>
          </div>
        </label>
      </div>

      {error && (
        <p className="text-xs text-rose-400 mb-3 font-medium flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-slate-500">
          Task type dictates downstream feature encoding, evaluation metrics, and model search spaces.
        </span>

        <button
          onClick={handleConfirm}
          disabled={saving || !selectedType}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2"
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
