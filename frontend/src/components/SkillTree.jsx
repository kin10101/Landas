import { useState, useEffect, useRef, useCallback } from 'react';
import SkillNode from './SkillNode';
import ResourcePanel from './ResourcePanel';

const API_URL = 'http://localhost:8000/api';

const SkillTree = () => {
  const [treeData, setTreeData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, completed: 0, inProgress: 0 });
  const [researchStatus, setResearchStatus] = useState({ running: false, last_run: null });
  const [connections, setConnections] = useState([]);
  const treeRef = useRef(null);

  // Load tree data from API or fallback to JSON
  useEffect(() => {
    loadTree();
    checkResearchStatus();
  }, []);

  const loadTree = async () => {
    try {
      // Try API first
      const res = await fetch(`${API_URL}/tree/1`);
      if (res.ok) {
        const data = await res.json();
        setTreeData(data);
        calculateStats(data);
        setLoading(false);
        return;
      }
    } catch (e) {
      console.log('API not available, using local JSON');
    }

    // Fallback to local JSON
    fetch('/skill_tree.json')
      .then((res) => res.json())
      .then((data) => {
        setTreeData(data);
        calculateStats(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load skill tree:', err);
        setLoading(false);
      });
  };

  const checkResearchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/research/status`);
      if (res.ok) {
        const data = await res.json();
        setResearchStatus(data);
      }
    } catch (e) {
      // API not available
    }
  };

  // Calculate connections after render
  useEffect(() => {
    if (treeData && treeRef.current) {
      setTimeout(() => calculateConnections(), 100);
    }
  }, [treeData]);

  const calculateConnections = useCallback(() => {
    if (!treeRef.current) return;

    const newConnections = [];
    const nodes = treeRef.current.querySelectorAll('[data-node-id]');

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

          // Determine connection color
          let color = '#cbd5e1'; // default gray
          if (parentStatus === 'completed' && childStatus === 'completed') {
            color = '#22c55e'; // green
          } else if (parentStatus === 'completed' || childStatus === 'in_progress') {
            color = '#f59e0b'; // amber
          }

          newConnections.push({
            id: `${parentId}-${node.dataset.nodeId}`,
            x1: parentRect.left + parentRect.width / 2 - treeRect.left,
            y1: parentRect.bottom - treeRect.top,
            x2: childRect.left + childRect.width / 2 - treeRect.left,
            y2: childRect.top - treeRect.top,
            color,
            completed: parentStatus === 'completed' && childStatus === 'completed',
          });
        }
      }
    });

    setConnections(newConnections);
  }, []);

  // Recalculate on window resize
  useEffect(() => {
    window.addEventListener('resize', calculateConnections);
    return () => window.removeEventListener('resize', calculateConnections);
  }, [calculateConnections]);

  // Calculate progress stats
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

  // Handle node click
  const handleNodeClick = (node) => {
    setSelectedNode(node);
    setIsPanelOpen(true);
  };

  // Handle status change
  const handleStatusChange = async (nodeId, newStatus) => {
    // Update locally
    const updateNodeStatus = (node) => {
      if (node.id === nodeId) {
        return {
          ...node,
          progress: { ...node.progress, status: newStatus },
        };
      }
      if (node.children) {
        return {
          ...node,
          children: node.children.map(updateNodeStatus),
        };
      }
      return node;
    };

    const updatedTree = updateNodeStatus(treeData);
    setTreeData(updatedTree);
    calculateStats(updatedTree);

    // Update selected node
    if (selectedNode?.id === nodeId) {
      setSelectedNode({
        ...selectedNode,
        progress: { ...selectedNode.progress, status: newStatus },
      });
    }

    // Recalculate connections
    setTimeout(calculateConnections, 50);

    // Try to save to API
    try {
      await fetch(`${API_URL}/progress/${nodeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (e) {
      console.log('API not available, progress saved locally');
    }
  };

  // Run research agent
  const handleRunResearch = async () => {
    setResearchStatus({ ...researchStatus, running: true });

    try {
      const res = await fetch(`${API_URL}/research/run`, { method: 'POST' });
      if (res.ok) {
        // Poll for status
        const pollStatus = setInterval(async () => {
          const statusRes = await fetch(`${API_URL}/research/status`);
          if (statusRes.ok) {
            const status = await statusRes.json();
            setResearchStatus(status);
            if (!status.running) {
              clearInterval(pollStatus);
              // Reload tree to get new data
              loadTree();
            }
          }
        }, 2000);
      }
    } catch (e) {
      setResearchStatus({ ...researchStatus, running: false, error: 'API not available' });
    }
  };

  // Close panel
  const handleClosePanel = () => {
    setIsPanelOpen(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading skill tree...</p>
        </div>
      </div>
    );
  }

  if (!treeData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center text-red-500">
          <p>Failed to load skill tree</p>
          <p className="text-sm text-gray-500 mt-2">Make sure the API is running or skill_tree.json exists</p>
        </div>
      </div>
    );
  }

  const progressPercent = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                🛤️ Landas
              </h1>
              <p className="text-sm text-gray-500">Your AI Career Roadmap</p>
            </div>

            {/* Research Button */}
            <button
              onClick={handleRunResearch}
              disabled={researchStatus.running}
              className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${
                researchStatus.running
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {researchStatus.running ? (
                <>
                  <span className="animate-spin">⟳</span>
                  Researching...
                </>
              ) : (
                <>
                  🔍 Run Research
                </>
              )}
            </button>

            {/* Progress Stats */}
            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">{progressPercent}%</div>
                <div className="text-xs text-gray-500">Complete</div>
              </div>
              <div className="flex gap-4 text-sm">
                <div className="text-center">
                  <div className="font-semibold text-green-600">{stats.completed}</div>
                  <div className="text-xs text-gray-500">Done</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-amber-600">{stats.inProgress}</div>
                  <div className="text-xs text-gray-500">Learning</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-gray-600">{stats.total - stats.completed - stats.inProgress}</div>
                  <div className="text-xs text-gray-500">Todo</div>
                </div>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-3 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Research Status */}
          {researchStatus.last_run && (
            <div className="mt-2 text-xs text-gray-500">
              Last research: {new Date(researchStatus.last_run).toLocaleString()}
              {researchStatus.last_result && (
                <span className="ml-2">
                  • Found {researchStatus.last_result.technologies_found} technologies
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Tree Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="skill-tree relative" ref={treeRef}>
          {/* SVG Connections */}
          <svg
            className="absolute inset-0 pointer-events-none"
            style={{ width: '100%', height: '100%', overflow: 'visible' }}
          >
            <defs>
              <marker
                id="arrowhead-gray"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#cbd5e1" />
              </marker>
              <marker
                id="arrowhead-green"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#22c55e" />
              </marker>
              <marker
                id="arrowhead-amber"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
              </marker>
            </defs>
            {connections.map((conn) => (
              <g key={conn.id}>
                <path
                  d={`M ${conn.x1} ${conn.y1}
                      C ${conn.x1} ${conn.y1 + 30},
                        ${conn.x2} ${conn.y2 - 30},
                        ${conn.x2} ${conn.y2}`}
                  fill="none"
                  stroke={conn.color}
                  strokeWidth={conn.completed ? 3 : 2}
                  markerEnd={`url(#arrowhead-${conn.color === '#22c55e' ? 'green' : conn.color === '#f59e0b' ? 'amber' : 'gray'})`}
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
            />
          </div>
        </div>
      </main>

      {/* Resource Panel */}
      <ResourcePanel
        node={selectedNode}
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
        onStatusChange={handleStatusChange}
      />

      {/* Overlay when panel is open */}
      {isPanelOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={handleClosePanel}
        />
      )}

      {/* Legend */}
      <footer className="fixed bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 text-sm">
        <h4 className="font-medium text-gray-700 mb-2">Legend</h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-8 h-0.5 bg-slate-300"></span>
            <span className="text-gray-600">Not started</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-0.5 bg-amber-500"></span>
            <span className="text-gray-600">In progress</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-8 h-1 bg-green-500"></span>
            <span className="text-gray-600">Completed</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default SkillTree;
