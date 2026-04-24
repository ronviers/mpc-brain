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
from mpc_packs.dynamical_gate import DynamicalGate

gate = DynamicalGate(window=500, tau_floor=0.05, dt=0.01,
                    recompute_interval=100, burn_frac=0.2)

for _ in range(n_steps):
    v = engine.step()
    gate.observe(v, energy_fn=substrate.energy)
    if gate.should_release():
        # Run measure_fdr at v, classify via classify_phase_dynamical,
        # populate PhaseTransitionEvent.fdr_slope.
        ...
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

## Open

1. **Observable choice.** Currently uses total substrate energy as the
   scalar V. This is substrate-agnostic and always available. For
   multi-proposition experiments, a per-proposition violation V_A or a
   PCA-projected coordinate may give a cleaner signal. Pluggable
   `energy_fn` argument makes this a caller's decision.
2. **Edge-triggered vs level-triggered.** Currently fires on every
   recompute that sees τ below floor (level-triggered), so a sustained
   pinning will release FDR every `recompute_interval` steps. A future
   iteration could only fire on the transition *into* the pinned
   regime (edge-triggered) to avoid redundant measurements.
3. **Integration with `PhaseTransitionEvent.fdr_slope`.** The field is
   already in place; wiring the gate to run `measure_fdr`, classify via
   `classify_phase_dynamical`, and populate the event is the next step.
