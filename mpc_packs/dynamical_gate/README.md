# dynamical_gate

Cheap linear predictor that gates the expensive dynamical (FDR) classifier.
Primitives, orchestrator, and four-scenario calibration are green; see
"Calibration findings" below for the substrate-specific empirical pattern
and the known limitation.

## The pattern

From a Maya predictive-VFX rig: linear forward/backward curves with a
wind field, an nParticle on the backward curve that drags in the field,
forcing the forward curve to lead the present. The nParticle is doing
control flow, not physics — it decides *when and where* to pay for the
expensive nonlinear simulation.

Translated to MPC:

| Maya                            | MPC                                                          |
|---------------------------------|--------------------------------------------------------------|
| forward orthogonal curve        | linear drift extrapolation  `v_ghost = v − γ⁻¹ ∇E · Δt`     |
| backward orthogonal curve       | rolling recent-trajectory tail  `v_tail`                    |
| wind field                      | local energy gradient ∇E                                     |
| nParticle dragging in field     | discrepancy `‖v_ghost − v_tail‖` — gate signal               |
| "VFX released ahead of time"    | `measure_fdr` launched at predicted landing, before arrival  |

Where the linear approximation holds (gate quiet), the topological
classifier's phase is trustworthy and `PhaseTransitionEvent.fdr_slope`
stays `None`. Where the linear approximation breaks (gate trips), we
release the FDR measurement ahead of time so the classification is ready
when the engine crosses into the new regime.

## Why not every-step FDR

`measure_fdr` from `physics_primitives` is seconds per call under current
parameters (paired matched-noise Langevin, `n_reps=32`). Per-step online
use is not viable. The gate amortises it onto trajectory events only.

## Components

Three pure functions + one orchestrator:

1. **`compute_ghost(v, grad_fn, gamma, dt) -> np.ndarray`**
   Single-step linear drift extrapolation. O(d).

2. **`compute_tail(buffer, window) -> np.ndarray`**
   Recent-trajectory direction vector (rolling linear fit or mean
   velocity over the last `window` frames). O(w·d).

3. **`gate_signal(v_ghost, v_tail, threshold) -> bool`**
   Trip when the linear-ghost and trajectory-tail disagree. Simple
   cosine or normalised-L2 discrepancy above threshold returns `True`.

4. **`DynamicalGate` class** — maintains the ring buffer, exposes
   `observe(v)` per step, and `should_release()` to query trip state.
   On trip, caller should invoke `physics_primitives.measure_fdr` at
   the predicted landing point.

## Calibration findings

Actual trip counts over 3000-step seeded Langevin trajectories on the
four Session-A scenarios, with the defaults in `config.py`
(`window=50`, `threshold=0.3`, `min_tail_factor=0.3`):

| Scenario  | Trips | Interpretation |
|-----------|-------|-----------------|
| conflict  |   0   | stiff disjoint wells pin the particle at the compromise point; per-step displacement stays below the thermal-magnitude gate. Gate silent. |
| committed |   8   | stiff compatible wells; particle settles at intersection minimum with tight thermal fluctuations. Gate rarely fires. |
| suspended |  81   | soft wells; thermal excursions regularly large enough that per-window drift direction disagrees with the instantaneous gradient. |
| reset     | 110   | softest potential; noise dominates drift; per-window tail direction is uncorrelated with gradient. |

The gate *does* produce a discriminating signal (110 vs 0 trips, 3+ orders of
magnitude of spread), but the **semantics are inverted** from what FDR needs:
the gate is silent in the pinned regimes (committed, conflict) where FDR is
load-bearing for the C vs K distinction, and fires most in the mobile regimes
(suspended, reset) where the topological classifier already works. The Maya-
topology linear-predictor pattern as-implemented measures "mobile vs pinned",
not "linear approximation breaks down vs holds".

## Acceptance test

The committed test is the weak form: `test_scenarios_discriminate` asserts
(a) the gate isn't silent across all scenarios, (b) the trip-count spread
is at least 3, and (c) `reset > committed` (mobile > pinned). The specific
ordering above is recorded, not asserted, because the useful direction is
still an open design question (below).

## Declared dependencies

- `numpy`
- `mpc_packs.physics_primitives` — for `measure_fdr` at the release step
  and `classify_phase_dynamical` for final Phase assignment.
- `mpc_kernel.rfc001.phase.Phase` — return type.

## Declared mutations

None yet. Engine integration will add a Governor-style mutation to populate
`PhaseTransitionEvent.fdr_slope` when the gate releases a measurement — but
only after the open design question below is resolved.

## Open: what the gate should actually detect

The current formulation separates mobile regimes from pinned regimes. That's
a useful signal, but it's the wrong direction for the FDR-release use case
we scoped for: on Markovian Langevin substrates, FDR is required *inside*
the pinned regime to separate C from K, and the gate is silent there.

Candidate reformulations:

1. **Invert the trigger.** Release FDR when `min_tail_mag` is *not*
   exceeded — i.e., when the particle is suspiciously still. Pair with a
   Hessian-curvature check to distinguish "settled at a real minimum" from
   "pinned at a frustrated compromise". This matches the intuition: run the
   expensive measurement in the pinned regime where cheap observables can't
   tell you more.
2. **Trajectory autocorrelation probe.** Streaming `τ_A` estimate via a
   rolling autocorrelation of V_A on the engine's own trajectory (no
   perturbation needed). When the estimate drops below the noise floor,
   release a full paired-noise FDR measurement. This is closer to what the
   mpc_lattice classifier actually does, just amortised per-engine rather
   than per-scenario.
3. **Gradient-rotation rate.** Fire when `∇E` direction has been changing
   coherently (descent into a basin, saddle crossing) rather than jittering
   (equilibrium). Clean kinematic signal that's independent of magnitude.

Whichever direction wins, the primitives in this pack (ghost / tail /
gate_signal) are reusable. Only the `DynamicalGate.observe` orchestration
has to change.
