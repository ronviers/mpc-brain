"""observation_socket pack configuration (RFC-002 §3.2).

Plug point: ObservationSocket (RFC-001 §7). Holds neither Substrate
nor EventBus. Produces `ConstraintSpec` objects the caller feeds into
a cluster's `.load()` method.

Declared dependencies:
    - numpy, hashlib, os, textwrap, logging (stdlib)
    - anthropic (optional) — AnthropicSocket only

Declared mutations: none (pure producer of ConstraintSpec values,
buffered in self._buffer until flush()).
"""

DECLARED_DEPENDENCIES = [
    "numpy",
    "anthropic",  # optional runtime dependency
]

DECLARED_MUTATIONS: list = []
