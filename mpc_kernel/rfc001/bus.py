from typing import Any, Callable, Dict, List

class EventBus:
    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: Any):
        for h in self._handlers.get(type(event), []):
            h(event)

    @staticmethod
    def null() -> "EventBus":
        return EventBus()