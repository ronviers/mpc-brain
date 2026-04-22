# Transitional shim. Replace in S6 with a first-class pack when the kernel
# carve-out lands. See SESSION-5a-part2-TASK-PROMPT.md §D7.
from mpc_session3 import DecayingSubstrate

__all__ = ["DecayingSubstrate"]
