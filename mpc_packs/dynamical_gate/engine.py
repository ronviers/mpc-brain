"""dynamical_gate.engine — MetastableEngine subclass that populates
PhaseTransitionEvent.fdr_slope.

Follows the Session-4 InstrumentedEngine pattern: inherit from
MetastableEngine, override step() to observe the gate and the
streaming observables per step, run release_and_classify
synchronously when the gate edge-fires, and emit PhaseTransitionEvent
with the cached fdr_slope on phase transitions.

RFC-001 §3 invariants are unchanged: classify() is not overridden, the
budget wall behaviour is inherited, maintenance-field behaviour is
inherited. Only event emission is enriched.

Synchronous release caveat. `measure_fdr` at full budget is ~8 s on CPU;
because the release is synchronous, the step() call in which the gate
edge-fires stalls for that duration. With edge-triggering this is ~1
stall per basin entry — bearable for short experiments, not for long
ones. Async release is future work.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from mpc_kernel.rfc001.engine import MetastableEngine
from mpc_kernel.rfc001.events import PhaseTransitionEvent
from mpc_kernel.rfc001.phase import Phase

from .observables import StreamingObservables
from .pack import DynamicalGate
from .release import release_and_classify


class DynamicalEngine(MetastableEngine):
    """MetastableEngine variant that populates
    `PhaseTransitionEvent.fdr_slope` via a DynamicalGate +
    StreamingObservables pair.

    Parameters
    ----------
    substrate, bus, E_star, dt, barrier_strength, cluster_id :
        Inherited MetastableEngine arguments.
    gate :
        A `DynamicalGate` instance. The engine calls `gate.observe`
        each step with the substrate energy.
    observables :
        A `StreamingObservables` instance with a bath reference set.
        The engine calls `observables.observe` each step.
    V_obs :
        The probe observable for the FDR measurement at release time.
    h_mag :
        FDR perturbation magnitude. Default 0.05 matches Session-A for
        committed/reset; tune per substrate.
    release_kwargs :
        Passed through to `release_and_classify` (`n_burnin`, `n_resp`,
        etc.). Defaults are Session-A full budget.
    """

    def __init__(
        self,
        substrate,
        bus,
        *,
        gate: DynamicalGate,
        observables: StreamingObservables,
        V_obs: Callable[[np.ndarray], float],
        h_mag: float = 0.05,
        release_kwargs: Optional[dict] = None,
        E_star: float = 5.0,
        dt: float = 0.01,
        barrier_strength: float = 0.5,
        cluster_id: str = "default",
    ):
        super().__init__(
            substrate=substrate,
            bus=bus,
            E_star=E_star,
            dt=dt,
            barrier_strength=barrier_strength,
            cluster_id=cluster_id,
        )
        self.gate = gate
        self.observables = observables
        self.V_obs = V_obs
        self.h_mag = h_mag
        self.release_kwargs = release_kwargs or {}

        self._cached_fdr_slope: Optional[float] = None
        self._release_count: int = 0

    @property
    def cached_fdr_slope(self) -> Optional[float]:
        """Most recent FDR slope measured by a gate release, or None
        if no release has fired since construction."""
        return self._cached_fdr_slope

    @property
    def release_count(self) -> int:
        """Number of gate releases that triggered a full FDR measurement."""
        return self._release_count

    def step(self, external_force: Optional[np.ndarray] = None) -> np.ndarray:
        """Advance v(t) one step; observe gate and observables; on edge
        fire, run release synchronously and cache the slope; on phase
        transition, emit PhaseTransitionEvent with fdr_slope populated."""
        ext = external_force if external_force is not None else np.zeros(self.sub.dim)
        state = self.sub._energy_state(self.v)
        F_cons = -state.gradient

        prev_phase = self.sub.classify(self.v)
        self._maint.update(self.v, prev_phase)
        F_maint = (
            self._maint.force(self.v, self.barrier_strength)
            if prev_phase == Phase.S
            else np.zeros(self.sub.dim)
        )

        std = np.sqrt(2.0 * self.attention_scarcity * self.dt + 1e-12)
        F_noise = std * np.random.randn(self.sub.dim)
        v_proposed = self.v + self.dt * (F_cons + F_maint + ext) + F_noise

        if self.sub.energy(v_proposed) > self.E_star:
            self._trigger_reset(prev_phase)
            self._t += self.dt
            return self.v

        self.v = v_proposed
        new_phase = self.sub.classify(self.v)

        # Dynamical observations.
        self.gate.observe(self.v, self.sub.energy)
        self.observables.observe(self.v)

        # Gate edge-fire → synchronous release, cache the slope.
        if self.gate.should_release() and self.observables.is_ready:
            release = release_and_classify(
                self.v,
                self.sub.energy,
                self.V_obs,
                tau_A=self.observables.tau_A(),
                tau_env=self.observables.tau_env,
                gamma_A=self.observables.gamma_A(),
                gamma_ij=self.observables.gamma_ij(),
                h_mag=self.h_mag,
                **self.release_kwargs,
            )
            self._cached_fdr_slope = release.fdr_slope
            self._release_count += 1

        if new_phase != prev_phase:
            self.bus.emit(
                PhaseTransitionEvent(
                    from_phase=prev_phase,
                    to_phase=new_phase,
                    position=self.v.copy(),
                    timestamp=self._t,
                    cluster_id=self.cluster_id,
                    energy=state.energy,
                    fdr_slope=self._cached_fdr_slope,
                )
            )

        self._phase_hist.append((self._t, new_phase))
        self._energy_hist.append(state.energy)
        self._t += self.dt
        return self.v
