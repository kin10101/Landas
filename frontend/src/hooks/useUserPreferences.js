import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const STORAGE_KEY = 'landas_preferences';

const getStoredPreferences = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

const storePreferences = (prefs) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Ignore storage errors
  }
};

const defaultPreferences = {
  target_role: 'AI Engineer',
  enabled_sources: {
    hackernews: true,
    github_trending: true,
    devto: true,
    medium: true,
    arxiv: true,
    stackoverflow: true,
    pypi: true,
  },
  relevance_threshold: 0.5,
  has_completed_onboarding: false,
};

export function useUserPreferences() {
  const [preferences, setPreferences] = useState(null);
  const [defaults, setDefaults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { authFetch, isAuthenticated } = useAuth();

  const fetchPreferences = useCallback(async () => {
    if (!isAuthenticated) {
      setPreferences(defaultPreferences);
      setLoading(false);
      return;
    }

    try {
      const res = await authFetch(`${API_URL}/preferences`);
      if (res.ok) {
        const data = await res.json();
        setPreferences(data);
        storePreferences(data);
      } else {
        const stored = getStoredPreferences();
        setPreferences(stored || defaultPreferences);
      }
    } catch (e) {
      console.error('Failed to fetch preferences:', e);
      const stored = getStoredPreferences();
      setPreferences(stored || defaultPreferences);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [authFetch, isAuthenticated]);

  const fetchDefaults = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/preferences/defaults`);
      if (res.ok) {
        const data = await res.json();
        setDefaults(data);
      }
    } catch (e) {
      console.error('Failed to fetch defaults:', e);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchPreferences();
    }
    fetchDefaults();
  }, [fetchPreferences, fetchDefaults, isAuthenticated]);

  const updatePreferences = useCallback(async (updates) => {
    const newPrefs = { ...preferences, ...updates };

    try {
      const res = await authFetch(`${API_URL}/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        const data = await res.json();
        setPreferences(data.preferences);
        storePreferences(data.preferences);
        return true;
      }
      // API failed, use local storage
      setPreferences(newPrefs);
      storePreferences(newPrefs);
      return true;
    } catch (e) {
      console.error('Failed to update preferences:', e);
      // Fallback to localStorage
      setPreferences(newPrefs);
      storePreferences(newPrefs);
      return true;
    }
  }, [preferences, authFetch]);

  const completeOnboarding = useCallback(async () => {
    return updatePreferences({ has_completed_onboarding: true });
  }, [updatePreferences]);

  const resetOnboarding = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setPreferences(defaultPreferences);
  }, []);

  const needsOnboarding = preferences && !preferences.has_completed_onboarding;

  return {
    preferences,
    defaults,
    loading,
    error,
    needsOnboarding,
    updatePreferences,
    completeOnboarding,
    resetOnboarding,
    refetch: fetchPreferences,
  };
}

export default useUserPreferences;
