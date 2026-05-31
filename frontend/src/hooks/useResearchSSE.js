import { useState, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const PHASES = {
  IDLE: 'idle',
  COLLECTING: 'collecting',
  ANALYZING: 'analyzing',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

const SOURCE_STATUS = {
  PENDING: 'pending',
  FETCHING: 'fetching',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

export function useResearchSSE() {
  const [isConnected, setIsConnected] = useState(false);
  const [currentPhase, setCurrentPhase] = useState(PHASES.IDLE);
  const [events, setEvents] = useState([]);
  const [sources, setSources] = useState({});
  const [stats, setStats] = useState({
    itemsCollected: 0,
    technologiesFound: 0,
    sourcesCompleted: 0,
    totalSources: 0,
    newTechnologies: 0,
  });
  const [discoveries, setDiscoveries] = useState([]);
  const [error, setError] = useState(null);

  const { authFetch } = useAuth();
  const eventSourceRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const handleEvent = useCallback((event) => {
    setEvents((prev) => [...prev, event]);

    switch (event.type) {
      case 'research_started':
        setCurrentPhase(PHASES.COLLECTING);
        setStats((prev) => ({
          ...prev,
          totalSources: event.data.total_sources || 0,
        }));
        if (event.data.source_names) {
          const initialSources = {};
          event.data.source_names.forEach((name) => {
            initialSources[name] = { status: SOURCE_STATUS.PENDING, items: 0, detail: '' };
          });
          setSources(initialSources);
        }
        break;

      case 'source_started':
        setSources((prev) => ({
          ...prev,
          [event.data.source]: {
            ...prev[event.data.source],
            status: SOURCE_STATUS.FETCHING,
            detail: event.data.detail || 'Starting...',
            totalItems: event.data.total_items || 0,
          },
        }));
        break;

      case 'source_iteration':
        setSources((prev) => ({
          ...prev,
          [event.data.source]: {
            ...prev[event.data.source],
            detail: event.data.detail || `${event.data.current}/${event.data.total}`,
            current: event.data.current,
            total: event.data.total,
          },
        }));
        break;

      case 'source_completed':
        setSources((prev) => ({
          ...prev,
          [event.data.source]: {
            ...prev[event.data.source],
            status: SOURCE_STATUS.COMPLETED,
            items: event.data.items_collected || 0,
            detail: `${event.data.items_collected} items`,
          },
        }));
        setStats((prev) => ({
          ...prev,
          sourcesCompleted: prev.sourcesCompleted + 1,
          itemsCollected: prev.itemsCollected + (event.data.items_collected || 0),
        }));
        break;

      case 'source_failed':
        setSources((prev) => ({
          ...prev,
          [event.data.source]: {
            ...prev[event.data.source],
            status: SOURCE_STATUS.FAILED,
            detail: event.data.error || 'Failed',
          },
        }));
        setStats((prev) => ({
          ...prev,
          sourcesCompleted: prev.sourcesCompleted + 1,
        }));
        break;

      case 'collection_completed':
        setStats((prev) => ({
          ...prev,
          itemsCollected: event.data.items_collected || prev.itemsCollected,
        }));
        break;

      case 'analysis_started':
        setCurrentPhase(PHASES.ANALYZING);
        break;

      case 'analysis_completed':
        setStats((prev) => ({
          ...prev,
          technologiesFound: event.data.technologies_found || 0,
          newTechnologies: event.data.new_technologies || 0,
        }));
        break;

      case 'tech_discovered':
        setDiscoveries((prev) => [
          ...prev,
          {
            name: event.data.name,
            category: event.data.category,
            relevance: event.data.relevance_score,
            trend: event.data.trend,
            isEmerging: event.data.is_emerging,
          },
        ]);
        break;

      case 'tree_updated':
        break;

      case 'research_completed':
        setCurrentPhase(PHASES.COMPLETED);
        setStats((prev) => ({
          ...prev,
          technologiesFound: event.data.technologies_found || prev.technologiesFound,
          newTechnologies: event.data.new_technologies || prev.newTechnologies,
        }));
        break;

      case 'research_failed':
        setCurrentPhase(PHASES.FAILED);
        setError(event.data.error || 'Research failed');
        break;

      default:
        break;
    }
  }, []);

  const fallbackToPolling = useCallback(() => {
    if (pollIntervalRef.current) return;

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/research/status`);
        if (res.ok) {
          const status = await res.json();
          if (!status.running) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            setCurrentPhase(status.error ? PHASES.FAILED : PHASES.COMPLETED);
            if (status.error) setError(status.error);
            if (status.last_result) {
              setStats((prev) => ({
                ...prev,
                technologiesFound: status.last_result.technologies_found || 0,
                newTechnologies: status.last_result.new_technologies || 0,
              }));
            }
          }
        }
      } catch (e) {
        console.error('Polling error:', e);
      }
    }, 2000);
  }, []);

  const startResearch = useCallback(async () => {
    setEvents([]);
    setSources({});
    setDiscoveries([]);
    setStats({
      itemsCollected: 0,
      technologiesFound: 0,
      sourcesCompleted: 0,
      totalSources: 0,
      newTechnologies: 0,
    });
    setError(null);
    setCurrentPhase(PHASES.COLLECTING);

    try {
      const res = await authFetch(`${API_URL}/research/start`, { method: 'POST' });
      if (!res.ok) {
        throw new Error('Failed to start research');
      }

      const { session_id } = await res.json();

      const eventSource = new EventSource(`${API_URL}/research/stream/${session_id}`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          handleEvent(event);
        } catch (err) {
          console.error('Error parsing SSE event:', err);
        }
      };

      eventSource.onerror = (e) => {
        console.error('SSE error:', e);
        setIsConnected(false);
        eventSource.close();
        eventSourceRef.current = null;
        fallbackToPolling();
      };
    } catch (e) {
      console.error('Failed to start research:', e);
      setError(e.message);
      setCurrentPhase(PHASES.FAILED);
    }
  }, [handleEvent, fallbackToPolling, authFetch]);

  const stopResearch = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const reset = useCallback(() => {
    stopResearch();
    setCurrentPhase(PHASES.IDLE);
    setEvents([]);
    setSources({});
    setDiscoveries([]);
    setStats({
      itemsCollected: 0,
      technologiesFound: 0,
      sourcesCompleted: 0,
      totalSources: 0,
      newTechnologies: 0,
    });
    setError(null);
  }, [stopResearch]);

  return {
    isConnected,
    currentPhase,
    events,
    sources,
    stats,
    discoveries,
    error,
    startResearch,
    stopResearch,
    reset,
    PHASES,
    SOURCE_STATUS,
  };
}

export default useResearchSSE;
