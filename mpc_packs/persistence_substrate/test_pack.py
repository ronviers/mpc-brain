"""persistence_substrate pack — sanity tests.

Invocation:

    python -m mpc_packs.persistence_substrate.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_kernel.rfc001.bus import EventBus
from mpc_packs.persistence_substrate import (
    PersistenceCluster,
    PersistenceSubstrate,
)


def _quadratic(center):
    c = np.asarray(center, dtype=np.float64)
    return lambda v: float(np.sum((np.asarray(v) - c) ** 2))


def test_construct_and_register():
    """PersistenceSubstrate: construct, register two constraints, run
    frustration() to populate _original_eps."""
    sub = PersistenceSubstrate(
        dim=4, tau_base=50.0, usage_coefficient=0.5, outcome_coefficient=0.3,
    )
    sub.register("A", _quadratic([1, 0, 0, 0]), lam=0.5)
    sub.register("B", _quadratic([0, 1, 0, 0]), lam=0.5)
    sub.frustration(np.zeros(sub.dim))
    assert ("A", "B") in sub._active_pairs
    assert ("A", "B") in sub._original_eps
    return sub


def test_record_traversal_increments_count():
    sub = test_construct_and_register()
    sub.record_traversal("A", "B")
    sub.record_traversal("B", "A")  # same edge (symmetric)
    assert sub._traversal[("A", "B")] == 2
    assert sub._total_traversals == 2


def test_apply_outcome_boosts_edge():
    sub = test_construct_and_register()
    key = ("A", "B")
    original = sub._original_eps[key]
    sub._decay_cache[key] = 0.1 * original   # force decay
    sub.apply_outcome("A")
    after = sub._decay_cache[key]
    assert after > 0.1 * original
    assert after <= original + 1e-12


def test_cluster_construct_and_run():
    """PersistenceCluster swaps in a PersistenceSubstrate; a short run
    does not crash."""
    np.random.seed(2)
    bus = EventBus()
    cl = PersistenceCluster(
        dim=4, E_star=10.0, max_engines=8, bus=bus,
        tau_base=50.0, usage_coefficient=0.5, outcome_coefficient=0.3,
    )
    assert isinstance(cl.sub, PersistenceSubstrate)
    for eng in cl.engines:
        assert eng.sub is cl.sub

    c1 = np.array([1.0, 0.0, 0.0, 0.0])
    c2 = np.array([0.0, 1.0, 0.0, 0.0])
    cl.load(
        {"A": _quadratic(c1), "B": _quadratic(c2)},
        stiffnesses={"A": 0.5, "B": 0.5},
        centres={"A": c1, "B": c2},
    )
    for _ in range(50):
        cl.step()
    rep = cl.population_report()
    assert rep["n_engines"] >= 1
    return cl, rep


if __name__ == "__main__":
    print("persistence_substrate pack — sanity tests")
    print("=" * 62)

    test_construct_and_register()
    print("[1] substrate register+frustration   _original_eps populated   OK")

    test_record_traversal_increments_count()
    print("[2] record_traversal                 count=2 total=2   OK")

    test_apply_outcome_boosts_edge()
    print("[3] apply_outcome                    edge boosted toward original   OK")

    cl, rep = test_cluster_construct_and_run()
    print(f"[4] cluster 50-step run              {rep}   OK")

    print("\nAll tests pass.")
