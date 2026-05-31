const ResourcePanel = ({ node, isOpen, onClose, onStatusChange }) => {
  if (!node) return null;

  const status = node.progress?.status || 'active';
  const difficultyStars = '★'.repeat(node.difficulty || 1) + '☆'.repeat(5 - (node.difficulty || 1));

  const getResourceIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'docs': return '📄';
      case 'tutorial': return '📖';
      case 'video': return '🎬';
      case 'course': return '🎓';
      case 'article': return '📰';
      default: return '🔗';
    }
  };

  const handleStatusChange = (newStatus) => {
    onStatusChange(node.id, newStatus);
  };

  return (
    <div className={`resource-panel ${isOpen ? '' : 'hidden'}`}>
      {/* Header */}
      <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-start justify-between">
        <div>
          <span className="text-xs text-blue-600 uppercase tracking-wide">{node.level}</span>
          <h2 className="text-xl font-semibold text-slate-900 mt-1">{node.name}</h2>
          <div className="difficulty-stars text-lg mt-1">{difficultyStars}</div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Description */}
        {node.description && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-2">Description</h3>
            <p className="text-slate-700">{node.description}</p>
          </div>
        )}

        {/* Progress Status */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3">Your Progress</h3>
          <div className="flex gap-2">
            <button
              onClick={() => handleStatusChange('active')}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                ${status === 'active' ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Not Started
            </button>
            <button
              onClick={() => handleStatusChange('in_progress')}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                ${status === 'in_progress' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              In Progress
            </button>
            <button
              onClick={() => handleStatusChange('completed')}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors
                ${status === 'completed' ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Completed
            </button>
          </div>
          <button
            onClick={() => handleStatusChange('removed')}
            className={`w-full mt-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors
              ${status === 'removed' ? 'bg-slate-500 text-white' : 'bg-slate-50 text-slate-500 hover:bg-slate-100 border border-slate-200'}`}
          >
            Remove from my roadmap
          </button>
        </div>

        {/* Resources */}
        <div>
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3">
            Learning Resources ({node.resources?.length || 0})
          </h3>

          {node.resources && node.resources.length > 0 ? (
            <div className="space-y-3">
              {node.resources.map((resource, idx) => (
                <a
                  key={idx}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl">{getResourceIcon(resource.resource_type)}</span>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-slate-900 truncate">{resource.title}</h4>
                      <p className="text-xs text-slate-500 mt-1 truncate">{resource.url}</p>
                      <span className="inline-block mt-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        {resource.resource_type}
                      </span>
                    </div>
                    <span className="text-slate-400">→</span>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm italic">
              No resources yet. Resources will be added as the research agent discovers them.
            </p>
          )}
        </div>

        {/* Children Preview */}
        {node.children && node.children.length > 0 && (
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3">
              Sub-skills ({node.children.length})
            </h3>
            <div className="flex flex-wrap gap-2">
              {node.children.map((child) => (
                <span
                  key={child.id}
                  className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded"
                >
                  {child.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResourcePanel;
