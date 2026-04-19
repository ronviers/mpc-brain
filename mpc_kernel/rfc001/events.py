from dataclasses import dataclass
import numpy as np
from .phase import Phase

@dataclass
class PhaseTransitionEvent:
    from_phase: Phase
    to_phase: Phase
    energy: float  
    position: np.ndarray
    timestamp: float
    cluster_id: str
    constraint_id: str = "engine_global"

@dataclass
class LandauerEvent:
    cluster_id: str
    info_content: float    
    kT: float = 1.0

@dataclass
class BudgetResetEvent:
    cluster_id: str
    position: np.ndarray
    timestamp: float
    info_cost: float = 1.0