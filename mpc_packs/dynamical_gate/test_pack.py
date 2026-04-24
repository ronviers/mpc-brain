"""dynamical_gate pack — sanity + four-scenario acceptance tests.

The four-scenario calibration regenerates Langevin trajectories and
takes ~6-10 s; skip with `DYNAMICAL_GATE_SKIP_SCENARIOS=1`.

Invocation:

    python -m mpc_packs.dynamical_gate.test_pack
"""

from __future__ import annotations

import os

import numpy as np

from mpc_kernel.rfc001.bus import EventBus
from mpc_kernel.rfc001.events import PhaseTransitionEvent
from mpc_kernel.rfc001.phase import Phase
from mpc_kernel.rfc001.substrate import Substrate
from mpc_packs.dynamical_gate.config import DynamicalGateConfig
from mpc_packs.dynamical_gate.engine import DynamicalEngine
from mpc_packs.dynamical_gate.observables import StreamingObservables
from mpc_packs.dynamical_gate.pack import DynamicalGate
from mpc_packs.dynamical_gate.release import release_and_classify
from mpc_packs.physics_primitives import DT, run_langevin


def test_warmup_and_constant_energy():
    """Buffer warm-up is silent. Constant-energy observable → variance
    below floor → tau set to 0 on first recompute → exactly one edge
    trip (enter pinned), no further trips while pinned."""
    gate = DynamicalGate(
        window=50, tau_floor=0.05, dt=0.01,
        recompute_interval=10, burn_frac=0.2,
    )
    const_energy = lambda v: 1.0

    for _ in range(49):
        gate.observe(np.zeros(2), const_energy)
    assert gate.trip_count == 0, "no trips during warm-up"
    assert gate.tau_estimate is None
    assert gate.is_pinned is False

    # Multiple recomputes after buffer fills. Edge fires once on entry.
    for _ in range(55):
        gate.observe(np.zeros(2), const_energy)
    assert gate.trip_count == 1, (
        f"constant energy should edge-fire exactly once, got {gate.trip_count}"
    )
    assert gate.tau_estimate == 0.0
    assert gate.is_pinned is True


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
    """Edge-triggered: pinned regimes fire once at basin entry, mobile
    regimes either don't fire or fire at most once from a boundary dip.
    A steady pinned engine produces one release, not 26.

    Empirical counts at n_steps=3000 (26 recomputes after warmup):

        committed  1 trip (fires on first recompute, stays pinned)
        conflict   1 trip (same)
        suspended  1 trip (boundary dip to tau=0.049 around step ~1400)
        reset      0 trips (tau always well above exit threshold)

    Asserted: pinned scenarios trip exactly once and `is_pinned` is
    True at end. Mobile scenarios trip at most once. reset never trips.
    """
    results = run_scenario_calibration()
    pinned = {"committed", "conflict"}
    mobile = {"suspended", "reset"}

    for name in pinned:
        trips, tau = results[name]
        assert trips == 1, (
            f"{name} (pinned) should edge-fire exactly once, "
            f"got trips={trips}, tau={tau}"
        )

    for name in mobile:
        trips, tau = results[name]
        assert trips <= 1, (
            f"{name} (mobile) should fire at most once, "
            f"got trips={trips}, tau={tau}"
        )

    assert results["reset"][0] == 0, (
        f"reset should not fire at all, got {results['reset']}"
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

    # 1. Pre-compute a bath trajectory for tau_env once.
    U_bath = lambda v: 0.15 * np.sum((v - _MID) ** 2)
    bath = run_langevin(U_bath, _MID, 1500, rng=np.random.default_rng(42))

    # 2. Attach gate + streaming observables with bath reference.
    gate = DynamicalGate(window=500, tau_floor=0.05, recompute_interval=100)
    obs = StreamingObservables(V_A_fn=V_A, window=500, bath_trajectory=bath)

    # 3. Run the committed trajectory. Stop at the first gate trip.
    traj = run_langevin(U, v0, 1500, rng=np.random.default_rng(2026))
    first_trip_step = None
    for i, v in enumerate(traj):
        gate.observe(v, U)
        obs.observe(v)
        if gate.should_release() and first_trip_step is None:
            first_trip_step = i
            break
    assert first_trip_step is not None, "committed scenario should trip"
    v_at_trip = traj[first_trip_step]

    # 4. Release FDR using the streaming estimators — no manual
    # correlation_time / survival_margin at the call site.
    release = release_and_classify(
        v_at_trip, U, V_A,
        tau_A=obs.tau_A(), tau_env=obs.tau_env, gamma_A=obs.gamma_A(),
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

    # 5. Populate PhaseTransitionEvent.fdr_slope.
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


def test_dynamical_engine_populates_fdr_slope():
    """Construct a `DynamicalEngine` on a committed-scenario substrate;
    let it run long enough for the gate to edge-fire once; verify
    that PhaseTransitionEvents emitted AFTER the release carry a
    populated `fdr_slope` matching the Session-A reference.

    Pre-release events (before the gate has fired) have fdr_slope=None,
    which is correct: no dynamical measurement exists yet.
    """
    # Build a committed-scenario substrate via the kernel's register API.
    sub = Substrate(dim=2, E_c=0.50, E_s=2.00)
    sub.register("pA", lambda v: (np.linalg.norm(v - _A) - 1.2) ** 2, lam=20.0)
    sub.register("pB", lambda v: (np.linalg.norm(v - _B) - 1.0) ** 2, lam=20.0)

    # Bath reference for tau_env.
    U_bath = lambda v: 0.15 * np.sum((v - _MID) ** 2)
    bath = run_langevin(U_bath, _MID, 500, rng=np.random.default_rng(42))

    V_A = lambda v: (np.linalg.norm(v - _A) - 1.2) ** 2

    gate = DynamicalGate(window=300, tau_floor=0.05, recompute_interval=100)
    obs = StreamingObservables(V_A_fn=V_A, window=300, bath_trajectory=bath)

    bus = EventBus()
    events: list[PhaseTransitionEvent] = []
    bus.subscribe(PhaseTransitionEvent, lambda e: events.append(e))

    eng = DynamicalEngine(
        substrate=sub, bus=bus,
        gate=gate, observables=obs, V_obs=V_A, h_mag=0.05,
        E_star=5.0, cluster_id="dynamical-committed",
    )
    eng.v = np.array([1.11, 0.456])  # start at intersection (committed minimum)

    np.random.seed(2026)
    for _ in range(800):
        eng.step()

    # The gate should fire exactly once (edge-triggered, stays pinned).
    assert eng.release_count == 1, (
        f"expected exactly one gate release in pinned committed, got "
        f"{eng.release_count}"
    )

    # Cached slope matches the Session-A committed reference (+0.96) to
    # two decimals — same wiring, same measure_fdr, same potentials.
    assert eng.cached_fdr_slope is not None
    assert abs(eng.cached_fdr_slope - 0.96) < 0.02, (
        f"cached slope drifted from Session-A committed reference +0.96: "
        f"got {eng.cached_fdr_slope:+.3f}"
    )

    # Of the events emitted, the ones after the first release must carry
    # fdr_slope. The ones before must have fdr_slope=None.
    slopes_populated = [e for e in events if e.fdr_slope is not None]
    slopes_none = [e for e in events if e.fdr_slope is None]
    assert len(slopes_populated) > 0, "no events emitted after release"
    assert all(
        abs(e.fdr_slope - eng.cached_fdr_slope) < 1e-9 for e in slopes_populated
    ), "all post-release events should carry the cached slope"

    return eng, events, len(slopes_populated), len(slopes_none)


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

        eng, events, n_pop, n_none = test_dynamical_engine_populates_fdr_slope()
        print(f"[5] DynamicalEngine integration")
        print(f"    release_count={eng.release_count}  "
              f"cached_slope={eng.cached_fdr_slope:+.3f}  "
              f"events={len(events)}  "
              f"with_slope={n_pop}  none={n_none}")

    print("\nAll tests pass.")
