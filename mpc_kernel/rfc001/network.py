import logging
from typing import Dict, List, Optional
import numpy as np

from .phase import Phase
from .events import PhaseTransitionEvent, LandauerEvent, BudgetResetEvent
from .bus import EventBus
from .cluster import MPCCluster

log = logging.getLogger(__name__)

class Calorimeter:
    def __init__(self, kT: float = 1.0, window: int = 30):
        self.kT = kT
        self._window = window
        self.total_landauer = 0.0
        self.transitions: List[PhaseTransitionEvent] = []
        self._flux_buf: Dict[str, List[float]] = {}
        self.heat_flux: Dict[str, float] = {}

    def attach(self, bus: EventBus) -> "Calorimeter":
        bus.subscribe(PhaseTransitionEvent, self._on_transition)
        bus.subscribe(LandauerEvent, self._on_landauer)
        bus.subscribe(BudgetResetEvent, self._on_reset)
        return self

    def get_heat_flux(self, cluster_id: str) -> float:
        return self.heat_flux.get(cluster_id, 0.0)

    def clear_flux(self, cluster_id: str):
        self._flux_buf.pop(cluster_id, None)
        self.heat_flux.pop(cluster_id, None)

    def report(self) -> str:
        n = len(self.transitions)
        resets = sum(1 for t in self.transitions if t.to_phase == Phase.R)
        return f"Calorimeter: {n} transitions, {resets} resets, total Landauer cost = {self.total_landauer:.4f} kT·ln2"

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

class ThermodynamicGovernor:
    def __init__(self, network: "Network", max_heat_fraction: float = 0.10):
        self.net = network
        self.max_heat_fraction = max_heat_fraction

    def allocate_budgets(self, task_requirements: Dict[str, float]):
        total = sum(c.local_budget for c in self.net.clusters.values())
        total_req = sum(task_requirements.values()) + 1e-9
        for cid, cluster in self.net.clusters.items():
            req = task_requirements.get(cid, 0.1)
            cluster.local_budget = max(0.5, total * req / total_req)
            for eng in cluster.engines:
                eng.E_star = cluster.local_budget
        log.info(f"Governor: budgets reallocated across {len(self.net.clusters)} clusters")

    def detect_thermal_runaway(self) -> List[str]:
        hot = []
        for cid, cluster in self.net.clusters.items():
            flux = self.net.get_heat_flux(cid)
            threshold = cluster.local_budget * self.max_heat_fraction
            if flux > threshold:
                hot.append(cid)
                log.warning(f"Thermal runaway [{cid}]: flux={flux:.4f} > {threshold:.4f}")
        return hot

    def quench(self, cluster_id: str):
        cluster = self.net.clusters.get(cluster_id)
        if cluster:
            for eng in cluster.engines:
                eng.v = np.zeros(eng.sub.dim)
                eng.attention_scarcity = 0.0
            if self.net._cal:
                self.net._cal.clear_flux(cluster_id)
            log.info(f"Governor: quenched [{cluster_id}]")

    def tick(self):
        for cid in self.detect_thermal_runaway():
            self.quench(cid)
        for cluster in self.net.clusters.values():
            cluster.enforce_separation()

class Network:
    def __init__(self, kT: float = 1.0, compat_threshold: float = 0.5, bus: Optional[EventBus] = None):
        self.kT = kT
        self.compat_threshold = compat_threshold
        self.bus = bus if bus is not None else EventBus()
        self._cal: Optional[Calorimeter] = None
        self.clusters: Dict[str, MPCCluster] = {}
        self.governor = ThermodynamicGovernor(self)

    def add_cluster(self, cluster_id: str, dim: int, local_budget: float = 5.0, E_c: float = 0.5, E_s: float = 2.0) -> MPCCluster:
        c = MPCCluster(cluster_id, dim, local_budget, self.bus, E_c, E_s)
        self.clusters[cluster_id] = c
        return c

    def route(self, src_id: str, tgt_id: str, signal: np.ndarray):
        src = self.clusters.get(src_id)
        tgt = self.clusters.get(tgt_id)
        if src is None or tgt is None: return
        eps = src.cross_cluster_compatibility(tgt)
        avg = float(eps.mean()) if eps.size else 0.0
        if avg > self.compat_threshold:
            log.debug(f"route {src_id}→{tgt_id}: conflict (ε̄={avg:.3f})")
            tgt.inject_conflict(signal)
        else:
            log.debug(f"route {src_id}→{tgt_id}: integrate (ε̄={avg:.3f})")
            tgt.integrate_signal(signal)

    def step(self):
        for cluster in self.clusters.values():
            cluster.diffuse(n_steps=1)
        self.governor.tick()

    def attach_calorimeter(self, cal: Calorimeter) -> Calorimeter:
        self._cal = cal
        return self._cal

    def get_heat_flux(self, cluster_id: str) -> float:
        return self._cal.get_heat_flux(cluster_id) if self._cal else 0.0

    def run(self, n_steps: int):
        for _ in range(n_steps): self.step()

    def status(self) -> str:
        rows = ["══ Network Status ══"]
        for cid, c in self.clusters.items():
            n_max = c.separation_bound()
            rows.append(f"  [{cid:12s}]  phase={c.dominant_phase.value}  S-active={c.count_s_state()}  N_max={n_max:5.1f}  budget={c.local_budget:.2f}")
        if self._cal:
            rows.append(self._cal.report())
        return "\n".join(rows)