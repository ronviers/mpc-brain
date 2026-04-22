"""RFC-001 kernel primitives (shim layer).

Re-exports Phase, PhaseTransitionEvent, LandauerEvent, BudgetResetEvent,
EventBus, and Calorimeter from the shim at `.events`. Callers should import
these names from `mpc_kernel.rfc001.events` directly.
"""

from .events import (
    Phase,
    PhaseTransitionEvent,
    LandauerEvent,
    BudgetResetEvent,
    EventBus,
    Calorimeter,
)

__all__ = [
    "Phase",
    "PhaseTransitionEvent",
    "LandauerEvent",
    "BudgetResetEvent",
    "EventBus",
    "Calorimeter",
]
