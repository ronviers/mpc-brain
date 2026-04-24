"""auto_cluster pack configuration (RFC-002 §3.2).

Plug point: SubstrateExtension-adjacent — subclasses `MPCCluster`.

Declared dependencies:
    - mpc_engine_rfc001.MPCCluster         (kernel base class)
    - mpc_kernel.rfc001.phase.Phase        (kernel enum)
    - mpc_packs.jax_substrate.JAXSubstrate (optional acceleration)
    - mpc_packs.jax_substrate.JAX_AVAILABLE (runtime flag)

Declared mutations: this pack DOES spawn/cull engines via the
`add_engine` / `self.engines` interface defined in MPCCluster. Those
mutations are confined to the cluster's own `self.engines` list and
its internal `_r_streak` dict; no external state is touched.
"""

DECLARED_DEPENDENCIES = [
    "mpc_engine_rfc001:MPCCluster",
    "mpc_kernel.rfc001.phase:Phase",
    "mpc_packs.jax_substrate:JAXSubstrate",
    "mpc_packs.jax_substrate:JAX_AVAILABLE",
]

DECLARED_MUTATIONS = [
    "self.engines",         # spawn / cull
    "self._r_streak",       # per-engine r-state step counter
    "self.sub",             # replaced with JAXSubstrate at construction
    "self.ops.sub",         # kept in sync with self.sub
]
