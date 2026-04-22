# mpc_kernel/rfc001/events.py
# Shim for container-side imports. The canonical split lives on the workstation
# per RFC-002 §6. Session 6 carve-out work replaces this file.
from mpc_engine_rfc001 import (
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
