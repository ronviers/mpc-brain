"""physics_primitives pack — core observables for the MPC Langevin rig.

Canonical import path for the validated primitives (moved from
docs/dynamical-track/physics_primitives.py, which remains in place until
step 5 of the Session 6 promotion).
"""

from .pack import (
    K_BT,
    DT,
    D_EFF,
    numerical_grad,
    run_langevin,
    run_paired,
    autocorr_fft,
    tau_integral,
    correlation_time,
    survival_margin,
    cross_dissipation,
    measure_fdr,
)

__all__ = [
    "K_BT",
    "DT",
    "D_EFF",
    "numerical_grad",
    "run_langevin",
    "run_paired",
    "autocorr_fft",
    "tau_integral",
    "correlation_time",
    "survival_margin",
    "cross_dissipation",
    "measure_fdr",
]
