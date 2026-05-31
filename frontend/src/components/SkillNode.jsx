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
      <div className={`tree-node ${levelClass}`}>
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
              <h3 className={`font-medium text-sm leading-tight ${node.level === 'role' ? 'text-white text-lg' : 'text-gray-800'}`}>
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
                  ${node.level === 'role' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                {isExpanded ? '−' : '+'}
              </button>
            )}
          </div>

          {/* Quick Status Buttons */}
          {node.level !== 'role' && (
            <div className="flex gap-1 mt-2 pt-2 border-t border-gray-100">
              <button
                onClick={(e) => handleStatusClick(e, 'completed')}
                className={`flex-1 text-xs py-1 rounded ${status === 'completed' ? 'bg-green-500 text-white' : 'bg-gray-100 hover:bg-green-100'}`}
                title="Mark as completed"
              >
                ✓
              </button>
              <button
                onClick={(e) => handleStatusClick(e, 'in_progress')}
                className={`flex-1 text-xs py-1 rounded ${status === 'in_progress' ? 'bg-amber-500 text-white' : 'bg-gray-100 hover:bg-amber-100'}`}
                title="Mark as in progress"
              >
                →
              </button>
              <button
                onClick={(e) => handleStatusClick(e, 'removed')}
                className={`flex-1 text-xs py-1 rounded ${status === 'removed' ? 'bg-gray-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
                title="Remove from roadmap"
              >
                ✕
              </button>
            </div>
          )}

          {/* Resource Count */}
          {node.resources && node.resources.length > 0 && (
            <div className="text-xs text-blue-500 mt-1">
              📚 {node.resources.length} resources
            </div>
          )}
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="tree-children">
          {node.children.map((child) => (
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
