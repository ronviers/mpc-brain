"""decaying_substrate pack configuration (RFC-002 §3.2).

Plug point: SubstrateExtension — subclasses the kernel's Substrate
(via JAXSubstrate) without changing the public API.

Declared dependencies:
    - mpc_engine_rfc001.ConstraintHandle
    - mpc_packs.jax_substrate.JAXSubstrate (parent class)

Declared mutations: internal decay state only (self._decay_cache,
self._initial_eps, self._uid_to_pid, self._active_pairs).
"""

DECLARED_DEPENDENCIES = [
    "mpc_engine_rfc001:ConstraintHandle",
    "mpc_packs.jax_substrate:JAXSubstrate",
]

DECLARED_MUTATIONS = [
    "self._decay_cache",
    "self._initial_eps",
    "self._uid_to_pid",
    "self._active_pairs",
]
