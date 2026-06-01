import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import SkillNode from './SkillNode';
import ResourcePanel from './ResourcePanel';
import ResearchProgressPanel from './ResearchProgressPanel';
import TreeControls from './TreeControls';
import TreeSkeleton from './TreeSkeleton';
import { useResearchSSE } from '../hooks/useResearchSSE';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from './Toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const SkillTree = () => {
  const [treeData, setTreeData] = useState(null);
  const [currentTreeId, setCurrentTreeId] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, completed: 0, inProgress: 0 });
  const [researchStatus, setResearchStatus] = useState({ running: false, last_run: null });
  const [connections, setConnections] = useState([]);
  const [topicInput, setTopicInput] = useState('');
  const [isResearchingTopic, setIsResearchingTopic] = useState(false);
  const [showProgressPanel, setShowProgressPanel] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [focusedNodeId, setFocusedNodeId] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [scrollPos, setScrollPos] = useState({ x: 0, y: 0 });

  const treeRef = useRef(null);
  const containerRef = useRef(null);
  const rafIdRef = useRef(null);
  const toast = useToast();
  const { preferences, loading: prefsLoading } = useUserPreferences();
  const { authFetch, user, logout } = useAuth();

  const {
    isConnected,
    currentPhase,
    sources,
    stats: researchStats,
    discoveries,
    error: researchError,
    startResearch,
    startTopicResearch,
    stopResearch,
    reset: resetResearch,
    PHASES,
    logs,
    mode,
    topicResult,
  } = useResearchSSE();

  useEffect(() => {
    if (!prefsLoading && preferences?.target_role) {
      loadTreeForRole(preferences.target_role);
    }
    checkResearchStatus();
  }, [prefsLoading, preferences?.target_role]);

  const loadTreeForRole = async (targetRole) => {
    setLoading(true);
    try {
      const treesRes = await authFetch(`${API_URL}/trees`);
      if (!treesRes.ok) throw new Error('Failed to load trees');

      const { trees } = await treesRes.json();
      const matchingTree = trees.find(
        t => t.name.toLowerCase() === targetRole.toLowerCase()
      );

      if (matchingTree) {
        await loadTree(Number(matchingTree.id));
      } else {
        toast.info(`Generating skill tree for ${targetRole}...`);
        const genRes = await authFetch(`${API_URL}/tree/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: targetRole }),
        });

        if (genRes.ok) {
          const data = await genRes.json();
          const id = Number(data.id);
          if (!id) throw new Error('Invalid tree ID returned from server');
          await loadTree(id);
          toast.success(`Skill tree for ${targetRole} created!`);
        } else {
          throw new Error('Failed to generate tree');
        }
      }
    } catch (e) {
      console.error('Error loading tree for role:', e);
      setLoading(false);
      toast.error('Failed to load skill tree');
    }
  };

  const loadTree = async (treeId = currentTreeId) => {
    if (!treeId || typeof treeId !== 'number') return;
    try {
      const res = await authFetch(`${API_URL}/tree/${treeId}`);
      if (res.ok) {
        const data = await res.json();
        setTreeData(data);
        setCurrentTreeId(treeId);
        calculateStats(data);
        initializeExpandedNodes(data);
        setLoading(false);
        return;
      }
    } catch (e) {
      console.log('API not available, using local JSON');
    }

    fetch('/skill_tree.json')
      .then((res) => res.json())
      .then((data) => {
        setTreeData(data);
        calculateStats(data);
        initializeExpandedNodes(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load skill tree:', err);
        setLoading(false);
        toast.error('Failed to load skill tree');
      });
  };

  const initializeExpandedNodes = (node, level = 0, expanded = new Set()) => {
    if (level < 2) expanded.add(node.id);
    node.children?.forEach(child => initializeExpandedNodes(child, level + 1, expanded));
    setExpandedNodes(expanded);
  };

  const checkResearchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/research/status`);
      if (res.ok) {
        const data = await res.json();
        setResearchStatus(data);
      }
    } catch (e) {}
  };

  const calculateConnections = useCallback(() => {
    if (!treeRef.current) return;

    const newConnections = [];
    const nodes = treeRef.current.querySelectorAll('[data-node-id]');
    const currentZoom = zoom || 1;

    nodes.forEach((node) => {
      const parentId = node.dataset.parentId;
      if (parentId) {
        const parentNode = treeRef.current.querySelector(`[data-node-id="${parentId}"]`);
        if (parentNode) {
          const parentRect = parentNode.getBoundingClientRect();
          const childRect = node.getBoundingClientRect();
          const treeRect = treeRef.current.getBoundingClientRect();

          const parentStatus = parentNode.dataset.status || 'active';
          const childStatus = node.dataset.status || 'active';

          let color = '#D6D3D1';
          if (parentStatus === 'completed' && childStatus === 'completed') {
            color = '#65A30D';
          } else if (parentStatus === 'completed' || childStatus === 'in_progress') {
            color = '#EA580C';
          }

          newConnections.push({
            id: `${parentId}-${node.dataset.nodeId}`,
            x1: (parentRect.left + parentRect.width / 2 - treeRect.left) / currentZoom,
            y1: (parentRect.bottom - treeRect.top) / currentZoom,
            x2: (childRect.left + childRect.width / 2 - treeRect.left) / currentZoom,
            y2: (childRect.top - treeRect.top) / currentZoom,
            color,
            completed: parentStatus === 'completed' && childStatus === 'completed',
          });
        }
      }
    });

    setConnections(newConnections);
  }, [zoom]);

  const scheduleConnections = useCallback(() => {
    if (rafIdRef.current) return;
    rafIdRef.current = window.requestAnimationFrame(() => {
      rafIdRef.current = null;
      calculateConnections();
    });
  }, [calculateConnections]);

  useEffect(() => {
    if (treeData && treeRef.current) {
      scheduleConnections();
    }
  }, [treeData, expandedNodes, zoom, scheduleConnections]);

  useEffect(() => {
    window.addEventListener('resize', scheduleConnections);
    return () => window.removeEventListener('resize', scheduleConnections);
  }, [scheduleConnections]);

  useEffect(() => {
    const containerEl = containerRef.current;
    if (!containerEl) return undefined;

    const handleScroll = () => scheduleConnections();
    containerEl.addEventListener('scroll', handleScroll, { passive: true });

    let resizeObserver = null;
    if ('ResizeObserver' in window && treeRef.current) {
      resizeObserver = new ResizeObserver(() => scheduleConnections());
      resizeObserver.observe(treeRef.current);
      resizeObserver.observe(containerEl);
    }

    return () => {
      containerEl.removeEventListener('scroll', handleScroll);
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, [scheduleConnections]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.ctrlKey || e.metaKey) {
        if (e.key === '=' || e.key === '+') {
          e.preventDefault();
          setZoom(z => Math.min(z + 0.1, 2));
        } else if (e.key === '-') {
          e.preventDefault();
          setZoom(z => Math.max(z - 0.1, 0.3));
        } else if (e.key === '0') {
          e.preventDefault();
          setZoom(1);
        }
      }

      switch (e.key.toLowerCase()) {
        case 'e':
          if (!e.ctrlKey && !e.metaKey) handleExpandAll();
          break;
        case 'c':
          if (!e.ctrlKey && !e.metaKey) handleCollapseAll();
          break;
        case 'f':
          if (!e.ctrlKey && !e.metaKey) handleFitView();
          break;
        case 'r':
          if (!e.ctrlKey && !e.metaKey) handleResetView();
          break;
        case 'escape':
          setIsPanelOpen(false);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const calculateStats = (node, stats = { total: 0, completed: 0, inProgress: 0 }) => {
    if (node.level !== 'role') {
      stats.total++;
      if (node.progress?.status === 'completed') stats.completed++;
      if (node.progress?.status === 'in_progress') stats.inProgress++;
    }
    node.children?.forEach((child) => calculateStats(child, stats));
    setStats({ ...stats });
    return stats;
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    setIsPanelOpen(true);
    setFocusedNodeId(node.id);
  };

  const handleToggleExpand = (nodeId) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
    scheduleConnections();
  };

  const handleStatusChange = async (nodeId, newStatus) => {
    const updateNodeStatus = (node) => {
      if (node.id === nodeId) {
        return { ...node, progress: { ...node.progress, status: newStatus } };
      }
      if (node.children) {
        return { ...node, children: node.children.map(updateNodeStatus) };
      }
      return node;
    };

    const updatedTree = updateNodeStatus(treeData);
    setTreeData(updatedTree);
    calculateStats(updatedTree);

    if (selectedNode?.id === nodeId) {
      setSelectedNode({ ...selectedNode, progress: { ...selectedNode.progress, status: newStatus } });
    }

    scheduleConnections();

    try {
      await authFetch(`${API_URL}/progress/${nodeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (e) {}
  };

  useEffect(() => {
    if (currentPhase === PHASES.COMPLETED && mode === 'full') {
      loadTree();
      checkResearchStatus();
      toast.success('Research completed! Tree updated with new skills.');
    } else if (currentPhase === PHASES.FAILED && mode === 'full') {
      toast.error('Research failed. Please try again.');
    }
  }, [currentPhase, mode, PHASES.COMPLETED, PHASES.FAILED]);

  useEffect(() => {
    if (!topicResult) return;
    if (topicResult.success) {
      loadTree();
      setTopicInput('');
      if (topicResult.nodes_added > 1) {
        const nodeNames = topicResult.nodes.map(n => n.name).join(', ');
        toast.success(`Added ${topicResult.nodes_added} skills: ${nodeNames}`);
      } else if (topicResult.nodes?.length === 1) {
        toast.success(`Added "${topicResult.nodes[0].name}" under "${topicResult.placement?.parent_name || 'this tree'}"`);
      }
    } else {
      toast.error(topicResult.message || 'Could not add topic');
    }
    setIsResearchingTopic(false);
  }, [topicResult]);

  useEffect(() => {
    if (currentPhase !== PHASES.FAILED || mode !== 'topic') return;
    toast.error(researchError || 'Topic research failed. Please try again.');
    setIsResearchingTopic(false);
  }, [currentPhase, mode, PHASES.FAILED, researchError]);

  const handleRunResearch = async () => {
    setShowProgressPanel(true);
    setResearchStatus({ ...researchStatus, running: true });
    toast.info('Starting full scan...');
    await startResearch();
  };

  const handleCancelResearch = () => {
    stopResearch();
    resetResearch();
    setResearchStatus({ ...researchStatus, running: false });
    toast.info('Scan cancelled');
    setTimeout(() => setShowProgressPanel(false), 1000);
  };

  const handleCloseProgressPanel = () => {
    setShowProgressPanel(false);
    if (currentPhase === PHASES.COMPLETED || currentPhase === PHASES.FAILED) {
      resetResearch();
    }
  };

  const handleTopicResearch = async () => {
    if (!topicInput.trim() || isResearchingTopic) return;

    setIsResearchingTopic(true);
    setShowProgressPanel(true);
    toast.info(`Researching "${topicInput}"...`);

    try {
      await startTopicResearch({
        topic: topicInput.trim(),
        treeId: treeData?.id || currentTreeId,
      });
    } catch (e) {
      toast.error('API not available. Make sure the backend is running.');
      setIsResearchingTopic(false);
    }
  };

  const handleClosePanel = () => setIsPanelOpen(false);

  const handleExpandAll = () => {
    const allIds = new Set();
    const collectIds = (node) => {
      allIds.add(node.id);
      node.children?.forEach(collectIds);
    };
    if (treeData) collectIds(treeData);
    setExpandedNodes(allIds);
    toast.info('All nodes expanded');
  };

  const handleCollapseAll = () => {
    if (treeData) {
      setExpandedNodes(new Set([treeData.id]));
      toast.info('All nodes collapsed');
    }
  };

  const handleFitView = () => {
    if (!containerRef.current || !treeRef.current) return;
    const containerWidth = containerRef.current.clientWidth;
    const treeWidth = treeRef.current.scrollWidth;
    const newZoom = Math.min(Math.max(containerWidth / treeWidth * 0.9, 0.3), 1);
    setZoom(newZoom);
  };

  const handleResetView = () => {
    setZoom(1);
    if (containerRef.current) {
      containerRef.current.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    }
  };

  const handleMouseDown = (e) => {
    if (e.button !== 0 || e.target.closest('.node-card')) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setScrollPos({
      x: containerRef.current?.scrollLeft || 0,
      y: containerRef.current?.scrollTop || 0,
    });
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !containerRef.current) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    containerRef.current.scrollLeft = scrollPos.x - dx;
    containerRef.current.scrollTop = scrollPos.y - dy;
    scheduleConnections();
  };

  const handleMouseUp = () => setIsDragging(false);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <header className="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="animate-pulse flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-200" />
                <div>
                  <div className="h-5 w-20 bg-slate-200 rounded mb-1" />
                  <div className="h-3 w-32 bg-slate-100 rounded" />
                </div>
              </div>
              <div className="h-10 w-64 bg-slate-200 rounded-xl" />
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8">
          <TreeSkeleton />
        </main>
      </div>
    );
  }

  if (!treeData) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="text-center p-8 bg-white rounded-xl shadow-lg max-w-md">
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Failed to load skill tree</h2>
          <p className="text-slate-500 mb-4">Make sure the API is running or skill_tree.json exists</p>
          <button
            onClick={loadTree}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const progressPercent = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-sm overflow-hidden">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" className="w-8 h-8">
                  <defs>
                    <linearGradient id="treeGradientHeader" x1="50%" y1="100%" x2="50%" y2="0%">
                      <stop offset="0%" stopColor="#DBEAFE"/>
                      <stop offset="100%" stopColor="#FFFFFF"/>
                    </linearGradient>
                  </defs>
                  <path d="M24 44 L24 28" stroke="url(#treeGradientHeader)" strokeWidth="4" strokeLinecap="round"/>
                  <path d="M24 28 Q20 24 14 18" stroke="url(#treeGradientHeader)" strokeWidth="3" strokeLinecap="round" fill="none"/>
                  <path d="M24 28 Q28 24 34 18" stroke="url(#treeGradientHeader)" strokeWidth="3" strokeLinecap="round" fill="none"/>
                  <path d="M24 28 L24 14" stroke="url(#treeGradientHeader)" strokeWidth="3" strokeLinecap="round"/>
                  <circle cx="14" cy="18" r="3" fill="#DBEAFE"/>
                  <circle cx="24" cy="14" r="3" fill="#DBEAFE"/>
                  <circle cx="34" cy="18" r="3" fill="#DBEAFE"/>
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">Landas</h1>
                <p className="text-xs text-slate-500 hidden sm:block">Discover your path</p>
              </div>
            </div>

            {/* Research Input */}
            <div className="flex items-center gap-2 flex-1 min-w-[200px] max-w-xl order-last sm:order-none w-full sm:w-auto">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Research a topic..."
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleTopicResearch()}
                  className="w-full px-4 py-2 pl-10 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-50 transition-all"
                  disabled={isResearchingTopic}
                />
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
              </div>
              <button
                onClick={handleTopicResearch}
                disabled={isResearchingTopic || !topicInput.trim()}
                className={`px-3 py-2 rounded-xl font-medium text-sm transition-all whitespace-nowrap ${
                  isResearchingTopic || !topicInput.trim()
                    ? 'bg-slate-100 text-slate-400'
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
                }`}
              >
                {isResearchingTopic ? <span className="animate-spin inline-block">⟳</span> : 'Add'}
              </button>
              <button
                onClick={handleRunResearch}
                disabled={currentPhase !== PHASES.IDLE && currentPhase !== PHASES.COMPLETED && currentPhase !== PHASES.FAILED}
                title="Full Scan - Discover new technologies from all sources"
                className={`px-3 py-2 rounded-xl font-medium text-sm transition-all flex items-center gap-1.5 whitespace-nowrap ${
                  currentPhase !== PHASES.IDLE && currentPhase !== PHASES.COMPLETED && currentPhase !== PHASES.FAILED
                    ? 'bg-slate-100 text-slate-400'
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
                }`}
              >
                {(currentPhase === PHASES.COLLECTING || currentPhase === PHASES.ANALYZING) ? (
                  <>
                    <span className="animate-spin">⟳</span>
                    <span className="hidden sm:inline">{currentPhase === PHASES.ANALYZING ? 'Analyzing' : 'Scanning'}</span>
                  </>
                ) : (
                  <span>Full Scan</span>
                )}
              </button>
            </div>

            {/* Progress Stats */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3 text-sm">
                <div className="flex items-center gap-1.5" title="Completed">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span className="font-medium text-slate-700">{stats.completed}</span>
                </div>
                <div className="flex items-center gap-1.5" title="In Progress">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                  <span className="font-medium text-slate-700">{stats.inProgress}</span>
                </div>
                <div className="flex items-center gap-1.5" title="To Do">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
                  <span className="font-medium text-slate-700">{stats.total - stats.completed - stats.inProgress}</span>
                </div>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-slate-700 w-10">{progressPercent}%</span>
              </div>
            </div>

            <Link
              to="/settings"
              className="ml-auto p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              title="Settings"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
              </svg>
            </Link>
          </div>
        </div>
      </header>

      {/* Tree Content */}
      <main className="relative">
        <div
          ref={containerRef}
          className={`skill-tree-container max-w-full overflow-auto ${isDragging ? 'dragging' : ''}`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{ minHeight: 'calc(100vh - 80px)' }}
        >
          <div
            className="skill-tree relative min-w-max"
            ref={treeRef}
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
          >
            {/* SVG Connections */}
            <svg
              className="absolute inset-0 pointer-events-none"
              style={{ width: '100%', height: '100%', overflow: 'visible' }}
            >
              <defs>
                <marker id="arrowhead-gray" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#D6D3D1" />
                </marker>
                <marker id="arrowhead-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#65A30D" />
                </marker>
                <marker id="arrowhead-amber" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#EA580C" />
                </marker>
              </defs>
              {connections.map((conn) => (
                <g key={conn.id}>
                  <path
                    d={`M ${conn.x1} ${conn.y1} C ${conn.x1} ${conn.y1 + 30}, ${conn.x2} ${conn.y2 - 30}, ${conn.x2} ${conn.y2}`}
                    fill="none"
                    stroke={conn.color}
                    strokeWidth={conn.completed ? 3 : 2}
                    markerEnd={`url(#arrowhead-${conn.color === '#65A30D' ? 'green' : conn.color === '#EA580C' ? 'amber' : 'gray'})`}
                    className="transition-all duration-300"
                  />
                </g>
              ))}
            </svg>

            {/* Tree Nodes */}
            <div className="flex justify-center relative z-10">
              <SkillNode
                node={treeData}
                onNodeClick={handleNodeClick}
                onStatusChange={handleStatusChange}
                onToggleExpand={handleToggleExpand}
                expandedNodes={expandedNodes}
                focusedNodeId={focusedNodeId}
              />
            </div>
          </div>
        </div>

        {/* Tree Controls */}
        <TreeControls
          zoom={zoom}
          onZoomChange={setZoom}
          onReset={handleResetView}
          onFitView={handleFitView}
          onCollapseAll={handleCollapseAll}
          onExpandAll={handleExpandAll}
          totalNodes={stats.total}
          completedNodes={stats.completed}
        />

        {/* Legend */}
        <div className="fixed bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-3 text-xs z-30 hidden sm:block">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="w-6 h-0.5 bg-stone-300" />
              <span className="text-stone-500">Todo</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-6 h-0.5 bg-orange-500" />
              <span className="text-stone-500">Learning</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-6 h-1 bg-lime-500" />
              <span className="text-stone-500">Done</span>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-stone-100 text-stone-400 text-center">
            Drag to pan • Ctrl +/- to zoom
          </div>
        </div>
      </main>

      {/* Resource Panel */}
      <ResourcePanel
        node={selectedNode}
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
        onStatusChange={handleStatusChange}
        onResourceAdded={() => loadTree()}
      />

      {/* Overlay when panel is open */}
      {isPanelOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm transition-opacity"
          onClick={handleClosePanel}
        />
      )}

      {/* Research Progress Panel */}
      <ResearchProgressPanel
        isOpen={showProgressPanel}
        currentPhase={currentPhase}
        sources={sources}
        stats={researchStats}
        discoveries={discoveries}
        logs={logs}
        error={researchError}
        onClose={handleCloseProgressPanel}
        onCancel={handleCancelResearch}
        onRetry={handleRunResearch}
        isConnected={isConnected}
        mode={mode}
      />
    </div>
  );
};

export default SkillTree;
