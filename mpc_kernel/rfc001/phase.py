from enum import Enum

class Phase(Enum):
    C = "c"   # committed  — deep minimum, high revision cost
    S = "s"   # suspended  — metastable, active maintenance required
    K = "k"   # conflict   — no satisfying configuration, elevated cost
    R = "r"   # reset      — maximally entropic prior, V_A ≡ 0