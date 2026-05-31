import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { useAuth } from '../contexts/AuthContext';

const SettingsPage = () => {
  const { preferences, defaults, loading, updatePreferences } = useUserPreferences();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [localPrefs, setLocalPrefs] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (preferences) {
      setLocalPrefs({ ...preferences });
    }
  }, [preferences]);

  if (loading || !localPrefs) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const handleRoleChange = (role) => {
    setLocalPrefs((prev) => ({ ...prev, target_role: role }));
    setSaved(false);
  };

  const handleSourceToggle = (sourceKey) => {
    setLocalPrefs((prev) => ({
      ...prev,
      enabled_sources: {
        ...prev.enabled_sources,
        [sourceKey]: !prev.enabled_sources[sourceKey],
      },
    }));
    setSaved(false);
  };

  const handleThresholdChange = (value) => {
    setLocalPrefs((prev) => ({ ...prev, relevance_threshold: parseFloat(value) }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    const success = await updatePreferences({
      target_role: localPrefs.target_role,
      enabled_sources: localPrefs.enabled_sources,
      relevance_threshold: localPrefs.relevance_threshold,
    });
    setSaving(false);
    if (success) {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
  };

  const handleReset = () => {
    setLocalPrefs({ ...preferences });
    setSaved(false);
  };

  const availableRoles = defaults?.available_roles || [
    'AI Engineer',
    'ML Engineer',
    'Data Engineer',
    'Analytics Engineer',
    'Data Scientist',
  ];

  const availableSources = defaults?.available_sources || {
    hackernews: { name: 'Hacker News', description: 'Tech news and discussions' },
    github_trending: { name: 'GitHub Trending', description: 'Trending repositories' },
    devto: { name: 'Dev.to', description: 'Developer articles' },
    medium: { name: 'Medium', description: 'Tech blogs' },
    arxiv: { name: 'ArXiv', description: 'Research papers' },
    stackoverflow: { name: 'Stack Overflow', description: 'Q&A trends' },
    pypi: { name: 'PyPI', description: 'Python packages' },
  };

  const hasChanges = JSON.stringify(localPrefs) !== JSON.stringify(preferences);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-slate-500 hover:text-slate-700">
              ← Back
            </Link>
            <h1 className="text-xl font-bold text-slate-900">Settings</h1>
          </div>
          <div className="flex items-center gap-2">
            {saved && (
              <span className="text-emerald-600 text-sm font-medium">Saved!</span>
            )}
            {hasChanges && (
              <button
                onClick={handleReset}
                className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800"
              >
                Reset
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`px-4 py-1.5 rounded-lg font-medium text-sm transition-colors ${
                hasChanges
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-8">
        {/* Target Role */}
        <section className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Target Role</h2>
          <p className="text-sm text-slate-500 mb-4">
            Your primary career focus. Research will be tailored to this role.
          </p>

          <div className="grid grid-cols-2 gap-2">
            {availableRoles.map((role) => (
              <button
                key={role}
                onClick={() => handleRoleChange(role)}
                className={`p-3 rounded-lg border-2 text-left transition-all ${
                  localPrefs.target_role === role
                    ? 'border-blue-600 bg-blue-50 text-blue-900'
                    : 'border-slate-200 hover:border-slate-300 text-slate-700'
                }`}
              >
                <span className="font-medium">{role}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Research Sources */}
        <section className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Research Sources</h2>
          <p className="text-sm text-slate-500 mb-4">
            Toggle which sources to monitor for emerging technologies.
          </p>

          <div className="space-y-2">
            {Object.entries(availableSources).map(([key, source]) => (
              <label
                key={key}
                className={`flex items-center p-3 rounded-lg border cursor-pointer transition-all ${
                  localPrefs.enabled_sources[key]
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={localPrefs.enabled_sources[key]}
                  onChange={() => handleSourceToggle(key)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 accent-blue-600"
                />
                <div className="ml-3 flex-1">
                  <span className="font-medium text-slate-900">{source.name}</span>
                  <span className="text-slate-500 text-sm ml-2">{source.description}</span>
                </div>
              </label>
            ))}
          </div>
        </section>

        {/* Relevance Threshold */}
        <section className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Relevance Threshold</h2>
          <p className="text-sm text-slate-500 mb-4">
            Minimum relevance score for technologies to be added to your skill tree.
            Lower = more discoveries, Higher = only highly relevant.
          </p>

          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.1"
              value={localPrefs.relevance_threshold}
              onChange={(e) => handleThresholdChange(e.target.value)}
              className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <span className="w-12 text-center font-mono text-slate-700">
              {localPrefs.relevance_threshold.toFixed(1)}
            </span>
          </div>
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>More discoveries</span>
            <span>Higher quality</span>
          </div>
        </section>

        {/* Account */}
        <section className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Account</h2>
          <p className="text-sm text-slate-500 mb-4">
            Signed in as {user?.email}
          </p>

          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="px-4 py-2 rounded-lg font-medium text-sm bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            Logout
          </button>
        </section>
      </main>
    </div>
  );
};

export default SettingsPage;
