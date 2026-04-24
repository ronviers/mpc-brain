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

The integrated path is `DynamicalEngine` — a `MetastableEngine`
subclass that carries a gate + observables pair and populates
`PhaseTransitionEvent.fdr_slope` automatically:

```python
from mpc_kernel.rfc001.substrate import Substrate
from mpc_kernel.rfc001.bus import EventBus
from mpc_packs.dynamical_gate import (
    DynamicalEngine, DynamicalGate, StreamingObservables,
)

sub = Substrate(dim=2)
sub.register("pA", V_A_fn, lam=20.0)
bus = EventBus()

gate = DynamicalGate(window=500, tau_floor=0.05, recompute_interval=100)
obs = StreamingObservables(V_A_fn=V_A_fn, window=500,
                          bath_trajectory=precomputed_bath)

eng = DynamicalEngine(
    substrate=sub, bus=bus,
    gate=gate, observables=obs, V_obs=V_A_fn, h_mag=0.05,
    cluster_id="engine-1",
)
for _ in range(n_steps):
    eng.step()  # emits PhaseTransitionEvents with fdr_slope populated
                # on edge fire (~1 per basin entry).
```

The lower-level pieces (`DynamicalGate`, `StreamingObservables`,
`release_and_classify`) are still exported for callers that want to
compose them manually.

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

The pack's `test_pack.py` runs two integration tests on the committed
scenario:

**`test_end_to_end_committed_wire`** — manual composition. Gate
trips, `release_and_classify` produces slope **+0.959** (Session-A
reference +0.96) and `Phase.C`, `PhaseTransitionEvent` is constructed
cleanly with `fdr_slope` populated.

**`test_dynamical_engine_populates_fdr_slope`** — `DynamicalEngine`
attached to a kernel substrate, 800 steps. Exactly one gate edge-fire,
cached slope **+0.959**, 68 PhaseTransitionEvents emitted (many
C↔S↔K oscillations under thermal noise). Of those, 50 carry the
cached `fdr_slope`; the 18 earlier events (before the gate had fired)
carry `fdr_slope=None` — correct semantics, no dynamical measurement
exists until the gate fires.

Both tests assert `abs(slope − 0.96) < 0.02`.

## Async release

`DynamicalEngine(..., async_release=True)` submits the measurement to a
single-worker `concurrent.futures.ThreadPoolExecutor`. The stepping
loop does not block on `measure_fdr`; the cached slope updates when the
worker returns. Overlapping releases are suppressed (at most one in
flight at a time).

Measured on the committed scenario, 800 steps + one release:

| Mode                           | Stepping wall | Total wall | Slope    |
|--------------------------------|---------------|------------|----------|
| `async_release=False` (sync)   | 7.91 s        | 7.91 s     | +0.9594  |
| `async_release=True` (async)   | 0.35 s        | 8.22 s     | +0.9594  |

Stepping runs ~23× faster and the released slope is byte-identical (same
inputs, same deterministic measurement). Extra ~0.3 s total wall is the
worker join overhead.

Companion API:

```python
eng = DynamicalEngine(..., async_release=True)
for _ in range(n_steps):
    eng.step()                # non-blocking; worker runs in parallel

if eng.release_in_flight:
    eng.wait_for_release()    # harvest pending worker into the cache

eng.close()                   # shut down executor cleanly
```

## Open

1. **Observable choice.** Currently the caller passes `V_obs`
   explicitly; the gate itself uses total substrate energy for its
   streaming τ buffer. Per-proposition violations V_A or PCA-projected
   coordinates may give cleaner signal in multi-proposition
   experiments.
2. **Substrate `energy` / `V_obs` function capture.** The async worker
   receives bare Python callables; if the substrate is mutated during
   stepping (constraints registered, λ changed), the worker may see
   inconsistent state. For our current use the substrate is built once
   at experiment setup — safe — but multi-phase experiments that mutate
   constraints on the fly need either a substrate snapshot or a
   pack-level copy-on-write discipline.
