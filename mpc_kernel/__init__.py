"""mpc_kernel — RFC-001 kernel package.

Session 5a scaffold: this package re-exports RFC-001 primitives from the
monolith `mpc_engine_rfc001` via `mpc_kernel.rfc001.events`. It is NOT a
canonical split. Session 6 replaces the contents with the per-file
carve-out described in RFC-002 §6.
"""

from .__version__ import __version__

__all__ = ["__version__"]
