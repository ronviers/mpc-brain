"""mobility_detector pack — linear mobile-vs-pinned classifier.

Exposes `MobilityDetector`, a per-engine companion that reports whether
the engine is exploring (gate fires, tension high) or settled (silent,
tension zero). See README.md for the four-scenario calibration.
"""

from .pack import (
    MobilityDetector,
    compute_ghost,
    compute_tail,
    gate_signal,
)

__all__ = [
    "MobilityDetector",
    "compute_ghost",
    "compute_tail",
    "gate_signal",
]
