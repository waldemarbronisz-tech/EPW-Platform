import threading
from typing import Callable, Dict, List, Any

class EventBus:
    """
    Framework-independent event bus.
    Replaces PyQt signals in the EPW CORE for headless operation.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def emit(self, event_type: str, *args, **kwargs):
        """
        Emits an event to all subscribers synchronously in the calling thread.
        """
        with self._lock:
            subs = self._subscribers.get(event_type, []).copy()
        
        for callback in subs:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                from epw_os.core.logging import log
                log.error(f"Error in event subscriber for {event_type}: {e}", exc_info=True)
