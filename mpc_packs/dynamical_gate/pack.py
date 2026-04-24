"""dynamical_gate — linear gate that decides when to release an FDR
measurement ahead of the engine.

Scaffold. Signatures and docstrings locked; bodies to be filled in
Session 7 step 1. See README.md for the design rationale and the
acceptance-test shape.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Deque, Optional

import numpy as np


# ── Pure primitives ─────────────────────────────────────────────────────────


def compute_ghost(
    v: np.ndarray,
    grad_fn: Callable[[np.ndarray], np.ndarray],
    gamma: float,
    dt: float,
) -> np.ndarray:
    """Linear drift extrapolation: where `v` would go under deterministic
    overdamped-Langevin drift in one step of size `dt`.

        v_ghost = v − γ⁻¹ · ∇E(v) · dt

    O(d). Uses the gradient the engine already computed for its own step.
    """
    raise NotImplementedError("Session 7 step 1: implement compute_ghost.")


def compute_tail(buffer: Deque[np.ndarray], window: int) -> np.ndarray:
    """Direction vector summarising the last `window` positions in
    `buffer`. Simplest-adequate form: mean-velocity vector
    `(v[t] − v[t−w]) / w`. Callers may substitute a rolling linear fit.

    Returns a vector aligned with the tail; caller compares to the
    forward ghost.
    """
    raise NotImplementedError("Session 7 step 1: implement compute_tail.")


def gate_signal(
    v_ghost_delta: np.ndarray,
    v_tail_delta: np.ndarray,
    threshold: float,
) -> bool:
    """Trip when the linear-ghost and trajectory-tail disagree.

    Both arguments are displacement vectors (ghost − v and tail − v_past).
    Returns True when the normalised discrepancy exceeds threshold —
    cosine-distance or L2 on unit vectors, calibrated per substrate.
    """
    raise NotImplementedError("Session 7 step 1: implement gate_signal.")


# ── Orchestrator ────────────────────────────────────────────────────────────


class DynamicalGate:
    """Per-engine companion that maintains a rolling trajectory buffer
    and exposes the gate state.

    Usage from an experiment's run loop:

        gate = DynamicalGate(dim=sub.dim, window=50, threshold=0.3)
        for _ in range(n_steps):
            v = engine.step()
            gate.observe(v, grad_fn=sub.gradient, gamma=gamma, dt=dt)
            if gate.should_release():
                # Expensive path: measure_fdr at predicted landing, or
                # use the precomputed classification from a prior release.
                ...
    """

    def __init__(self, dim: int, window: int = 50, threshold: float = 0.3):
        self.dim = dim
        self.window = window
        self.threshold = threshold
        self._buffer: Deque[np.ndarray] = deque(maxlen=window)
        self._last_trip: Optional[int] = None
        self._step: int = 0

    def observe(
        self,
        v: np.ndarray,
        grad_fn: Callable[[np.ndarray], np.ndarray],
        gamma: float,
        dt: float,
    ) -> None:
        """Push a new position and update the internal gate state."""
        raise NotImplementedError("Session 7 step 1: implement observe.")

    def should_release(self) -> bool:
        """True when the most recent observation tripped the gate."""
        raise NotImplementedError("Session 7 step 1: implement should_release.")

    @property
    def trip_count(self) -> int:
        """Total trips since construction. For calibration tests."""
        raise NotImplementedError("Session 7 step 1: implement trip_count.")
