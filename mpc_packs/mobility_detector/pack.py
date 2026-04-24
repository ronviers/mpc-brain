"""mobility_detector — linear mobile-vs-pinned classifier.

Measures whether an engine is actively exploring (noise dominates drift,
per-window displacement direction uncorrelated with gradient) or settled
(per-window displacement sub-thermal, signal suppressed). Originally
scoped as the FDR-release gate; retained as a mobility observable after
the four-scenario calibration showed its semantics are orthogonal to the
FDR-release need. See README "Why it's shelved" for the full context.
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
    min_tail_mag: float = 0.0,
) -> bool:
    """Trip when the linear-ghost and trajectory-tail disagree in direction.

    Both arguments are displacement vectors per unit time (ghost is a
    one-step drift, tail is the mean per-step displacement over the window).
    The signal is the cosine distance `1 − cos(θ)`: 0 when aligned, 1 when
    orthogonal, 2 when anti-aligned. Returns True when that distance
    exceeds `threshold`.

    `min_tail_mag` suppresses the gate whenever the tail's mean per-step
    displacement falls below that magnitude: direction comparisons on sub-
    thermal motion are pure noise and the gate would fire every step.
    Calibrate against the substrate's thermal displacement scale,
    `sqrt(2·D_eff·dt)`. Set to 0 for the raw geometric signal.
    """
    ng = float(np.linalg.norm(v_ghost_delta))
    nt = float(np.linalg.norm(v_tail_delta))
    if ng < 1e-12 or nt < 1e-12:
        return False
    if nt < min_tail_mag:
        return False
    cos_sim = float(np.dot(v_ghost_delta, v_tail_delta) / (ng * nt))
    return (1.0 - cos_sim) > threshold


# ── Orchestrator ────────────────────────────────────────────────────────────


class MobilityDetector:
    """Per-engine companion that maintains a rolling trajectory buffer
    and exposes a mobility signature.

    Usage from an experiment's run loop:

        det = MobilityDetector(dim=sub.dim, window=50, threshold=0.3)
        for _ in range(n_steps):
            v = engine.step()
            det.observe(v, grad_fn=sub.gradient, gamma=gamma, dt=dt)
            # Continuous observables:
            mobile_score = det.tension          # in [0, ∞), 0 when settled
            mobile_event = det.should_release() # discrete boolean
    """

    def __init__(
        self,
        dim: int,
        window: int = 50,
        threshold: float = 0.3,
        min_tail_mag: float = 0.0,
    ):
        self.dim = dim
        self.window = window
        self.threshold = threshold
        self.min_tail_mag = min_tail_mag
        self._buffer: Deque[np.ndarray] = deque(maxlen=window)
        self._step: int = 0
        self._trip_count: int = 0
        self._last_trip_step: Optional[int] = None
        self._tripped: bool = False
        self._tension: float = 0.0

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
        # Normalise the tail to a per-step displacement so it compares to
        # the per-step ghost on the same time scale.
        tail_per_step = (v_cur - v_past) / self.window

        # Continuous tension signal — unit-free. High when ghost and tail
        # disagree and both have appreciable magnitude; zero otherwise.
        ng = float(np.linalg.norm(ghost_delta))
        nt = float(np.linalg.norm(tail_per_step))
        if ng > 1e-12 and nt > 1e-12:
            cos_sim = float(np.dot(ghost_delta, tail_per_step) / (ng * nt))
            self._tension = (1.0 - cos_sim) * min(ng, nt)
        else:
            self._tension = 0.0

        if gate_signal(ghost_delta, tail_per_step, self.threshold, self.min_tail_mag):
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

    @property
    def tension(self) -> float:
        """Continuous mobility signal (unit-free). High when the linear
        drift and recent trajectory disagree in direction AND both have
        appreciable magnitude; zero when motion is sub-thermal or purely
        drift-aligned. Consumers may integrate, threshold, or use as a
        feature. Updated every `observe()` call."""
        return self._tension
