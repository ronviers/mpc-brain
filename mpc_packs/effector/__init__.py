"""effector pack — passive commit-accounting subscriber.

Canonical home of `Effector` and `EffectorEvent`, previously defined
inside `experiments/historical/mpc_session4.py`. The historical module
now re-exports from this pack.
"""

from .pack import Effector, EffectorEvent

__all__ = ["Effector", "EffectorEvent"]
