# dynamical_gate

Streaming integral-correlation-time gate. Maintains a rolling buffer of
a scalar observable (default: substrate energy) and periodically
recomputes τ via `autocorr_fft` + `tau_integral`. Fires when τ drops
below a calibrated floor — the signature of the pinned regime where
trajectory-only observables cannot separate C from K, and an FDR
measurement carries new information.

## Why streaming τ (not a linear gate)

An earlier attempt — a linear mobility gate in the Maya
forward-curve/backward-curve pattern — discriminated pinned from mobile
with 3 orders of magnitude of signal, but with **inverted semantics**:
silent exactly in the pinned regime where FDR is needed. That pack is
retained at `mpc_packs/mobility_detector/` as a mobility observable.

This pack uses the signal that actually works in mpc_lattice.py's
regime classifier: the integral correlation time τ of a trajectory
observable. When τ collapses to the noise floor, the engine is pinned;
whether the pinning is committed or conflict requires FDR to decide.

## The signal

From SESSION_A_STATE.md "Markovian sign caveat":

> In the committed and conflict regimes, both τ_A and τ_ij collapse to
> the noise floor, so trajectory observables alone cannot distinguish
> c from k. The FDR slope DOES distinguish them.

Measured over the four canonical Session-A scenarios with a
500-sample window and a 20% burn-in, final τ_E:

| Scenario  | τ_E            | Regime  |
|-----------|----------------|---------|
| conflict  | 0.005          | pinned  |
| committed | 0.010          | pinned  |
| suspended | 0.23           | mobile  |
| reset     | 0.8 – 2.1      | mobile  |

A `tau_floor = 0.05` sits ~5× above the pinned estimates and ~5× below
the mobile ones. The gate is edge-triggered with hysteresis
(`tau_floor_exit = 2 × tau_floor = 0.10`), so a pinned engine produces
**one** release at basin entry rather than one per recompute:

| Scenario  | Edge trips | Final state | τ range over 26 recomputes |
|-----------|-----------|-------------|--------------------------|
| conflict  | 1         | pinned      | 0.004 – 0.007            |
| committed | 1         | pinned      | 0.007 – 0.016            |
| suspended | 1         | unpinned    | 0.049 – 0.352 (one boundary dip to 0.049) |
| reset     | 0         | unpinned    | 0.118 – 0.708            |

Edge-triggering cuts per-trajectory release count from ~26 to 1 for
pinned engines, ~26× reduction in the expensive `measure_fdr` work.
The suspended scenario's one trip is a single boundary dip — the
hysteresis exit at 0.10 prevents it from re-triggering once τ climbs
back above the band.

## API

```python
from mpc_packs.dynamical_gate import DynamicalGate, release_and_classify

gate = DynamicalGate(window=500, tau_floor=0.05, dt=0.01,
                    recompute_interval=100, burn_frac=0.2)

for _ in range(n_steps):
    v = engine.step()
    gate.observe(v, energy_fn=substrate.energy)
    if gate.should_release():
        # Expensive path: measure_fdr + classify_phase_dynamical.
        # Produces an FDRRelease with .fdr_slope and .phase.
        release = release_and_classify(
            v, U=substrate.energy, V_obs=chosen_observable,
            tau_A=streaming_tau_A, tau_env=streaming_tau_env,
            gamma_A=streaming_gamma_A,
        )
        # Populate PhaseTransitionEvent emitted by the engine next step.
        pending_fdr_slope = release.fdr_slope
```

`observe()` is O(1) per step (one energy eval + deque append).
The τ recompute runs every `recompute_interval` steps and is
O(window · log window) for the FFT autocorrelation. At the calibrated
defaults that's ~500 samples every 100 steps, negligible compared to
`measure_fdr`.

Observables exposed:

- `should_release() -> bool` — True on the single `observe()` where
  the engine transitioned from unpinned to pinned. Edge-triggered.
- `is_pinned -> bool` — current level state, updated every recompute
  with hysteresis. True while τ_E has been below `tau_floor` and has
  not yet risen above `tau_floor_exit`.
- `tau_estimate -> Optional[float]` — most-recent τ estimate, or
  `None` before the buffer fills.
- `trip_count`, `last_trip_step` — cumulative edge-fire bookkeeping.

## Streaming observables (`observables.py`)

`classify_phase_dynamical` takes `tau_A`, `tau_env`, `gamma_A`, and
optionally `gamma_ij` alongside `fdr_slope`. `StreamingObservables`
consolidates the rolling-buffer + `correlation_time` /
`survival_margin` / `cross_dissipation` logic so the caller doesn't
hand-roll it:

```python
from mpc_packs.dynamical_gate import StreamingObservables

bath_traj = run_langevin(U_bath, v0_bath, n, rng=...)
obs = StreamingObservables(V_A_fn=V_A, window=500,
                          bath_trajectory=bath_traj)

for v in trajectory:
    gate.observe(v, U)
    obs.observe(v)
    if gate.should_release():
        release = release_and_classify(
            v, U, V_obs=V_A,
            tau_A=obs.tau_A(),
            tau_env=obs.tau_env,
            gamma_A=obs.gamma_A(),
            gamma_ij=obs.gamma_ij(),   # None if V_B_fn was not supplied
        )
```

`tau_env` is computed once from a separately-supplied bath trajectory
(it cannot be derived from the engine's own path — bath dynamics live
in a different substrate by definition).

## Release chain (`release.py`)

Thin helpers that run the expensive path on a trip:

- `release_fdr_slope(v, U, V_obs, h_mag, ...) -> float` — single
  `measure_fdr` call at `v`, returns the FDT-scaled late-time slope
  (formula matches mpc_lattice.py: `polyfit` on the upper half of
  `chi` vs `(C[0] − C) / D_eff`).
- `release_and_classify(v, U, V_obs, tau_A, tau_env, gamma_A, ...) -> FDRRelease`
  — adds the classifier call and returns both slope and Phase.

Measured wall time on CPU at full budget
(`n_burnin=2000`, `n_resp=5000`, `n_reps=32`): ~7–8 s per release.
Reduced budgets are noisier and do **not** preserve the 0.5-classifier
threshold — don't use them as ground truth for C-vs-K separation.

## Declared dependencies

- `numpy`.
- `mpc_packs.physics_primitives` — for `autocorr_fft`, `tau_integral`,
  `DT`.

## Declared mutations

None. Pure observational pack. Events and fdr_slope population happen in
the caller when `should_release()` is true.

## Invocation

```bash
python -m mpc_packs.dynamical_gate.test_pack
```

Primitive checks (constant-energy, slow-oscillation) run in <1 s.
Four-scenario calibration takes ~6–10 s; skip with
`DYNAMICAL_GATE_SKIP_SCENARIOS=1`.

## End-to-end verification

The pack's `test_pack.py` runs the full chain on the committed
scenario:

1. Gate observes a 1500-step Langevin trajectory.
2. Gate trips at step ~499 (`tau_E ≈ 0.015`, below floor).
3. `release_and_classify` fires at the trip position using streaming
   `tau_A`, `tau_env`, `gamma_A` computed from the gate's buffer.
4. FDR slope comes out to **+0.959** — matches Session-A reference
   (+0.96) to two decimals.
5. `classify_phase_dynamical` returns `Phase.C`.
6. `PhaseTransitionEvent(fdr_slope=+0.959, to_phase=Phase.C)` is
   constructed cleanly.

The end-to-end test is asserted, not just demonstrated:
`abs(slope − 0.96) < 0.02` and `phase == Phase.C`.

## Open

1. **Observable choice.** Currently the caller passes `V_obs`
   explicitly; the gate itself uses total substrate energy for its
   streaming τ buffer. Per-proposition violations V_A or PCA-projected
   coordinates may give cleaner signal in multi-proposition
   experiments.
2. **Engine integration.** A Governor-style pack that attaches a
   `DynamicalGate` + `StreamingObservables` pair to each engine and
   populates outgoing `PhaseTransitionEvent.fdr_slope` at release time
   is the remaining wiring step. The primitives are all in place.
