import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { normalizeApiError } from './errors';

const resolveApiBaseUrl = (): string => {
  const envUrl = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_URL;
  if (!envUrl || typeof envUrl !== 'string' || !envUrl.trim()) {
    return '/api/v1';
  }
  const cleanUrl = envUrl.trim().replace(/\/+$/, '');
  if (cleanUrl.endsWith('/api/v1')) {
    return cleanUrl;
  }
  return `${cleanUrl}/api/v1`;
};

export const API_BASE_URL = resolveApiBaseUrl();

let inMemoryAccessToken: string | null = null;

export const setAccessToken = (token: string | null): void => {
  inMemoryAccessToken = token;
};

export const getAccessToken = (): string | null => inMemoryAccessToken;

export const httpClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

httpClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(normalizeApiError(error))
);

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: string | null) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

httpClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: unknown) => {
    if (typeof error === 'object' && error !== null && 'response' in error) {
      const axiosErr = error as {
        response?: { status?: number };
        config?: InternalAxiosRequestConfig & { _retry?: boolean };
      };
      const originalRequest = axiosErr.config;

      if (
        axiosErr.response?.status === 401 &&
        originalRequest &&
        !originalRequest._retry &&
        !originalRequest.url?.includes('/auth/login') &&
        !originalRequest.url?.includes('/auth/refresh')
      ) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              if (originalRequest.headers && typeof token === 'string') {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              return httpClient(originalRequest);
            })
            .catch((err) => Promise.reject(normalizeApiError(err)));
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const refreshRes = await axios.post<{ access_token: string }>(
            `${API_BASE_URL}/auth/refresh`,
            {},
            { withCredentials: true }
          );
          const newAccessToken = refreshRes.data.access_token;
          setAccessToken(newAccessToken);
          processQueue(null, newAccessToken);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          }
          return httpClient(originalRequest);
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          setAccessToken(null);
          if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          return Promise.reject(normalizeApiError(refreshErr));
        } finally {
          isRefreshing = false;
        }
      }
    }
    return Promise.reject(normalizeApiError(error));
  }
);
