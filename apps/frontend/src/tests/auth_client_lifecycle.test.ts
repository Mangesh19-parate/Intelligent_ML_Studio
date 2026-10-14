import { describe, it, expect, beforeEach, vi } from 'vitest';
import apiClient, {
  setAccessToken as setClientToken,
  getAccessToken as getClientToken,
  authApi as canonicalAuthApi,
} from '../api/client';
import {
  httpClient,
  setAccessToken as setSharedToken,
  getAccessToken as getSharedToken,
} from '../shared/api/httpClient';
import { authApi as featureAuthApi } from '../features/auth/api';

describe('Frontend Authentication & Consolidated API Client Lifecycle', () => {
  beforeEach(() => {
    localStorage.clear();
    setClientToken(null);
    vi.restoreAllMocks();
  });

  it('1. consolidates to a single shared Axios instance across active features', () => {
    expect(httpClient).toBe(apiClient);
    expect(getSharedToken()).toBeNull();
    expect(getClientToken()).toBeNull();
  });

  it('2. synchronizes token state across client.ts and shared/api/httpClient.ts', () => {
    const testToken = 'jwt-sample-token-xyz';
    setClientToken(testToken);

    // Both accessors must return the exact same token
    expect(getClientToken()).toBe(testToken);
    expect(getSharedToken()).toBe(testToken);
    expect(localStorage.getItem('access_token')).toBe(testToken);

    // Modifying via shared module updates canonical module
    const newToken = 'jwt-updated-token-abc';
    setSharedToken(newToken);
    expect(getClientToken()).toBe(newToken);
    expect(getSharedToken()).toBe(newToken);
    expect(localStorage.getItem('access_token')).toBe(newToken);
  });

  it('3. attaches Authorization: Bearer token on outgoing authenticated requests', async () => {
    const fakeToken = 'test-bearer-token-12345';
    setClientToken(fakeToken);

    // Interceptor test: verify config gets Authorization header
    const mockConfig: any = { headers: {} };
    // Trigger request interceptor
    const requestHandler = (apiClient.interceptors.request as any).handlers?.[0]?.fulfilled;
    expect(requestHandler).toBeDefined();

    const transformedConfig = requestHandler(mockConfig);
    expect(transformedConfig.headers.Authorization).toBe(`Bearer ${fakeToken}`);
  });

  it('4. rejects unauthenticated protected requests without Bearer header when token is null', () => {
    setClientToken(null);
    const mockConfig: any = { headers: {} };
    const requestHandler = (apiClient.interceptors.request as any).handlers?.[0]?.fulfilled;
    const transformedConfig = requestHandler(mockConfig);
    expect(transformedConfig.headers.Authorization).toBeUndefined();
  });

  it('5. login succeeds with valid test account and updates shared token state', async () => {
    const mockUser = {
      id: 'usr-1',
      email: 'admin@studio.dev',
      full_name: 'Admin Tester',
      role: { role_name: 'ADMIN' },
      is_active: true,
      created_at: new Date().toISOString(),
    };
    const mockLoginResponse = {
      data: {
        access_token: 'auth-test-valid-access-token',
        token_type: 'bearer',
        requires_2fa: false,
        user: mockUser,
      },
    };

    vi.spyOn(apiClient, 'post').mockResolvedValueOnce(mockLoginResponse as any);

    const result = await canonicalAuthApi.login('admin@studio.dev', 'DemoPassword123!');
    expect(result.data.access_token).toBe('auth-test-valid-access-token');
    expect(getClientToken()).toBe('auth-test-valid-access-token');
    expect(getSharedToken()).toBe('auth-test-valid-access-token');
    expect(localStorage.getItem('access_token')).toBe('auth-test-valid-access-token');
  });

  it('6. invalid login is rejected and does not set access token', async () => {
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce({
      response: {
        status: 401,
        data: { detail: 'Incorrect email or password' },
      },
    });

    await expect(
      canonicalAuthApi.login('invalid@example.com', 'WrongPassword123!')
    ).rejects.toBeDefined();

    expect(getClientToken()).toBeNull();
    expect(getSharedToken()).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('7. logout clears the consolidated token in memory and in localStorage', async () => {
    setClientToken('active-session-token');
    expect(getClientToken()).toBe('active-session-token');

    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({ data: { message: 'Logged out' } } as any);

    await canonicalAuthApi.logout();

    expect(getClientToken()).toBeNull();
    expect(getSharedToken()).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('8. features/auth/api.ts operates through the consolidated client lifecycle', async () => {
    const mockUser = {
      id: 'usr-2',
      email: 'trainer@demo.com',
      full_name: 'Trainer User',
      role: { role_name: 'TRAINER' },
      is_active: true,
      created_at: new Date().toISOString(),
    };

    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      data: {
        access_token: 'feature-auth-token',
        token_type: 'bearer',
        requires_2fa: false,
        user: mockUser,
      },
    } as any);

    const loginRes = await featureAuthApi.login('trainer@demo.com', 'DemoPassword123!');
    expect(loginRes.access_token).toBe('feature-auth-token');
    expect(getClientToken()).toBe('feature-auth-token');
    expect(getSharedToken()).toBe('feature-auth-token');

    // Test feature logout
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({ data: { message: 'Logged out' } } as any);
    await featureAuthApi.logout();
    expect(getClientToken()).toBeNull();
    expect(getSharedToken()).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
