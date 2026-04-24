"""dynamical_gate — streaming integral-correlation-time gate.

Maintains a rolling buffer of a scalar observable (default: substrate
energy) and periodically recomputes its integral correlation time via
the same `autocorr_fft` + `tau_integral` primitives used in the Session
A lattice rig. Fires when tau drops below a floor — the signature of
the pinned regime.

Why this semantics. SESSION_A_STATE.md "Markovian sign caveat":

    In the committed and conflict regimes, both τ_A and τ_ij collapse
    to the noise floor, so trajectory observables alone cannot
    distinguish c from k. The FDR slope DOES distinguish them.

The gate releases an FDR measurement exactly when it enters that
ambiguous pinned zone, and stays quiet otherwise. The call that
classifies between C and K once FDR is measured lives in
`mpc_packs.physics_primitives.classify_phase_dynamical`.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Deque, Optional

import numpy as np

from mpc_packs.physics_primitives import DT, autocorr_fft, tau_integral


class DynamicalGate:
    """Per-engine companion that gates FDR release on streaming tau_E.

    Usage from an experiment's run loop:

        gate = DynamicalGate(window=500, tau_floor=0.05, dt=0.01)
        for _ in range(n_steps):
            v = engine.step()
            gate.observe(v, energy_fn=substrate.energy)
            if gate.should_release():
                # Pinned regime entered. Run measure_fdr at v, classify
                # via classify_phase_dynamical, populate
                # PhaseTransitionEvent.fdr_slope on the next emit.
                ...

    The gate is cheap: observations are O(1) (one energy eval plus
    buffer append). The tau estimate only runs every
    `recompute_interval` steps and is O(window log window) for the FFT.
    """

    def __init__(
        self,
        window: int = 500,
        tau_floor: float = 0.05,
        dt: float = DT,
        recompute_interval: int = 100,
        burn_frac: float = 0.2,
        min_variance: float = 1e-14,
    ):
        if window <= 0:
            raise ValueError(f"window must be positive, got {window}")
        if not 0.0 <= burn_frac < 1.0:
            raise ValueError(f"burn_frac must be in [0, 1), got {burn_frac}")
        self.window = window
        self.tau_floor = tau_floor
        self.dt = dt
        self.recompute_interval = max(1, recompute_interval)
        self.burn_frac = burn_frac
        self.min_variance = min_variance

        self._buffer: Deque[float] = deque(maxlen=window)
        self._step: int = 0
        self._tau_estimate: Optional[float] = None
        self._trip_count: int = 0
        self._last_trip_step: Optional[int] = None
        self._tripped: bool = False

    def observe(
        self,
        v: np.ndarray,
        energy_fn: Callable[[np.ndarray], float],
    ) -> None:
        """Push a new position; record its energy; refresh tau_E when due.

        No-op on the tau side until the buffer is full; after that the
        tau estimate is refreshed every `recompute_interval` steps.
        """
        self._step += 1
        self._buffer.append(float(energy_fn(v)))
        self._tripped = False

        if len(self._buffer) < self.window:
            return
        if self._step % self.recompute_interval != 0:
            return

        e_arr = np.asarray(self._buffer, dtype=float)
        start = int(len(e_arr) * self.burn_frac)
        e_seg = e_arr[start:]

        if np.var(e_seg) < self.min_variance:
            # Degenerate: the observable is effectively constant. That
            # counts as maximal pinning — release.
            self._tau_estimate = 0.0
        else:
            e_centered = e_seg - np.mean(e_seg)
            C = autocorr_fft(e_centered, normalize=True)
            self._tau_estimate = tau_integral(C, self.dt)

        if self._tau_estimate < self.tau_floor:
            self._tripped = True
            self._trip_count += 1
            self._last_trip_step = self._step

    def should_release(self) -> bool:
        """True on the most recent `observe()` if the tau estimate fell
        below the floor on that observation's recompute."""
        return self._tripped

    @property
    def tau_estimate(self) -> Optional[float]:
        """Most recent tau_E estimate, or None if the buffer has not yet
        filled enough for a first estimate."""
        return self._tau_estimate

    @property
    def trip_count(self) -> int:
        return self._trip_count

    @property
    def last_trip_step(self) -> Optional[int]:
        return self._last_trip_step
