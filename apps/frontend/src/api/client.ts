import axios, { InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import {
  User,
  Project,
  ProjectSnapshot,
  Dataset,
  DatasetColumn,
  DatasetProfile,
  DatasetSplit,
  TransformationConfig,
  FeatureImportanceResponse,
  Experiment,
  ExperimentCreateResponse,
  ModelLeaderboardItem,
  ModelPassport,
  Deployment,
  PredictionResponse,
  AuditLogRecord,
  LivenessResponse,
  ReadinessResponse,
  DetailedHealthResponse,
  LoginResponse,
  TwoFactorSetupResponse,
  TwoFactorConfirmRequest,
  TwoFactorVerifyLoginRequest,
  TwoFactorDisableRequest,
  TwoFactorStatusResponse,
} from '../types/api';

const resolveApiBaseUrl = (): string => {
  const envUrl = (import.meta as any).env?.VITE_API_URL;
  if (!envUrl || typeof envUrl !== 'string' || !envUrl.trim()) {
    return '/api/v1';
  }
  const cleanUrl = envUrl.trim().replace(/\/+$/, '');
  if (cleanUrl.endsWith('/api/v1')) {
    return cleanUrl;
  }
  return `${cleanUrl}/api/v1`;
};

const API_BASE_URL = resolveApiBaseUrl();

if (typeof window !== 'undefined' && window.location && !['localhost', '127.0.0.1'].includes(window.location.hostname) && API_BASE_URL.startsWith('/')) {
  console.error(
    '⚠️ [ML Studio Configuration Alert] VITE_API_URL is missing in this Vercel deployment.\n' +
    'API requests are falling back to relative paths on Vercel CDN which rejects POST with 405.\n' +
    'To fix: Add VITE_API_URL=https://<your-render-backend>.onrender.com/api/v1 in Vercel Environment Variables and redeploy.'
  );
}

let inMemoryAccessToken: string | null = null;

export const setAccessToken = (token: string | null): void => {
  inMemoryAccessToken = token;
};

export const getAccessToken = (): string | null => inMemoryAccessToken;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Attach in-memory JWT token if present
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (inMemoryAccessToken && config.headers) {
      config.headers.Authorization = `Bearer ${inMemoryAccessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 refresh & retry
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/login') && !originalRequest.url?.includes('/auth/refresh')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshRes = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newAccessToken = refreshRes.data.access_token;
        setAccessToken(newAccessToken);
        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        setAccessToken(null);
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (email: string, password: string) => {
    const res = await apiClient.post<LoginResponse>('/auth/login', { email, password });
    if (res.data?.access_token) {
      setAccessToken(res.data.access_token);
    }
    return res;
  },
  register: (fullName: string, email: string, password: string) =>
    apiClient.post('/auth/signup', { full_name: fullName, email, password }),
  refresh: async () => {
    const res = await apiClient.post('/auth/refresh', {});
    if (res.data?.access_token) {
      setAccessToken(res.data.access_token);
    }
    return res;
  },
  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // ignore logout network errors
    } finally {
      setAccessToken(null);
    }
  },
  getMe: () => apiClient.get<User>('/auth/me'),
};

export const twoFactorApi = {
  verifyLogin: async (twoFactorToken: string, code: string) => {
    const res = await apiClient.post<{ access_token: string; refresh_token: string; token_type: string; user: User }>(
      '/auth/2fa/verify-login',
      { two_factor_token: twoFactorToken, code }
    );
    if (res.data?.access_token) {
      setAccessToken(res.data.access_token);
    }
    return res;
  },
  resendOtp: (twoFactorToken: string) =>
    apiClient.post<{ message: string; email_masked?: string }>('/auth/2fa/resend', {
      two_factor_token: twoFactorToken,
    }),
  setup: () => apiClient.post<TwoFactorSetupResponse>('/auth/2fa/setup'),
  confirm: (payload: TwoFactorConfirmRequest) =>
    apiClient.post<{ message: string }>('/auth/2fa/confirm', payload),
  disable: (payload: TwoFactorDisableRequest) =>
    apiClient.post<{ message: string }>('/auth/2fa/disable', payload),
  getStatus: () => apiClient.get<TwoFactorStatusResponse>('/auth/2fa/status'),
};

export const workspaceApi = {
  getSummary: () => apiClient.get('/workspace/summary'),
};

export const projectApi = {
  list: (skip = 0, limit = 100) => apiClient.get<Project[]>(`/projects?skip=${skip}&limit=${limit}`),
  get: (id: string) => apiClient.get<Project>(`/projects/${id}`),
  getSnapshot: (id: string) => apiClient.get<ProjectSnapshot>(`/projects/${id}/snapshot`),
  create: (
    payloadOrName: string | { project_name: string; target_column?: string | null; task_type?: string },
    targetColumn: string | null = null
  ) => {
    if (typeof payloadOrName === 'string') {
      return apiClient.post<Project>('/projects', { project_name: payloadOrName, target_column: targetColumn });
    }
    return apiClient.post<Project>('/projects', {
      project_name: payloadOrName.project_name,
      target_column: payloadOrName.target_column ?? null,
      task_type: payloadOrName.task_type ?? 'UNDETERMINED',
    });
  },
  update: (id: string, payload: Partial<Project>) => apiClient.put<Project>(`/projects/${id}`, payload),
  updateTaskType: (id: string, taskType: string) => apiClient.put(`/projects/${id}/task-type`, { task_type: taskType }),
  getRecommendations: (id: string) => apiClient.get(`/projects/${id}/recommendations`),
  updateRecommendationStatus: (id: string, recId: string, status: string) =>
    apiClient.patch(`/projects/${id}/recommendations/${recId}`, { status }),
  delete: (id: string) => apiClient.delete(`/projects/${id}`),
};

export const datasetApi = {
  upload: (projectId: string, file: File | FormData) => {
    let formData: FormData;
    if (file instanceof FormData) {
      formData = file;
    } else {
      formData = new FormData();
      formData.append('file', file);
    }
    return apiClient.post<Dataset>(`/projects/${projectId}/datasets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  listVersions: (projectId: string) => apiClient.get<Dataset[]>(`/projects/${projectId}/datasets`),
  getColumns: (datasetId: string) => apiClient.get<DatasetColumn[]>(`/datasets/${datasetId}/columns`),
  profile: (datasetId: string) => apiClient.post<DatasetProfile>(`/datasets/${datasetId}/profile`),
  getProfile: (datasetId: string) => apiClient.get<DatasetProfile>(`/datasets/${datasetId}/profile`),
  getEdaReport: (datasetId: string, maxSampleRows = 1000) =>
    apiClient.get<any>(`/datasets/${datasetId}/eda-report?max_sample_rows=${maxSampleRows}`),
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
  create: (projectId: string, payload: any) => apiClient.post<ExperimentCreateResponse>(`/projects/${projectId}/experiments`, payload),
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
    apiClient.get<any>(`/projects/${projectId}/leaderboard${experimentId ? `?experiment_id=${experimentId}` : ''}`),
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
  updateUserStatus: (userId: string, isActive: boolean) =>
    apiClient.patch<User>(`/admin/users/${userId}`, { is_active: isActive }),
  resetUserPassword: (userId: string) =>
    apiClient.post<{ message: string; temporary_password?: string; email?: string }>(`/admin/users/${userId}/reset-password`),
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

export const healthApi = {
  getBaseline: () => apiClient.get('/health'),
  getLive: () => apiClient.get<LivenessResponse>('/health/live'),
  getReady: () => apiClient.get<ReadinessResponse>('/health/ready'),
  getStatus: () => apiClient.get<DetailedHealthResponse>('/health/status'),
};

export default apiClient;
