"""observation_socket pack — AMEND-004 ObservationSocket family.

Canonical home of `ConstraintSpec`, `ObservationSocket` (abstract base),
and `AnthropicSocket` (Anthropic-API-backed concrete implementation),
previously defined inside `experiments/historical/mpc_session3.py`.
The historical module now re-exports from this pack.

`Z3SymbolicSocket` (`mpc_packs.z3_socket`) is a different concrete
implementation of the same abstract base; both subclass the
`ObservationSocket` defined here.
"""

from .pack import (
    SYSTEM_TEMPLATE,
    AnthropicSocket,
    ConstraintSpec,
    ObservationSocket,
)

__all__ = [
    "AnthropicSocket",
    "ConstraintSpec",
    "ObservationSocket",
    "SYSTEM_TEMPLATE",
]
