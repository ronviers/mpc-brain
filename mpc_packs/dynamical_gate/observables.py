"""dynamical_gate.observables — streaming estimators for tau_A,
gamma_A, gamma_ij on a single engine's trajectory.

`classify_phase_dynamical` requires these alongside `fdr_slope` to make
the full regime decision. Without a companion, each caller reimplements
the same rolling-buffer + `correlation_time`/`survival_margin` logic
that mpc_lattice.py already has. This module consolidates it.

`tau_env` is supplied once from an external bath trajectory — that
observable cannot be derived from the engine's own path because it
lives in a different (weak-potential) substrate by definition.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Deque, Optional

import numpy as np

from mpc_packs.physics_primitives import (
    DT,
    correlation_time,
    cross_dissipation,
)


class StreamingObservables:
    """Per-engine rolling-buffer estimators.

    Parameters
    ----------
    V_A_fn :
        Primary observable (e.g. a proposition-violation function).
    V_B_fn :
        Optional second observable; enables `gamma_ij()`.
    window :
        Trajectory-buffer length. Must be long enough for a stable
        autocorrelation integral at the scales of interest.
    dt, burn_frac :
        Passed through to `correlation_time` and `cross_dissipation`.
    bath_trajectory :
        Optional; if supplied at construction, `tau_env` is computed
        immediately. Otherwise call `set_bath_reference` before
        `gamma_A()` is valid.
    """

    def __init__(
        self,
        V_A_fn: Callable[[np.ndarray], float],
        V_B_fn: Optional[Callable[[np.ndarray], float]] = None,
        window: int = 500,
        dt: float = DT,
        burn_frac: float = 0.2,
        bath_trajectory: Optional[np.ndarray] = None,
    ):
        if window <= 0:
            raise ValueError(f"window must be positive, got {window}")
        self.V_A_fn = V_A_fn
        self.V_B_fn = V_B_fn
        self.window = window
        self.dt = dt
        self.burn_frac = burn_frac

        self._buffer: Deque[np.ndarray] = deque(maxlen=window)
        self._tau_env: Optional[float] = None

        if bath_trajectory is not None:
            self.set_bath_reference(bath_trajectory)

    # ── Per-step observation ────────────────────────────────────────────

    def observe(self, v: np.ndarray) -> None:
        """Push a position into the rolling buffer."""
        self._buffer.append(np.asarray(v, dtype=float).copy())

    def set_bath_reference(self, bath_trajectory: np.ndarray) -> None:
        """Compute tau_env from a supplied bath trajectory. One-shot;
        the caller is responsible for regenerating if the bath changes."""
        traj = np.asarray(bath_trajectory, dtype=float)
        if traj.ndim != 2:
            raise ValueError(
                f"bath_trajectory must be 2D (n_steps, dim), got shape {traj.shape}"
            )
        self._tau_env = correlation_time(self.V_A_fn, traj, self.dt, self.burn_frac)

    # ── Accessors ───────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """True when the buffer is full AND a bath reference has been set."""
        return len(self._buffer) >= self.window and self._tau_env is not None

    @property
    def tau_env(self) -> Optional[float]:
        return self._tau_env

    def _as_array(self) -> np.ndarray:
        return np.asarray(self._buffer, dtype=float)

    def tau_A(self) -> float:
        """Integral correlation time of V_A on the current buffer.
        Returns NaN if the buffer is not yet full."""
        if len(self._buffer) < self.window:
            return float("nan")
        return correlation_time(self.V_A_fn, self._as_array(), self.dt, self.burn_frac)

    def gamma_A(self) -> float:
        """Survival margin  1/tau_A - 1/tau_env. NaN if either tau is
        missing or non-positive."""
        tA = self.tau_A()
        tE = self._tau_env
        if tE is None or tE <= 0 or not np.isfinite(tA) or tA <= 0:
            return float("nan")
        return 1.0 / tA - 1.0 / tE

    def gamma_ij(self) -> Optional[float]:
        """Cross-dissipation gamma_ij = 1/tau_{i∧j} - max(1/tau_i, 1/tau_j).
        None when V_B_fn was not supplied."""
        if self.V_B_fn is None or len(self._buffer) < self.window:
            return None
        g, _, _, _ = cross_dissipation(self.V_A_fn, self.V_B_fn, self._as_array(), self.dt)
        return float(g)
