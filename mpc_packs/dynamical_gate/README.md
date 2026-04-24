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
the mobile ones. Trip rate across 26 recomputes per scenario:

| Scenario  | Trip rate | τ range over recomputes |
|-----------|-----------|--------------------------|
| conflict  | 26/26 = 100% | 0.004 – 0.007         |
| committed | 26/26 = 100% | 0.007 – 0.016         |
| suspended |  1/26 =   4% | 0.049 – 0.352 (one boundary dip) |
| reset     |  0/26 =   0% | 0.118 – 0.708         |

25× separation in trip rate between pinned and mobile classes.

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

- `should_release() -> bool` — true on the most-recent observe if τ was
  below the floor on that recompute.
- `tau_estimate -> Optional[float]` — most-recent τ estimate, or `None`
  before the buffer fills.
- `trip_count`, `last_trip_step` — cumulative bookkeeping.

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
2. **Edge-triggered release.** The gate fires every recompute while
   pinned (level-triggered). A pinned engine over 3000 steps with
   `recompute_interval=100` would fire ~26 releases, each ~8 s —
   ~200 s of compute per trajectory, which is too expensive for online
   use. Edge-triggered release (fire on the transition *into* pinned,
   not while pinned) cuts this to 1 release per basin entry.
3. **Streaming γ_A, γ_ij, tau_A.** `release_and_classify` currently
   requires the caller to supply streaming-estimator values for these.
   A companion class that maintains them alongside the gate's τ_E
   estimator would make integration a single-object attach.
