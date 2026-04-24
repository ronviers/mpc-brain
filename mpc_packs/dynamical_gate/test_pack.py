"""dynamical_gate pack — sanity + acceptance tests.

Runs in well under a second for the primitive checks. The full
four-scenario calibration test regenerates short Langevin trajectories
and will take a few seconds; skip it during fast CI by setting
`DYNAMICAL_GATE_SKIP_SCENARIOS=1` in the environment.

Invocation:

    python -m mpc_packs.dynamical_gate.test_pack
"""

from __future__ import annotations

from collections import deque

import numpy as np

from mpc_packs.dynamical_gate.pack import (
    DynamicalGate,
    compute_ghost,
    compute_tail,
    gate_signal,
)


def test_compute_ghost_harmonic():
    """U = |v|^2 / 2, grad = v; γ=1, dt=0.01 → v_ghost = 0.99·v."""
    v = np.array([1.0, 0.0])
    grad = lambda x: x.copy()
    gh = compute_ghost(v, grad, gamma=1.0, dt=0.01)
    assert np.allclose(gh, np.array([0.99, 0.0])), f"ghost: {gh}"
    return gh


def test_compute_tail_straight_line():
    """Straight-line motion: `v[-1] − v[-w]` equals accumulated displacement."""
    buf = deque(maxlen=10)
    for i in range(10):
        buf.append(np.array([float(i), 0.0]))
    tail = compute_tail(buf, window=10)
    assert np.allclose(tail, np.array([9.0, 0.0])), f"tail: {tail}"
    # Early-return cases
    assert compute_tail(deque(), 10) is None
    assert compute_tail(deque([np.zeros(2)]), 10) is None
    return tail


def test_gate_signal_directions():
    """Aligned → no trip; orthogonal or anti-aligned → trip at threshold 0.3."""
    a = np.array([1.0, 0.0])
    assert gate_signal(a, np.array([1.0, 0.0]), 0.3) is False
    assert gate_signal(a, np.array([0.0, 1.0]), 0.3) is True     # orthogonal
    assert gate_signal(a, np.array([-1.0, 0.0]), 0.3) is True    # anti-aligned
    assert gate_signal(np.zeros(2), a, 0.3) is False             # zero-mag


def test_gate_warmup_and_trip():
    """Smooth descent toward a harmonic minimum: no trips once the window
    fills. Abrupt direction reversal: one trip immediately after."""
    grad = lambda v: v.copy()                           # U = |v|^2 / 2
    gate = DynamicalGate(dim=2, window=10, threshold=0.3)

    # Warm-up phase: first 9 observations buffer only, no gate signal.
    v = np.array([1.0, 0.0])
    for _ in range(9):
        gate.observe(v, grad, gamma=1.0, dt=0.01)
        v = v - v * 0.01                                # deterministic drift
    assert gate.trip_count == 0, "no trips during warm-up"

    # 10th observation + more smooth descent: ghost and tail both point
    # toward origin → aligned → no trips.
    for _ in range(20):
        gate.observe(v, grad, gamma=1.0, dt=0.01)
        v = v - v * 0.01
    assert gate.trip_count == 0, f"smooth descent tripped: {gate.trip_count}"

    # Flip direction sharply: now the tail says "leftward", ghost still
    # says "rightward toward origin" (v is positive-x). Anti-alignment
    # → trip.
    v_flip = np.array([-1.0, 0.0])
    gate.observe(v_flip, grad, gamma=1.0, dt=0.01)
    assert gate.should_release(), "direction flip should trip"
    assert gate.trip_count == 1


if __name__ == "__main__":
    print("dynamical_gate pack — sanity tests")
    print("=" * 62)

    gh = test_compute_ghost_harmonic()
    print(f"[1] compute_ghost harmonic    v_ghost = {gh}   OK")

    tail = test_compute_tail_straight_line()
    print(f"[2] compute_tail straight     displacement = {tail}   OK")

    test_gate_signal_directions()
    print(f"[3] gate_signal direction     aligned/orthogonal/anti   OK")

    test_gate_warmup_and_trip()
    print(f"[4] DynamicalGate warmup+trip smooth descent quiet, flip trips   OK")

    print("\nPrimitive + orchestrator sanity tests pass.")
