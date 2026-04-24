"""dynamical_gate configuration — calibrated for the Markovian Langevin
substrate used in Session A. Substrate-specific; re-calibrate for other
substrates (memory-kernel, active-drive, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass

from mpc_packs.physics_primitives import DT


@dataclass
class DynamicalGateConfig:
    """Defaults calibrated against the four Session-A scenarios.

    tau_E on the Markovian Langevin substrate:

        conflict    0.005   |  pinned, FDR needed
        committed   0.010   |  pinned, FDR needed
        suspended   0.23    |  mobile, topological is enough
        reset       0.8-2.1 |  mobile, topological is enough

    A tau_floor of 0.05 sits at ~5× the pinned estimates and ~5× below
    the mobile ones — comfortable margin on both sides.
    """

    window: int = 500
    tau_floor: float = 0.05
    dt: float = DT
    recompute_interval: int = 100
    burn_frac: float = 0.2
