# dynamical_gate

Cheap linear predictor that gates the expensive dynamical (FDR) classifier.
Scaffold only — design locked, implementation pending (Session 7 step 1).

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

## Acceptance test (Session 7, step 1)

Runs over the four Session-A scenario trajectories saved from
`mpc_lattice.py`:

| Scenario  | Expected trips |
|-----------|-----------------|
| reset     | near zero (~0–1) — linear approximation holds in a flat bath |
| suspended | low (~1–3) — smooth descent into a single well |
| committed | one burst at basin entry, then quiet |
| conflict  | repeated trips — nonlinear competition between wells |

Concretely: `test_pack.py` loads the four trajectories, runs the gate
over each, asserts `trip_count(reset) < trip_count(conflict)` and that
committed has a single trip-burst early in the trajectory. A
calibration table of thresholds is recorded in the test output.

This test does **not** require any engine modification and does **not**
require the release step — it validates only that the gate signal has
discriminating power on the four known-regime trajectories.

## Declared dependencies

- `numpy`
- `mpc_packs.physics_primitives` — for `measure_fdr` at the release step
  and `classify_phase_dynamical` for final Phase assignment.
- `mpc_kernel.rfc001.phase.Phase` — return type.

## Declared mutations

None yet. Session 7 step 2 (engine integration) will add a Governor-
style mutation to populate `PhaseTransitionEvent.fdr_slope` when the
gate releases a measurement.

## Pickup checklist (Session 7, step 1)

1. Implement `compute_ghost`, `compute_tail`, `gate_signal` in `pack.py`.
2. Implement `DynamicalGate` ring buffer + `observe` + `should_release`.
3. Wire `test_pack.py`: save/reload the four Session-A trajectories (or
   regenerate deterministically from `mpc_lattice.py`'s seeded config),
   run the gate, assert the trip-count ordering above.
4. Tune threshold on the four scenarios; record in `config.py` with a
   comment on the calibration method.
5. Commit as "dynamical_gate: linear gate for FDR release".
