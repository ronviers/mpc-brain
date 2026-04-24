"""RFC-001 kernel primitives.

Re-exports the canonical event types (`.events`), the event bus (`.bus`),
and the Calorimeter consumer (`.network`).
"""

from .events import (
    Phase,
    PhaseTransitionEvent,
    LandauerEvent,
    BudgetResetEvent,
    EventBus,
)
from .network import Calorimeter

__all__ = [
    "Phase",
    "PhaseTransitionEvent",
    "LandauerEvent",
    "BudgetResetEvent",
    "EventBus",
    "Calorimeter",
]
