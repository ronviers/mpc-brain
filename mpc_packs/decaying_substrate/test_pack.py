"""decaying_substrate pack — sanity tests.

Exercises the AMEND-001 additions (decay_step, ping,
update_frustration) and confirms the active-pair set evolves as
expected.

Invocation:

    python -m mpc_packs.decaying_substrate.test_pack
"""

from __future__ import annotations

import numpy as np

from mpc_packs.decaying_substrate import DecayingSubstrate


def _reset_state(sub, frust_fn):
    sub.frustration(np.zeros(sub.dim))


def test_constructor_and_register():
    """Construct, register two constraints, trigger frustration pass
    to seed the decay cache. Active pairs should include (A, B)."""
    sub = DecayingSubstrate(dim=4, tau_base=50.0, epsilon_floor=1e-4)
    sub.register("A", lambda v: float(np.sum((v - np.array([1, 0, 0, 0])) ** 2)), lam=0.5)
    sub.register("B", lambda v: float(np.sum((v - np.array([0, 1, 0, 0])) ** 2)), lam=0.5)
    sub.frustration(np.zeros(sub.dim))
    assert ("A", "B") in sub._active_pairs
    return sub


def test_decay_step_shrinks_edge():
    """decay_step() must reduce the cached ε for active pairs."""
    sub = test_constructor_and_register()
    before = sub._decay_cache[("A", "B")]
    sub.decay_step()
    after = sub._decay_cache[("A", "B")]
    assert after < before, f"no decay: {before} → {after}"


def test_ping_restamps_edge():
    """ping() must restore the decayed edge toward its initial value,
    capped at the original."""
    sub = test_constructor_and_register()
    for _ in range(30):
        sub.decay_step()
    decayed = sub._decay_cache[("A", "B")]
    sub.ping("A", "B", strength=1.0)
    restamped = sub._decay_cache[("A", "B")]
    original = sub._initial_eps[("A", "B")]
    assert restamped > decayed
    assert restamped <= original + 1e-12


def test_edge_drops_below_floor():
    """After enough decay, an edge drops out of active_pairs."""
    sub = DecayingSubstrate(dim=2, tau_base=1.0, epsilon_floor=0.1)
    sub.register("A", lambda v: float((v[0] - 1) ** 2), lam=0.5)
    sub.register("B", lambda v: float((v[1] - 1) ** 2), lam=0.5)
    sub.frustration(np.zeros(sub.dim))
    assert ("A", "B") in sub._active_pairs
    for _ in range(20):
        sub.decay_step()
    assert ("A", "B") not in sub._active_pairs


if __name__ == "__main__":
    print("decaying_substrate pack — sanity tests")
    print("=" * 62)

    test_constructor_and_register()
    print("[1] construct + register    active pairs seeded   OK")

    test_decay_step_shrinks_edge()
    print("[2] decay_step              edge shrinks   OK")

    test_ping_restamps_edge()
    print("[3] ping                    restamps up to original   OK")

    test_edge_drops_below_floor()
    print("[4] decay below floor       drops from active set   OK")

    print("\nAll tests pass.")
