"""auto_cluster pack — self-organising MPCCluster (RFC-001 §4.3).

Subclasses `MPCCluster` with RFC-001 §4.3 self-regulation:

    dominant_phase == r            → do nothing
    dominant_phase == s,           → spawn engine (up to max_engines)
        count_s < separation_bound
    dominant_phase == k            → shed_load(0.3)
    engine in r-state ≥ 50 steps   → cull (keep ≥ 1)

Constructs a `JAXSubstrate` when JAX is available so the per-step
gradient/hessian work is JIT-compiled; falls back to the kernel's
finite-difference `Substrate` otherwise.

RFC-001 compliance: holds exactly one Substrate and one EventBus
(both inherited). No Calorimeter reference. New methods do not alter
the existing RFC-001 interface.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

import numpy as np

from mpc_engine_rfc001 import MPCCluster
from mpc_kernel.rfc001.phase import Phase
from mpc_packs.jax_substrate import JAX_AVAILABLE, JAXSubstrate


class AutoCluster(MPCCluster):
    """RFC-001 §4.3-conforming self-organising cluster.

    Subclasses MPCCluster — does NOT re-implement cluster logic from
    scratch. Uses JAXSubstrate when available (replaced before engines
    are added so every engine sees the JAX-enhanced substrate).

    Constructor: `(dim, E_star, max_engines, bus)` — no n_engines
    required; the cluster seeds itself with one engine and grows as
    needed.
    """

    _CULL_THRESHOLD = 50

    def __init__(self, dim, E_star, max_engines, bus, E_c=0.5, E_s=2.0):
        cluster_id = f"auto_{uuid.uuid4().hex[:6]}"
        super().__init__(cluster_id, dim, E_star, bus, E_c, E_s, alpha=0.10)
        self.max_engines = max_engines

        # Replace plain Substrate with JAXSubstrate BEFORE adding any engines.
        if JAX_AVAILABLE:
            jax_sub = JAXSubstrate(dim=dim, E_c=E_c, E_s=E_s, epsilon=1e-4)
            self.sub = jax_sub
            self.ops.sub = jax_sub

        # Per-engine consecutive r-state step counter.
        self._r_streak: Dict[int, int] = {}

        # Seed with one engine (minimum for separation_bound() to evaluate).
        self._spawn_engine()

    # ── Public interface ────────────────────────────────────────────────────

    def step(self):
        """Advance all engines one step, then self-regulate population size.

        Calls only RFC-001 §4.3 interface methods: `diffuse`, `add_engine`,
        `shed_load`, `dominant_phase`, `count_s_state`, `separation_bound`.
        """
        self.diffuse(n_steps=1)
        self._update_r_streaks()
        self._cull_stale_engines()
        self._regulate()

    def population_report(self) -> Dict[str, Any]:
        """Snapshot of current engine population."""
        phases = [e.phase for e in self.engines]
        sb = self.separation_bound() if self.engines else 0.0
        return {
            "n_engines": len(self.engines),
            "n_committed": sum(1 for p in phases if p == Phase.C),
            "n_suspended": sum(1 for p in phases if p == Phase.S),
            "n_conflict": sum(1 for p in phases if p == Phase.K),
            "n_reset": sum(1 for p in phases if p == Phase.R),
            "separation_bound": round(sb, 2),
        }

    # ── Internal ────────────────────────────────────────────────────────────

    def _spawn_engine(self):
        eng = self.add_engine(E_star=self.local_budget, dt=0.01)
        eng.v = np.random.randn(self.sub.dim) * 0.05
        self._r_streak[id(eng)] = 0
        return eng

    def _regulate(self):
        dp = self.dominant_phase
        if dp == Phase.R:
            pass
        elif dp == Phase.S:
            n_s = self.count_s_state()
            n_max = self.separation_bound() if self.engines else 0.0
            if n_s < n_max and len(self.engines) < self.max_engines:
                self._spawn_engine()
        elif dp == Phase.K:
            self.shed_load(0.3)

    def _update_r_streaks(self):
        for eng in self.engines:
            eid = id(eng)
            self._r_streak[eid] = (
                self._r_streak.get(eid, 0) + 1 if eng.phase == Phase.R else 0
            )

    def _cull_stale_engines(self):
        to_cull = [
            e for e in self.engines
            if self._r_streak.get(id(e), 0) >= self._CULL_THRESHOLD
        ]
        max_cull = max(0, len(self.engines) - 1)   # keep >= 1
        for eng in to_cull[:max_cull]:
            self.engines.remove(eng)
            self._r_streak.pop(id(eng), None)
