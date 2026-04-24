"""persistence_substrate pack — AMEND-006 persistence + traversal memory.

Previously a transitional shim over mpc_session4; now a first-class
pack (Session 9 carve-out). Hosts:

  - PersistenceSubstrate — DecayingSubstrate with usage-modulated τ
    and an apply_outcome reinforcement hook.
  - PersistenceCluster  — LateralCluster backed by PersistenceSubstrate
    with traversal-frequency recording and active reinforcement on
    phase-C transitions.

Re-exports `Effector` / `EffectorEvent` from `mpc_packs.effector` and
`InstrumentedEngine` from `mpc_session4` for backward compatibility
with Session-5-era import patterns.
"""

from mpc_packs.effector import Effector, EffectorEvent

from .pack import InstrumentedEngine, PersistenceCluster, PersistenceSubstrate

__all__ = [
    "PersistenceSubstrate",
    "PersistenceCluster",
    "Effector",
    "EffectorEvent",
    "InstrumentedEngine",
]
