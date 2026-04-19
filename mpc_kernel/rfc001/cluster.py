import logging
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

from .phase import Phase
from .bus import EventBus
from .events import LandauerEvent
from .substrate import Substrate, ConstraintHandle
from .engine import MetastableEngine

log = logging.getLogger(__name__)

class OperatorAlgebra:
    def __init__(self, substrate: Substrate, bus: EventBus):
        self.sub = substrate
        self.bus = bus

    def commit(self, ha: ConstraintHandle, hb: ConstraintHandle) -> ConstraintHandle:
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

    def conflict_resolve(self, handle_k: ConstraintHandle, global_reserve: float, cluster_id: str, borrow_delta: float = 0.5) -> Optional[ConstraintHandle]:
        if global_reserve > borrow_delta:
            self.sub.update_lambda(handle_k, handle_k.stiffness * 0.5)
            return handle_k
        return self.reset(handle_k, cluster_id)

    def reset(self, handle: ConstraintHandle, cluster_id: str) -> None:
        entry = self.sub._constraints.get(handle.uid)
        if entry is None:
            return None
        fn, _ = entry

        samples = np.array([fn(np.random.randn(self.sub.dim)) for _ in range(32)])
        raw = float(np.var(samples) + 1e-6)
        info_content = min(raw / (raw + 1.0) * 4.0, 4.0)

        self.bus.emit(LandauerEvent(cluster_id=cluster_id, info_content=info_content))
        self.sub.deregister(handle)
        log.debug(f"reset [{cluster_id}]: '{handle.proposition_id}' erased.")
        return None

class MPCCluster:
    def __init__(self, cluster_id: str, dim: int, local_budget: float, bus: EventBus, E_c: float = 0.50, E_s: float = 2.00, alpha: float = 0.10):
        self.cluster_id = cluster_id
        self.local_budget = local_budget
        self.bus = bus
        self.alpha = alpha
        self.sub = Substrate(dim=dim, E_c=E_c, E_s=E_s)
        self.engines: List[MetastableEngine] = []
        self.ops = OperatorAlgebra(self.sub, bus)
        self._handles: Dict[str, ConstraintHandle] = {}

    def load(self, constraints: Dict[str, Callable[[np.ndarray], float]], stiffnesses: Optional[Dict[str, float]] = None):
        for pid, fn in constraints.items():
            lam = (stiffnesses or {}).get(pid, 1.0)
            h = self.sub.register(pid, fn, lam)
            self._handles[pid] = h

    def diffuse(self, n_steps: int = 1):
        for eng in self.engines:
            eng.run(n_steps)

    def separation_bound(self) -> float:
        v = self.engines[0].v if self.engines else np.zeros(self.sub.dim)
        self.sub.frustration(v)
        d_avg = max(self.sub._average_degree(), 1e-6)
        eps_min = self.sub._min_nonzero_frustration()
        return float(np.sqrt(2.0 * self.local_budget / (self.alpha * eps_min * d_avg)))

    def enforce_separation(self):
        N_active = self.count_s_state()
        N_max = self.separation_bound()
        if N_active <= N_max:
            return
        excess = int(N_active - N_max) + 1
        log.info(f"[{self.cluster_id}] N_active={N_active} > N_max={N_max:.1f} — shedding {excess}")
        victims = sorted(self._handles.values(), key=lambda h: h.stiffness)[:excess]
        for h in victims:
            self.ops.reset(h, self.cluster_id)
            self._handles.pop(h.proposition_id, None)

    @property
    def dominant_phase(self) -> Phase:
        if not self.engines:
            return Phase.R
        phases = [e.dominant_phase for e in self.engines]
        return max(set(phases), key=phases.count)

    def extract_commitment(self) -> Optional[np.ndarray]:
        for eng in self.engines:
            if eng.phase == Phase.C:
                return eng.v.copy()
        return None

    def shed_load(self, factor: float = 0.5):
        n_shed = max(1, int(len(self._handles) * factor))
        victims = sorted(self._handles.values(), key=lambda h: h.stiffness)[:n_shed]
        for h in victims:
            self.ops.reset(h, self.cluster_id)
            self._handles.pop(h.proposition_id, None)

    def add_engine(self, E_star: Optional[float] = None, dt: float = 0.01) -> MetastableEngine:
        eng = MetastableEngine(
            substrate=self.sub, bus=self.bus,
            E_star=E_star if E_star is not None else self.local_budget,
            dt=dt, cluster_id=self.cluster_id,
        )
        self.engines.append(eng)
        return eng

    def cross_cluster_compatibility(self, other: "MPCCluster") -> np.ndarray:
        v_s = self.engines[0].v if self.engines else np.zeros(self.sub.dim)
        v_o = other.engines[0].v if other.engines else np.zeros(other.sub.dim)
        d_s, d_o = self.sub.dim, other.sub.dim
        si = list(self.sub._constraints.items())
        oi = list(other.sub._constraints.items())
        if not si or not oi:
            return np.zeros((len(si), len(oi)))
        eps = np.zeros((len(si), len(oi)))
        for i, (_, (fn_i, h_i)) in enumerate(si):
            for j, (_, (fn_j, h_j)) in enumerate(oi):
                eps[i, j] = (h_i.stiffness * fn_i(v_o[:d_s]) + h_j.stiffness * fn_j(v_s[:d_o]))
        return eps

    def inject_conflict(self, signal: np.ndarray):
        for eng in self.engines:
            eng.v += signal * 0.5
            eng.attention_scarcity = min(1.0, eng.attention_scarcity + 0.2)

    def integrate_signal(self, signal: np.ndarray):
        for eng in self.engines:
            eng.v += signal * 0.1

    def count_s_state(self) -> int:
        return sum(1 for e in self.engines if e.phase == Phase.S)