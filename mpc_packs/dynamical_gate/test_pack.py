"""dynamical_gate pack — sanity + four-scenario acceptance tests.

The four-scenario calibration regenerates Langevin trajectories and
takes ~6-10 s; skip with `DYNAMICAL_GATE_SKIP_SCENARIOS=1`.

Invocation:

    python -m mpc_packs.dynamical_gate.test_pack
"""

from __future__ import annotations

import os

import numpy as np

from mpc_kernel.rfc001.events import PhaseTransitionEvent
from mpc_kernel.rfc001.phase import Phase
from mpc_packs.dynamical_gate.config import DynamicalGateConfig
from mpc_packs.dynamical_gate.pack import DynamicalGate
from mpc_packs.dynamical_gate.release import release_and_classify
from mpc_packs.physics_primitives import (
    DT,
    correlation_time,
    run_langevin,
    survival_margin,
)


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


# ── End-to-end wire: gate → measure_fdr → classifier → event ────────────────


def test_end_to_end_committed_wire():
    """Run the gate on a committed trajectory until it trips, release
    measure_fdr at the trip position, classify, and populate
    PhaseTransitionEvent.fdr_slope. Asserts:

      - The gate trips (tau_E drops below the floor).
      - measure_fdr's scaled slope matches the Session-A committed
        reference (+0.96) to two decimals — same machinery, same params.
      - classify_phase_dynamical returns Phase.C given that slope.
      - The resulting PhaseTransitionEvent carries a non-None fdr_slope.

    Takes ~8 s on CPU (the full-budget measure_fdr call). Skipped when
    DYNAMICAL_GATE_SKIP_SCENARIOS=1.
    """
    U = _SCENARIOS["committed"][0]
    v0 = _SCENARIOS["committed"][1]
    V_A = lambda v: _V_dist(v, _A, 1.2, 1.0)
    h_mag = 0.05

    # 1. Run the gate on the committed trajectory until first trip.
    traj = run_langevin(U, v0, 1500, rng=np.random.default_rng(2026))
    gate = DynamicalGate(window=500, tau_floor=0.05, recompute_interval=100)
    first_trip_step = None
    for i, v in enumerate(traj):
        gate.observe(v, U)
        if gate.should_release() and first_trip_step is None:
            first_trip_step = i
            break
    assert first_trip_step is not None, "committed scenario should trip"

    # 2. Compute streaming observables on what the gate has seen so far.
    v_at_trip = traj[first_trip_step]
    past = traj[:first_trip_step]
    U_bath = lambda v: 0.15 * np.sum((v - _MID) ** 2)
    bath = run_langevin(U_bath, _MID, first_trip_step,
                        rng=np.random.default_rng(42))
    tau_A = correlation_time(V_A, past)
    tau_env = correlation_time(V_A, bath)
    gamma_A, _, _ = survival_margin(V_A, past, bath)

    # 3. Release FDR at the trip position.
    release = release_and_classify(
        v_at_trip, U, V_A,
        tau_A=tau_A, tau_env=tau_env, gamma_A=gamma_A,
        h_mag=h_mag,
    )
    assert release.phase == Phase.C, (
        f"committed expected Phase.C, got {release.phase} "
        f"with slope={release.fdr_slope:+.3f}"
    )
    # Match against Session-A reference (+0.96) to two decimals.
    assert abs(release.fdr_slope - 0.96) < 0.02, (
        f"committed slope drift from Session-A reference +0.96: "
        f"got {release.fdr_slope:+.3f}"
    )

    # 4. Populate PhaseTransitionEvent.fdr_slope.
    evt = PhaseTransitionEvent(
        from_phase=Phase.S, to_phase=release.phase,
        position=v_at_trip.copy(),
        timestamp=first_trip_step * DT,
        cluster_id="committed-demo",
        energy=float(U(v_at_trip)),
        fdr_slope=release.fdr_slope,
    )
    assert evt.fdr_slope is not None
    assert evt.to_phase == Phase.C

    return release, evt


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

        release, evt = test_end_to_end_committed_wire()
        print(f"[4] end-to-end committed wire")
        print(f"    fdr_slope={release.fdr_slope:+.3f}  "
              f"phase={release.phase.name}  "
              f"wall={release.wall_time_s:.1f}s")
        print(f"    event: from={evt.from_phase.name} "
              f"to={evt.to_phase.name}  "
              f"fdr_slope={evt.fdr_slope:+.3f}")

    print("\nAll tests pass.")
