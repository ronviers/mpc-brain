"""jax_substrate pack configuration (RFC-002 §3.2).

Plug point: SubstrateExtension (RFC-002 §4.1). Subclasses `Substrate`
and overrides `gradient` / `hessian` without changing the public API.

Declared dependencies:
    - mpc_engine_rfc001.Substrate (kernel base class)
    - jax, jax.numpy (optional — finite-difference fallback)

Declared mutations: none. Only overrides numerical methods on the
existing interface.
"""

DECLARED_DEPENDENCIES = [
    "mpc_engine_rfc001:Substrate",
    "jax",        # optional runtime dependency
    "jax.numpy",  # optional runtime dependency
]

DECLARED_MUTATIONS: list = []
