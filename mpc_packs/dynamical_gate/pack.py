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
    v = np.asarray(v, dtype=float)
    return v - (grad_fn(v) / gamma) * dt


def compute_tail(buffer: Deque[np.ndarray], window: int) -> Optional[np.ndarray]:
    """Displacement vector summarising the last `window` positions in
    `buffer`: `v[t] − v[t−w]` where `w = min(window, len(buffer) − 1)`.

    Direction-only signal for the gate; magnitude is informational. Returns
    `None` if fewer than two positions are available.
    """
    if len(buffer) < 2:
        return None
    w = min(window, len(buffer) - 1)
    return np.asarray(buffer[-1], dtype=float) - np.asarray(buffer[-1 - w], dtype=float)


def gate_signal(
    v_ghost_delta: np.ndarray,
    v_tail_delta: np.ndarray,
    threshold: float,
) -> bool:
    """Trip when the linear-ghost and trajectory-tail disagree in direction.

    Both arguments are displacement vectors (ghost − v and tail). The signal
    is the cosine distance `1 − cos(θ)`: 0 when perfectly aligned, 1 when
    orthogonal, 2 when anti-aligned. Returns True when the distance exceeds
    `threshold`. Zero-magnitude inputs return False (no information).
    """
    ng = float(np.linalg.norm(v_ghost_delta))
    nt = float(np.linalg.norm(v_tail_delta))
    if ng < 1e-12 or nt < 1e-12:
        return False
    cos_sim = float(np.dot(v_ghost_delta, v_tail_delta) / (ng * nt))
    return (1.0 - cos_sim) > threshold


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
        self._step: int = 0
        self._trip_count: int = 0
        self._last_trip_step: Optional[int] = None
        self._tripped: bool = False

    def observe(
        self,
        v: np.ndarray,
        grad_fn: Callable[[np.ndarray], np.ndarray],
        gamma: float,
        dt: float,
    ) -> None:
        """Push a new position and update the internal gate state.

        No-op on the first `window − 1` observations (buffer not yet full).
        """
        self._step += 1
        self._buffer.append(np.asarray(v, dtype=float).copy())
        self._tripped = False
        if len(self._buffer) < self.window:
            return
        v_cur = self._buffer[-1]
        v_past = self._buffer[0]
        ghost = compute_ghost(v_cur, grad_fn, gamma, dt)
        ghost_delta = ghost - v_cur
        tail_delta = v_cur - v_past
        if gate_signal(ghost_delta, tail_delta, self.threshold):
            self._tripped = True
            self._trip_count += 1
            self._last_trip_step = self._step

    def should_release(self) -> bool:
        """True when the most recent observation tripped the gate."""
        return self._tripped

    @property
    def trip_count(self) -> int:
        """Total trips since construction. For calibration tests."""
        return self._trip_count

    @property
    def last_trip_step(self) -> Optional[int]:
        """Step index of the most recent trip, or None if never tripped."""
        return self._last_trip_step
