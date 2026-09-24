import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { projectApi, datasetApi, datasetSplitApi } from '../api/client';
import { useProject } from '../context/ProjectContext';
import {
  UploadZone,
  DatasetSummaryCards,
  SplitPanel,
  SchemaTable,
  DatasetItem,
  ColumnSchemaItem,
} from '../components/data';
import { EmptyState } from '../components/feedback/EmptyState';
import { ErrorState } from '../components/feedback/ErrorState';
import { Skeleton } from '../components/feedback/Skeleton';
import {
  Database,
  ArrowRight,
  CheckCircle2,
  Plus,
  FolderOpen,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { TaskType } from '../types/api';

export const DataStage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentProject, currentProjectId, projects, selectProject, refreshProjects } = useProject();

  const urlProjectId = searchParams.get('project_id');
  const activeProjectId = urlProjectId || currentProjectId;

  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetItem | null>(null);
  const [columns, setColumns] = useState<ColumnSchemaItem[]>([]);
  const [splitSummary, setSplitSummary] = useState<any>(null);
  const [devPreview, setDevPreview] = useState<any[] | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [creatingSplit, setCreatingSplit] = useState<boolean>(false);
  const [lockedTestPct, setLockedTestPct] = useState<number>(20);
  const [splitSeed, setSplitSeed] = useState<string>('42');
  const [error, setError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Quick Create Project Modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newProjectName, setNewProjectName] = useState<string>('');
  const [newTargetCol, setNewTargetCol] = useState<string>('');
  const [newTaskType, setNewTaskType] = useState<TaskType>('UNDETERMINED');
  const [creatingProject, setCreatingProject] = useState<boolean>(false);

  // Sync URL project_id with ProjectContext
  useEffect(() => {
    if (urlProjectId && urlProjectId !== currentProjectId) {
      selectProject(urlProjectId);
    } else if (!currentProjectId && projects.length > 0) {
      const firstId = String(projects[0].id);
      selectProject(firstId);
      setSearchParams({ project_id: firstId }, { replace: true });
    }
  }, [urlProjectId, currentProjectId, projects, selectProject, setSearchParams]);

  // Load dataset split and preview
  const loadSplitAndPreview = async (datasetId: string) => {
    try {
      const splitRes = await datasetSplitApi.getSplit(datasetId);
      setSplitSummary(splitRes.data);

      const previewRes = await datasetSplitApi.getDevelopmentPreview(datasetId, 10);
      const rows = previewRes.data?.preview_rows || (Array.isArray(previewRes.data) ? previewRes.data : []);
      setDevPreview(rows);
    } catch (err) {
      setSplitSummary(null);
      setDevPreview(null);
    }
  };

  // Load project details and datasets
  const loadProjectData = async (projId: string) => {
    if (!projId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError('');

      const dsRes = await datasetApi.listVersions(projId);
      const dsList = dsRes.data || [];
      setDatasets(dsList as unknown as DatasetItem[]);

      if (dsList.length > 0) {
        const latest = dsList[0];
        setSelectedDataset(latest as unknown as DatasetItem);
        const colRes = await datasetApi.getColumns(latest.id);
        setColumns((colRes.data || []) as unknown as ColumnSchemaItem[]);
        await loadSplitAndPreview(latest.id);
      } else {
        setSelectedDataset(null);
        setColumns([]);
        setSplitSummary(null);
        setDevPreview(null);
      }
    } catch (err: any) {
      console.error('Failed to load project data', err);
      setError(err.response?.data?.detail || 'Failed to load dataset details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeProjectId) {
      loadProjectData(activeProjectId);
    } else {
      setLoading(false);
    }
  }, [activeProjectId]);

  const handleSelectProject = (projId: string) => {
    selectProject(projId);
    setSearchParams({ project_id: projId });
  };

  // Handle dataset file upload
  const handleFileUpload = async (file: File) => {
    if (!activeProjectId) {
      setError('Please select or create a project first.');
      return;
    }
    try {
      setUploading(true);
      setError('');
      setSuccessMsg('');

      const formData = new FormData();
      formData.append('file', file);

      await datasetApi.upload(activeProjectId, formData);
      setSuccessMsg(`Dataset "${file.name}" uploaded and validated successfully!`);
      await loadProjectData(activeProjectId);
    } catch (err: any) {
      console.error('Upload error', err);
      setError(err.response?.data?.detail || 'Failed to upload dataset.');
    } finally {
      setUploading(false);
    }
  };

  // Handle dataset split creation
  const handleCreateSplit = async () => {
    if (!selectedDataset) return;
    try {
      setCreatingSplit(true);
      setError('');
      setSuccessMsg('');

      const payload = {
        locked_test_pct: Number(lockedTestPct),
        seed: splitSeed ? Number(splitSeed) : null,
      };

      await datasetSplitApi.createSplit(selectedDataset.id, payload);
      setSuccessMsg('Development / Locked Test partition created and cryptographically sealed!');
      await loadSplitAndPreview(selectedDataset.id);
    } catch (err: any) {
      console.error('Split creation error', err);
      setError(err.response?.data?.detail || 'Failed to create dataset partition.');
    } finally {
      setCreatingSplit(false);
    }
  };

  const handleRandomizeSeed = () => {
    setSplitSeed(Math.floor(Math.random() * 1000000).toString());
  };

  // Quick project creation
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      setCreatingProject(true);
      setError('');
      const res = await projectApi.create({
        project_name: newProjectName.trim(),
        target_column: newTargetCol.trim() || null,
        task_type: newTaskType,
      });
      setShowCreateModal(false);
      setNewProjectName('');
      setNewTargetCol('');
      setNewTaskType('UNDETERMINED');
      await refreshProjects();
      selectProject(String(res.data.id));
      navigate(`/data?project_id=${res.data.id}`);
    } catch (err: any) {
      console.error('Create project error', err);
      setError(err.response?.data?.detail || 'Failed to create project.');
    } finally {
      setCreatingProject(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-6">
      {/* Header Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent-border)]">
              <Database className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-black text-[var(--color-text)]">
              Dataset Ingestion & Locked Partitioning
            </h1>
          </div>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Ingest tabular data, inspect column roles, and establish strict developmental vs locked test boundaries.
          </p>
        </div>

        <div className="flex items-center space-x-3 flex-wrap gap-2">
          {/* Project Selector Dropdown */}
          {projects.length > 0 && (
            <div className="flex items-center gap-2 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 shadow-xs">
              <FolderOpen className="w-4 h-4 text-[var(--color-accent)]" />
              <select
                id="project-select"
                value={activeProjectId || ''}
                onChange={(e) => handleSelectProject(e.target.value)}
                className="bg-transparent text-xs font-semibold text-[var(--color-text)] border-none focus:outline-none cursor-pointer pr-2"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-[var(--color-surface)] text-[var(--color-text)]">
                    {p.project_name || (p as any).name || p.id}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="rounded-full text-xs font-bold"
          >
            <Plus className="w-4 h-4 mr-1" />
            <span>New Project</span>
          </Button>

          {selectedDataset && (
            <Link
              to={`/data-analysis?project_id=${activeProjectId}`}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-full bg-[var(--color-accent-soft)] hover:bg-[var(--color-accent)] hover:text-white text-[var(--color-accent)] text-xs font-bold transition-all border border-[var(--color-accent-border)]"
            >
              <span>Proceed to Data Profiling</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          <Skeleton variant="rectangular" height="120px" className="rounded-2xl" />
          <Skeleton variant="rectangular" height="300px" className="rounded-2xl" />
        </div>
      ) : !activeProjectId ? (
        <div className="p-6 space-y-6">
          <EmptyState
            title="No Project Selected"
            description="Create a new ML project or select an existing one to begin dataset ingestion and partitioning."
            actionLabel="Create Project"
            onAction={() => setShowCreateModal(true)}
          />
        </div>
      ) : (
        <>
          {error && (
            <ErrorState
              title="Data Stage Error"
              message={error}
              onRetry={() => setError('')}
            />
          )}

          {successMsg && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Dataset Summary Cards (if version exists) */}
          {selectedDataset && (
            <DatasetSummaryCards
              datasets={datasets}
              selectedDataset={selectedDataset}
              onSelectDataset={(ds) => {
                setSelectedDataset(ds);
                datasetApi.getColumns(ds.id).then((res) => setColumns((res.data || []) as unknown as ColumnSchemaItem[]));
                loadSplitAndPreview(ds.id);
              }}
            />
          )}

          {/* Upload Zone */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 space-y-4 shadow-sm">
            <h2 className="text-sm font-bold text-[var(--color-text)]">
              {selectedDataset ? 'Upload New Dataset Version' : 'Upload Initial Dataset'}
            </h2>
            <UploadZone
              onFileUpload={handleFileUpload}
              uploading={uploading}
            />
          </div>

          {/* Split & Partitioning Panel (if dataset exists) */}
          {selectedDataset && (
            <SplitPanel
              splitSummary={splitSummary}
              totalRows={selectedDataset.row_count}
              lockedTestPct={lockedTestPct}
              onLockedTestPctChange={setLockedTestPct}
              splitSeed={splitSeed}
              onSplitSeedChange={setSplitSeed}
              onRandomizeSeed={handleRandomizeSeed}
              onCreateSplit={handleCreateSplit}
              creatingSplit={creatingSplit}
            />
          )}

          {/* Schema & Preview Table */}
          {columns.length > 0 && (
            <SchemaTable
              columns={columns}
              targetColumn={currentProject?.target_column}
              previewData={devPreview}
            />
          )}
        </>
      )}

      {/* Quick Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <h3 className="text-base font-bold text-[var(--color-text)]">Create New ML Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Customer Churn Experiment"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Target Column (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. churned"
                  value={newTargetCol}
                  onChange={(e) => setNewTargetCol(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-[var(--color-text)]">Task Type (Optional)</label>
                <select
                  value={newTaskType}
                  onChange={(e) => setNewTaskType(e.target.value as TaskType)}
                  className="w-full px-3.5 py-2 text-xs rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer"
                >
                  <option value="UNDETERMINED">Auto-detect / Profile Later</option>
                  <option value="CLASSIFICATION">Classification (Categorical / Labels)</option>
                  <option value="REGRESSION">Regression (Continuous Values)</option>
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-full"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={creatingProject}
                  isLoading={creatingProject}
                  className="rounded-full font-bold shadow-sm"
                >
                  Create Project
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataStage;
