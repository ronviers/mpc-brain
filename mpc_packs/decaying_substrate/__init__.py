"""decaying_substrate pack — temporal frustration decay (AMEND-001).

First-class pack (Session-8 carve-out from the Session-3 monolith).
Previously a transitional shim that re-exported from mpc_session3.
"""

from .pack import DecayingSubstrate

__all__ = ["DecayingSubstrate"]
