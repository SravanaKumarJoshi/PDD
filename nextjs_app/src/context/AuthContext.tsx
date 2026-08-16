'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchApi, getAuthToken, setAuthToken, removeAuthToken } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  display_name?: string;
  role: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const storedToken = getAuthToken();
      if (storedToken) {
        setTokenState(storedToken);
        try {
          // Verify session & load profile from backend /auth/me via JWT token
          const userData = await fetchApi<User>('/auth/me');
          setUser(userData);
        } catch (e) {
          console.warn('JWT session expired or invalid, clearing auth token');
          removeAuthToken();
          setTokenState(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    }
    loadUser();
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await fetchApi<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password: pass }),
    });

    if (res.access_token) {
      setAuthToken(res.access_token);
      setTokenState(res.access_token);
      setUser(res.user);
    }
  };

  const register = async (email: string, pass: string, name?: string) => {
    const res = await fetchApi<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password: pass, display_name: name }),
    });

    if (res.access_token) {
      setAuthToken(res.access_token);
      setTokenState(res.access_token);
      setUser(res.user);
    }
  };

  const logout = () => {
    removeAuthToken();
    setTokenState(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

