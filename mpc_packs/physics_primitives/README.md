# physics_primitives

Core observables for the MPC Langevin rig. Provides the primitive layer
that dynamical-phase classifiers (c / s / k / r per RFC-004) are built
on top of: overdamped Langevin integration, autocorrelations, integral
correlation times, survival margin, cross-dissipation, and FDR
measurement.

**Status:** scaffold. Implementation not yet moved in.

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

## Declared mutations

None. Pure numerical library.

## Pickup checklist

If this pack is still a scaffold, the next step is:

1. Copy `docs/dynamical-track/physics_primitives.py` into `pack.py`.
2. Re-export its public names from `__init__.py`.
3. Flesh out `test_pack.py` with the committed-well smoke test.
4. Repoint `docs/dynamical-track/mpc_lattice.py` to import from here.
5. `git rm` the old copy under `docs/dynamical-track/`.
