"""effector pack — passive commit-accounting subscriber (RFC-001 §7).

Carves `Effector` and `EffectorEvent` out of the Session-4 monolith.
The RFC-001 §7 measurement-layer contract is preserved: the Effector
holds no reference to any Substrate / Engine / Cluster, calls no
brain-side method, and never influences the energy landscape. λ_avg
is supplied externally by the caller via `register_cluster` so the
Effector never touches a Substrate.

AMEND-005 cost model: on every phase-C commit, emit an EffectorEvent
carrying energy_at_c (read from `PhaseTransitionEvent.energy`),
landauer_cost (LandauerEvents accumulated since last commit for this
cluster), and work_estimate (||v_c − v_reset||² · λ_avg).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from mpc_kernel.rfc001.events import (
    BudgetResetEvent,
    EventBus,
    LandauerEvent,
    PhaseTransitionEvent,
)
from mpc_kernel.rfc001.phase import Phase

log = logging.getLogger(__name__)


@dataclass
class EffectorEvent:
    """Emitted by the Effector at every c-phase commitment.

    Components:
      energy_at_c    — E(v_c); read from PhaseTransitionEvent.energy.
      landauer_cost  — Σ (LandauerEvent.info_content · kT) since last commit
                       for this cluster_id.
      work_estimate  — ||v_c − v_reset||² · λ_avg, where v_reset is the
                       position at this cluster's most recent BudgetResetEvent
                       (or zeros if no reset has occurred), and λ_avg is the
                       registered mean stiffness at commit time.
      total_cost     — sum of the three.
    """

    cluster_id: str
    position: np.ndarray
    energy_at_c: float
    landauer_cost: float
    work_estimate: float
    total_cost: float
    timestamp: float


class Effector:
    """AMEND-005 — passive measurement component.

    RFC-001 §7 compliance (same contract as Calorimeter):
      * Attaches to the bus via .attach(bus).
      * Holds NO reference to any Substrate, Engine, or Cluster.
      * Never calls any method on any brain component.
      * Never influences the energy landscape or phase classification.
      * Reads only via event subscription; exposes emitted EffectorEvents
        through .effector_events().

    λ_avg (used for work_estimate) is supplied externally by the caller
    via register_cluster(); the Effector does not inspect any Substrate
    to obtain it, preserving the strict measurement-layer separation.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self._landauer_acc: Dict[str, float] = {}
        self._last_reset_pos: Dict[str, np.ndarray] = {}
        self._lambda_avg: Dict[str, float] = {}
        self._events: List[EffectorEvent] = []
        self._attached_bus: Optional[EventBus] = None

        if bus is not None:
            self.attach(bus)

    # ── public API ──────────────────────────────────────────────────────────

    def attach(self, bus: EventBus) -> "Effector":
        """Subscribe to the three event types needed to compute total cost."""
        bus.subscribe(PhaseTransitionEvent, self._on_phase_transition)
        bus.subscribe(LandauerEvent, self._on_landauer)
        bus.subscribe(BudgetResetEvent, self._on_reset)
        self._attached_bus = bus
        return self

    def register_cluster(self, cluster_id: str, lambda_avg: float) -> None:
        """Provide the mean registered-constraint stiffness for this cluster.

        MUST be called by the caller (not by any brain component) so the
        Effector never reads from a Substrate.
        """
        self._lambda_avg[cluster_id] = float(lambda_avg)

    def effector_events(
        self, cluster_id: Optional[str] = None
    ) -> List[EffectorEvent]:
        """Return emitted EffectorEvents, optionally filtered by cluster_id."""
        if cluster_id is None:
            return list(self._events)
        return [e for e in self._events if e.cluster_id == cluster_id]

    def report(self) -> str:
        n = len(self._events)
        if not self._events:
            return "Effector: 0 commitments"
        costs = [e.total_cost for e in self._events]
        return (
            f"Effector: {n} commitments  "
            f"total_cost min={min(costs):.3f} "
            f"mean={float(np.mean(costs)):.3f} "
            f"max={max(costs):.3f}"
        )

    # ── event handlers (internal) ───────────────────────────────────────────

    def _on_landauer(self, e: LandauerEvent) -> None:
        self._landauer_acc[e.cluster_id] = (
            self._landauer_acc.get(e.cluster_id, 0.0)
            + e.info_content * e.kT
        )

    def _on_reset(self, e: BudgetResetEvent) -> None:
        self._last_reset_pos[e.cluster_id] = np.asarray(
            e.position, dtype=np.float64
        ).copy()

    def _on_phase_transition(self, e: PhaseTransitionEvent) -> None:
        if e.to_phase != Phase.C:
            return

        cid = e.cluster_id
        v_c = np.asarray(e.position, dtype=np.float64)

        # energy_at_c — canonical kernel PhaseTransitionEvent carries `energy`
        # (defaults to 0.0 for callers that don't populate it).
        energy_at_c = float(getattr(e, "energy", 0.0))
        if not hasattr(e, "energy"):
            log.warning(
                "Effector: PhaseTransitionEvent without .energy for "
                f"cluster='{cid}'; using 0.0 (legacy engine?)"
            )

        landauer_cost = float(self._landauer_acc.get(cid, 0.0))

        v_reset = self._last_reset_pos.get(cid)
        if v_reset is None:
            v_reset = np.zeros_like(v_c)
        # Match dimensions defensively — v_c and v_reset should agree.
        n = min(len(v_c), len(v_reset))
        diff_sq = float(np.sum((v_c[:n] - v_reset[:n]) ** 2))
        lam_avg = float(self._lambda_avg.get(cid, 1.0))
        work_estimate = diff_sq * lam_avg

        total_cost = energy_at_c + landauer_cost + work_estimate

        self._events.append(
            EffectorEvent(
                cluster_id=cid,
                position=v_c.copy(),
                energy_at_c=energy_at_c,
                landauer_cost=landauer_cost,
                work_estimate=work_estimate,
                total_cost=total_cost,
                timestamp=float(e.timestamp),
            )
        )

        # Reset Landauer accumulator for this cluster after emission.
        self._landauer_acc[cid] = 0.0
