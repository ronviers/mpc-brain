"""lateral_cluster pack — AMEND-003 Lateral Maintenance Field.

Canonical home of `LateralCluster`, previously defined inside
`experiments/historical/mpc_session3.py`. The historical module now
re-exports from this pack.
"""

from .pack import LateralCluster

__all__ = ["LateralCluster"]
