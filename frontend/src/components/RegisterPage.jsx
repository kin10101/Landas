import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    const result = await register(email, password, name || null);

    if (result.success) {
      navigate('/onboarding', { replace: true });
    } else {
      setError(result.error);
    }

    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" className="w-16 h-16">
              <defs>
                <linearGradient id="treeGradientReg" x1="50%" y1="100%" x2="50%" y2="0%">
                  <stop offset="0%" stopColor="#1E40AF"/>
                  <stop offset="50%" stopColor="#3B82F6"/>
                  <stop offset="100%" stopColor="#60A5FA"/>
                </linearGradient>
              </defs>
              <path d="M24 44 L24 28" stroke="url(#treeGradientReg)" strokeWidth="4" strokeLinecap="round"/>
              <path d="M24 28 Q20 24 14 18" stroke="url(#treeGradientReg)" strokeWidth="3" strokeLinecap="round" fill="none"/>
              <path d="M24 28 Q28 24 34 18" stroke="url(#treeGradientReg)" strokeWidth="3" strokeLinecap="round" fill="none"/>
              <path d="M24 28 L24 14" stroke="url(#treeGradientReg)" strokeWidth="3" strokeLinecap="round"/>
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
          <h1 className="text-center text-4xl font-bold text-white">Landas</h1>
          <h2 className="mt-2 text-center text-lg text-slate-400">
            Create your account
          </h2>
        </div>

        <form className="mt-8 space-y-6 bg-slate-800/80 backdrop-blur p-8 rounded-xl shadow-xl border border-slate-700/50" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1">
                Name (optional)
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Your name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Confirm your password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating account...
              </span>
            ) : (
              'Create account'
            )}
          </button>

          <div className="text-center">
            <p className="text-slate-400 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RegisterPage;
