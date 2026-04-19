import logging
from typing import List, Optional, Tuple
import numpy as np

from .phase import Phase
from .events import PhaseTransitionEvent, BudgetResetEvent
from .bus import EventBus
from .substrate import Substrate

log = logging.getLogger(__name__)

class MaintenanceField:
    def __init__(self, dim: int, lr: float = 0.05):
        self.dim = dim
        self.lr = lr
        self._ema: Optional[np.ndarray] = None

    def update(self, v: np.ndarray, phase: Phase):
        if phase == Phase.S:
            self._ema = v.copy() if self._ema is None else ((1 - self.lr) * self._ema + self.lr * v)

    def force(self, v: np.ndarray, barrier_strength: float) -> np.ndarray:
        if self._ema is None:
            return np.zeros(self.dim)
        return (1.0 - barrier_strength) * (self._ema - v) * 0.12

class MetastableEngine:
    def __init__(self, substrate: Substrate, bus: EventBus, E_star: float = 5.0, dt: float = 0.01, barrier_strength: float = 0.5, cluster_id: str = "default"):
        self.sub = substrate
        self.bus = bus
        self.E_star = E_star
        self.dt = dt
        self.barrier_strength = barrier_strength
        self.cluster_id = cluster_id
        self.v: np.ndarray = np.zeros(substrate.dim)
        self.attention_scarcity: float = 0.10  
        self._t: float = 0.0
        self._phase_hist: List[Tuple[float, Phase]] = []
        self._energy_hist: List[float] = []
        self._reset_count: int = 0
        self._maint = MaintenanceField(substrate.dim)

    def step(self, external_force: Optional[np.ndarray] = None) -> np.ndarray:
        ext = external_force if external_force is not None else np.zeros(self.sub.dim)
        state = self.sub._energy_state(self.v)
        F_cons = -state.gradient
        prev_phase = self.sub.classify(self.v)
        self._maint.update(self.v, prev_phase)
        F_maint = self._maint.force(self.v, self.barrier_strength) if prev_phase == Phase.S else np.zeros(self.sub.dim)
        std = np.sqrt(2.0 * self.attention_scarcity * self.dt + 1e-12)
        F_noise = std * np.random.randn(self.sub.dim)
        v_proposed = self.v + self.dt * (F_cons + F_maint + ext) + F_noise

        if self.sub.energy(v_proposed) > self.E_star:
            self._trigger_reset(prev_phase)
            self._t += self.dt
            return self.v

        self.v = v_proposed
        new_phase = self.sub.classify(self.v)

        if new_phase != prev_phase:
            self.bus.emit(PhaseTransitionEvent(
                from_phase=prev_phase, to_phase=new_phase, energy=state.energy,
                position=self.v.copy(), timestamp=self._t, cluster_id=self.cluster_id,
            ))

        self._phase_hist.append((self._t, new_phase))
        self._energy_hist.append(state.energy)
        self._t += self.dt
        return self.v

    def run(self, n_steps: int, forces: Optional[List[np.ndarray]] = None) -> np.ndarray:
        traj = np.empty((n_steps, self.sub.dim))
        for i in range(n_steps):
            traj[i] = self.step(forces[i] if forces else None)
        return traj

    @property
    def phase(self) -> Phase:
        return self.sub.classify(self.v)

    def detect_insight(self) -> bool:
        if len(self._energy_hist) < 10:
            return False
        recent_e = self._energy_hist[-10:]
        recent_ph = [p for _, p in self._phase_hist[-10:]]
        energy_drop = recent_e[0] - recent_e[-1]
        had_s = Phase.S in recent_ph[:5]
        now_c = bool(recent_ph) and recent_ph[-1] == Phase.C
        return had_s and now_c and energy_drop > 0.15

    @property
    def dominant_phase(self) -> Phase:
        if not self._phase_hist:
            return Phase.R
        recent = [p for _, p in self._phase_hist[-50:]]
        return max(set(recent), key=recent.count)

    def _trigger_reset(self, prev_phase: Phase):
        self._reset_count += 1
        self.bus.emit(BudgetResetEvent(
            cluster_id=self.cluster_id, position=self.v.copy(), timestamp=self._t, info_cost=1.0,
        ))
        self.v = np.random.randn(self.sub.dim) * 0.01
        log.debug(f"[{self.cluster_id}] budget reset #{self._reset_count} at t={self._t:.3f}")