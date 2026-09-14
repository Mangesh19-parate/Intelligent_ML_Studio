import axios, { InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import {
  User,
  Project,
  ProjectSnapshot,
  Dataset,
  DatasetProfile,
  DatasetSplit,
  TransformationConfig,
  FeatureImportanceResponse,
  Experiment,
  ModelLeaderboardItem,
  ModelPassport,
  Deployment,
  PredictionResponse,
  AuditLogRecord,
} from '../types/api';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Attach JWT token if present
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 logout
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  register: (fullName: string, email: string, password: string) =>
    apiClient.post('/auth/signup', { full_name: fullName, email, password }),
  getMe: () => apiClient.get<User>('/auth/me'),
};

export const workspaceApi = {
  getSummary: () => apiClient.get('/workspace/summary'),
};

export const projectApi = {
  list: (skip = 0, limit = 100) => apiClient.get<Project[]>(`/projects?skip=${skip}&limit=${limit}`),
  get: (id: string) => apiClient.get<Project>(`/projects/${id}`),
  getSnapshot: (id: string) => apiClient.get<ProjectSnapshot>(`/projects/${id}/snapshot`),
  create: (projectName: string, targetColumn: string | null = null) =>
    apiClient.post<Project>('/projects', { project_name: projectName, target_column: targetColumn }),
  update: (id: string, payload: Partial<Project>) => apiClient.put<Project>(`/projects/${id}`, payload),
  updateTaskType: (id: string, taskType: string) => apiClient.put(`/projects/${id}/task-type`, { task_type: taskType }),
  getRecommendations: (id: string) => apiClient.get(`/projects/${id}/recommendations`),
  updateRecommendationStatus: (id: string, recId: string, status: string) =>
    apiClient.patch(`/projects/${id}/recommendations/${recId}`, { status }),
  delete: (id: string) => apiClient.delete(`/projects/${id}`),
};

export const datasetApi = {
  upload: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<Dataset>(`/projects/${projectId}/datasets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  listVersions: (projectId: string) => apiClient.get<Dataset[]>(`/projects/${projectId}/datasets`),
  getColumns: (datasetId: string) => apiClient.get<{ columns: string[] }>(`/datasets/${datasetId}/columns`),
  profile: (datasetId: string) => apiClient.post<DatasetProfile>(`/datasets/${datasetId}/profile`),
  getProfile: (datasetId: string) => apiClient.get<DatasetProfile>(`/datasets/${datasetId}/profile`),
};

export const datasetSplitApi = {
  createSplit: (datasetId: string, payload = { locked_test_pct: 20, seed: null as number | null }) =>
    apiClient.post<DatasetSplit>(`/datasets/${datasetId}/split`, payload),
  getSplit: (datasetId: string) => apiClient.get<DatasetSplit>(`/datasets/${datasetId}/split`),
  getDevelopmentPreview: (datasetId: string, limit = 10) =>
    apiClient.get(`/datasets/${datasetId}/development-preview?limit=${limit}`),
};

export const transformationApi = {
  getConfigs: (projectId: string) => apiClient.get<TransformationConfig[]>(`/projects/${projectId}/transformations`),
  updateColumn: (projectId: string, column: string, payload: any) =>
    apiClient.put(`/projects/${projectId}/transformations/${encodeURIComponent(column)}`, payload),
  preview: (projectId: string, column: string, sampleSize = 50) =>
    apiClient.post(`/projects/${projectId}/transformations/preview`, {
      column,
      sample_size: sampleSize,
    }),
};

export const featureSelectionApi = {
  run: (projectId: string, payload: any = {}) =>
    apiClient.post(`/projects/${projectId}/feature-selection/run`, payload),
  getImportance: (projectId: string) =>
    apiClient.get<FeatureImportanceResponse>(`/projects/${projectId}/feature-importance`),
  getFolds: (projectId: string, experimentId: string) =>
    apiClient.get(`/projects/${projectId}/experiments/${experimentId}/folds`),
  updateThreshold: (projectId: string, payload: any) =>
    apiClient.put(`/projects/${projectId}/feature-selection/threshold`, payload),
};

export const experimentApi = {
  create: (projectId: string, payload: any) => apiClient.post<Experiment>(`/projects/${projectId}/experiments`, payload),
  get: (experimentId: string) => apiClient.get<Experiment>(`/experiments/${experimentId}`),
  listByProject: (projectId: string) => apiClient.get<Experiment[]>(`/projects/${projectId}/experiments`),
  getSelection: (experimentId: string) => apiClient.get(`/experiments/${experimentId}/selection`),
  getLineage: (experimentId: string) => apiClient.get(`/experiments/${experimentId}/lineage`),
  getHealth: (experimentId: string) => apiClient.get(`/experiments/${experimentId}/health`),
  reproduce: (experimentId: string) => apiClient.post(`/experiments/${experimentId}/reproduce`),
  finalize: (experimentId: string) => apiClient.post(`/experiments/${experimentId}/finalize`),
  diagnosticRerun: (experimentId: string) => apiClient.post(`/experiments/${experimentId}/diagnostic-rerun`),
};

export const modelApi = {
  getLeaderboard: (projectId: string, experimentId: string | null = null) =>
    apiClient.get<ModelLeaderboardItem[]>(`/projects/${projectId}/leaderboard${experimentId ? `?experiment_id=${experimentId}` : ''}`),
  getMetrics: (modelId: string) => apiClient.get(`/models/${modelId}/metrics`),
  getPassport: (modelId: string) => apiClient.get<ModelPassport>(`/models/${modelId}/passport`),
  getExplainability: (modelId: string, backgroundSampleSize = 200) =>
    apiClient.get(`/models/${modelId}/explainability?background_sample_size=${backgroundSampleSize}`),
  getLocalExplainability: (modelId: string, inputRow: any) =>
    apiClient.post(`/models/${modelId}/explainability/local`, inputRow),
  getDeploymentGate: (modelId: string) => apiClient.get(`/models/${modelId}/deployment-gate`),
  approveDeploymentGate: (modelId: string) => apiClient.post(`/models/${modelId}/deployment-gate/approve`),
  deploy: (modelId: string) => apiClient.post(`/models/${modelId}/deploy`),
  download: (modelId: string, format = 'joblib') =>
    apiClient.get(`/models/${modelId}/download?format=${format}`, { responseType: 'blob' }),
};

export const deploymentApi = {
  get: (deploymentId: string) => apiClient.get<Deployment>(`/deployments/${deploymentId}`),
  getMonitoring: (deploymentId: string, lookbackHours = 24) =>
    apiClient.get(`/deployments/${deploymentId}/monitoring?lookback_hours=${lookbackHours}`),
  updateStatus: (deploymentId: string, status: string) => apiClient.put(`/deployments/${deploymentId}/status`, { status }),
  rollback: (deploymentId: string, targetDeploymentId: string, reason: string | null = null) =>
    apiClient.post(`/deployments/${deploymentId}/rollback`, { target_deployment_id: targetDeploymentId, reason }),
  getLogs: (deploymentId: string, limit = 50) => apiClient.get(`/deployments/${deploymentId}/logs?limit=${limit}`),
};

export const predictApi = {
  predict: (deploymentId: string, payload: any) => apiClient.post<PredictionResponse>(`/predict/${deploymentId}`, payload),
  predictExplain: (deploymentId: string, payload: any) => apiClient.post(`/predict/${deploymentId}/explain`, payload),
};

export const adminApi = {
  getUsers: () => apiClient.get<User[]>('/admin/users'),
  createUser: (payload: any) => apiClient.post<User>('/admin/users', payload),
  updateUser: (userId: string, payload: any) => apiClient.patch<User>(`/admin/users/${userId}`, payload),
  setPermissionOverride: (userId: string, permissionKey: string, isGranted: boolean) =>
    apiClient.put(`/admin/users/${userId}/overrides`, { permission_key: permissionKey, is_granted: isGranted }),
  deletePermissionOverride: (userId: string, permissionKey: string) =>
    apiClient.delete(`/admin/users/${userId}/overrides/${permissionKey}`),
  getAlgorithms: () => apiClient.get('/admin/catalog/algorithms'),
  getMetrics: () => apiClient.get('/admin/catalog/metrics'),
  getFeatures: () => apiClient.get('/admin/catalog/features'),
  getAuditLogs: (eventType = '', search = '', limit = 100) => {
    let url = `/admin/audit-logs?limit=${limit}`;
    if (eventType) url += `&event_type=${encodeURIComponent(eventType)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    return apiClient.get<AuditLogRecord[]>(url);
  },
};

export default apiClient;
