"""Metareasoner — AMEND-008 normative implementation.

Spec source: SESSION-5-TASK-PROMPT-v2.md §AMEND-008.

RFC-001 §7 compliance: passive measurement. Subscribes to exactly two
event types (BudgetResetEvent, EffectorEvent). Holds no Substrate / Engine
/ Cluster / Effector reference.

Signal definitions (all clipped to [0, 1]):

    under_budget(c)            = _landauer_total[c] / max(_total_cost_total[c], 1e-9)
    distant_start(c)           = mean(work_estimates) / _known_e_star[c]   (0 if no commits)
    exploration_saturation(c)  = (max bucket count) / len(_commit_history[c])  (0 if empty)
                                  bucket = nearest existing commit position,
                                  Euclidean tol 0.5
    thermal_pressure(c)        = len(_reset_history[c]) / window
    idle(c)                    = _steps_since_commit[c] / window
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional

import numpy as np

from mpc_kernel.rfc001.events import BudgetResetEvent, EventBus
from mpc_session4 import EffectorEvent


class Metareasoner:
    """Event-driven signal computation per cluster_id.

    Keeps five per-cluster dicts. Two event handlers (BudgetResetEvent and
    EffectorEvent). A tick() helper that advances _steps_since_commit for
    every registered cluster.
    """

    def __init__(self, window: int = 50):
        self.window: int = int(window)

        self._commit_history: Dict[str, Deque[EffectorEvent]] = {}
        self._reset_history: Dict[str, Deque[float]] = {}
        self._landauer_total: Dict[str, float] = {}
        self._total_cost_total: Dict[str, float] = {}
        self._steps_since_commit: Dict[str, int] = {}
        self._known_e_star: Dict[str, float] = {}

        self._registered: set = set()
        self._attached_bus: Optional[EventBus] = None

    # ── RFC-001 §7 public interface ──────────────────────────────────────────

    def attach(self, bus: EventBus) -> "Metareasoner":
        """Subscribe to BudgetResetEvent + EffectorEvent. Returns self."""
        bus.subscribe(BudgetResetEvent, self._on_reset)
        bus.subscribe(EffectorEvent, self._on_commit)
        self._attached_bus = bus
        return self

    def register_cluster(self, cluster_id: str, e_star: float) -> None:
        """Required before `snapshot()` returns non-empty for this cluster."""
        self._registered.add(cluster_id)
        self._known_e_star[cluster_id] = float(e_star)
        self._commit_history.setdefault(
            cluster_id, deque(maxlen=self.window)
        )
        self._reset_history.setdefault(
            cluster_id, deque(maxlen=self.window)
        )
        self._landauer_total.setdefault(cluster_id, 0.0)
        self._total_cost_total.setdefault(cluster_id, 0.0)
        self._steps_since_commit.setdefault(cluster_id, 0)

    def tick(self) -> None:
        """Increment _steps_since_commit for every registered cluster."""
        for cid in self._registered:
            self._steps_since_commit[cid] = self._steps_since_commit.get(cid, 0) + 1

    def snapshot(self, cluster_id: str) -> Dict[str, float]:
        """Return the five signals or {} if cluster not registered."""
        if cluster_id not in self._registered:
            return {}

        commits = self._commit_history.get(cluster_id, deque())
        resets = self._reset_history.get(cluster_id, deque())
        e_star = self._known_e_star.get(cluster_id, 1.0) or 1.0

        # under_budget
        l_tot = self._landauer_total.get(cluster_id, 0.0)
        c_tot = self._total_cost_total.get(cluster_id, 0.0)
        under_budget = l_tot / max(c_tot, 1e-9)

        # distant_start
        if commits:
            work_mean = float(np.mean([ev.work_estimate for ev in commits]))
            distant_start = work_mean / max(e_star, 1e-9)
        else:
            distant_start = 0.0

        # exploration_saturation: nearest-bucket, Euclidean tol 0.5
        n_commits = len(commits)
        if n_commits == 0:
            exploration_saturation = 0.0
        else:
            positions: List[np.ndarray] = [
                np.asarray(ev.position, dtype=np.float64) for ev in commits
            ]
            bucket_centres: List[np.ndarray] = []
            counts: List[int] = []
            for p in positions:
                matched = False
                for i, centre in enumerate(bucket_centres):
                    n = min(len(p), len(centre))
                    if float(np.linalg.norm(p[:n] - centre[:n])) <= 0.5:
                        counts[i] += 1
                        matched = True
                        break
                if not matched:
                    bucket_centres.append(p.copy())
                    counts.append(1)
            max_bucket = max(counts) if counts else 0
            exploration_saturation = max_bucket / n_commits

        # thermal_pressure
        thermal_pressure = len(resets) / max(self.window, 1)

        # idle
        idle = self._steps_since_commit.get(cluster_id, 0) / max(self.window, 1)

        def clip(x: float) -> float:
            return float(max(0.0, min(1.0, x)))

        return {
            "under_budget": clip(under_budget),
            "distant_start": clip(distant_start),
            "exploration_saturation": clip(exploration_saturation),
            "thermal_pressure": clip(thermal_pressure),
            "idle": clip(idle),
        }

    # ── event handlers (internal) ────────────────────────────────────────────

    def _on_reset(self, e: BudgetResetEvent) -> None:
        cid = e.cluster_id
        if cid not in self._reset_history:
            self._reset_history[cid] = deque(maxlen=self.window)
        self._reset_history[cid].append(float(e.timestamp))

    def _on_commit(self, e: EffectorEvent) -> None:
        cid = e.cluster_id
        if cid not in self._commit_history:
            self._commit_history[cid] = deque(maxlen=self.window)
        self._commit_history[cid].append(e)
        self._landauer_total[cid] = (
            self._landauer_total.get(cid, 0.0) + float(e.landauer_cost)
        )
        self._total_cost_total[cid] = (
            self._total_cost_total.get(cid, 0.0) + float(e.total_cost)
        )
        # A commit resets idle: the agent just committed.
        self._steps_since_commit[cid] = 0


# ── AMEND-008 acceptance test ────────────────────────────────────────────────

def test_amend008() -> bool:
    """v2 §AMEND-008 expected-values table (tolerance 0.01)."""
    bus = EventBus()
    mr = Metareasoner(window=50).attach(bus)
    mr.register_cluster("A", e_star=10.0)

    # 5 × BudgetResetEvent
    for i, t in enumerate([0.1, 0.2, 0.3, 0.4, 0.5]):
        bus.emit(BudgetResetEvent(cluster_id="A", position=np.zeros(4), timestamp=t))

    # 2 × EffectorEvent(work=2.0, total=3.9, landauer=1.5), pos [1,0,0,0]
    for _ in range(2):
        bus.emit(EffectorEvent(
            cluster_id="A",
            position=np.array([1.0, 0.0, 0.0, 0.0]),
            energy_at_c=0.4,
            landauer_cost=1.5,
            work_estimate=2.0,
            total_cost=3.9,
            timestamp=1.0,
        ))

    # 1 × EffectorEvent(work=4.0, total=4.5, landauer=0.0), pos [1,0,0,0]
    bus.emit(EffectorEvent(
        cluster_id="A",
        position=np.array([1.0, 0.0, 0.0, 0.0]),
        energy_at_c=0.5,
        landauer_cost=0.0,
        work_estimate=4.0,
        total_cost=4.5,
        timestamp=2.0,
    ))

    # 10 ticks
    for _ in range(10):
        mr.tick()

    s = mr.snapshot("A")

    expected = {
        "under_budget": 3.0 / 12.3,              # ≈ 0.244
        "distant_start": (2.0 + 2.0 + 4.0) / 3.0 / 10.0,  # ≈ 0.267
        "exploration_saturation": 1.0,
        "thermal_pressure": 5.0 / 50.0,          # 0.1
        "idle": 10.0 / 50.0,                     # 0.2
    }

    tol = 0.01
    for k, v in expected.items():
        got = s.get(k)
        assert got is not None and abs(got - v) < tol, (
            f"{k}: got {got}, expected {v} (tol={tol})"
        )

    return True


if __name__ == "__main__":
    print("AMEND-008:", "PASS" if test_amend008() else "FAIL")
