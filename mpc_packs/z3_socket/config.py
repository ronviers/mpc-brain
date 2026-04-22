"""z3_socket pack manifest — RFC-002 §3.2 / §4.3.

declared_dependencies:
    - mpc_session3.ObservationSocket  (abstract base class)
    - mpc_session3.ConstraintSpec     (returned record)
    - third-party: z3-solver

declared_mutations:
    NONE. The socket is a measurement-side component. It does not touch
    Substrate state, Bus state, Cluster state, or Engine state. It allocates
    a private Solver per observation and accumulates specs in self._buffer
    until flush() drains them to the caller.

no_modify_kernel: True
no_shadow:        True   (imports, does not re-declare, ObservationSocket /
                         ConstraintSpec)

§7.2 measurement compliance:
    - Holds no Substrate reference.
    - Holds no Bus reference.
    - Does not subscribe to any event.
    - `observe*()` are pure: input string/formula_fn -> ConstraintSpec.
"""

PACK_NAME = "z3_socket"
PACK_VERSION = "0.1.0"
DECLARED_DEPENDENCIES = [
    "mpc_session3:ObservationSocket",
    "mpc_session3:ConstraintSpec",
    "z3-solver",
]
DECLARED_MUTATIONS: list = []   # measurement-only pack
NO_MODIFY_KERNEL = True
NO_SHADOW = True
