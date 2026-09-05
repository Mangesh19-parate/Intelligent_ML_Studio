import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Attach JWT token if present
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor: handle 401 logout
apiClient.interceptors.response.use(
  (response) => response,
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
  login: (email, password) => apiClient.post('/auth/login', { email, password }),
  register: (fullName, email, password, roleName = 'ML_ENGINEER') =>
    apiClient.post('/auth/register', { full_name: fullName, email, password, role_name: roleName }),
  getMe: () => apiClient.get('/auth/me'),
};

export const projectApi = {
  list: (skip = 0, limit = 100) => apiClient.get(`/projects?skip=${skip}&limit=${limit}`),
  get: (id) => apiClient.get(`/projects/${id}`),
  create: (projectName, targetColumn = null) =>
    apiClient.post('/projects', { project_name: projectName, target_column: targetColumn }),
  update: (id, payload) => apiClient.put(`/projects/${id}`, payload),
  updateTaskType: (id, taskType) => apiClient.put(`/projects/${id}/task-type`, { task_type: taskType }),
  getRecommendations: (id) => apiClient.get(`/projects/${id}/recommendations`),
  delete: (id) => apiClient.delete(`/projects/${id}`),
};

export const datasetApi = {
  upload: (projectId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/projects/${projectId}/datasets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  listVersions: (projectId) => apiClient.get(`/projects/${projectId}/datasets`),
  getColumns: (datasetId) => apiClient.get(`/datasets/${datasetId}/columns`),
  profile: (datasetId) => apiClient.post(`/datasets/${datasetId}/profile`),
  getProfile: (datasetId) => apiClient.get(`/datasets/${datasetId}/profile`),
};

export const datasetSplitApi = {
  createSplit: (datasetId, payload = { locked_test_pct: 20, seed: null }) =>
    apiClient.post(`/datasets/${datasetId}/split`, payload),
  getSplit: (datasetId) => apiClient.get(`/datasets/${datasetId}/split`),
  getDevelopmentPreview: (datasetId, limit = 10) =>
    apiClient.get(`/datasets/${datasetId}/development-preview?limit=${limit}`),
};

export const transformationApi = {
  getConfigs: (projectId) => apiClient.get(`/projects/${projectId}/transformations`),
  updateColumn: (projectId, column, payload) =>
    apiClient.put(`/projects/${projectId}/transformations/${encodeURIComponent(column)}`, payload),
  preview: (projectId, column, sampleSize = 50) =>
    apiClient.post(`/projects/${projectId}/transformations/preview`, {
      column,
      sample_size: sampleSize,
    }),
};

export const experimentApi = {
  create: (projectId, payload) => apiClient.post(`/projects/${projectId}/experiments`, payload),
  get: (experimentId) => apiClient.get(`/experiments/${experimentId}`),
  listByProject: (projectId) => apiClient.get(`/projects/${projectId}/experiments`),
  getSelection: (experimentId) => apiClient.get(`/experiments/${experimentId}/selection`),
  getLineage: (experimentId) => apiClient.get(`/experiments/${experimentId}/lineage`),
  finalize: (experimentId) => apiClient.post(`/experiments/${experimentId}/finalize`),
  diagnosticRerun: (experimentId) => apiClient.post(`/experiments/${experimentId}/diagnostic-rerun`),
};

export const modelApi = {
  getLeaderboard: (projectId, experimentId = null) =>
    apiClient.get(`/projects/${projectId}/leaderboard${experimentId ? `?experiment_id=${experimentId}` : ''}`),
  getMetrics: (modelId) => apiClient.get(`/models/${modelId}/metrics`),
  getExplainability: (modelId, backgroundSampleSize = 200) =>
    apiClient.get(`/models/${modelId}/explainability?background_sample_size=${backgroundSampleSize}`),
  getLocalExplainability: (modelId, inputRow) =>
    apiClient.post(`/models/${modelId}/explainability/local`, inputRow),
};

export default apiClient;

