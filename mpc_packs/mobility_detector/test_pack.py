"""mobility_detector pack — sanity + calibration tests.

Runs in well under a second for the primitive checks. The full
four-scenario calibration regenerates short Langevin trajectories
and takes ~6-10 s; skip it during fast CI by setting
`MOBILITY_DETECTOR_SKIP_SCENARIOS=1` in the environment.

Invocation:

    python -m mpc_packs.mobility_detector.test_pack
"""

from __future__ import annotations

import os
from collections import deque

import numpy as np

from mpc_packs.mobility_detector.config import MobilityDetectorConfig
from mpc_packs.mobility_detector.pack import (
    MobilityDetector,
    compute_ghost,
    compute_tail,
    gate_signal,
)
from mpc_packs.physics_primitives import DT, numerical_grad, run_langevin


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
    assert compute_tail(deque(), 10) is None
    assert compute_tail(deque([np.zeros(2)]), 10) is None
    return tail


def test_gate_signal_directions():
    """Aligned → no trip; orthogonal or anti-aligned → trip at threshold 0.3."""
    a = np.array([1.0, 0.0])
    assert gate_signal(a, np.array([1.0, 0.0]), 0.3) is False
    assert gate_signal(a, np.array([0.0, 1.0]), 0.3) is True
    assert gate_signal(a, np.array([-1.0, 0.0]), 0.3) is True
    assert gate_signal(np.zeros(2), a, 0.3) is False


def test_detector_warmup_and_trip():
    """Smooth descent toward a harmonic minimum: no trips once the window
    fills. Abrupt direction reversal: one trip immediately after."""
    grad = lambda v: v.copy()
    det = MobilityDetector(dim=2, window=10, threshold=0.3)

    v = np.array([1.0, 0.0])
    for _ in range(9):
        det.observe(v, grad, gamma=1.0, dt=0.01)
        v = v - v * 0.01
    assert det.trip_count == 0, "no trips during warm-up"

    for _ in range(20):
        det.observe(v, grad, gamma=1.0, dt=0.01)
        v = v - v * 0.01
    assert det.trip_count == 0, f"smooth descent tripped: {det.trip_count}"

    v_flip = np.array([-1.0, 0.0])
    det.observe(v_flip, grad, gamma=1.0, dt=0.01)
    assert det.should_release(), "direction flip should trip"
    assert det.trip_count == 1
    assert det.tension > 0, "tension should be positive on a trip"


# ── Four-scenario calibration (Session-A Langevin substrate) ────────────────


_A = np.array([0.0, 0.0])
_B = np.array([2.0, 0.0])
_MID = 0.5 * (_A + _B)


def _V_dist(v, anchor, r, lam):
    return lam * (np.linalg.norm(v - anchor) - r) ** 2


_SCENARIOS = {
    "committed": (lambda v: _V_dist(v, _A, 1.2, 20.0) + _V_dist(v, _B, 1.0, 20.0),
                  np.array([1.11, 0.456])),
    "suspended": (lambda v: _V_dist(v, _A, 1.2, 0.8)  + _V_dist(v, _B, 1.0, 0.8),
                  np.array([1.11, 0.456])),
    "conflict":  (lambda v: _V_dist(v, _A, 0.25, 30.0) + _V_dist(v, _B, 0.25, 30.0),
                  np.array([1.0, 0.0])),
    "reset":     (lambda v: 0.15 * np.sum((v - _MID) ** 2),
                  np.array([1.0, 0.0])),
}


def run_scenario_calibration(n_steps: int = 3000, gamma: float = 1.0):
    """Run MobilityDetector over each of the four Session-A scenarios with
    calibrated-default settings; return trip counts per scenario.

    Deterministic: same seed across scenarios (2026), same trajectory
    length. Takes ~6-10 s on CPU.
    """
    cfg = MobilityDetectorConfig()
    results: dict[str, int] = {}
    for name, (U, v0) in _SCENARIOS.items():
        traj = run_langevin(U, v0, n_steps, rng=np.random.default_rng(2026))
        det = MobilityDetector(
            dim=2,
            window=cfg.window,
            threshold=cfg.threshold,
            min_tail_mag=cfg.min_tail_mag,
        )
        grad = lambda v: numerical_grad(U, v)
        for v in traj:
            det.observe(v, grad, gamma=gamma, dt=DT)
        results[name] = det.trip_count
    return results


def test_scenarios_discriminate():
    """Calibration: the detector produces a spread of trip counts across
    the four canonical scenarios, with mobile regimes firing more than
    pinned ones."""
    trips = run_scenario_calibration()
    max_t = max(trips.values())
    min_t = min(trips.values())
    assert max_t > 0, f"detector silent across all scenarios: {trips}"
    assert max_t - min_t >= 3, f"detector does not discriminate: {trips}"
    assert trips["reset"] > trips["committed"], (
        f"expected reset > committed (mobile > pinned), got {trips}"
    )
    return trips


if __name__ == "__main__":
    print("mobility_detector pack — sanity tests")
    print("=" * 62)

    gh = test_compute_ghost_harmonic()
    print(f"[1] compute_ghost harmonic    v_ghost = {gh}   OK")

    tail = test_compute_tail_straight_line()
    print(f"[2] compute_tail straight     displacement = {tail}   OK")

    test_gate_signal_directions()
    print(f"[3] gate_signal direction     aligned/orthogonal/anti   OK")

    test_detector_warmup_and_trip()
    print(f"[4] detector warmup+trip      smooth descent quiet, flip trips   OK")

    if os.environ.get("MOBILITY_DETECTOR_SKIP_SCENARIOS") == "1":
        print("\n[scenarios skipped via MOBILITY_DETECTOR_SKIP_SCENARIOS=1]")
    else:
        trips = test_scenarios_discriminate()
        print(f"[5] four-scenario calibration trips = {trips}   OK")

    print("\nAll tests pass.")
