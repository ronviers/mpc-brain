# physics_primitives

Core observables for the MPC Langevin rig, plus the dynamical regime
classifier. Provides overdamped Langevin integration, autocorrelations,
integral correlation times, survival margin, cross-dissipation, FDR
measurement, and `classify_phase_dynamical(tau_A, tau_env, gamma_A,
gamma_ij, fdr_slope) -> Phase` — the Markovian-honest classifier
calibrated in Task A.

## Provenance

The primitives were developed and validated in the dynamical-track
prototyping session; findings and the four-scenario classification
table are in [docs/dynamical-track/SESSION_A_STATE.md](../../docs/dynamical-track/SESSION_A_STATE.md).
The current source-of-truth file is
[docs/dynamical-track/physics_primitives.py](../../docs/dynamical-track/physics_primitives.py)
(268 lines, unchanged since Task A). This pack will absorb that module
and become the canonical import path.

## Declared dependencies

- `numpy`
- `mpc_kernel.rfc001.phase.Phase` — classifier return type.

## Declared mutations

None. Pure library.
