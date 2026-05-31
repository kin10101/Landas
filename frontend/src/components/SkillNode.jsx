import { useState } from 'react';

const SkillNode = ({ node, onNodeClick, onStatusChange, level = 0 }) => {
  const [isExpanded, setIsExpanded] = useState(level < 2);

  const hasChildren = node.children && node.children.length > 0;
  const progress = node.progress;
  const status = progress?.status || 'active';

  const difficultyStars = '★'.repeat(node.difficulty || 1) + '☆'.repeat(5 - (node.difficulty || 1));

  const levelClass = `level-${node.level}`;
  const statusClass = status;

  const handleClick = (e) => {
    e.stopPropagation();
    onNodeClick(node);
  };

  const handleToggle = (e) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  const handleStatusClick = (e, newStatus) => {
    e.stopPropagation();
    onStatusChange(node.id, newStatus);
  };

  return (
    <div className={`tree-branch animate-fade-in`} style={{ animationDelay: `${level * 50}ms` }}>
      <div
        className={`tree-node ${levelClass}`}
        data-node-id={node.id}
        data-parent-id={node.parent_id || ''}
        data-status={status}
      >
        <div
          className={`node-card ${statusClass} relative`}
          onClick={handleClick}
        >
          {/* Progress Badge */}
          {status === 'completed' && (
            <span className="progress-badge completed">✓</span>
          )}
          {status === 'in_progress' && (
            <span className="progress-badge in-progress">→</span>
          )}

          {/* Node Content */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className={`font-medium text-sm leading-tight ${node.level === 'role' ? 'text-white text-lg' : 'text-slate-800'}`}>
                {node.name}
              </h3>
              {node.level !== 'role' && (
                <div className="difficulty-stars mt-1">{difficultyStars}</div>
              )}
            </div>

            {hasChildren && (
              <button
                onClick={handleToggle}
                className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs
                  ${node.level === 'role' ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {isExpanded ? '−' : `+${node.children.length}`}
              </button>
            )}
          </div>

          {/* Quick Status Buttons */}
          {node.level !== 'role' && (
            <div className="flex gap-1 mt-2 pt-2 border-t border-slate-100">
              <button
                onClick={(e) => handleStatusClick(e, 'completed')}
                className={`flex-1 text-xs py-1 rounded transition-colors ${status === 'completed' ? 'bg-emerald-500 text-white' : 'bg-slate-100 hover:bg-emerald-100 text-slate-600'}`}
                title="Mark as completed"
              >
                ✓
              </button>
              <button
                onClick={(e) => handleStatusClick(e, 'in_progress')}
                className={`flex-1 text-xs py-1 rounded transition-colors ${status === 'in_progress' ? 'bg-blue-500 text-white' : 'bg-slate-100 hover:bg-blue-100 text-slate-600'}`}
                title="Mark as in progress"
              >
                →
              </button>
              <button
                onClick={(e) => handleStatusClick(e, 'removed')}
                className={`flex-1 text-xs py-1 rounded transition-colors ${status === 'removed' ? 'bg-slate-500 text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-600'}`}
                title="Remove from roadmap"
              >
                ✕
              </button>
            </div>
          )}

          {/* Resource Count */}
          {node.resources && node.resources.length > 0 && (
            <div className="text-xs text-blue-600 mt-1 flex items-center gap-1">
              <span>📚</span>
              <span>{node.resources.length} resources</span>
            </div>
          )}
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="tree-children">
          {node.children
            .filter(child => child.progress?.status !== 'removed')
            .map((child) => (
              <SkillNode
                key={child.id}
                node={child}
                onNodeClick={onNodeClick}
                onStatusChange={onStatusChange}
                level={level + 1}
              />
            ))}
        </div>
      )}
    </div>
  );
};

export default SkillNode;
