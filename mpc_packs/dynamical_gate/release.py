"""dynamical_gate.release — FDR release at gate trip.

Runs `measure_fdr` at the current position, extracts the late-time
parametric slope in FDT-scaled units (FDT → 1.0), and classifies the
regime via `classify_phase_dynamical`. This is the expensive path that
the streaming-tau gate amortises onto pinned-regime events only.

Slope formula matches docs/dynamical-track/mpc_lattice.py:

    x = (C[0] - C) / D_eff
    late = slice(len(x) // 2, None)
    slope = polyfit(x[late], chi[late], 1)[0]

so the numerical values align with the Session-A reference table.

Full-budget measurement (n_burnin=2000, n_resp=5000, n_reps=32) takes
~7-8 s per call on CPU. Reduced budgets preserve order-of-magnitude
structure but do not preserve the Session-A decimal values — do not
use them as ground truth for the 0.5-classifier threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from mpc_kernel.rfc001.phase import Phase
from mpc_packs.physics_primitives import (
    D_EFF,
    classify_phase_dynamical,
    measure_fdr,
)


@dataclass
class FDRRelease:
    """Result of a single gate-triggered FDR measurement.

    Carries both the slope (for populating
    `PhaseTransitionEvent.fdr_slope`) and the classified Phase (for the
    `to_phase` of any event the caller emits).
    """

    fdr_slope: float
    phase: Phase
    wall_time_s: float


def _scaled_late_slope(C: np.ndarray, chi: np.ndarray) -> float:
    """Late-time slope of chi vs (C(0) - C)/D_eff on the upper half of
    the parametric curve. FDT → slope = 1. Matches mpc_lattice.py."""
    x = (C[0] - C) / D_EFF
    late = slice(int(len(x) * 0.5), None)
    if x[late].std() < 1e-9:
        return float("nan")
    return float(np.polyfit(x[late], chi[late], 1)[0])


def release_fdr_slope(
    v: np.ndarray,
    U: Callable[[np.ndarray], float],
    V_obs: Callable[[np.ndarray], float],
    h_mag: float = 0.05,
    n_burnin: int = 2000,
    n_resp: int = 5000,
    n_reps: int = 32,
    seed: int = 7,
) -> float:
    """Run measure_fdr at `v` under a linear `-h·V_obs` perturbation and
    return the FDT-scaled late-time slope.

    Sign convention matches mpc_lattice.py:  U_pert = U − h·V_obs.
    """
    U_pert = lambda x, _U=U, _h=h_mag, _V=V_obs: _U(x) - _h * _V(x)
    _, C, chi = measure_fdr(
        U, U_pert, V_obs, v, h_mag,
        n_burnin=n_burnin, n_resp=n_resp, n_reps=n_reps, seed=seed,
    )
    return _scaled_late_slope(C, chi)


def release_and_classify(
    v: np.ndarray,
    U: Callable[[np.ndarray], float],
    V_obs: Callable[[np.ndarray], float],
    tau_A: float,
    tau_env: float,
    gamma_A: float,
    gamma_ij: Optional[float] = None,
    h_mag: float = 0.05,
    **fdr_kwargs,
) -> FDRRelease:
    """Full release chain: measure FDR, classify, return both slope and
    Phase. The classifier inputs `tau_A`, `tau_env`, `gamma_A`,
    `gamma_ij` come from the caller's streaming estimators; the slope
    is what this function computes.
    """
    import time
    t0 = time.time()
    slope = release_fdr_slope(v, U, V_obs, h_mag=h_mag, **fdr_kwargs)
    phase = classify_phase_dynamical(
        tau_A=tau_A, tau_env=tau_env, gamma_A=gamma_A,
        gamma_ij=gamma_ij, fdr_slope=slope,
    )
    return FDRRelease(fdr_slope=slope, phase=phase, wall_time_s=time.time() - t0)
