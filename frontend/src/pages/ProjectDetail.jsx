import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { projectApi, datasetApi } from '../api/client';
import {
  Upload,
  Database,
  ArrowLeft,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  Info,
  Clock
} from 'lucide-react';

export const ProjectDetail = () => {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [columns, setColumns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const projRes = await projectApi.get(id);
      setProject(projRes.data);

      const dsRes = await datasetApi.listVersions(id);
      setDatasets(dsRes.data);

      if (dsRes.data.length > 0) {
        const latest = dsRes.data[0];
        setSelectedDataset(latest);
        const colRes = await datasetApi.getColumns(latest.id);
        setColumns(colRes.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleSelectDataset = async (dataset) => {
    setSelectedDataset(dataset);
    try {
      const colRes = await datasetApi.getColumns(dataset.id);
      setColumns(colRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const res = await datasetApi.upload(id, file);
      // Reload versions and set new uploaded dataset as active
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload and structural parse failed');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="h-64 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Nav Back */}
      <div className="flex items-center space-x-3">
        <Link
          to="/dashboard"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[var(--color-text-muted)] hover:text-text"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Projects</span>
        </Link>
      </div>

      {/* Project Header Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-extrabold text-text">{project?.project_name}</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text-muted)]">
                {project?.task_type}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-[var(--color-text-muted)]">
              {project?.target_column && (
                <span>Target Column: <strong className="text-text font-mono">{project.target_column}</strong></span>
              )}
              <span>Pipeline Stage: <strong className="text-emerald-600 dark:text-emerald-400">{project?.pipeline_stage}</strong></span>
              <span>Dataset Versions: <strong className="text-text">{datasets.length}</strong></span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <label className="cursor-pointer inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all">
              <Upload className="w-4 h-4" />
              <span>{uploading ? 'Processing & Validating...' : 'Upload Dataset'}</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.json"
                className="hidden"
                disabled={uploading}
                onChange={(e) => handleFileUpload(e.target.files?.[0])}
              />
            </label>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Sixth Invariant Info Callout */}
      <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15 text-xs text-indigo-900 dark:text-indigo-200 flex items-start space-x-3">
        <Info className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-text">Sixth Invariant Enforced: </strong>
          Dataset upload performs strictly structural dtype inference (`NUMERIC`, `CATEGORICAL`, `DATETIME`, `MIXED`) with row/column counts, unique counts, and missing percentages. No profiling, correlations, health scoring, or task-type guessing occurs before the locked test partition is established on Day 2.
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left: Version History & Upload Drag Zone */}
        <div className="space-y-6">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
            <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--color-text-muted)] mb-4">
              Version History
            </h3>
            {datasets.length === 0 ? (
              <p className="text-xs text-[var(--color-text-muted)] italic">No datasets uploaded yet.</p>
            ) : (
              <div className="space-y-2">
                {datasets.map((ds) => (
                  <button
                    key={ds.id}
                    onClick={() => handleSelectDataset(ds)}
                    className={`w-full text-left p-3 rounded-xl border text-xs transition-all flex items-center justify-between cursor-pointer ${
                      selectedDataset?.id === ds.id
                        ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)] font-semibold text-[var(--color-accent)]'
                        : 'bg-[var(--color-bg)] border-[var(--color-border)] text-text hover:bg-[var(--color-surface-hover)]'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <FileSpreadsheet className="w-4 h-4 shrink-0" />
                      <span>Version {ds.version_number}</span>
                    </div>
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {ds.row_count} rows
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Upload Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFileUpload(e.dataTransfer.files?.[0]);
            }}
            className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all ${
              dragOver
                ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5'
                : 'border-[var(--color-border)] bg-[var(--color-surface)]'
            }`}
          >
            <Upload className="w-8 h-8 mx-auto text-[var(--color-text-muted)] mb-2" />
            <p className="text-xs font-semibold text-text">Drag & drop dataset</p>
            <p className="text-[11px] text-[var(--color-text-muted)] mt-1">
              Supports .csv, .xlsx, .json
            </p>
          </div>
        </div>

        {/* Right: Structural Schema Viewer */}
        <div className="lg:col-span-3">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-sm overflow-hidden">
            <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">
                  Structural Schema Metadata {selectedDataset && `(Version ${selectedDataset.version_number})`}
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {selectedDataset
                    ? `${selectedDataset.row_count} rows × ${selectedDataset.column_count} columns`
                    : 'Select or upload a dataset to inspect structural schema'}
                </p>
              </div>
            </div>

            {columns.length === 0 ? (
              <div className="text-center py-16 text-xs text-[var(--color-text-muted)]">
                No column metadata available. Upload a dataset to begin.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--color-bg)] border-b border-[var(--color-border)] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="px-6 py-3.5">Column Name</th>
                      <th className="px-6 py-3.5">Inferred DType</th>
                      <th className="px-6 py-3.5">Unique Count</th>
                      <th className="px-6 py-3.5">Missing (%)</th>
                      <th className="px-6 py-3.5">Role</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {columns.map((col) => (
                      <tr key={col.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                        <td className="px-6 py-4 font-mono font-semibold text-text">
                          {col.column_name}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                            col.data_type === 'NUMERIC'
                              ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                              : col.data_type === 'DATETIME'
                              ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                              : col.data_type === 'CATEGORICAL'
                              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                          }`}>
                            {col.data_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-mono text-text">
                          {col.unique_count.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 font-mono text-text">
                          {col.missing_percentage}%
                        </td>
                        <td className="px-6 py-4">
                          {col.is_target ? (
                            <span className="px-2 py-0.5 rounded-full bg-indigo-500/15 text-[var(--color-accent)] font-bold text-[10px] border border-indigo-500/20">
                              TARGET
                            </span>
                          ) : (
                            <span className="text-[var(--color-text-muted)] text-[11px]">Feature</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
