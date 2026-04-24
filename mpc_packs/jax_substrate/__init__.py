"""jax_substrate pack — JAX-accelerated Substrate.

Canonical home of `JAXSubstrate` and the `JAX_AVAILABLE` runtime flag,
previously defined inside `experiments/historical/mpc_session2.py`.
The historical module now re-exports from this pack.
"""

from .pack import JAX_AVAILABLE, JAXSubstrate

__all__ = ["JAX_AVAILABLE", "JAXSubstrate"]
