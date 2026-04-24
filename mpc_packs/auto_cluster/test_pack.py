"""auto_cluster pack — sanity tests.

Runs in a few seconds. Constructs an AutoCluster, loads two
overlapping quadratic constraints, steps 200 times, and verifies the
population self-regulates without crashing.

Invocation:

    python -m mpc_packs.auto_cluster.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_kernel.rfc001.bus import EventBus
from mpc_packs.auto_cluster import AutoCluster


def _quadratic_constraint(center):
    c = np.asarray(center, dtype=np.float64)
    return lambda v: float(np.sum((np.asarray(v) - c) ** 2))


def test_construct_loads_and_seeds_one_engine():
    """Fresh AutoCluster starts with exactly one engine."""
    bus = EventBus()
    ac = AutoCluster(dim=8, E_star=10.0, max_engines=16, bus=bus)
    assert len(ac.engines) == 1
    rep = ac.population_report()
    assert rep["n_engines"] == 1
    return ac


def test_step_self_regulates_without_crash():
    """Run 200 steps with two overlapping wells; engines must stay ≥ 1
    and population report remains consistent."""
    np.random.seed(1)
    bus = EventBus()
    ac = AutoCluster(dim=8, E_star=10.0, max_engines=16, bus=bus)

    c1 = np.zeros(8); c1[0] = 1.0
    c2 = np.zeros(8); c2[0] = 0.9; c2[1] = 0.1
    ac.load(
        {"A": _quadratic_constraint(c1), "B": _quadratic_constraint(c2)},
        stiffnesses={"A": 0.5, "B": 0.5},
    )

    for _ in range(200):
        ac.step()

    rep = ac.population_report()
    assert rep["n_engines"] >= 1
    total = (rep["n_committed"] + rep["n_suspended"]
             + rep["n_conflict"] + rep["n_reset"])
    assert total == rep["n_engines"]
    return ac, rep


if __name__ == "__main__":
    print("auto_cluster pack — sanity tests")
    print("=" * 62)

    ac = test_construct_loads_and_seeds_one_engine()
    print("[1] construct + seed        n_engines=1   OK")

    ac, rep = test_step_self_regulates_without_crash()
    print(f"[2] 200 steps self-regulate {rep}   OK")

    print("\nAll tests pass.")
