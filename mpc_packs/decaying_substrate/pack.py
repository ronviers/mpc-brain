"""decaying_substrate pack — temporal frustration decay (AMEND-001).

JAXSubstrate subclass with a decay cache over the pairwise-frustration
graph. Edges decay exponentially in time toward zero; decayed edges
below `epsilon_floor` drop out of the *active* frustration graph used
by `MPCCluster.separation_bound()`, so `N_max` grows as edges decay.

Decay law per edge (i, j):
    ε_ij(t+1) = ε_ij(t) · exp(-1 / τ_ij),  τ_ij = tau_base / min(λ_i, λ_j)

Constraints themselves remain registered; only the active edges shift.

AMEND-001 public interface additions:
    decay_step()            — advance one time step
    ping(i, j, strength)    — re-stamp an edge toward its original value
    update_frustration(i, j, new_ε)  — AMEND-004 direct setter
"""

from __future__ import annotations

from typing import Dict, Set, Tuple

import numpy as np

from mpc_engine_rfc001 import ConstraintHandle
from mpc_packs.jax_substrate.pack import JAXSubstrate


class DecayingSubstrate(JAXSubstrate):
    """AMEND-001: JAXSubstrate with a temporal frustration decay cache.

    Overrides `_min_nonzero_frustration()` and `_average_degree()` so
    `MPCCluster.separation_bound()` draws from the decayed active graph
    automatically.
    """

    def __init__(
        self,
        *args,
        tau_base: float = 50.0,
        epsilon_floor: float = 1e-4,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tau_base = tau_base
        self.epsilon_floor = epsilon_floor

        # Sorted proposition-id pair keys: (min_pid, max_pid).
        self._decay_cache: Dict[Tuple[str, str], float] = {}
        self._initial_eps: Dict[Tuple[str, str], float] = {}
        # uid → proposition_id bridge for the uid-keyed frustration dict.
        self._uid_to_pid: Dict[str, str] = {}
        # Pairs currently above epsilon_floor.
        self._active_pairs: Set[Tuple[str, str]] = set()

    # ── RFC-001 §4.1 overrides ──────────────────────────────────────────────

    def register(
        self, proposition_id: str, fn, lam: float = 1.0
    ) -> ConstraintHandle:
        h = super().register(proposition_id, fn, lam)
        self._uid_to_pid[h.uid] = proposition_id
        return h

    def deregister(self, handle: ConstraintHandle):
        pid = self._uid_to_pid.pop(handle.uid, None)
        super().deregister(handle)
        if pid is not None:
            dead = {k for k in self._active_pairs if pid in k}
            self._active_pairs -= dead

    def frustration(self, v: np.ndarray) -> Dict:
        """Compute pairwise frustration (parent), then initialise the
        decay cache for any newly-seen pairs. Existing cache entries are
        NOT overwritten so decay state is preserved across calls."""
        result = super().frustration(v)
        for (uid_a, uid_b), eps_val in result.items():
            pid_a = self._uid_to_pid.get(uid_a, uid_a)
            pid_b = self._uid_to_pid.get(uid_b, uid_b)
            key = (min(pid_a, pid_b), max(pid_a, pid_b))
            if key not in self._initial_eps:
                init = max(float(eps_val), self.epsilon_floor * 10.0)
                self._initial_eps[key] = init
                self._decay_cache[key] = init
                self._active_pairs.add(key)
        return result

    # ── AMEND-001 new methods ───────────────────────────────────────────────

    def decay_step(self):
        """Advance one decay step.

        ε_ij(t+1) = ε_ij(t) · exp(-1 / τ_ij),
        τ_ij = tau_base / min(λ_i, λ_j)

        Edges below epsilon_floor drop out of the active graph.
        """
        for key in list(self._active_pairs):
            pid_a, pid_b = key
            lam_a = self._get_lambda_for_pid(pid_a)
            lam_b = self._get_lambda_for_pid(pid_b)
            tau = self.tau_base / max(min(lam_a, lam_b), 1e-9)
            self._decay_cache[key] = (
                self._decay_cache.get(key, 0.0) * np.exp(-1.0 / tau)
            )
            if self._decay_cache[key] < self.epsilon_floor:
                self._active_pairs.discard(key)

    def ping(self, i: str, j: str, strength: float = 1.0):
        """Reset the decay clock for edge (i, j).

        ε_ij += strength · ε_ij_original, capped at ε_ij_original.
        Re-activates the edge if it had decayed below the floor.
        """
        key = (min(i, j), max(i, j))
        if key not in self._initial_eps:
            return
        original = self._initial_eps[key]
        current = self._decay_cache.get(key, 0.0)
        self._decay_cache[key] = min(current + strength * original, original)
        self._active_pairs.add(key)

    def update_frustration(self, i: str, j: str, new_epsilon: float):
        """AMEND-004 interface: directly set ε_ij. Activates or
        deactivates the edge as appropriate."""
        key = (min(i, j), max(i, j))
        val = float(new_epsilon)
        self._decay_cache[key] = val
        if val >= self.epsilon_floor:
            self._active_pairs.add(key)
        else:
            self._active_pairs.discard(key)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_lambda_for_pid(self, pid: str) -> float:
        for _, h in self._constraints.values():
            if h.proposition_id == pid:
                return h.stiffness
        return 1.0

    def _min_nonzero_frustration(self) -> float:
        """AMEND-001: use decayed values; fall back to base if no active pairs."""
        if self._active_pairs:
            vals = [
                self._decay_cache[k]
                for k in self._active_pairs
                if self._decay_cache.get(k, 0.0) > 1e-9
            ]
            if vals:
                return float(min(vals))
        return super()._min_nonzero_frustration()

    def _average_degree(self) -> float:
        """AMEND-001: use active-pair count; fall back to base if empty."""
        n = self.constraint_count
        if n <= 1:
            return 0.0
        if self._active_pairs:
            return 2.0 * len(self._active_pairs) / n
        return super()._average_degree()
