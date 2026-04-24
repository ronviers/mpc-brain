"""dynamical_gate configuration — calibrated for the Markovian Langevin
substrate used in Session A (docs/dynamical-track/). Substrate-specific.

See the "Calibration findings" section of README.md for the empirical trip
counts across the four canonical scenarios at these settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from mpc_packs.physics_primitives import DT, D_EFF
import numpy as np


# Expected thermal per-step displacement on the Markovian substrate. Derived,
# not a free parameter.
THERMAL_STEP: float = float(np.sqrt(2.0 * D_EFF * DT))


@dataclass
class DynamicalGateConfig:
    """Calibrated defaults for the Markovian Langevin substrate."""

    window: int = 50
    threshold: float = 0.3
    # Suppress the gate when the per-step tail is well below thermal motion.
    # 0.3 × THERMAL_STEP is the empirical sweet spot: below it the gate
    # fires every step from noise; above 0.6 × it never fires at all.
    min_tail_factor: float = 0.3

    @property
    def min_tail_mag(self) -> float:
        return self.min_tail_factor * THERMAL_STEP
