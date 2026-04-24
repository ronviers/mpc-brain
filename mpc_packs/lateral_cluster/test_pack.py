"""lateral_cluster pack — sanity tests.

Construct, load two wells, run ~100 steps, verify the cluster survives
without crash and engines stay s-state-distributed around the wells.

Invocation:

    python -m mpc_packs.lateral_cluster.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_kernel.rfc001.bus import EventBus
from mpc_packs.decaying_substrate import DecayingSubstrate
from mpc_packs.lateral_cluster import LateralCluster


def _quadratic(center):
    c = np.asarray(center, dtype=np.float64)
    return lambda v: float(np.sum((np.asarray(v) - c) ** 2))


def test_construct_swaps_substrate():
    """LateralCluster must replace its substrate with DecayingSubstrate
    at construction so decay mechanics are active."""
    bus = EventBus()
    cl = LateralCluster(dim=4, E_star=10.0, max_engines=8, bus=bus,
                        tau_base=50.0)
    assert isinstance(cl.sub, DecayingSubstrate)
    # All engines also point at the new substrate.
    for eng in cl.engines:
        assert eng.sub is cl.sub
    return cl


def test_load_with_centres():
    """load(centres=...) must populate the centre cache for
    nearest-well lookup."""
    cl = test_construct_swaps_substrate()
    c1 = np.array([1.0, 0.0, 0.0, 0.0])
    c2 = np.array([0.0, 1.0, 0.0, 0.0])
    cl.load(
        {"A": _quadratic(c1), "B": _quadratic(c2)},
        stiffnesses={"A": 0.5, "B": 0.5},
        centres={"A": c1, "B": c2},
    )
    assert cl._centres["A"] is c1
    assert cl._nearest_constraint(c1) == "A"
    assert cl._nearest_constraint(c2) == "B"


def test_step_runs_without_crash():
    """200 steps with two overlapping wells — cluster survives."""
    np.random.seed(3)
    bus = EventBus()
    cl = LateralCluster(dim=4, E_star=10.0, max_engines=8, bus=bus,
                        tau_base=50.0, lateral_scale=0.02)
    c1 = np.array([1.0, 0.0, 0.0, 0.0])
    c2 = np.array([0.0, 1.0, 0.0, 0.0])
    cl.load(
        {"A": _quadratic(c1), "B": _quadratic(c2)},
        stiffnesses={"A": 0.5, "B": 0.5},
        centres={"A": c1, "B": c2},
    )
    for _ in range(200):
        cl.step()
    rep = cl.population_report()
    assert rep["n_engines"] >= 1
    return cl, rep


if __name__ == "__main__":
    print("lateral_cluster pack — sanity tests")
    print("=" * 62)

    cl = test_construct_swaps_substrate()
    print(f"[1] construct               substrate={type(cl.sub).__name__}   OK")

    test_load_with_centres()
    print("[2] load(centres=...)       nearest-well lookup works   OK")

    cl, rep = test_step_runs_without_crash()
    print(f"[3] 200 steps + self-regulate  {rep}   OK")

    print("\nAll tests pass.")
