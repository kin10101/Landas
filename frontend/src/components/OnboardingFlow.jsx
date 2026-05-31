import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserPreferences } from '../hooks/useUserPreferences';

const STEPS = {
  WELCOME: 0,
  ROLE: 1,
  SOURCES: 2,
  COMPLETE: 3,
};

const OnboardingFlow = () => {
  const navigate = useNavigate();
  const { defaults, updatePreferences, completeOnboarding } = useUserPreferences();
  const [step, setStep] = useState(STEPS.WELCOME);
  const [selectedRole, setSelectedRole] = useState('AI Engineer');
  const [enabledSources, setEnabledSources] = useState({
    hackernews: true,
    github_trending: true,
    devto: true,
    medium: true,
    arxiv: true,
    stackoverflow: true,
    pypi: true,
  });
  const [saving, setSaving] = useState(false);

  const handleSourceToggle = (sourceKey) => {
    setEnabledSources((prev) => ({
      ...prev,
      [sourceKey]: !prev[sourceKey],
    }));
  };

  const handleNext = async () => {
    if (step === STEPS.SOURCES) {
      setSaving(true);
      await updatePreferences({
        target_role: selectedRole,
        enabled_sources: enabledSources,
      });
      setSaving(false);
      setStep(STEPS.COMPLETE);
    } else {
      setStep(step + 1);
    }
  };

  const handleComplete = async () => {
    setSaving(true);
    await completeOnboarding();
    navigate('/');
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-8">
        {/* Progress indicator */}
        <div className="flex justify-center mb-8">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`w-3 h-3 rounded-full mx-1 transition-colors ${
                i <= step ? 'bg-blue-600' : 'bg-slate-200'
              }`}
            />
          ))}
        </div>

        {/* Welcome Step */}
        {step === STEPS.WELCOME && (
          <div className="text-center">
            <div className="flex justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" className="w-20 h-20">
                <defs>
                  <linearGradient id="treeGradientOnboard" x1="50%" y1="100%" x2="50%" y2="0%">
                    <stop offset="0%" stopColor="#1E40AF"/>
                    <stop offset="50%" stopColor="#3B82F6"/>
                    <stop offset="100%" stopColor="#60A5FA"/>
                  </linearGradient>
                </defs>
                <path d="M24 44 L24 28" stroke="url(#treeGradientOnboard)" strokeWidth="4" strokeLinecap="round"/>
                <path d="M24 28 Q20 24 14 18" stroke="url(#treeGradientOnboard)" strokeWidth="3" strokeLinecap="round" fill="none"/>
                <path d="M24 28 Q28 24 34 18" stroke="url(#treeGradientOnboard)" strokeWidth="3" strokeLinecap="round" fill="none"/>
                <path d="M24 28 L24 14" stroke="url(#treeGradientOnboard)" strokeWidth="3" strokeLinecap="round"/>
                <circle cx="14" cy="18" r="4" fill="#3B82F6"/>
                <circle cx="14" cy="18" r="2" fill="#DBEAFE"/>
                <circle cx="24" cy="14" r="4" fill="#3B82F6"/>
                <circle cx="24" cy="14" r="2" fill="#DBEAFE"/>
                <circle cx="34" cy="18" r="4" fill="#3B82F6"/>
                <circle cx="34" cy="18" r="2" fill="#DBEAFE"/>
                <path d="M14 18 Q10 14 8 10" stroke="#60A5FA" strokeWidth="2" strokeLinecap="round" fill="none"/>
                <circle cx="8" cy="10" r="2.5" fill="#60A5FA"/>
                <path d="M24 14 L24 6" stroke="#60A5FA" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="24" cy="6" r="2.5" fill="#60A5FA"/>
                <path d="M34 18 Q38 14 40 10" stroke="#60A5FA" strokeWidth="2" strokeLinecap="round" fill="none"/>
                <circle cx="40" cy="10" r="2.5" fill="#60A5FA"/>
              </svg>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4">Welcome to Landas</h1>
            <p className="text-xl text-slate-600 mb-8">
              Discover your path with AI-powered skill mapping.
            </p>
            <div className="bg-blue-50 rounded-xl p-6 mb-8 border border-blue-100">
              <h3 className="font-semibold text-blue-900 mb-2">What you'll get:</h3>
              <ul className="text-left text-blue-800 space-y-2">
                <li>• Personalized skill tree based on your career goals</li>
                <li>• Auto-updated with emerging technologies</li>
                <li>• Curated learning resources for each skill</li>
                <li>• Progress tracking to stay motivated</li>
              </ul>
            </div>
            <button
              onClick={handleNext}
              className="bg-blue-600 text-white px-8 py-3 rounded-xl font-semibold text-lg hover:bg-blue-700 transition-colors"
            >
              Get Started
            </button>
          </div>
        )}

        {/* Role Selection Step */}
        {step === STEPS.ROLE && (
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2 text-center">
              What's your target role?
            </h2>
            <p className="text-slate-600 mb-6 text-center">
              This helps us tailor your skill tree and research focus.
            </p>

            <div className="grid grid-cols-1 gap-3 mb-8">
              {availableRoles.map((role) => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    selectedRole === role
                      ? 'border-blue-600 bg-blue-50 text-blue-900'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <span className="font-semibold">{role}</span>
                </button>
              ))}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep(STEPS.WELCOME)}
                className="text-slate-500 hover:text-slate-700 font-medium"
              >
                Back
              </button>
              <button
                onClick={handleNext}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Sources Selection Step */}
        {step === STEPS.SOURCES && (
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2 text-center">
              Choose your research sources
            </h2>
            <p className="text-slate-600 mb-6 text-center">
              Select which sources to monitor for emerging technologies.
            </p>

            <div className="space-y-3 mb-8">
              {Object.entries(availableSources).map(([key, source]) => (
                <label
                  key={key}
                  className={`flex items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    enabledSources[key]
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={enabledSources[key]}
                    onChange={() => handleSourceToggle(key)}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 accent-blue-600"
                  />
                  <div className="ml-3">
                    <span className="font-semibold text-slate-900">{source.name}</span>
                    <p className="text-sm text-slate-500">{source.description}</p>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep(STEPS.ROLE)}
                className="text-slate-500 hover:text-slate-700 font-medium"
              >
                Back
              </button>
              <button
                onClick={handleNext}
                disabled={saving}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Continue'}
              </button>
            </div>
          </div>
        )}

        {/* Complete Step */}
        {step === STEPS.COMPLETE && (
          <div className="text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">You're all set!</h2>
            <p className="text-slate-600 mb-6">
              Your personalized roadmap for <strong>{selectedRole}</strong> is ready.
            </p>

            <div className="bg-emerald-50 rounded-xl p-6 mb-8 border border-emerald-100">
              <h3 className="font-semibold text-emerald-900 mb-2">What's next:</h3>
              <ul className="text-left text-emerald-800 space-y-2">
                <li>• Explore your skill tree and set progress</li>
                <li>• Run research to discover new technologies</li>
                <li>• Find learning resources for each skill</li>
              </ul>
            </div>

            <button
              onClick={handleComplete}
              disabled={saving}
              className="bg-emerald-600 text-white px-8 py-3 rounded-xl font-semibold text-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Loading...' : 'View My Roadmap'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingFlow;
