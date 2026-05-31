import { useState, useEffect } from 'react';
import SkillNode from './SkillNode';
import ResourcePanel from './ResourcePanel';

const SkillTree = () => {
  const [treeData, setTreeData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, completed: 0, inProgress: 0 });

  // Load tree data
  useEffect(() => {
    fetch('/skill_tree.json')
      .then((res) => res.json())
      .then((data) => {
        setTreeData(data);
        setLoading(false);
        calculateStats(data);
      })
      .catch((err) => {
        console.error('Failed to load skill tree:', err);
        setLoading(false);
      });
  }, []);

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
  const handleStatusChange = (nodeId, newStatus) => {
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

    // Update selected node if it's the one being changed
    if (selectedNode?.id === nodeId) {
      setSelectedNode({
        ...selectedNode,
        progress: { ...selectedNode.progress, status: newStatus },
      });
    }

    // TODO: Save to backend
    console.log(`Node ${nodeId} status changed to ${newStatus}`);
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
          <p className="text-sm text-gray-500 mt-2">Make sure skill_tree.json exists in the public folder</p>
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
        </div>
      </header>

      {/* Tree Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="skill-tree flex justify-center">
          <SkillNode
            node={treeData}
            onNodeClick={handleNodeClick}
            onStatusChange={handleStatusChange}
          />
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
            <span className="w-3 h-3 rounded-full bg-blue-500"></span>
            <span className="text-gray-600">Not started</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-amber-500"></span>
            <span className="text-gray-600">In progress</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-gray-600">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-gray-400"></span>
            <span className="text-gray-600">Removed</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default SkillTree;
