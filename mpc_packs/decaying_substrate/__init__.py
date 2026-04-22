"""decaying_substrate pack — transitional shim over mpc_session3.

Replace in S6 with a first-class pack when the kernel carve-out lands.
"""

from .pack import DecayingSubstrate

__all__ = ["DecayingSubstrate"]
