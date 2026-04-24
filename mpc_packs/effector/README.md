# effector

Passive commit-accounting subscriber. Carved from the Session-4
monolith as part of the Session-8 S2/S3/S4 cleanup.

## What it does

On every phase-C commit (`PhaseTransitionEvent.to_phase == Phase.C`),
the Effector emits an `EffectorEvent` summarising the cost of that
commit:

| Component | Source |
|---|---|
| `energy_at_c` | `PhaseTransitionEvent.energy` (populated by the engine at commit time) |
| `landauer_cost` | Σ `LandauerEvent.info_content · kT` accumulated for this cluster since last commit |
| `work_estimate` | `‖v_c − v_reset‖² · λ_avg`, where `v_reset` comes from the cluster's most recent `BudgetResetEvent` (or zero if none) |
| `total_cost` | sum of the three |

The Landauer accumulator is reset after each emission.

## RFC-001 §7 compliance

Pure measurement-layer component:

- Attaches to the bus via `.attach(bus)`.
- Holds no reference to any `Substrate`, `Engine`, or `Cluster`.
- Never calls any brain-side method.
- Never influences the energy landscape or phase classification.
- `λ_avg` is supplied by the caller via `register_cluster` — the
  Effector never reads a Substrate for stiffness.

## API

```python
from mpc_packs.effector import Effector, EffectorEvent

eff = Effector().attach(bus)
eff.register_cluster("main", lambda_avg=0.4)

# ... run substrate loop ...

events = eff.effector_events("main")  # list[EffectorEvent]
print(eff.report())
```

## Declared dependencies

- `numpy`
- `mpc_kernel.rfc001.events.{EventBus, PhaseTransitionEvent, LandauerEvent, BudgetResetEvent}`
- `mpc_kernel.rfc001.phase.Phase`

## Declared mutations

None. Measurement-layer only.

## Provenance

Verbatim port from `experiments/historical/mpc_session4.py`
(lines 158–295). The historical module now re-exports from this
pack so existing callers (maze experiment, `persistence_substrate`
pack) continue to work unchanged.
