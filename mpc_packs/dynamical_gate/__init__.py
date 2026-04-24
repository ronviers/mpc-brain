"""dynamical_gate pack — streaming-tau gate for FDR release.

Exposes `DynamicalGate`, a per-engine companion that maintains a rolling
energy-time-series and estimates the integral correlation time tau_E.
Fires when tau_E falls below a calibrated floor — i.e., when the engine
enters the pinned regime where trajectory observables cannot separate C
from K and FDR is load-bearing.
"""

from .observables import StreamingObservables
from .pack import DynamicalGate
from .release import FDRRelease, release_and_classify, release_fdr_slope

__all__ = [
    "DynamicalGate",
    "FDRRelease",
    "StreamingObservables",
    "release_and_classify",
    "release_fdr_slope",
]
