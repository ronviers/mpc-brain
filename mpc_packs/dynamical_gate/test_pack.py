"""dynamical_gate pack — sanity + four-scenario acceptance tests.

The four-scenario calibration regenerates Langevin trajectories and
takes ~6-10 s; skip with `DYNAMICAL_GATE_SKIP_SCENARIOS=1`.

Invocation:

    python -m mpc_packs.dynamical_gate.test_pack
"""

from __future__ import annotations

import os

import numpy as np

from mpc_packs.dynamical_gate.config import DynamicalGateConfig
from mpc_packs.dynamical_gate.pack import DynamicalGate
from mpc_packs.physics_primitives import DT, run_langevin


def test_warmup_and_constant_energy():
    """Buffer warm-up is silent. Constant-energy observable → variance
    below floor → tau set to 0 on first recompute → trip."""
    gate = DynamicalGate(
        window=50, tau_floor=0.05, dt=0.01,
        recompute_interval=10, burn_frac=0.2,
    )
    const_energy = lambda v: 1.0

    # Warm-up: first 49 observations buffer only.
    for _ in range(49):
        gate.observe(np.zeros(2), const_energy)
    assert gate.trip_count == 0, "no trips during warm-up"
    assert gate.tau_estimate is None

    # Fill the buffer; next recompute fires on step divisible by 10.
    for _ in range(11):
        gate.observe(np.zeros(2), const_energy)
    assert gate.trip_count >= 1, "constant energy should trip (max pinning)"
    assert gate.tau_estimate == 0.0


def test_oscillating_energy_above_floor():
    """Slowly-oscillating observable → tau comparable to period → above
    floor → no trips."""
    gate = DynamicalGate(
        window=500, tau_floor=0.05, dt=0.01,
        recompute_interval=100, burn_frac=0.2,
    )
    # Slow sinusoid, period ~ 500 steps (5 time units).
    def slow_E(v, _t=[0]):
        _t[0] += 1
        return np.sin(2 * np.pi * _t[0] / 500.0)
    for _ in range(800):
        gate.observe(np.zeros(2), slow_E)
    # Estimated tau should be well above the 0.05 floor.
    assert gate.tau_estimate is not None
    assert gate.tau_estimate > 0.05, f"tau_E = {gate.tau_estimate} below floor"
    assert gate.trip_count == 0, f"slow oscillation tripped: {gate.trip_count}"


# ── Four-scenario acceptance (Session-A Langevin substrate) ─────────────────


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


def run_scenario_calibration(n_steps: int = 3000):
    """Run DynamicalGate over each Session-A scenario; return per-scenario
    (trip_count, final_tau_estimate)."""
    cfg = DynamicalGateConfig()
    results: dict[str, tuple[int, Optional[float]]] = {}
    for name, (U, v0) in _SCENARIOS.items():
        traj = run_langevin(U, v0, n_steps, rng=np.random.default_rng(2026))
        gate = DynamicalGate(
            window=cfg.window,
            tau_floor=cfg.tau_floor,
            dt=cfg.dt,
            recompute_interval=cfg.recompute_interval,
            burn_frac=cfg.burn_frac,
        )
        for v in traj:
            gate.observe(v, U)
        results[name] = (gate.trip_count, gate.tau_estimate)
    return results


def test_scenarios_separate_pinned_from_mobile():
    """The gate fires in pinned regimes (committed, conflict) and stays
    near-silent in mobile regimes (suspended, reset). This is the
    inverted-semantics we wanted: FDR releases exactly where
    trajectory-only observables cannot separate C from K.

    Empirical rates at n_steps=3000 (26 recomputes after warmup):

        committed  26/26 = 100%   tau range 0.007-0.016
        conflict   26/26 = 100%   tau range 0.004-0.007
        suspended   1/26 =   4%   tau range 0.049-0.352  (one boundary dip)
        reset       0/26 =   0%   tau range 0.118-0.708

    Asserted bounds: pinned ≥ 20 trips, mobile ≤ 3 trips. This tolerates
    occasional transient dips near the floor while still requiring
    ~7× separation in trip rate.
    """
    results = run_scenario_calibration()
    pinned = {"committed", "conflict"}
    mobile = {"suspended", "reset"}

    for name in pinned:
        trips, tau = results[name]
        assert trips >= 20, (
            f"{name} (pinned) should trip most recomputes, "
            f"got trips={trips}, tau={tau}"
        )

    for name in mobile:
        trips, tau = results[name]
        assert trips <= 3, (
            f"{name} (mobile) should stay near-silent, "
            f"got trips={trips}, tau={tau}"
        )

    # Separation: pinned rate is at least 7x mobile rate.
    pinned_trips = sum(results[n][0] for n in pinned)
    mobile_trips = sum(results[n][0] for n in mobile)
    assert pinned_trips >= 7 * max(mobile_trips, 1), (
        f"pinned/mobile separation too small: "
        f"pinned={pinned_trips}, mobile={mobile_trips}"
    )
    return results


# The `Optional` re-import keeps the annotation in run_scenario_calibration
# working when the module is exec'd without from-future imports.
from typing import Optional  # noqa: E402


if __name__ == "__main__":
    print("dynamical_gate pack — sanity tests")
    print("=" * 62)

    test_warmup_and_constant_energy()
    print(f"[1] warmup + constant energy  trips on max pinning   OK")

    test_oscillating_energy_above_floor()
    print(f"[2] slow oscillation          tau above floor, silent   OK")

    if os.environ.get("DYNAMICAL_GATE_SKIP_SCENARIOS") == "1":
        print("\n[scenarios skipped via DYNAMICAL_GATE_SKIP_SCENARIOS=1]")
    else:
        results = test_scenarios_separate_pinned_from_mobile()
        print(f"[3] four-scenario separation")
        for name, (trips, tau) in results.items():
            tau_str = f"{tau:.4f}" if tau is not None else "none"
            print(f"    {name:<10}  trips={trips:>3}  tau_E={tau_str}")

    print("\nAll tests pass.")
