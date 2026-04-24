"""lateral_cluster pack — AMEND-003 Lateral Maintenance Field.

AutoCluster subclass augmented with a collective lateral maintenance
field. Engines sharing the same hypothesis (same nearest-well) attract
one another to maintain intra-hypothesis coherence:

    F_lateral(i) = Σ_{j≠i, j∈s-state, same well}  w_ij · (v_j − v_i)
    w_ij         = exp(−ε_ij / k_BT),            k_BT = 1.0

Engines assigned to different wells do not exchange lateral forces —
cross-well coupling is handled by `cross_cluster_compatibility()`, not
here. Non-s-state engines receive zero force (RFC-001 §3.4 intact).

Substrate is replaced with `DecayingSubstrate` at construction so the
ε_ij values used by the lateral field decay in time (AMEND-001).
An optional `ObservationSocket` is flushed before each step.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np

from mpc_kernel.rfc001.events import EventBus
from mpc_kernel.rfc001.phase import Phase
from mpc_packs.auto_cluster import AutoCluster
from mpc_packs.decaying_substrate import DecayingSubstrate
from mpc_packs.observation_socket import ObservationSocket


class LateralCluster(AutoCluster):
    """AMEND-003 AutoCluster with lateral maintenance field.

    RFC-001 compliance:
      * Holds exactly one Substrate (DecayingSubstrate) and one EventBus.
      * No Calorimeter reference.
      * ObservationSocket (if any) holds neither Substrate nor Bus.
    """

    def __init__(
        self,
        dim: int,
        E_star: float,
        max_engines: int,
        bus: EventBus,
        E_c: float = 0.5,
        E_s: float = 2.0,
        socket: Optional[ObservationSocket] = None,
        tau_base: float = 50.0,
        lateral_scale: float = 0.02,
    ):
        super().__init__(dim, E_star, max_engines, bus, E_c, E_s)

        # Replace JAXSubstrate (AutoCluster default) with DecayingSubstrate.
        dec_sub = DecayingSubstrate(
            dim=dim, E_c=E_c, E_s=E_s, epsilon=1e-4, tau_base=tau_base,
        )
        self.sub = dec_sub
        self.ops.sub = dec_sub
        for eng in self.engines:
            eng.sub = dec_sub   # update the engine spawned by AutoCluster.__init__

        self._socket = socket
        # lateral_scale attenuates the collective lateral force so it acts
        # as a soft perturbation, not a dominant centripetal collapse.
        self._lateral_scale = lateral_scale
        # Optional centre cache populated by load(centres=...) — used in
        # _nearest_constraint() for exact nearest-well lookup without
        # evaluating constraint functions at every call.
        self._centres: Dict[str, np.ndarray] = {}

    # ── Extended load() ─────────────────────────────────────────────────────

    def load(
        self,
        constraints: Dict[str, Callable],
        stiffnesses: Optional[Dict[str, float]] = None,
        centres: Optional[Dict[str, np.ndarray]] = None,
    ):
        """Register constraints. Optional `centres` speeds up nearest-well lookup."""
        super().load(constraints, stiffnesses)
        if centres:
            self._centres.update(centres)

    # ── AMEND-003 lateral field ─────────────────────────────────────────────

    def _nearest_constraint(self, v: np.ndarray) -> Optional[str]:
        """Return the proposition_id of the constraint whose well is
        nearest to v. Uses squared distance to stored centres when
        available; falls back to evaluating fn(v)."""
        if not self._handles:
            return None
        best_pid, best_dist = None, float("inf")
        for pid, h in self._handles.items():
            if pid in self._centres:
                d = float(np.sum((v - self._centres[pid]) ** 2))
            else:
                entry = self.sub._constraints.get(h.uid)
                if entry is None:
                    continue
                fn, _ = entry
                try:
                    d = float(fn(v))
                except Exception:
                    d = float("inf")
            if d < best_dist:
                best_dist, best_pid = d, pid
        return best_pid

    def _get_frustration_between_pids(self, pid_a: str, pid_b: str) -> float:
        """ε(pid_a, pid_b) from DecayingSubstrate cache (or uid-keyed
        _frustration dict on plain substrates)."""
        if pid_a == pid_b:
            return 0.0
        if isinstance(self.sub, DecayingSubstrate):
            key = (min(pid_a, pid_b), max(pid_a, pid_b))
            return self.sub._decay_cache.get(key, 0.0)
        uid_a = uid_b = None
        for uid, (_, h) in self.sub._constraints.items():
            if h.proposition_id == pid_a:
                uid_a = uid
            elif h.proposition_id == pid_b:
                uid_b = uid
        if uid_a is None or uid_b is None:
            return 0.0
        key = (min(uid_a, uid_b), max(uid_a, uid_b))
        return float(self.sub._frustration.get(key, 0.0))

    def _compute_lateral_forces(self) -> List[np.ndarray]:
        """Per-engine lateral force vectors.

        Within the same well: `w_ij = exp(−ε_ij / k_BT)`, k_BT = 1.0,
        scaled by `lateral_scale / max(n_same − 1, 1)` so force
        magnitude is O(1) regardless of cluster size. Engines not in
        s-state receive zero force (RFC-001 §3.4 intact).
        """
        n = len(self.engines)
        forces = [np.zeros(self.sub.dim) for _ in range(n)]
        if n < 2 or not self._handles:
            return forces

        pid_of = [self._nearest_constraint(e.v) for e in self.engines]
        s_idx = [i for i, e in enumerate(self.engines) if e.phase == Phase.S]

        for i in s_idx:
            pid_i = pid_of[i]
            same_well = [j for j in s_idx if j != i and pid_of[j] == pid_i]
            if not same_well:
                continue
            scale = self._lateral_scale / len(same_well)
            for j in same_well:
                eps_ij = self._get_frustration_between_pids(pid_i, pid_of[j])
                w_ij = float(np.exp(-eps_ij))   # k_BT = 1.0
                forces[i] = forces[i] + scale * w_ij * (
                    self.engines[j].v - self.engines[i].v
                )

        return forces

    def diffuse(self, n_steps: int = 1):
        """AMEND-003 override: apply lateral forces to each s-state
        engine before integration."""
        for _ in range(n_steps):
            lateral = self._compute_lateral_forces()
            for eng, force in zip(self.engines, lateral):
                eng.step(external_force=force)

    def step(self):
        """AMEND-004 integration: flush the socket before stepping,
        then call the inherited AutoCluster.step()."""
        if self._socket is not None:
            specs = self._socket.flush()
            if specs:
                self.load(
                    {s.label: s.fn for s in specs},
                    stiffnesses={s.label: s.lambda_ for s in specs},
                )
        super().step()
