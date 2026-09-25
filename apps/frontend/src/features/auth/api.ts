import { httpClient, setAccessToken } from '../../shared/api/httpClient';
import {
  User,
  LoginResponse,
  TwoFactorSetupResponse,
  TwoFactorConfirmRequest,
  TwoFactorVerifyLoginRequest,
  TwoFactorDisableRequest,
  TwoFactorStatusResponse,
} from '../../types/api';

export const authApi = {
  login: async (email: string, password: string, totpCode?: string): Promise<LoginResponse> => {
    const res = await httpClient.post<LoginResponse>('/auth/login', {
      email,
      password,
      totp_code: totpCode,
    });
    if (res.data.access_token) {
      setAccessToken(res.data.access_token);
    }
    return res.data;
  },

  logout: async (): Promise<void> => {
    try {
      await httpClient.post('/auth/logout');
    } finally {
      setAccessToken(null);
    }
  },

  getCurrentUser: async (): Promise<User> => {
    const res = await httpClient.get<User>('/auth/me');
    return res.data;
  },

  setupTwoFactor: async (): Promise<TwoFactorSetupResponse> => {
    const res = await httpClient.post<TwoFactorSetupResponse>('/auth/2fa/setup');
    return res.data;
  },

  confirmTwoFactor: async (payload: TwoFactorConfirmRequest): Promise<User> => {
    const res = await httpClient.post<User>('/auth/2fa/confirm', payload);
    return res.data;
  },

  verifyTwoFactorLogin: async (payload: TwoFactorVerifyLoginRequest): Promise<LoginResponse> => {
    const res = await httpClient.post<LoginResponse>('/auth/2fa/verify-login', payload);
    if (res.data.access_token) {
      setAccessToken(res.data.access_token);
    }
    return res.data;
  },

  disableTwoFactor: async (payload: TwoFactorDisableRequest): Promise<User> => {
    const res = await httpClient.post<User>('/auth/2fa/disable', payload);
    return res.data;
  },

  getTwoFactorStatus: async (): Promise<TwoFactorStatusResponse> => {
    const res = await httpClient.get<TwoFactorStatusResponse>('/auth/2fa/status');
    return res.data;
  },
};
