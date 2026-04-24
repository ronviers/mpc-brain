"""RFC-001 event types.

First-class dataclass definitions, carved out of the historical
`mpc_engine_rfc001` / `mpc_session4` monoliths. Field shapes match the
canonical forms established in Session 4 (`PhaseTransitionEvent.energy`
per AMEND-005) and Session 5 (no engine_id yet — tracked as SESSION-5
carry-forward item C3).
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .bus import EventBus
from .phase import Phase


@dataclass
class PhaseTransitionEvent:
    """Emitted by MetastableEngine on phase change (RFC-001 §6).

    `fdr_slope` is populated when the transition was classified using
    a dynamical measurement (FDR parametric slope in scaled units,
    FDT → 1). None when the transition came from the topological
    classifier alone.
    """

    from_phase: Phase
    to_phase: Phase
    position: np.ndarray
    timestamp: float
    cluster_id: str
    energy: float = 0.0
    fdr_slope: Optional[float] = None


@dataclass
class LandauerEvent:
    """Emitted on information-erasing operations (RFC-001 §6)."""

    cluster_id: str
    info_content: float
    kT: float = 1.0


@dataclass
class BudgetResetEvent:
    """Emitted when an engine exceeds its local energy budget (RFC-001 §6)."""

    cluster_id: str
    position: np.ndarray
    timestamp: float
    info_cost: float = 1.0


__all__ = [
    "Phase",
    "PhaseTransitionEvent",
    "LandauerEvent",
    "BudgetResetEvent",
    "EventBus",
]
