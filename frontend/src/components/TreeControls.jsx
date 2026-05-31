import { useState, useCallback } from 'react';

const TreeControls = ({
  zoom,
  onZoomChange,
  onReset,
  onFitView,
  onCollapseAll,
  onExpandAll,
  totalNodes,
  completedNodes,
}) => {
  const [showMinimap, setShowMinimap] = useState(false);

  const handleZoomIn = () => onZoomChange(Math.min(zoom + 0.1, 2));
  const handleZoomOut = () => onZoomChange(Math.max(zoom - 0.1, 0.3));

  return (
    <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
      {/* Zoom Controls */}
      <div className="bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden">
        <button
          onClick={handleZoomIn}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors border-b border-slate-200"
          title="Zoom in (Ctrl +)"
          aria-label="Zoom in"
        >
          <span className="text-lg">+</span>
        </button>
        <div className="w-10 h-8 flex items-center justify-center text-xs text-slate-500 bg-slate-50 border-b border-slate-200">
          {Math.round(zoom * 100)}%
        </div>
        <button
          onClick={handleZoomOut}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors"
          title="Zoom out (Ctrl -)"
          aria-label="Zoom out"
        >
          <span className="text-lg">−</span>
        </button>
      </div>

      {/* View Controls */}
      <div className="bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden">
        <button
          onClick={onFitView}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors border-b border-slate-200"
          title="Fit to view (F)"
          aria-label="Fit to view"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        <button
          onClick={onReset}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors"
          title="Reset view (R)"
          aria-label="Reset view"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Expand/Collapse Controls */}
      <div className="bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden">
        <button
          onClick={onExpandAll}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors border-b border-slate-200"
          title="Expand all (E)"
          aria-label="Expand all nodes"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button
          onClick={onCollapseAll}
          className="w-10 h-10 flex items-center justify-center hover:bg-slate-100 transition-colors"
          title="Collapse all (C)"
          aria-label="Collapse all nodes"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      </div>

      {/* Minimap Toggle */}
      <button
        onClick={() => setShowMinimap(!showMinimap)}
        className={`w-10 h-10 rounded-lg shadow-lg border flex items-center justify-center transition-colors ${
          showMinimap ? 'bg-blue-500 text-white border-blue-500' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
        }`}
        title="Toggle minimap (M)"
        aria-label="Toggle minimap"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      </button>

      {/* Minimap */}
      {showMinimap && (
        <Minimap
          totalNodes={totalNodes}
          completedNodes={completedNodes}
        />
      )}
    </div>
  );
};

const Minimap = ({ totalNodes, completedNodes }) => {
  const progress = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0;

  return (
    <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-3 w-40">
      <div className="text-xs font-medium text-slate-600 mb-2">Overview</div>
      <div className="relative h-20 bg-slate-100 rounded overflow-hidden mb-2">
        <div
          className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-emerald-500 to-emerald-400 transition-all duration-500"
          style={{ height: `${progress}%` }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-slate-700">{Math.round(progress)}%</span>
        </div>
      </div>
      <div className="text-xs text-slate-500 text-center">
        {completedNodes}/{totalNodes} skills
      </div>
    </div>
  );
};

export default TreeControls;
