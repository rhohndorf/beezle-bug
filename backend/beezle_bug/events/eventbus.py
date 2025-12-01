from typing import Callable, Dict, List
from loguru import logger

from beezle_bug.events.event import Event, EventType

class EventBus:
    """Publish-subscribe event bus for agent introspection."""
    
    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._all_subscribers: List[Callable[[Event], None]] = []
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
    
    def subscribe_all(self, callback: Callable[[Event], None]) -> None:
        """Subscribe to all events."""
        if callback not in self._all_subscribers:
            self._all_subscribers.append(callback)
    
    def emit(self, event: Event) -> None:
        """Emit an event to all relevant subscribers."""
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}")
        
        for callback in self._all_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in global subscriber: {e}")