'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchApi, getAuthToken, setAuthToken, removeAuthToken } from '@/lib/api';
import { firebaseSignIn, firebaseSignUp, firebaseLookupToken } from '@/lib/firebase';

export interface User {
  id: string;
  email: string;
  display_name?: string;
  role: string;
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
          // Attempt loading user from backend /auth/me
          const userData = await fetchApi<User>('/auth/me');
          setUser(userData);
        } catch (e) {
          // Fallback: verify Firebase ID Token directly with Firebase Lookup REST API
          try {
            const fbUser = await firebaseLookupToken(storedToken);
            if (fbUser) {
              setUser({
                id: fbUser.localId,
                email: fbUser.email,
                display_name: fbUser.displayName || fbUser.email.split('@')[0],
                role: 'user',
              });
            } else {
              throw new Error('Invalid session');
            }
          } catch {
            console.warn('Session expired or invalid, clearing auth token');
            removeAuthToken();
            setTokenState(null);
            setUser(null);
          }
        }
      }
      setIsLoading(false);
    }
    loadUser();
  }, []);

  const login = async (email: string, pass: string) => {
    const res = await firebaseSignIn(email, pass);
    setAuthToken(res.idToken);
    setTokenState(res.idToken);

    try {
      const dbUser = await fetchApi<User>('/auth/me');
      setUser(dbUser);
    } catch {
      setUser({
        id: res.localId,
        email: res.email,
        display_name: res.displayName || res.email.split('@')[0],
        role: 'user',
      });
    }
  };

  const register = async (email: string, pass: string, name?: string) => {
    const res = await firebaseSignUp(email, pass, name);
    setAuthToken(res.idToken);
    setTokenState(res.idToken);

    try {
      const dbUser = await fetchApi<User>('/auth/me');
      setUser(dbUser);
    } catch {
      setUser({
        id: res.localId,
        email: res.email,
        display_name: name || res.displayName || res.email.split('@')[0],
        role: 'user',
      });
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
