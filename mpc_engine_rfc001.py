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
#  Value objects + brain components (Session 10 unification)
#
#  All canonical definitions live in mpc_kernel.rfc001.* and are re-exported
#  here so this monolith preserves its pre-RFC-002 public API while every
#  brain class yields a single class object across both import paths. The
#  _topology phase-classification logic, MetastableEngine.step semantics,
#  MPCCluster cross-cluster compatibility, and Network routing have all
#  been verified byte-equivalent between the previous local copies and the
#  kernel versions; the previous parallel implementations are retired.
# ═══════════════════════════════════════════════════════════════════════════════

from mpc_kernel.rfc001.substrate import (  # noqa: E402,F401
    ConstraintHandle,
    EnergyState,
    Substrate,
    TopologyResult,
)
from mpc_kernel.rfc001.engine import (  # noqa: E402,F401
    MaintenanceField,
    MetastableEngine,
)
from mpc_kernel.rfc001.cluster import (  # noqa: E402,F401
    MPCCluster,
    OperatorAlgebra,
)
from mpc_kernel.rfc001.network import (  # noqa: E402,F401
    Calorimeter,
    Network,
    ThermodynamicGovernor,
)


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
