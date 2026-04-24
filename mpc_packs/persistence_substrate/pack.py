"""persistence_substrate pack — AMEND-006.

PersistenceSubstrate extends DecayingSubstrate with:
  - A usage-modulated τ  τ_ij = base_τ · (1 + k_usage · traversal_freq)
  - An `apply_outcome(pid)` active-reinforcement hook that boosts every
    pair containing `pid`, capped at the original ε.

PersistenceCluster is a LateralCluster backed by PersistenceSubstrate.
It records traversals whenever an engine's nearest-well changes, and
calls apply_outcome on every phase-C transition it sees through the
bus.

RFC-001 §4.1 compliance: the interface additions never modify the
energy landscape directly — they modulate only the frustration *cache*
used by separation_bound(). Phase classification remains purely
energy + Hessian.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from mpc_kernel.rfc001.engine import MetastableEngine
from mpc_kernel.rfc001.events import EventBus, PhaseTransitionEvent
from mpc_kernel.rfc001.phase import Phase
from mpc_packs.decaying_substrate import DecayingSubstrate
from mpc_packs.effector import Effector, EffectorEvent  # noqa: F401 (back-compat re-export)
from mpc_packs.lateral_cluster import LateralCluster
from mpc_packs.observation_socket import ObservationSocket


# ── InstrumentedEngine ──────────────────────────────────────────────────────
#
# Carved from mpc_session4 into this pack to break a circular import
# (session4 re-exports PersistenceCluster from here, which was trying to
# import InstrumentedEngine from session4). mpc_session4 now re-exports
# InstrumentedEngine from here instead.


class InstrumentedEngine(MetastableEngine):
    """MetastableEngine variant that emits PhaseTransitionEvent with
    `energy = float(sub.energy(v_post))` populated (AMEND-005,
    Session 4). RFC-001 §3 invariants are inherited unchanged:
    classification, budget wall, and maintenance-field behaviour come
    from the parent; only the event emission is enriched.

    The canonical kernel MetastableEngine already populates `energy`
    (with the pre-update value). InstrumentedEngine uses the post-update
    value — subtle but observable to consumers like the Effector. Kept
    as a distinct class for bit-level backward compatibility with
    Session-5-era Effector total_cost statistics.
    """

    def step(self, external_force: Optional[np.ndarray] = None) -> np.ndarray:
        ext = external_force if external_force is not None else np.zeros(self.sub.dim)
        state = self.sub._energy_state(self.v)
        F_cons = -state.gradient

        prev_phase = self.sub.classify(self.v)
        self._maint.update(self.v, prev_phase)
        F_maint = (
            self._maint.force(self.v, self.barrier_strength)
            if prev_phase == Phase.S
            else np.zeros(self.sub.dim)
        )

        std = np.sqrt(2.0 * self.attention_scarcity * self.dt + 1e-12)
        F_noise = std * np.random.randn(self.sub.dim)
        v_proposed = self.v + self.dt * (F_cons + F_maint + ext) + F_noise

        if self.sub.energy(v_proposed) > self.E_star:
            self._trigger_reset(prev_phase)
            self._t += self.dt
            return self.v

        self.v = v_proposed
        new_phase = self.sub.classify(self.v)

        if new_phase != prev_phase:
            self.bus.emit(PhaseTransitionEvent(
                from_phase=prev_phase, to_phase=new_phase,
                position=self.v.copy(), timestamp=self._t,
                cluster_id=self.cluster_id,
                energy=float(self.sub.energy(self.v)),
            ))

        self._phase_hist.append((self._t, new_phase))
        self._energy_hist.append(state.energy)
        self._t += self.dt
        return self.v


# ── PersistenceSubstrate ────────────────────────────────────────────────────


class PersistenceSubstrate(DecayingSubstrate):
    """AMEND-006 — DecayingSubstrate with usage-modulated τ and
    apply_outcome reinforcement."""

    def __init__(
        self,
        *args,
        usage_coefficient: float = 0.5,
        outcome_coefficient: float = 0.3,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.usage_coefficient = float(usage_coefficient)
        self.outcome_coefficient = float(outcome_coefficient)

        # Ordered-key traversal accounting. Keys: (min(pid), max(pid)).
        self._traversal: Dict[Tuple[str, str], int] = {}
        self._total_traversals: int = 0

        # Original frustration values at pair-initialisation time.
        # Kept separate from DecayingSubstrate._initial_eps so the
        # AMEND-006 contract is explicit.
        self._original_eps: Dict[Tuple[str, str], float] = {}

    # ── frustration() — also populate _original_eps ─────────────────────────

    def frustration(self, v: np.ndarray) -> Dict:
        result = super().frustration(v)
        for key, val in self._initial_eps.items():
            if key not in self._original_eps:
                self._original_eps[key] = float(val)
        return result

    # ── AMEND-006 new methods ───────────────────────────────────────────────

    def record_traversal(self, pid_a: str, pid_b: str) -> None:
        """Increment the traversal count for edge (pid_a, pid_b)."""
        if pid_a is None or pid_b is None or pid_a == pid_b:
            return
        key = (min(pid_a, pid_b), max(pid_a, pid_b))
        self._traversal[key] = self._traversal.get(key, 0) + 1
        self._total_traversals += 1

    def apply_outcome(self, pid: str) -> None:
        """Active reinforcement: boost every pair containing `pid`.

        For each (pid, other) currently in _decay_cache:
            ε_ij ← min(ε_ij + outcome_coefficient · ε_original, ε_original)
        and re-activate the edge if it had decayed below the floor.
        """
        if pid is None:
            return
        for key in list(self._decay_cache.keys()):
            if pid not in key:
                continue
            original = self._original_eps.get(
                key, self._initial_eps.get(key, 0.0)
            )
            if original <= 0.0:
                continue
            boost = self.outcome_coefficient * original
            new_val = min(self._decay_cache.get(key, 0.0) + boost, original)
            self._decay_cache[key] = new_val
            if new_val >= self.epsilon_floor:
                self._active_pairs.add(key)

    # ── decay_step override: τ modulated by traversal frequency ─────────────

    def decay_step(self) -> None:
        """ε_ij(t+1) = ε_ij(t) · exp(−1/τ_ij), τ_ij usage-modulated."""
        inv_total = 1.0 / max(self._total_traversals, 1)
        for key in list(self._active_pairs):
            pid_a, pid_b = key
            lam_a = self._get_lambda_for_pid(pid_a)
            lam_b = self._get_lambda_for_pid(pid_b)
            base_tau = self.tau_base / max(min(lam_a, lam_b), 1e-9)
            traversal_freq = self._traversal.get(key, 0) * inv_total
            tau = base_tau * (1.0 + self.usage_coefficient * traversal_freq)
            self._decay_cache[key] = (
                self._decay_cache.get(key, 0.0) * np.exp(-1.0 / tau)
            )
            if self._decay_cache[key] < self.epsilon_floor:
                self._active_pairs.discard(key)


# ── PersistenceCluster ──────────────────────────────────────────────────────


class PersistenceCluster(LateralCluster):
    """AMEND-006 — LateralCluster backed by PersistenceSubstrate, populated
    by InstrumentedEngine instances.

    Runtime hooks:
      diffuse()        — after each engine step, record a traversal
                         whenever an engine's nearest well changes.
      on phase→C event — call substrate.apply_outcome(pid) to reinforce
                         the committing well's edges.

    RFC-001 §4.3 compliance:
      * Exactly one Substrate (PersistenceSubstrate) + one Bus (inherited)
      * No Calorimeter or Effector reference
      * Lateral field + socket behaviour from LateralCluster preserved
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
        usage_coefficient: float = 0.5,
        outcome_coefficient: float = 0.3,
    ):
        super().__init__(
            dim, E_star, max_engines, bus,
            E_c=E_c, E_s=E_s, socket=socket,
            tau_base=tau_base, lateral_scale=lateral_scale,
        )

        # (1) Replace DecayingSubstrate (LateralCluster default) with
        # PersistenceSubstrate.
        persist_sub = PersistenceSubstrate(
            dim=dim, E_c=E_c, E_s=E_s, epsilon=1e-4,
            tau_base=tau_base,
            usage_coefficient=usage_coefficient,
            outcome_coefficient=outcome_coefficient,
        )
        self.sub = persist_sub
        self.ops.sub = persist_sub

        # (2) Replace every inherited engine with an InstrumentedEngine.
        new_engines: List[InstrumentedEngine] = []
        for old in self.engines:
            new_eng = InstrumentedEngine(
                substrate=persist_sub, bus=self.bus,
                E_star=old.E_star, dt=old.dt, cluster_id=self.cluster_id,
            )
            new_eng.v = old.v.copy()
            new_eng.attention_scarcity = old.attention_scarcity
            new_eng.barrier_strength = old.barrier_strength
            self._r_streak.pop(id(old), None)
            self._r_streak[id(new_eng)] = 0
            new_engines.append(new_eng)
        self.engines = new_engines

        # (3) Previous-pid tracking for traversal accounting.
        self._prev_pids: List[Optional[str]] = [None] * len(self.engines)

        # (4) Subscribe to phase-transition events for outcome reinforcement.
        self.bus.subscribe(PhaseTransitionEvent, self._on_phase_transition)

    # ── Engine factory override ─────────────────────────────────────────────

    def add_engine(
        self, E_star: Optional[float] = None, dt: float = 0.01,
    ) -> InstrumentedEngine:
        """Always produce InstrumentedEngine so Effector sees the
        AMEND-005 energy field populated at commit time."""
        eng = InstrumentedEngine(
            substrate=self.sub, bus=self.bus,
            E_star=E_star if E_star is not None else self.local_budget,
            dt=dt, cluster_id=self.cluster_id,
        )
        self.engines.append(eng)
        return eng

    # ── diffuse() override — traversal accounting ───────────────────────────

    def diffuse(self, n_steps: int = 1) -> None:
        """Lateral diffusion + per-step traversal recording."""
        for _ in range(n_steps):
            lateral = self._compute_lateral_forces()
            for eng, force in zip(self.engines, lateral):
                eng.step(external_force=force)

            # Align _prev_pids length to current engine count (spawn/cull).
            if len(self._prev_pids) < len(self.engines):
                self._prev_pids.extend(
                    [None] * (len(self.engines) - len(self._prev_pids))
                )
            elif len(self._prev_pids) > len(self.engines):
                self._prev_pids = self._prev_pids[: len(self.engines)]

            # Compute current wells and record well-crossings.
            current_pids: List[Optional[str]] = [
                self._nearest_constraint(e.v) for e in self.engines
            ]
            for i, pid_now in enumerate(current_pids):
                pid_prev = self._prev_pids[i]
                if (
                    pid_now is not None
                    and pid_prev is not None
                    and pid_now != pid_prev
                ):
                    self.sub.record_traversal(pid_now, pid_prev)
            self._prev_pids = current_pids

    # ── Phase-transition handler — active reinforcement ─────────────────────

    def _on_phase_transition(self, e: PhaseTransitionEvent) -> None:
        if e.cluster_id != self.cluster_id:
            return
        if e.to_phase != Phase.C:
            return
        pid = self._nearest_constraint(
            np.asarray(e.position, dtype=np.float64)
        )
        if pid is not None:
            self.sub.apply_outcome(pid)
