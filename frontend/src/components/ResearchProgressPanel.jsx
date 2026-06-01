import { useState } from 'react';

const SOURCE_ICONS = {
  HackerNews: '🟠',
  GitHub: '🐙',
  'Dev.to': '📝',
  Medium: '📰',
  ArXiv: '📄',
  StackOverflow: '📚',
  PyPI: '🐍',
};

const SOURCE_DESCRIPTIONS = {
  HackerNews: 'Tech news & discussions',
  GitHub: 'Trending repositories',
  'Dev.to': 'Developer articles',
  Medium: 'Tech blog posts',
  ArXiv: 'Research papers',
  StackOverflow: 'Q&A trends',
  PyPI: 'Python packages',
};

const PHASE_CONFIG = {
  idle: {
    label: 'Ready to Scan',
    color: 'bg-slate-400',
    icon: '⏸',
    description: 'Click Full Scan to discover new technologies'
  },
  collecting: {
    label: 'Gathering Data',
    color: 'bg-blue-500',
    icon: '📥',
    description: 'Fetching latest content from tech sources'
  },
  analyzing: {
    label: 'AI Analysis',
    color: 'bg-violet-600',
    icon: '🧠',
    description: 'Identifying relevant technologies for your role'
  },
  completed: {
    label: 'Scan Complete',
    color: 'bg-emerald-500',
    icon: '✓',
    description: 'Your skill tree has been updated'
  },
  failed: {
    label: 'Scan Failed',
    color: 'bg-red-500',
    icon: '✕',
    description: 'Something went wrong'
  },
};

const PHASE_STEPS = [
  { key: 'collecting', label: 'Collect', icon: '📥' },
  { key: 'analyzing', label: 'Analyze', icon: '🧠' },
  { key: 'completed', label: 'Done', icon: '✓' },
];

const ResearchProgressPanel = ({
  isOpen,
  currentPhase,
  sources,
  stats,
  discoveries,
  logs,
  error,
  onClose,
  onCancel,
  onRetry,
  isConnected,
  mode,
}) => {
  const [activeTab, setActiveTab] = useState('sources');
  const [isMinimized, setIsMinimized] = useState(false);

  if (!isOpen) return null;

  const phaseConfig = PHASE_CONFIG[currentPhase] || PHASE_CONFIG.idle;
  const isRunning = currentPhase === 'collecting' || currentPhase === 'analyzing';
  const isFinished = currentPhase === 'completed' || currentPhase === 'failed';

  const headerLabel = mode === 'topic'
    ? currentPhase === 'completed'
      ? 'Topic Added'
      : currentPhase === 'failed'
      ? 'Topic Failed'
      : 'Adding Topic'
    : phaseConfig.label;

  const progressPercent =
    stats.totalSources > 0
      ? Math.round((stats.sourcesCompleted / stats.totalSources) * 100)
      : 0;

  const sourceEntries = Object.entries(sources);
  const activeSources = sourceEntries.filter(([, d]) => d.status === 'fetching');
  const completedSources = sourceEntries.filter(([, d]) => d.status === 'completed');
  const failedSources = sourceEntries.filter(([, d]) => d.status === 'failed');

  const getStepStatus = (stepKey) => {
    if (currentPhase === 'failed') {
      if (stepKey === 'collecting' && currentPhase !== 'collecting') return 'completed';
      return 'failed';
    }
    if (currentPhase === stepKey) return 'active';
    if (currentPhase === 'completed') return 'completed';
    if (currentPhase === 'analyzing' && stepKey === 'collecting') return 'completed';
    return 'pending';
  };

  return (
    <div className={`fixed z-50 overflow-hidden transition-all duration-300
      sm:bottom-4 sm:right-4 sm:w-[420px] sm:max-w-[calc(100vw-2rem)] sm:rounded-2xl
      bottom-0 right-0 left-0 w-full rounded-t-2xl sm:left-auto
      bg-white shadow-2xl border border-slate-200
      ${isMinimized ? 'h-14' : ''}`}>
      {/* Header */}
      <div className={`${phaseConfig.color} text-white px-4 py-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center ${isRunning ? 'animate-pulse' : ''}`}>
              <span className="text-xl">{phaseConfig.icon}</span>
            </div>
            <div>
              <div className="font-semibold text-sm">{headerLabel}</div>
              <div className="text-xs text-white/80">{phaseConfig.description}</div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {!isConnected && isRunning && (
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full mr-2">Reconnecting...</span>
            )}
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="hover:bg-white/20 rounded-lg p-1.5 transition-colors"
              title={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? '▲' : '▼'}
            </button>
            <button
              onClick={onClose}
              className="hover:bg-white/20 rounded-lg p-1.5 transition-colors"
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Phase Steps */}
          <div className="px-4 py-3 border-b bg-slate-50">
            <div className="flex items-center justify-between">
              {PHASE_STEPS.map((step, i) => {
                const status = getStepStatus(step.key);
                return (
                  <div key={step.key} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all
                          ${status === 'active' ? 'bg-blue-500 text-white ring-4 ring-blue-100' : ''}
                          ${status === 'completed' ? 'bg-emerald-500 text-white' : ''}
                          ${status === 'pending' ? 'bg-slate-200 text-slate-400' : ''}
                          ${status === 'failed' ? 'bg-red-500 text-white' : ''}
                        `}
                      >
                        {status === 'completed' ? '✓' : step.icon}
                      </div>
                      <span className={`text-xs mt-1 font-medium ${status === 'active' ? 'text-blue-600' : status === 'completed' ? 'text-emerald-600' : 'text-slate-400'}`}>
                        {step.label}
                      </span>
                    </div>
                    {i < PHASE_STEPS.length - 1 && (
                      <div className={`w-16 h-1 mx-2 rounded-full transition-all ${
                        status === 'completed' || (status === 'active' && i === 0) ? 'bg-emerald-400' : 'bg-slate-200'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Overall Progress */}
          {isRunning && (
            <div className="px-4 py-3 border-b">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-700">
                  {currentPhase === 'collecting' ? 'Fetching sources...' : 'Analyzing content...'}
                </span>
                <span className="text-sm font-bold text-blue-600">
                  {currentPhase === 'collecting' ? `${progressPercent}%` : 'Processing...'}
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    currentPhase === 'analyzing'
                      ? 'bg-gradient-to-r from-violet-500 to-violet-400 animate-pulse w-full'
                      : 'bg-gradient-to-r from-blue-500 to-blue-400'
                  }`}
                  style={{ width: currentPhase === 'collecting' ? `${progressPercent}%` : '100%' }}
                />
              </div>
              {currentPhase === 'collecting' && (
                <div className="text-xs text-slate-500 mt-1">
                  {stats.sourcesCompleted} of {stats.totalSources} sources completed
                </div>
              )}
            </div>
          )}

          {/* Stats Row */}
          <div className="px-4 py-3 grid grid-cols-3 gap-3 border-b">
            <div className="bg-blue-50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.itemsCollected}</div>
              <div className="text-xs text-blue-600/70 font-medium">Items Fetched</div>
            </div>
            <div className="bg-violet-50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-violet-600">{stats.technologiesFound}</div>
              <div className="text-xs text-violet-600/70 font-medium">Tech Found</div>
            </div>
            <div className="bg-emerald-50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-emerald-600">{stats.newTechnologies}</div>
              <div className="text-xs text-emerald-600/70 font-medium">New Skills</div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('sources')}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'sources'
                  ? 'text-blue-600 border-b-2 border-blue-500 bg-blue-50/50'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Sources {sourceEntries.length > 0 && `(${completedSources.length}/${sourceEntries.length})`}
            </button>
            <button
              onClick={() => setActiveTab('discoveries')}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors relative ${
                activeTab === 'discoveries'
                  ? 'text-emerald-600 border-b-2 border-emerald-500 bg-emerald-50/50'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Discoveries
              {discoveries.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-emerald-500 text-white rounded-full">
                  {discoveries.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'logs'
                  ? 'text-slate-600 border-b-2 border-slate-500 bg-slate-50'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Activity
            </button>
          </div>

          {/* Tab Content */}
          <div className="max-h-56 overflow-y-auto">
            {/* Sources Tab */}
            {activeTab === 'sources' && (
              <div className="p-3 space-y-2">
                {sourceEntries.length === 0 ? (
                  <div className="text-center py-6 text-slate-400 text-sm">
                    Waiting for sources to start...
                  </div>
                ) : (
                  sourceEntries.map(([name, data]) => (
                    <div
                      key={name}
                      className={`rounded-xl p-3 transition-all ${
                        data.status === 'fetching' ? 'bg-blue-50 ring-1 ring-blue-200' :
                        data.status === 'completed' ? 'bg-emerald-50' :
                        data.status === 'failed' ? 'bg-red-50' : 'bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{SOURCE_ICONS[name] || '📦'}</span>
                          <div>
                            <span className="font-medium text-sm text-slate-800">{name}</span>
                            <div className="text-xs text-slate-500">{SOURCE_DESCRIPTIONS[name] || ''}</div>
                          </div>
                        </div>
                        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
                          data.status === 'fetching' ? 'bg-blue-100 text-blue-700' :
                          data.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                          data.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {data.status === 'fetching' && <span className="animate-spin">⟳</span>}
                          {data.status === 'completed' && '✓'}
                          {data.status === 'failed' && '✕'}
                          {data.status === 'pending' && '⏳'}
                          <span className="capitalize">{data.status}</span>
                        </div>
                      </div>
                      {data.status === 'fetching' && data.current && data.total && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs text-blue-600 mb-1">
                            <span>{data.detail || 'Processing...'}</span>
                            <span>{data.current}/{data.total}</span>
                          </div>
                          <div className="h-1.5 bg-blue-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 transition-all duration-300"
                              style={{ width: `${(data.current / data.total) * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                      {data.status === 'completed' && data.items > 0 && (
                        <div className="text-xs text-emerald-600 mt-1">
                          Found {data.items} items
                        </div>
                      )}
                      {data.status === 'failed' && (
                        <div className="text-xs text-red-600 mt-1">
                          {data.detail || 'Failed to fetch'}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Discoveries Tab */}
            {activeTab === 'discoveries' && (
              <div className="p-3">
                {discoveries.length === 0 ? (
                  <div className="text-center py-6 text-slate-400 text-sm">
                    {isRunning ? 'Waiting for discoveries...' : 'No new technologies found'}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {discoveries.slice().reverse().map((tech, i) => (
                      <div
                        key={`${tech.name}-${i}`}
                        className="flex items-center gap-3 p-3 bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl animate-fade-in"
                      >
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${
                          tech.isEmerging ? 'bg-amber-100' : 'bg-emerald-100'
                        }`}>
                          {tech.isEmerging ? '🚀' : tech.category === 'tool' ? '🔧' : tech.category === 'framework' ? '📦' : '💡'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-slate-800 text-sm truncate">{tech.name}</div>
                          <div className="flex items-center gap-2 text-xs">
                            {tech.category && (
                              <span className="text-slate-500 capitalize">{tech.category}</span>
                            )}
                            {tech.isEmerging && (
                              <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">
                                Emerging
                              </span>
                            )}
                            {tech.trend && (
                              <span className={`${
                                tech.trend === 'rising' ? 'text-emerald-600' :
                                tech.trend === 'falling' ? 'text-red-500' : 'text-slate-400'
                              }`}>
                                {tech.trend === 'rising' ? '↗' : tech.trend === 'falling' ? '↘' : '→'}
                              </span>
                            )}
                          </div>
                        </div>
                        {tech.relevance && (
                          <div className="text-right">
                            <div className="text-xs text-slate-400">Relevance</div>
                            <div className="text-sm font-bold text-blue-600">
                              {Math.round(tech.relevance * 100)}%
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Logs Tab */}
            {activeTab === 'logs' && (
              <div className="p-3">
                {(!logs || logs.length === 0) ? (
                  <div className="text-center py-6 text-slate-400 text-sm">
                    No activity yet
                  </div>
                ) : (
                  <div className="space-y-1 font-mono text-xs">
                    {logs.slice(-15).map((log, idx) => (
                      <div
                        key={`${log.timestamp}-${idx}`}
                        className={`py-1 px-2 rounded ${
                          log.level === 'error' ? 'bg-red-50 text-red-700' :
                          log.level === 'warning' ? 'bg-amber-50 text-amber-700' :
                          'text-slate-600'
                        }`}
                      >
                        <span className="text-slate-400 mr-2">
                          {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        {log.source && <span className="text-blue-500">[{log.source}]</span>}
                        {' '}{log.message}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="px-4 py-3 bg-red-50 border-t border-red-100">
              <div className="flex items-start gap-2">
                <span className="text-red-500">⚠️</span>
                <div>
                  <div className="text-sm font-medium text-red-700">Error</div>
                  <div className="text-xs text-red-600">{error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="px-4 py-3 border-t bg-slate-50 flex items-center justify-between gap-2">
            {isRunning && onCancel && (
              <button
                onClick={onCancel}
                className="flex-1 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-colors"
              >
                Cancel Scan
              </button>
            )}
            {currentPhase === 'failed' && onRetry && (
              <button
                onClick={onRetry}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-xl transition-colors"
              >
                Retry Scan
              </button>
            )}
            {isFinished && (
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
              >
                {currentPhase === 'completed' ? 'Done' : 'Close'}
              </button>
            )}
            {!isRunning && !isFinished && (
              <div className="text-xs text-slate-400 text-center flex-1">
                Ready to scan
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ResearchProgressPanel;
