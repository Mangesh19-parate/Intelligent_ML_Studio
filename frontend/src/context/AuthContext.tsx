import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi, twoFactorApi } from '../api/client';
import { User, LoginResponse } from '../types/api';

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<LoginResponse>;
  verify2FA: (twoFactorToken: string, code: string) => Promise<User>;
  register: (fullName: string, email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isAuthenticated: boolean;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  const refreshUser = async (): Promise<void> => {
    try {
      const meRes = await authApi.getMe();
      setUser(meRes.data);
    } catch {
      setUser(null);
    }
  };

  // Initial silent auth initialization via HttpOnly cookie refresh
  useEffect(() => {
    const initAuth = async () => {
      try {
        await authApi.refresh();
        await refreshUser();
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<LoginResponse> => {
    const res = await authApi.login(email, password);
    if (!res.data.requires_2fa && res.data.user) {
      setUser(res.data.user);
    }
    return res.data;
  };

  const verify2FA = async (twoFactorToken: string, code: string): Promise<User> => {
    const res = await twoFactorApi.verifyLogin(twoFactorToken, code);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (fullName: string, email: string, password: string): Promise<User> => {
    await authApi.register(fullName, email, password);
    const loginRes = await login(email, password);
    return loginRes.user as User;
  };

  const logout = async (): Promise<void> => {
    await authApi.logout();
    setUser(null);
  };

  const toggleDarkMode = (): void => setDarkMode((prev) => !prev);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        verify2FA,
        register,
        logout,
        refreshUser,
        isAuthenticated: !!user,
        darkMode,
        toggleDarkMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
