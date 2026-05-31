"""
Progress tracking infrastructure for real-time research updates.

Provides event types, models, and callback mechanism for streaming
research progress to the frontend via SSE.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from pydantic import BaseModel


class EventType(str, Enum):
    """Types of progress events emitted during research."""
    RESEARCH_STARTED = "research_started"
    SOURCE_STARTED = "source_started"
    SOURCE_ITERATION = "source_iteration"
    SOURCE_COMPLETED = "source_completed"
    SOURCE_FAILED = "source_failed"
    COLLECTION_COMPLETED = "collection_completed"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    TECH_DISCOVERED = "tech_discovered"
    TREE_UPDATED = "tree_updated"
    RESEARCH_COMPLETED = "research_completed"
    RESEARCH_FAILED = "research_failed"


class ProgressEvent(BaseModel):
    """A single progress event with type, timestamp, and payload."""
    type: EventType
    timestamp: datetime
    data: dict[str, Any]

    class Config:
        use_enum_values = True


class ProgressCallback:
    """
    Wraps an asyncio.Queue to provide progress event emission.

    Passed to sources and the research runner to emit events
    that are streamed to the frontend via SSE.
    """

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def emit(self, event_type: EventType, **data) -> None:
        """Emit a progress event to the queue."""
        event = ProgressEvent(
            type=event_type,
            timestamp=datetime.utcnow(),
            data=data
        )
        await self.queue.put(event)

    def emit_sync(self, event_type: EventType, **data) -> None:
        """Emit a progress event synchronously (for non-async contexts)."""
        event = ProgressEvent(
            type=event_type,
            timestamp=datetime.utcnow(),
            data=data
        )
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


def create_progress_callback(queue: Optional[asyncio.Queue] = None) -> Optional[ProgressCallback]:
    """Create a progress callback if queue is provided."""
    if queue is not None:
        return ProgressCallback(queue)
    return None
