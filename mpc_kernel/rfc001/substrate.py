import uuid
from dataclasses import dataclass
from typing import Callable, Dict, Tuple
import numpy as np

from .phase import Phase

@dataclass
class EnergyState:
    energy: float
    gradient: np.ndarray
    hessian: np.ndarray

@dataclass
class TopologyResult:
    phase: Phase
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    basin_depth: float

@dataclass
class ConstraintHandle:
    uid: str
    proposition_id: str
    stiffness: float   

class Substrate:
    def __init__(self, dim: int, E_c: float = 0.50, E_s: float = 2.00, epsilon: float = 1e-4):
        self.dim = dim
        self.E_c = E_c
        self.E_s = E_s
        self._eps = epsilon
        self._constraints: Dict[str, Tuple[Callable[[np.ndarray], float], ConstraintHandle]] = {}
        self._frustration: Dict[Tuple[str, str], float] = {}

    def energy(self, v: np.ndarray) -> float:
        e = 0.0
        for fn, h in self._constraints.values():
            e += h.stiffness * fn(v)
        return e

    def gradient(self, v: np.ndarray) -> np.ndarray:
        g, eps = np.zeros(self.dim), self._eps
        for i in range(self.dim):
            vp, vm = v.copy(), v.copy()
            vp[i] += eps; vm[i] -= eps
            g[i] = (self.energy(vp) - self.energy(vm)) / (2 * eps)
        return g

    def hessian(self, v: np.ndarray) -> np.ndarray:
        n, eps = self.dim, self._eps
        H = np.zeros((n, n))
        E0 = self.energy(v)
        for i in range(n):
            vpi, vmi = v.copy(), v.copy()
            vpi[i] += eps; vmi[i] -= eps
            H[i, i] = (self.energy(vpi) - 2 * E0 + self.energy(vmi)) / eps**2
            for j in range(i + 1, n):
                vpp, vpm, vmp, vmm = [v.copy() for _ in range(4)]
                vpp[i] += eps; vpp[j] += eps
                vpm[i] += eps; vpm[j] -= eps
                vmp[i] -= eps; vmp[j] += eps
                vmm[i] -= eps; vmm[j] -= eps
                val = (self.energy(vpp) - self.energy(vpm) - self.energy(vmp) + self.energy(vmm)) / (4 * eps**2)
                H[i, j] = H[j, i] = val
        return H

    def classify(self, v: np.ndarray) -> Phase:
        return self._topology(v).phase

    def register(self, proposition_id: str, fn: Callable[[np.ndarray], float], lam: float = 1.0) -> ConstraintHandle:
        uid = uuid.uuid4().hex[:8]
        handle = ConstraintHandle(uid=uid, proposition_id=proposition_id, stiffness=lam)
        self._constraints[uid] = (fn, handle)
        return handle

    def update_lambda(self, handle: ConstraintHandle, lam: float):
        if handle.uid in self._constraints:
            handle.stiffness = max(0.0, lam)

    def deregister(self, handle: ConstraintHandle):
        self._constraints.pop(handle.uid, None)

    def frustration(self, v: np.ndarray) -> Dict[Tuple[str, str], float]:
        uids = list(self._constraints)
        result: Dict[Tuple[str, str], float] = {}
        for a, uid_a in enumerate(uids):
            fn_a, h_a = self._constraints[uid_a]
            for uid_b in uids[a + 1:]:
                fn_b, h_b = self._constraints[uid_b]
                result[(uid_a, uid_b)] = h_a.stiffness * fn_a(v) + h_b.stiffness * fn_b(v)
        self._frustration = result
        return result

    @property
    def constraint_count(self) -> int:
        return len(self._constraints)

    def _topology(self, v: np.ndarray) -> TopologyResult:
        E = self.energy(v)
        if not self._constraints:
            return TopologyResult(Phase.R, np.zeros(self.dim), np.eye(self.dim), 0.0)
        H = self.hessian(v)
        eigvals, eigvecs = np.linalg.eigh(H)
        pos_eigs = eigvals[eigvals > 0]
        basin_depth = float(pos_eigs.min()) if len(pos_eigs) else 0.0
        if E < self.E_c and eigvals.min() > 0:
            phase = Phase.C
        elif E > self.E_s or eigvals.min() < -0.05:
            phase = Phase.K
        else:
            phase = Phase.S
        return TopologyResult(phase, eigvals, eigvecs, basin_depth)

    def _energy_state(self, v: np.ndarray) -> EnergyState:
        return EnergyState(energy=self.energy(v), gradient=self.gradient(v), hessian=self.hessian(v))

    def _average_degree(self) -> float:
        n = self.constraint_count
        if n <= 1:
            return 0.0
        active = sum(1 for val in self._frustration.values() if val > 0)
        return 2.0 * active / n

    def _min_nonzero_frustration(self) -> float:
        vals = [v for v in self._frustration.values() if v > 1e-9]
        return float(min(vals)) if vals else 1e-9