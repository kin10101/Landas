const SOURCE_ICONS = {
  HackerNews: '🟠',
  GitHub: '🐙',
  'Dev.to': '📝',
  Medium: '📰',
  ArXiv: '📄',
  StackOverflow: '📚',
  PyPI: '🐍',
};

const PHASE_CONFIG = {
  idle: { label: 'Ready', color: 'bg-slate-400', icon: '⏸' },
  collecting: { label: 'Collecting Data', color: 'bg-blue-500', icon: '📥' },
  analyzing: { label: 'Analyzing with AI', color: 'bg-blue-700', icon: '🧠' },
  completed: { label: 'Completed', color: 'bg-emerald-500', icon: '✓' },
  failed: { label: 'Failed', color: 'bg-red-500', icon: '✕' },
};

const STATUS_ICONS = {
  pending: '⏳',
  fetching: '🔄',
  completed: '✓',
  failed: '✕',
};

const ResearchProgressPanel = ({
  isOpen,
  currentPhase,
  sources,
  stats,
  discoveries,
  error,
  onClose,
  isConnected,
}) => {
  if (!isOpen) return null;

  const phaseConfig = PHASE_CONFIG[currentPhase] || PHASE_CONFIG.idle;
  const progressPercent =
    stats.totalSources > 0
      ? Math.round((stats.sourcesCompleted / stats.totalSources) * 100)
      : 0;

  const sourceEntries = Object.entries(sources);

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 overflow-hidden">
      {/* Header */}
      <div className={`${phaseConfig.color} text-white px-4 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{phaseConfig.icon}</span>
          <span className="font-semibold">{phaseConfig.label}</span>
          {!isConnected && currentPhase !== 'completed' && currentPhase !== 'failed' && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">Polling</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="hover:bg-white/20 rounded-full p-1 transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Progress Bar */}
      {currentPhase === 'collecting' && (
        <div className="px-4 py-2 bg-slate-50 border-b">
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Sources Progress</span>
            <span>{stats.sourcesCompleted}/{stats.totalSources}</span>
          </div>
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Phase Indicator */}
      <div className="px-4 py-3 border-b flex justify-between">
        {['collecting', 'analyzing', 'completed'].map((phase, i) => (
          <div key={phase} className="flex items-center">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                ${
                  currentPhase === phase
                    ? 'bg-blue-500 text-white'
                    : ['completed', 'failed'].includes(currentPhase) ||
                      (currentPhase === 'analyzing' && phase === 'collecting')
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-200 text-slate-500'
                }`}
            >
              {i + 1}
            </div>
            {i < 2 && (
              <div
                className={`w-8 h-0.5 mx-1
                  ${
                    (currentPhase === 'analyzing' && phase === 'collecting') ||
                    currentPhase === 'completed'
                      ? 'bg-emerald-500'
                      : 'bg-slate-200'
                  }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="px-4 py-3 grid grid-cols-3 gap-2 border-b bg-slate-50">
        <div className="text-center">
          <div className="text-lg font-bold text-blue-600">{stats.itemsCollected}</div>
          <div className="text-xs text-slate-500">Items</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-blue-700">{stats.technologiesFound}</div>
          <div className="text-xs text-slate-500">Technologies</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-emerald-600">{stats.newTechnologies}</div>
          <div className="text-xs text-slate-500">New</div>
        </div>
      </div>

      {/* Sources List */}
      <div className="px-4 py-2 max-h-48 overflow-y-auto">
        <div className="text-xs font-medium text-slate-500 mb-2">Sources</div>
        <div className="space-y-1">
          {sourceEntries.map(([name, data]) => (
            <div
              key={name}
              className={`flex items-center justify-between py-1.5 px-2 rounded text-sm
                ${data.status === 'fetching' ? 'bg-blue-50' : ''}
                ${data.status === 'completed' ? 'bg-emerald-50' : ''}
                ${data.status === 'failed' ? 'bg-red-50' : ''}`}
            >
              <div className="flex items-center gap-2">
                <span>{SOURCE_ICONS[name] || '📦'}</span>
                <span className="font-medium">{name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 truncate max-w-24">
                  {data.detail}
                </span>
                <span
                  className={`
                    ${data.status === 'fetching' ? 'animate-spin' : ''}
                    ${data.status === 'completed' ? 'text-emerald-600' : ''}
                    ${data.status === 'failed' ? 'text-red-600' : ''}
                  `}
                >
                  {STATUS_ICONS[data.status] || '⏳'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Discoveries Preview */}
      {discoveries.length > 0 && (
        <div className="px-4 py-2 border-t bg-blue-50">
          <div className="text-xs font-medium text-blue-700 mb-1">
            Latest Discoveries
          </div>
          <div className="flex flex-wrap gap-1">
            {discoveries.slice(-5).map((tech, i) => (
              <span
                key={i}
                className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
              >
                {tech.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200">
          <div className="text-sm text-red-700">{error}</div>
        </div>
      )}
    </div>
  );
};

export default ResearchProgressPanel;
