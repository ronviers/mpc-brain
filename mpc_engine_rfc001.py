"""
Metastable Propositional Calculus — Full Implementation
Conforms to RFC-001-MPC-BRAIN (April 2026)

Substrate · Langevin Layer · Operator Algebra · Cluster Network · Governor · Agent
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Phase, Events, and EventBus  —  RFC-001 §3, §6
#
#  Canonical definitions now live in mpc_kernel.rfc001 (carved in Session 6).
#  Re-exported here so this monolith keeps its pre-RFC-002 API while
#  downstream subscribers bind to a single type identity across the kernel,
#  this monolith, and the Session-4 InstrumentedEngine.
#
#  The kernel PhaseTransitionEvent adds `energy: float = 0.0` (AMEND-005,
#  Session 4) and `fdr_slope: Optional[float] = None` (Session 6). Both
#  fields default, so S1-era five-argument constructors still work.
# ═══════════════════════════════════════════════════════════════════════════════

from mpc_kernel.rfc001.phase import Phase
from mpc_kernel.rfc001.events import (
    PhaseTransitionEvent,
    LandauerEvent,
    BudgetResetEvent,
)
from mpc_kernel.rfc001.bus import EventBus


# ═══════════════════════════════════════════════════════════════════════════════
#  Value objects  (internal)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EnergyState:
    energy:   float
    gradient: np.ndarray
    hessian:  np.ndarray

@dataclass
class TopologyResult:
    phase:        Phase
    eigenvalues:  np.ndarray
    eigenvectors: np.ndarray
    basin_depth:  float

@dataclass
class ConstraintHandle:
    uid:            str
    proposition_id: str
    stiffness:      float   # λ in units of k_BT — dynamic control parameter


# ═══════════════════════════════════════════════════════════════════════════════
#  Calorimeter  —  RFC-001 §7  (passive subscriber, no brain references)
# ═══════════════════════════════════════════════════════════════════════════════

class Calorimeter:
    """
    RFC-001 §7 — Passive measurement subscriber.

    Attach to any EventBus via .attach(bus).
    MUST NOT hold a reference to any brain component.
    MUST NOT call any method on any brain component.
    Exposes get_heat_flux(cluster_id) for the Governor (RFC-001 §7, §8.4).
    """

    def __init__(self, kT: float = 1.0, window: int = 30):
        self.kT = kT
        self._window = window
        self.total_landauer = 0.0
        self.transitions: List[PhaseTransitionEvent] = []
        self._flux_buf:   Dict[str, List[float]] = {}
        self.heat_flux:   Dict[str, float] = {}

    def attach(self, bus: EventBus) -> "Calorimeter":
        """
        Subscribe to all RFC-001 §6 event types.
        Returns self for chaining.  MUST be called exactly once per bus.
        """
        bus.subscribe(PhaseTransitionEvent, self._on_transition)
        bus.subscribe(LandauerEvent,        self._on_landauer)
        bus.subscribe(BudgetResetEvent,     self._on_reset)
        return self

    def get_heat_flux(self, cluster_id: str) -> float:
        return self.heat_flux.get(cluster_id, 0.0)

    def clear_flux(self, cluster_id: str):
        self._flux_buf.pop(cluster_id, None)
        self.heat_flux.pop(cluster_id, None)

    def report(self) -> str:
        n      = len(self.transitions)
        resets = sum(1 for t in self.transitions if t.to_phase == Phase.R)
        return (
            f"Calorimeter: {n} transitions, {resets} resets, "
            f"total Landauer cost = {self.total_landauer:.4f} kT·ln2"
        )

    def _on_transition(self, e: PhaseTransitionEvent):
        self.transitions.append(e)

    def _on_landauer(self, e: LandauerEvent):
        cost = e.info_content * e.kT * np.log(2)
        self.total_landauer += cost
        self._push_flux(e.cluster_id, cost)

    def _on_reset(self, e: BudgetResetEvent):
        cost = e.info_cost * self.kT * np.log(2)
        self.total_landauer += cost
        self._push_flux(e.cluster_id, cost)

    def _push_flux(self, cluster_id: str, heat: float):
        buf = self._flux_buf.setdefault(cluster_id, [])
        buf.append(heat)
        if len(buf) > self._window:
            buf.pop(0)
        self.heat_flux[cluster_id] = float(np.mean(buf))


# ═══════════════════════════════════════════════════════════════════════════════
#  Substrate  —  RFC-001 §4.1
# ═══════════════════════════════════════════════════════════════════════════════

class Substrate:
    """
    RFC-001 §4.1 — Constraint compiler.

    Flattens propositions into a joint geometric potential
    V_total(v) = Σ λ_i · V_i(v) over configuration space R^n.

    MUST NOT hold a reference to any bus, calorimeter, or measurement
    component (RFC-001 §4.1).

    Public interface (RFC-001 §4.1):
        energy(v)            gradient(v)          hessian(v)
        classify(v)          register(id, fn, lam) update_lambda(handle, lam)
        deregister(handle)   frustration(v)
    """

    def __init__(
        self,
        dim:     int,
        E_c:     float = 0.50,
        E_s:     float = 2.00,
        epsilon: float = 1e-4,
    ):
        self.dim = dim
        self.E_c = E_c
        self.E_s = E_s
        self._eps = epsilon
        self._constraints: Dict[str, Tuple[Callable[[np.ndarray], float], ConstraintHandle]] = {}
        self._frustration:  Dict[Tuple[str, str], float] = {}

    # ── RFC-001 §4.1 public interface ─────────────────────────────────────────

    def energy(self, v: np.ndarray) -> float:
        """Total constraint energy at v, in units of k_BT."""
        e = 0.0
        for fn, h in self._constraints.values():
            e += h.stiffness * fn(v)
        return e

    def gradient(self, v: np.ndarray) -> np.ndarray:
        """First derivative of energy w.r.t. v."""
        g, eps = np.zeros(self.dim), self._eps
        for i in range(self.dim):
            vp, vm = v.copy(), v.copy()
            vp[i] += eps; vm[i] -= eps
            g[i] = (self.energy(vp) - self.energy(vm)) / (2 * eps)
        return g

    def hessian(self, v: np.ndarray) -> np.ndarray:
        """Second derivative of energy w.r.t. v.  MUST be symmetric."""
        n, eps = self.dim, self._eps
        H      = np.zeros((n, n))
        E0     = self.energy(v)
        for i in range(n):
            vpi, vmi = v.copy(), v.copy()
            vpi[i] += eps; vmi[i] -= eps
            H[i, i] = (self.energy(vpi) - 2 * E0 + self.energy(vmi)) / eps**2
            for j in range(i + 1, n):
                vpp, vpm, vmp, vmm = [v.copy() for _ in range(4)]
                vpp[i] += eps; vpp[j] += eps
                vpm[i] += eps; vpm[j] -= eps
                vmp[i] -= eps; vmp[j] += eps
                vmm[i] -= eps; vmm[j] -= eps
                val = (self.energy(vpp) - self.energy(vpm)
                       - self.energy(vmp) + self.energy(vmm)) / (4 * eps**2)
                H[i, j] = H[j, i] = val
        return H

    def classify(self, v: np.ndarray) -> Phase:
        """
        Phase classification per RFC-001 §3.1 (non-amendable):

            E < E_c  AND  λ_min(H) > 0   →  c
            E > E_s  OR   λ_min(H) < 0   →  k
            no constraints                →  r
            otherwise                     →  s
        """
        return self._topology(v).phase

    def register(
        self,
        proposition_id: str,
        fn:             Callable[[np.ndarray], float],
        lam:            float = 1.0,
    ) -> ConstraintHandle:
        """Register a constraint fn: R^n → R+ with stiffness λ (lam in k_BT)."""
        uid    = uuid.uuid4().hex[:8]
        handle = ConstraintHandle(uid=uid, proposition_id=proposition_id, stiffness=lam)
        self._constraints[uid] = (fn, handle)
        return handle

    def update_lambda(self, handle: ConstraintHandle, lam: float):
        """
        Modify stiffness of a registered constraint.  RFC-001 §4.1 (update_λ).
        Primary knob for budget regulation — varying λ varies effective E*.
        """
        if handle.uid in self._constraints:
            handle.stiffness = max(0.0, lam)

    def deregister(self, handle: ConstraintHandle):
        """
        Remove a constraint.  RFC-001 §4.1.
        MUST NOT emit any event — the calling layer emits LandauerEvent.
        """
        self._constraints.pop(handle.uid, None)

    def frustration(self, v: np.ndarray) -> Dict[Tuple[str, str], float]:
        """
        Pairwise joint energies ε_ij for all registered constraint pairs at v.
        RFC-001 §4.1.
        """
        uids   = list(self._constraints)
        result: Dict[Tuple[str, str], float] = {}
        for a, uid_a in enumerate(uids):
            fn_a, h_a = self._constraints[uid_a]
            for uid_b in uids[a + 1:]:
                fn_b, h_b = self._constraints[uid_b]
                result[(uid_a, uid_b)] = h_a.stiffness * fn_a(v) + h_b.stiffness * fn_b(v)
        self._frustration = result
        return result

    # ── internal helpers  (not part of RFC interface) ─────────────────────────

    @property
    def constraint_count(self) -> int:
        return len(self._constraints)

    def _topology(self, v: np.ndarray) -> TopologyResult:
        """Full topology result including eigenstructure.  Internal use only."""
        E = self.energy(v)

        if not self._constraints:
            return TopologyResult(Phase.R, np.zeros(self.dim), np.eye(self.dim), 0.0)

        H                = self.hessian(v)
        eigvals, eigvecs = np.linalg.eigh(H)
        pos_eigs         = eigvals[eigvals > 0]
        basin_depth      = float(pos_eigs.min()) if len(pos_eigs) else 0.0

        if E < self.E_c and eigvals.min() > 0:
            phase = Phase.C
        elif E > self.E_s or eigvals.min() < -0.05:
            phase = Phase.K
        else:
            phase = Phase.S

        return TopologyResult(phase, eigvals, eigvecs, basin_depth)

    def _energy_state(self, v: np.ndarray) -> EnergyState:
        """Bundle energy + gradient + hessian.  Internal convenience."""
        return EnergyState(energy=self.energy(v),
                           gradient=self.gradient(v),
                           hessian=self.hessian(v))

    def _average_degree(self) -> float:
        n = self.constraint_count
        if n <= 1:
            return 0.0
        active = sum(1 for val in self._frustration.values() if val > 0)
        return 2.0 * active / n

    def _min_nonzero_frustration(self) -> float:
        vals = [v for v in self._frustration.values() if v > 1e-9]
        return float(min(vals)) if vals else 1e-9


# ═══════════════════════════════════════════════════════════════════════════════
#  Operator Algebra  (dynamical constraint transformations)
# ═══════════════════════════════════════════════════════════════════════════════

class OperatorAlgebra:
    """
    MPC operators as dynamical landscape transformations.
    Holds exactly one Substrate and one EventBus.
    """

    def __init__(self, substrate: Substrate, bus: EventBus):
        self.sub = substrate
        self.bus = bus

    def commit(self, ha: ConstraintHandle, hb: ConstraintHandle) -> ConstraintHandle:
        """C(A, B) — logsumexp union.  High λ drives toward joint minimum or k."""
        fn_a, _ = self.sub._constraints.get(ha.uid, (None, None))
        fn_b, _ = self.sub._constraints.get(hb.uid, (None, None))
        if fn_a is None or fn_b is None:
            raise ValueError("commit: one or both handles not registered")
        la, lb = ha.stiffness, hb.stiffness

        def joint(v: np.ndarray) -> float:
            ea, eb = la * fn_a(v), lb * fn_b(v)
            m = max(ea, eb)
            return m + np.log(np.exp(ea - m) + np.exp(eb - m))

        return self.sub.register(f"C({ha.proposition_id},{hb.proposition_id})", joint, lam=2.0)

    def suspend(self, ha: ConstraintHandle, hb: ConstraintHandle) -> ConstraintHandle:
        """S(A, B) — softmin bimodal landscape.  Low λ maintains saddle (s-state)."""
        fn_a, _ = self.sub._constraints.get(ha.uid, (None, None))
        fn_b, _ = self.sub._constraints.get(hb.uid, (None, None))
        if fn_a is None or fn_b is None:
            raise ValueError("suspend: one or both handles not registered")
        la, lb = ha.stiffness, hb.stiffness

        def bimodal(v: np.ndarray) -> float:
            ea, eb = la * fn_a(v), lb * fn_b(v)
            m = min(ea, eb)
            return m - np.log(np.exp(-(ea - m)) + np.exp(-(eb - m)))

        return self.sub.register(f"S({ha.proposition_id},{hb.proposition_id})", bimodal, lam=0.3)

    def conflict_resolve(
        self,
        handle_k:       ConstraintHandle,
        global_reserve: float,
        cluster_id:     str,
        borrow_delta:   float = 0.5,
    ) -> Optional[ConstraintHandle]:
        """Relax λ if reserve allows; otherwise Landauer-reset."""
        if global_reserve > borrow_delta:
            self.sub.update_lambda(handle_k, handle_k.stiffness * 0.5)
            return handle_k
        return self.reset(handle_k, cluster_id)

    def reset(self, handle: ConstraintHandle, cluster_id: str) -> None:
        """
        R(X) — Landauer erasure.  RFC-001 §3.2.
        Emits LandauerEvent before deregistering.  Cost capped at 4 bits.
        """
        entry = self.sub._constraints.get(handle.uid)
        if entry is None:
            return None
        fn, _ = entry

        samples      = np.array([fn(np.random.randn(self.sub.dim)) for _ in range(32)])
        raw          = float(np.var(samples) + 1e-6)
        info_content = min(raw / (raw + 1.0) * 4.0, 4.0)

        self.bus.emit(LandauerEvent(cluster_id=cluster_id, info_content=info_content))
        self.sub.deregister(handle)
        log.debug(f"reset [{cluster_id}]: '{handle.proposition_id}' erased.")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Maintenance Field  —  RFC-001 §3.4
# ═══════════════════════════════════════════════════════════════════════════════

class MaintenanceField:
    """
    Per-engine EMA anti-friction pump.  RFC-001 §3.4.
    Active only in s-state.  Force magnitude ∝ (1 − barrier_strength).

    NOTE: AMEND-003 promotes this to cluster-scope lateral field.
    """

    def __init__(self, dim: int, lr: float = 0.05):
        self.dim = dim
        self.lr  = lr
        self._ema: Optional[np.ndarray] = None

    def update(self, v: np.ndarray, phase: Phase):
        if phase == Phase.S:
            self._ema = v.copy() if self._ema is None else (
                (1 - self.lr) * self._ema + self.lr * v
            )

    def force(self, v: np.ndarray, barrier_strength: float) -> np.ndarray:
        """F_maint = (1 − barrier_strength) · (ema − v) · 0.12"""
        if self._ema is None:
            return np.zeros(self.dim)
        return (1.0 - barrier_strength) * (self._ema - v) * 0.12


# ═══════════════════════════════════════════════════════════════════════════════
#  MetastableEngine  —  RFC-001 §4.2
# ═══════════════════════════════════════════════════════════════════════════════

class MetastableEngine:
    """
    RFC-001 §4.2 — Euler-Maruyama Langevin integrator.

    MUST hold exactly one Substrate and one EventBus.
    MUST NOT hold a reference to a Calorimeter.

    Public interface (RFC-001 §4.2):
        step(external_force)   run(n_steps)   phase
        detect_insight()       v              attention_scarcity
    """

    def __init__(
        self,
        substrate:        Substrate,
        bus:              EventBus,
        E_star:           float = 5.0,
        dt:               float = 0.01,
        barrier_strength: float = 0.5,
        cluster_id:       str   = "default",
    ):
        self.sub               = substrate
        self.bus               = bus
        self.E_star            = E_star
        self.dt                = dt
        self.barrier_strength  = barrier_strength
        self.cluster_id        = cluster_id

        self.v:                  np.ndarray = np.zeros(substrate.dim)
        self.attention_scarcity: float      = 0.10  # T: 0=focused, 1=distracted
        self._t:                 float      = 0.0

        self._phase_hist:  List[Tuple[float, Phase]] = []
        self._energy_hist: List[float]               = []
        self._reset_count: int                       = 0
        self._maint        = MaintenanceField(substrate.dim)

    # ── RFC-001 §4.2 public interface ─────────────────────────────────────────

    def step(self, external_force: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Advance v(t) by one integration step.

        Enforces RFC-001 §3.3 (budget hard wall) and §3.4 (maintenance invariant).
        Emits PhaseTransitionEvent on phase change; BudgetResetEvent on hard wall.
        """
        ext    = external_force if external_force is not None else np.zeros(self.sub.dim)
        state  = self.sub._energy_state(self.v)
        F_cons = -state.gradient

        prev_phase = self.sub.classify(self.v)
        self._maint.update(self.v, prev_phase)

        # RFC-001 §3.4 — maintenance force active only in s-state
        F_maint = (
            self._maint.force(self.v, self.barrier_strength)
            if prev_phase == Phase.S
            else np.zeros(self.sub.dim)
        )

        std     = np.sqrt(2.0 * self.attention_scarcity * self.dt + 1e-12)
        F_noise = std * np.random.randn(self.sub.dim)

        v_proposed = self.v + self.dt * (F_cons + F_maint + ext) + F_noise

        # RFC-001 §3.3 — hard budget wall
        if self.sub.energy(v_proposed) > self.E_star:
            self._trigger_reset(prev_phase)
            self._t += self.dt
            return self.v

        self.v    = v_proposed
        new_phase = self.sub.classify(self.v)

        if new_phase != prev_phase:
            self.bus.emit(PhaseTransitionEvent(
                from_phase=prev_phase,
                to_phase=new_phase,
                position=self.v.copy(),
                timestamp=self._t,
                cluster_id=self.cluster_id,
            ))

        self._phase_hist.append((self._t, new_phase))
        self._energy_hist.append(state.energy)
        self._t += self.dt
        return self.v

    def run(self, n_steps: int, forces: Optional[List[np.ndarray]] = None) -> np.ndarray:
        """Returns trajectory of shape (n_steps, dim).  RFC-001 §4.2."""
        traj = np.empty((n_steps, self.sub.dim))
        for i in range(n_steps):
            traj[i] = self.step(forces[i] if forces else None)
        return traj

    @property
    def phase(self) -> Phase:
        """Current phase of v(t).  RFC-001 §4.2."""
        return self.sub.classify(self.v)

    def detect_insight(self) -> bool:
        """
        Returns True when a sustained s → c energy drop is detected.  RFC-001 §4.2.

        Implementation definition (RFC-001 §4.2 requires documentation):
          "recent"    = last 10 integration steps
          "sustained" = first 5 of those steps contain at least one s-phase,
                        AND the final step is c-phase,
                        AND total energy drop across the window > 0.15 k_BT
        """
        if len(self._energy_hist) < 10:
            return False
        recent_e    = self._energy_hist[-10:]
        recent_ph   = [p for _, p in self._phase_hist[-10:]]
        energy_drop = recent_e[0] - recent_e[-1]
        had_s       = Phase.S in recent_ph[:5]
        now_c       = bool(recent_ph) and recent_ph[-1] == Phase.C
        return had_s and now_c and energy_drop > 0.15

    # ── internal ──────────────────────────────────────────────────────────────

    @property
    def dominant_phase(self) -> Phase:
        if not self._phase_hist:
            return Phase.R
        recent = [p for _, p in self._phase_hist[-50:]]
        return max(set(recent), key=recent.count)

    def _trigger_reset(self, prev_phase: Phase):
        """RFC-001 §3.3 — budget exceeded → reset, emit BudgetResetEvent (1 bit)."""
        self._reset_count += 1
        self.bus.emit(BudgetResetEvent(
            cluster_id=self.cluster_id,
            position=self.v.copy(),
            timestamp=self._t,
            info_cost=1.0,
        ))
        self.v = np.random.randn(self.sub.dim) * 0.01
        log.debug(f"[{self.cluster_id}] budget reset #{self._reset_count} at t={self._t:.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MPC Cluster  —  RFC-001 §4.3
# ═══════════════════════════════════════════════════════════════════════════════

class MPCCluster:
    """
    RFC-001 §4.3 — Colony of engines sharing a local E* budget pool.

    Engines share one Substrate and one EventBus.  Clusters share a bus
    but NOT a substrate (RFC-001 §8.2).

    Public interface (RFC-001 §4.3):
        load(constraints)    diffuse(n_steps)    separation_bound()
        enforce_separation() dominant_phase      extract_commitment()
        shed_load(factor)
    """

    def __init__(
        self,
        cluster_id:   str,
        dim:          int,
        local_budget: float,
        bus:          EventBus,
        E_c:          float = 0.50,
        E_s:          float = 2.00,
        alpha:        float = 0.10,
    ):
        self.cluster_id   = cluster_id
        self.local_budget = local_budget
        self.bus          = bus
        self.alpha        = alpha

        self.sub     = Substrate(dim=dim, E_c=E_c, E_s=E_s)
        self.engines: List[MetastableEngine] = []
        self.ops     = OperatorAlgebra(self.sub, bus)

        self._handles: Dict[str, ConstraintHandle] = {}

    # ── RFC-001 §4.3 public interface ─────────────────────────────────────────

    def load(
        self,
        constraints:  Dict[str, Callable[[np.ndarray], float]],
        stiffnesses:  Optional[Dict[str, float]] = None,
    ):
        """Register proposition → constraint_fn mappings.  RFC-001 §4.3."""
        for pid, fn in constraints.items():
            lam = (stiffnesses or {}).get(pid, 1.0)
            h   = self.sub.register(pid, fn, lam)
            self._handles[pid] = h

    def diffuse(self, n_steps: int = 1):
        """Advance all engines by n_steps.  RFC-001 §4.3."""
        for eng in self.engines:
            eng.run(n_steps)

    def separation_bound(self) -> float:
        """
        Theorem 6.1 bound N_max = √(2E* / α·ε_min·d_avg).  RFC-001 §4.3.
        Evaluated at first engine's current position.
        """
        v = self.engines[0].v if self.engines else np.zeros(self.sub.dim)
        self.sub.frustration(v)
        d_avg   = max(self.sub._average_degree(), 1e-6)
        eps_min = self.sub._min_nonzero_frustration()
        return float(np.sqrt(2.0 * self.local_budget / (self.alpha * eps_min * d_avg)))

    def enforce_separation(self):
        """
        Reset weakest constraints until s-count ≤ N_max.  RFC-001 §4.3.
        Each reset MUST emit a LandauerEvent on the bus.
        """
        N_active = self.count_s_state()
        N_max    = self.separation_bound()
        if N_active <= N_max:
            return
        excess  = int(N_active - N_max) + 1
        log.info(f"[{self.cluster_id}] N_active={N_active} > N_max={N_max:.1f} — shedding {excess}")
        victims = sorted(self._handles.values(), key=lambda h: h.stiffness)[:excess]
        for h in victims:
            self.ops.reset(h, self.cluster_id)
            self._handles.pop(h.proposition_id, None)

    @property
    def dominant_phase(self) -> Phase:
        """Most frequent phase among engines over recent window.  RFC-001 §4.3."""
        if not self.engines:
            return Phase.R
        phases = [e.dominant_phase for e in self.engines]
        return max(set(phases), key=phases.count)

    def extract_commitment(self) -> Optional[np.ndarray]:
        """Return first c-state engine position, or None.  RFC-001 §4.3."""
        for eng in self.engines:
            if eng.phase == Phase.C:
                return eng.v.copy()
        return None

    def shed_load(self, factor: float = 0.5):
        """Reset weakest (factor×100)% of constraints.  RFC-001 §4.3."""
        n_shed  = max(1, int(len(self._handles) * factor))
        victims = sorted(self._handles.values(), key=lambda h: h.stiffness)[:n_shed]
        for h in victims:
            self.ops.reset(h, self.cluster_id)
            self._handles.pop(h.proposition_id, None)

    # ── construction helpers ───────────────────────────────────────────────────

    def add_engine(self, E_star: Optional[float] = None, dt: float = 0.01) -> MetastableEngine:
        eng = MetastableEngine(
            substrate=self.sub,
            bus=self.bus,
            E_star=E_star if E_star is not None else self.local_budget,
            dt=dt,
            cluster_id=self.cluster_id,
        )
        self.engines.append(eng)
        return eng

    # ── cross-cluster  (RFC-001 §8.3 — routing only) ──────────────────────────

    def cross_cluster_compatibility(self, other: "MPCCluster") -> np.ndarray:
        v_s  = self.engines[0].v  if self.engines  else np.zeros(self.sub.dim)
        v_o  = other.engines[0].v if other.engines else np.zeros(other.sub.dim)
        d_s, d_o = self.sub.dim, other.sub.dim
        si   = list(self.sub._constraints.items())
        oi   = list(other.sub._constraints.items())
        if not si or not oi:
            return np.zeros((len(si), len(oi)))
        eps  = np.zeros((len(si), len(oi)))
        for i, (_, (fn_i, h_i)) in enumerate(si):
            for j, (_, (fn_j, h_j)) in enumerate(oi):
                eps[i, j] = (
                    h_i.stiffness * fn_i(v_o[:d_s])
                    + h_j.stiffness * fn_j(v_s[:d_o])
                )
        return eps

    def inject_conflict(self, signal: np.ndarray):
        """Signal arrives as conflict (high-ε route).  RFC-001 §8.3."""
        for eng in self.engines:
            eng.v += signal * 0.5
            eng.attention_scarcity = min(1.0, eng.attention_scarcity + 0.2)

    def integrate_signal(self, signal: np.ndarray):
        """Signal arrives cleanly (low-ε route).  RFC-001 §8.3."""
        for eng in self.engines:
            eng.v += signal * 0.1

    def count_s_state(self) -> int:
        return sum(1 for e in self.engines if e.phase == Phase.S)


# ═══════════════════════════════════════════════════════════════════════════════
#  Thermodynamic Governor  —  RFC-001 §8.4
# ═══════════════════════════════════════════════════════════════════════════════

class ThermodynamicGovernor:
    """
    RFC-001 §8.4 — Budget allocation and thermal runaway detection.

    MAY read heat flux via Network.get_heat_flux() (the only permitted
    read-path from measurement back to governance).
    MAY call cluster.shed_load() and engine quench.
    MUST NOT modify the energy landscape directly.
    """

    def __init__(self, network: "Network", max_heat_fraction: float = 0.10):
        self.net               = network
        self.max_heat_fraction = max_heat_fraction

    def allocate_budgets(self, task_requirements: Dict[str, float]):
        """Proportional E* allocation — 'attention' in MPC formalism."""
        total     = sum(c.local_budget for c in self.net.clusters.values())
        total_req = sum(task_requirements.values()) + 1e-9
        for cid, cluster in self.net.clusters.items():
            req                  = task_requirements.get(cid, 0.1)
            cluster.local_budget = max(0.5, total * req / total_req)
            for eng in cluster.engines:
                eng.E_star = cluster.local_budget
        log.info(f"Governor: budgets reallocated across {len(self.net.clusters)} clusters")

    def detect_thermal_runaway(self) -> List[str]:
        hot = []
        for cid, cluster in self.net.clusters.items():
            flux      = self.net.get_heat_flux(cid)
            threshold = cluster.local_budget * self.max_heat_fraction
            if flux > threshold:
                hot.append(cid)
                log.warning(f"Thermal runaway [{cid}]: flux={flux:.4f} > {threshold:.4f}")
        return hot

    def quench(self, cluster_id: str):
        """Force r-state across cluster.  Clears flux window for recovery."""
        cluster = self.net.clusters.get(cluster_id)
        if cluster:
            for eng in cluster.engines:
                eng.v                  = np.zeros(eng.sub.dim)
                eng.attention_scarcity = 0.0
            if self.net._cal:
                self.net._cal.clear_flux(cluster_id)
            log.info(f"Governor: quenched [{cluster_id}]")

    def tick(self):
        for cid in self.detect_thermal_runaway():
            self.quench(cid)
        for cluster in self.net.clusters.values():
            cluster.enforce_separation()


# ═══════════════════════════════════════════════════════════════════════════════
#  Network  —  RFC-001 §4.4
# ═══════════════════════════════════════════════════════════════════════════════

class Network:
    """
    RFC-001 §4.4 — Graph of clusters with a shared EventBus.

    MUST NOT create or hold a Calorimeter.
    Calorimeter attaches externally via attach_calorimeter().

    Public interface (RFC-001 §4.4):
        add_cluster(id, ...)   route(src, tgt, signal)   step()   bus
    """

    def __init__(
        self,
        kT:               float = 1.0,
        compat_threshold: float = 0.5,
        bus:              Optional[EventBus] = None,
    ):
        self.kT               = kT
        self.compat_threshold = compat_threshold
        self.bus              = bus if bus is not None else EventBus()
        self._cal:   Optional[Calorimeter] = None
        self.clusters: Dict[str, MPCCluster] = {}
        self.governor  = ThermodynamicGovernor(self)

    # ── RFC-001 §4.4 public interface ─────────────────────────────────────────

    def add_cluster(
        self,
        cluster_id:   str,
        dim:          int,
        local_budget: float = 5.0,
        E_c:          float = 0.5,
        E_s:          float = 2.0,
    ) -> MPCCluster:
        c = MPCCluster(cluster_id, dim, local_budget, self.bus, E_c, E_s)
        self.clusters[cluster_id] = c
        return c

    def route(self, src_id: str, tgt_id: str, signal: np.ndarray):
        """
        RFC-001 §4.4, §8.3 — Route signal by cross-cluster frustration.

        ε̄ < compat_threshold  →  integrate_signal (clean)
        ε̄ ≥ compat_threshold  →  inject_conflict
        """
        src = self.clusters.get(src_id)
        tgt = self.clusters.get(tgt_id)
        if src is None or tgt is None:
            return
        eps = src.cross_cluster_compatibility(tgt)
        avg = float(eps.mean()) if eps.size else 0.0
        if avg > self.compat_threshold:
            log.debug(f"route {src_id}→{tgt_id}: conflict (ε̄={avg:.3f})")
            tgt.inject_conflict(signal)
        else:
            log.debug(f"route {src_id}→{tgt_id}: integrate (ε̄={avg:.3f})")
            tgt.integrate_signal(signal)

    def step(self):
        """Advance all clusters one step, then run governance tick.  RFC-001 §4.4."""
        for cluster in self.clusters.values():
            cluster.diffuse(n_steps=1)
        self.governor.tick()

    # ── calorimeter attachment  (RFC-001 §7) ──────────────────────────────────

    def attach_calorimeter(self, cal: Calorimeter) -> Calorimeter:
        """
        Store a Calorimeter reference for Governor heat-flux queries.
        RFC-001 §7: cal.attach(bus) MUST have been called before this.
        This method MUST NOT call cal.attach() — that would duplicate handlers.
        """
        self._cal = cal
        return self._cal

    def get_heat_flux(self, cluster_id: str) -> float:
        """Governor read-path to Calorimeter.  RFC-001 §7, §8.4."""
        return self._cal.get_heat_flux(cluster_id) if self._cal else 0.0

    # ── convenience ───────────────────────────────────────────────────────────

    def run(self, n_steps: int):
        for _ in range(n_steps):
            self.step()

    def status(self) -> str:
        rows = ["══ Network Status ══"]
        for cid, c in self.clusters.items():
            n_max = c.separation_bound()
            rows.append(
                f"  [{cid:12s}]  phase={c.dominant_phase.value}  "
                f"S-active={c.count_s_state()}  "
                f"N_max={n_max:5.1f}  budget={c.local_budget:.2f}"
            )
        if self._cal:
            rows.append(self._cal.report())
        return "\n".join(rows)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers: encode / decode  —  RFC-001 §5
# ═══════════════════════════════════════════════════════════════════════════════

def encode_observation(
    obs: np.ndarray,
    dim: int,
) -> Dict[str, Callable[[np.ndarray], float]]:
    """
    RFC-001 §5 — Observation encoder.

    Guarantees fn(v) = 0 at satisfaction point, fn(v) > 0 elsewhere.
    Stiffness is caller-controlled via load(stiffnesses=...).
    """
    fns: Dict[str, Callable[[np.ndarray], float]] = {}
    for i, val in enumerate(obs[:dim]):
        pid  = f"obs_{i}"
        t, j = float(val), i % dim
        fns[pid] = lambda v, _t=t, _j=j: float((v[_j] - _t) ** 2)
    return fns


def decode_commitment(v: np.ndarray) -> np.ndarray:
    return v.copy()


# ═══════════════════════════════════════════════════════════════════════════════
#  MPC Agent
# ═══════════════════════════════════════════════════════════════════════════════

class MPCAgent:
    """
    Autonomous perceive → think → act loop.

    RFC-001 §7 compliance: Calorimeter.attach(bus) called exactly once.
    Network.attach_calorimeter() stores the reference; it does NOT re-subscribe.
    """

    def __init__(
        self,
        dim:               int   = 8,
        kT:                float = 1.0,
        perception_budget: float = 3.0,
        reasoning_budget:  float = 6.0,
        action_budget:     float = 4.0,
        dt:                float = 0.01,
    ):
        self.dim     = dim
        self.network = Network(kT=kT)

        # attach once; attach_calorimeter stores without re-subscribing
        self.cal = Calorimeter(kT=kT).attach(self.network.bus)
        self.network.attach_calorimeter(self.cal)

        self.perception = self.network.add_cluster(
            "perception", dim=dim, local_budget=perception_budget, E_c=0.3, E_s=1.5)
        self.reasoning  = self.network.add_cluster(
            "reasoning",  dim=dim, local_budget=reasoning_budget,  E_c=0.5, E_s=2.5)
        self.action     = self.network.add_cluster(
            "action",     dim=dim, local_budget=action_budget,     E_c=0.4, E_s=2.0)

        for cluster in (self.perception, self.reasoning, self.action):
            cluster.add_engine(dt=dt)

        self._step_count = 0

    def perceive(self, observation: np.ndarray):
        fns = encode_observation(observation, self.dim)
        self.perception.load(fns)
        self.network.route("perception", "reasoning", observation[:self.dim].copy())

    def think(self, duration: int = 200) -> Optional[np.ndarray]:
        for _ in range(duration):
            self.network.step()
            self._step_count += 1

            for eng in self.reasoning.engines:
                if eng.detect_insight():
                    commitment = self.reasoning.extract_commitment()
                    if commitment is not None:
                        self.network.route("reasoning", "action", commitment)
                        return commitment

            if self.network.governor.detect_thermal_runaway():
                self.reasoning.shed_load(factor=0.5)

        return self.reasoning.extract_commitment()

    def act(self) -> Optional[np.ndarray]:
        if self.action.dominant_phase == Phase.C:
            c = self.action.extract_commitment()
            return decode_commitment(c) if c is not None else None
        return None

    def run_episode(self, observation: np.ndarray, think_steps: int = 200) -> Optional[np.ndarray]:
        self.perceive(observation)
        self.think(duration=think_steps)
        return self.act()

    def reallocate_attention(self, priorities: Dict[str, float]):
        self.network.governor.allocate_budgets(priorities)

    def status(self) -> str:
        return f"MPCAgent  steps={self._step_count}\n{self.network.status()}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════════════════════════

def _demo_substrate():
    print("\n─── Substrate (RFC-001 §4.1) ───")
    sub = Substrate(dim=2, E_c=0.3, E_s=1.5)
    sub.register("x1=1",    lambda v: (v[0] - 1.0) ** 2)
    sub.register("x2=1",    lambda v: (v[1] - 1.0) ** 2)
    sub.register("x1+x2=1", lambda v: (v[0] + v[1] - 1.0) ** 2)
    for label, v in [
        ("(1,1) joint min of A∧B", np.array([1.0, 1.0])),
        ("(0.5,0.5) satisfies C",  np.array([0.5, 0.5])),
        ("origin",                  np.array([0.0, 0.0])),
    ]:
        print(f"  {label:28s}  E={sub.energy(v):.3f}  phase={sub.classify(v).value}")


def _demo_operators():
    print("\n─── Operator algebra ───")
    bus = EventBus()
    cal = Calorimeter().attach(bus)
    sub = Substrate(dim=2, E_c=0.5, E_s=2.0)
    ops = OperatorAlgebra(sub, bus)
    ha  = sub.register("A", lambda v: (v[0] - 1.0) ** 2)
    hb  = sub.register("B", lambda v: (v[1] - 1.0) ** 2)
    hc  = ops.commit(ha, hb)
    ops.suspend(ha, hb)
    print(f"  C(A,B) at (1,1):     E={sub.energy(np.array([1.0,1.0])):.3f}")
    print(f"  C(A,B) at (0.5,0.5): E={sub.energy(np.array([0.5,0.5])):.3f}")
    ops.reset(hc, "demo")
    print(f"  After Reset(C): {cal.report()}")


def _demo_engine():
    print("\n─── MetastableEngine (RFC-001 §4.2) ───")
    bus = EventBus.null()
    sub = Substrate(dim=4, E_c=0.4, E_s=2.0)
    sub.register("well", lambda v: float(np.sum((v - np.array([1,0,0,0])) ** 2)))
    eng   = MetastableEngine(sub, bus=bus, E_star=3.0, dt=0.02, cluster_id="test")
    eng.v = np.random.randn(4) * 0.5
    eng.run(100)
    from collections import Counter
    phases = []
    eng2   = MetastableEngine(sub, bus=EventBus.null(), E_star=3.0, dt=0.02, cluster_id="t2")
    eng2.v = np.random.randn(4) * 0.5
    for _ in range(100):
        eng2.step()
        phases.append(eng2.phase.value)
    print(f"  Phase distribution: {dict(Counter(phases))}")
    print(f"  Final phase: {eng2.phase.value}  resets: {eng2._reset_count}")
    print(f"  detect_insight(): {eng2.detect_insight()}")


def _demo_agent():
    print("\n─── MPCAgent episode ───")
    agent = MPCAgent(dim=6, kT=1.0,
                     perception_budget=8.0,
                     reasoning_budget=10.0,
                     action_budget=6.0,
                     dt=0.02)
    obs = np.random.randn(6) * 0.3
    agent.reallocate_attention({"perception": 2.0, "reasoning": 4.0, "action": 2.0})
    result = agent.run_episode(obs, think_steps=200)
    print(agent.status())
    if result is not None:
        print(f"  Action emitted: {np.round(result, 3)}")
    else:
        print("  No committed action (increase think_steps or budget)")
    print(f"  {agent.cal.report()}")


if __name__ == "__main__":
    np.random.seed(42)
    _demo_substrate()
    _demo_operators()
    _demo_engine()
    _demo_agent()
