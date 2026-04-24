# persistence_substrate

First-class pack for AMEND-006: `PersistenceSubstrate` (usage-modulated
τ + active reinforcement) and `PersistenceCluster` (LateralCluster
backed by PersistenceSubstrate with traversal recording and
outcome-driven reinforcement on phase-C transitions).

**Status:** first-class pack (Session 9 carve-out). Previously a
transitional shim over `mpc_session4`.

## AMEND-006 in one page

**Usage modulation.** `PersistenceSubstrate` extends the
AMEND-001 decay law with a traversal-frequency term:

```
τ_ij = (tau_base / min(λ_i, λ_j)) · (1 + usage_coefficient · freq_ij)
freq_ij = _traversal[(i,j)] / max(_total_traversals, 1)
```

Edges traversed more often decay more slowly. Passive rehearsal.

**Active reinforcement.** On every phase-C transition,
`PersistenceCluster._on_phase_transition` calls
`PersistenceSubstrate.apply_outcome(pid)` where `pid` is the nearest-
well at commit time. For every pair `(pid, other)` currently in the
decay cache:

```
ε_ij ← min(ε_ij + outcome_coefficient · ε_original, ε_original)
```

Edges containing the committing well get boosted (capped at original).

## Contents re-exported for backward compatibility

```
PersistenceSubstrate   (first-class, this pack)
PersistenceCluster     (first-class, this pack)
Effector               ← mpc_packs.effector
EffectorEvent          ← mpc_packs.effector
InstrumentedEngine     ← mpc_session4 (retirement deferred)
```

## Declared dependencies

- `numpy`
- `mpc_kernel.rfc001.events.{EventBus, PhaseTransitionEvent}`
- `mpc_kernel.rfc001.phase.Phase`
- `mpc_packs.decaying_substrate.DecayingSubstrate` (PersistenceSubstrate parent)
- `mpc_packs.lateral_cluster.LateralCluster` (PersistenceCluster parent)
- `mpc_packs.observation_socket.ObservationSocket` (optional, via LateralCluster)
- `mpc_session4.InstrumentedEngine` (engine class used by PersistenceCluster)

## Declared mutations

- `PersistenceSubstrate`: `self._traversal`, `self._total_traversals`,
  `self._original_eps`, inherited `_decay_cache`/`_active_pairs`.
- `PersistenceCluster`: `self.sub`/`self.ops.sub` (replaced with
  PersistenceSubstrate), `self.engines` (replaced with
  InstrumentedEngines), `self._prev_pids`, bus subscription to
  `PhaseTransitionEvent`.

## Provenance

Verbatim port from `experiments/historical/mpc_session4.py`
lines 270–515.
