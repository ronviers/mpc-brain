# persistence_substrate — transitional shim

**Transitional shim. Replace in S6 with a first-class pack when the kernel carve-out lands.**

Re-exports `PersistenceSubstrate`, `PersistenceCluster`, `Effector`,
`InstrumentedEngine`, and `EffectorEvent` from `mpc_session4` unchanged.
No new behaviour. No new mutations.

## Import guidance for 5b's maze experiment

```python
from mpc_packs.persistence_substrate.pack import (
    PersistenceCluster, Effector, InstrumentedEngine, EffectorEvent,
)
```

Note that `Effector` subscribes to `mpc_session4.PhaseTransitionEvent`
(the S4 shadow dataclass with `energy: float = 0.0`), **not** the
kernel one — this is why `PersistenceCluster` spawns `InstrumentedEngine`
instances that emit the S4 event type. See Session 5a handoff notes and
RFC-001-AMENDMENTS-B item 1 (deferred housekeeping).

## Declared dependencies

- `mpc_session4.PersistenceSubstrate`
- `mpc_session4.PersistenceCluster`
- `mpc_session4.Effector`
- `mpc_session4.InstrumentedEngine`
- `mpc_session4.EffectorEvent`

## Declared mutations

None (pure re-export).
