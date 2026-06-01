import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const AUTH_TOKEN_KEY = 'landas_auth_token';
const AUTH_USER_KEY = 'landas_auth_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedUser = localStorage.getItem(AUTH_USER_KEY);

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      verifyToken(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyToken = async (tokenToVerify) => {
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${tokenToVerify}` }
      });

      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData));
      } else {
        logout();
      }
    } catch (e) {
      console.error('Token verification failed:', e);
    } finally {
      setLoading(false);
    }
  };

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const text = await res.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        console.error('Failed to parse response:', text);
        throw new Error('Server error - please try again');
      }

      if (!res.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));

      return { success: true };
    } catch (e) {
      setError(e.message);
      return { success: false, error: e.message };
    }
  }, []);

  const register = useCallback(async (email, password, name) => {
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });

      const text = await res.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        console.error('Failed to parse response:', text);
        throw new Error('Server error - please try again');
      }

      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed');
      }

      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));

      return { success: true };
    } catch (e) {
      setError(e.message);
      return { success: false, error: e.message };
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem('landas_preferences');
  }, []);

  const getAuthHeaders = useCallback(() => {
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
  }, [token]);

  const authFetch = useCallback(async (url, options = {}) => {
    const headers = {
      ...options.headers,
      ...getAuthHeaders(),
    };
    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
      logout();
      throw new Error('Session expired. Please login again.');
    }

    return res;
  }, [getAuthHeaders, logout]);

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      error,
      isAuthenticated: !!token,
      login,
      register,
      logout,
      getAuthHeaders,
      authFetch,
    }}>
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
