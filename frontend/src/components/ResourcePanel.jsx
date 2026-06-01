import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from './Toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const DEFAULT_PANEL_WIDTH = 384;
const MIN_PANEL_WIDTH = 280;
const MAX_PANEL_WIDTH = 720;

const ResourcePanel = ({ node, isOpen, onClose, onStatusChange, onResourceAdded }) => {
  if (!node) return null;

  const toast = useToast();
  const { authFetch } = useAuth();
  const [panelWidth, setPanelWidth] = useState(DEFAULT_PANEL_WIDTH);
  const [isMobile, setIsMobile] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStateRef = useRef({ startX: 0, startWidth: DEFAULT_PANEL_WIDTH });

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isAdding, setIsAdding] = useState(null);
  const [isDeleting, setIsDeleting] = useState(null);
  const [showSearch, setShowSearch] = useState(false);
  const lastAutoSearchNodeId = useRef(null);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      setShowSearch(false);
      setSearchResults([]);
      setSearchQuery('');
      lastAutoSearchNodeId.current = null;
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (event) => {
      const maxWidth = Math.min(window.innerWidth * 0.7, MAX_PANEL_WIDTH);
      const delta = resizeStateRef.current.startX - event.clientX;
      const nextWidth = Math.min(
        Math.max(resizeStateRef.current.startWidth + delta, MIN_PANEL_WIDTH),
        maxWidth
      );
      setPanelWidth(nextWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

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

  const handleResizeStart = (event) => {
    if (isMobile) return;
    setIsResizing(true);
    resizeStateRef.current = {
      startX: event.clientX,
      startWidth: panelWidth,
    };
  };

  const searchPlaceholder = useMemo(() => {
    if (!node?.name) return 'Search resources...';
    return `Search resources for ${node.name}`;
  }, [node?.name]);

  const handleResourceSearch = async (queryOverride) => {
    const query = (queryOverride ?? searchQuery).trim();
    if (!query || isSearching) return;
    setIsSearching(true);
    try {
      const res = await fetch(`${API_URL}/resources/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          skill_name: node.name,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to search resources');
      }

      const data = await res.json();
      setSearchResults(data.resources || []);
      if ((data.resources || []).length === 0) {
        toast.info('No resources found. Try a different query.');
      }
    } catch (e) {
      toast.error(e.message || 'Failed to search resources');
    } finally {
      setIsSearching(false);
    }
  };

  const handleToggleSearch = () => {
    setShowSearch((prev) => {
      const next = !prev;
      if (next && node?.name && lastAutoSearchNodeId.current !== node.id) {
        lastAutoSearchNodeId.current = node.id;
        setSearchQuery(node.name);
        handleResourceSearch(node.name);
      }
      return next;
    });
  };

  const handleAddResource = async (resource) => {
    if (isAdding) return;
    setIsAdding(resource.url);
    try {
      const res = await authFetch(`${API_URL}/resources/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_node_id: node.id,
          title: resource.title,
          url: resource.url,
          resource_type: resource.resource_type || 'article',
          source: resource.source,
        }),
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to add resource');
      }

      toast.success('Resource added to this skill.');
      if (onResourceAdded) onResourceAdded();
    } catch (e) {
      toast.error(e.message || 'Failed to add resource');
    } finally {
      setIsAdding(null);
    }
  };

  const handleDeleteResource = async (resource) => {
    if (isDeleting) return;
    setIsDeleting(resource.id);
    try {
      const res = await authFetch(`${API_URL}/resources/${resource.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to delete resource');
      }
      toast.success('Resource removed.');
      if (onResourceAdded) onResourceAdded();
    } catch (e) {
      toast.error(e.message || 'Failed to delete resource');
    } finally {
      setIsDeleting(null);
    }
  };

  return (
    <div
      className={`resource-panel ${isOpen ? '' : 'hidden'}`}
      style={!isMobile ? { width: `${panelWidth}px` } : undefined}
    >
      <div
        className="resource-panel-resizer"
        onMouseDown={handleResizeStart}
        aria-hidden="true"
      />
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
              {node.resources.map((resource) => (
                <div
                  key={resource.id || resource.url}
                  className="p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl">{getResourceIcon(resource.resource_type)}</span>
                    <a
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 min-w-0"
                    >
                      <h4 className="font-medium text-slate-900 truncate">{resource.title}</h4>
                      <p className="text-xs text-slate-500 mt-1 truncate">{resource.url}</p>
                      <span className="inline-block mt-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        {resource.resource_type}
                      </span>
                    </a>
                    <button
                      onClick={() => handleDeleteResource(resource)}
                      className="text-slate-400 hover:text-slate-600"
                      disabled={isDeleting === resource.id}
                      aria-label="Delete resource"
                      title="Delete resource"
                    >
                      {isDeleting === resource.id ? (
                        <span className="text-xs">...</span>
                      ) : (
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M8 6v-1a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1" />
                          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                          <line x1="10" y1="11" x2="10" y2="17" />
                          <line x1="14" y1="11" x2="14" y2="17" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm italic">
              No resources yet. Resources will be added as the research agent discovers them.
            </p>
          )}
        </div>

        {/* Search Resources */}
        <div className="mt-6 pt-6 border-t">
          <button
            onClick={handleToggleSearch}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-blue-200 bg-blue-50 text-sm font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
          >
            <span>Find More Resources</span>
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
          </button>

          {showSearch && (
            <div className="mt-3">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleResourceSearch()}
                  placeholder={searchPlaceholder}
                  className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={() => handleResourceSearch()}
                  disabled={!searchQuery.trim() || isSearching}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    !searchQuery.trim() || isSearching
                      ? 'bg-slate-100 text-slate-400'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {isSearching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="mt-4 space-y-3">
                  {searchResults.map((resource) => (
                    <div
                      key={resource.url}
                      className="p-3 border border-slate-200 rounded-lg bg-white"
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-xl">{getResourceIcon(resource.resource_type)}</span>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-slate-900 truncate">{resource.title}</h4>
                          <p className="text-xs text-slate-500 mt-1 truncate">{resource.url}</p>
                          <div className="mt-2 flex items-center gap-2">
                            <span className="inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                              {resource.resource_type}
                            </span>
                            {resource.source && (
                              <span className="text-xs text-slate-400">{resource.source}</span>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => handleAddResource(resource)}
                          className="text-xs text-emerald-600 hover:text-emerald-700 font-medium"
                          disabled={isAdding === resource.url}
                        >
                          {isAdding === resource.url ? 'Adding...' : 'Add'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
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
