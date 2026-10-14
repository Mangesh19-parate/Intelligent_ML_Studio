import { AxiosInstance } from 'axios';
import apiClient, {
  setAccessToken as clientSetAccessToken,
  getAccessToken as clientGetAccessToken,
  API_BASE_URL as clientApiBaseUrl,
} from '../../api/client';
import { normalizeApiError, ApiError } from './errors';

export const API_BASE_URL = clientApiBaseUrl;
export const setAccessToken = clientSetAccessToken;
export const getAccessToken = clientGetAccessToken;
export const httpClient: AxiosInstance = apiClient;
export { normalizeApiError, ApiError };
export default httpClient;
